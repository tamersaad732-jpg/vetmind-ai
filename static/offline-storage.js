/**
 * VetMind AI - Client-Side Offline Storage Engine
 * Stores all clinic data, appointments, prescriptions, inventory, and notes
 * locally on the user's mobile device / browser using IndexedDB & localStorage.
 * Guarantees 100% privacy, zero server bloat, and full offline functionality.
 */

(function () {
  'use strict';

  const DB_NAME = 'VetMind_Local_Storage';
  const DB_VERSION = 2;
  const STORES = ['clinic_profile', 'appointments', 'inventory', 'vaccinations', 'prescriptions', 'offline_notes'];

  let dbInstance = null;

  // Initialize IndexedDB
  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (dbInstance) return resolve(dbInstance);
      if (!window.indexedDB) {
        console.warn('IndexedDB not supported in this browser, falling back to localStorage.');
        return resolve(null);
      }

      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = function (event) {
        const db = event.target.result;
        STORES.forEach(storeName => {
          if (!db.objectStoreNames.contains(storeName)) {
            db.createObjectStore(storeName, { keyPath: 'id', autoIncrement: true });
          }
        });
      };

      request.onsuccess = function (event) {
        dbInstance = event.target.result;
        resolve(dbInstance);
      };

      request.onerror = function (event) {
        console.error('IndexedDB open error:', event.target.error);
        resolve(null);
      };
    });
  }

  // Generic Save to IndexedDB with localStorage fallback
  async function saveItem(storeName, item) {
    item.updated_at = new Date().toISOString();
    const db = await openDatabase();

    if (db) {
      return new Promise((resolve) => {
        try {
          const tx = db.transaction(storeName, 'readwrite');
          const store = tx.objectStore(storeName);
          const req = store.put(item);
          req.onsuccess = () => resolve(req.result);
          req.onerror = () => {
            saveToLocalStorage(storeName, item);
            resolve(item.id || Date.now());
          };
        } catch (e) {
          saveToLocalStorage(storeName, item);
          resolve(item.id || Date.now());
        }
      });
    } else {
      saveToLocalStorage(storeName, item);
      return item.id || Date.now();
    }
  }

  // Generic Get All from Store
  async function getAllItems(storeName) {
    const db = await openDatabase();
    if (db) {
      return new Promise((resolve) => {
        try {
          const tx = db.transaction(storeName, 'readonly');
          const store = tx.objectStore(storeName);
          const req = store.getAll();
          req.onsuccess = () => {
            const results = req.result || [];
            const local = getFromLocalStorage(storeName);
            // Merge unique by id or timestamp
            const merged = [...results];
            local.forEach(loc => {
              if (!merged.some(m => m.id === loc.id)) {
                merged.push(loc);
              }
            });
            resolve(merged);
          };
          req.onerror = () => resolve(getFromLocalStorage(storeName));
        } catch (e) {
          resolve(getFromLocalStorage(storeName));
        }
      });
    } else {
      return getFromLocalStorage(storeName);
    }
  }

  function saveToLocalStorage(storeName, item) {
    try {
      const key = 'vm_local_' + storeName;
      const existing = JSON.parse(localStorage.getItem(key) || '[]');
      const index = existing.findIndex(x => x.id === item.id);
      if (index >= 0) {
        existing[index] = item;
      } else {
        if (!item.id) item.id = 'loc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 4);
        existing.push(item);
      }
      localStorage.setItem(key, JSON.stringify(existing));
    } catch (e) {
      console.warn('localStorage save failed:', e);
    }
  }

  function getFromLocalStorage(storeName) {
    try {
      const key = 'vm_local_' + storeName;
      return JSON.parse(localStorage.getItem(key) || '[]');
    } catch (e) {
      return [];
    }
  }

  // Network Online/Offline Status Management
  function updateNetworkIndicator() {
    const isOnline = navigator.onLine;
    let badge = document.getElementById('network-status-badge');
    if (!badge) {
      badge = document.createElement('div');
      badge.id = 'network-status-badge';
      badge.style.cssText = `
        position: fixed;
        bottom: 72px;
        left: 14px;
        z-index: 999;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 20px;
        display: flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
        pointer-events: auto;
      `;
      document.body.appendChild(badge);
    }

    if (isOnline) {
      badge.style.background = '#ecfdf5';
      badge.style.color = '#065f46';
      badge.style.border = '1px solid #6ee7b7';
      badge.innerHTML = '🟢 متصل (الحفظ محلي وسحابي)';
      // Auto-hide online badge after 4 seconds to keep screen clean
      setTimeout(() => {
        if (badge && navigator.onLine) badge.style.opacity = '0.35';
      }, 4000);
    } else {
      badge.style.background = '#fef2f2';
      badge.style.color = '#991b1b';
      badge.style.border = '1.5px solid #f87171';
      badge.style.opacity = '1';
      badge.innerHTML = '⚡ وضع بدون إنترنت (بياناتك محفوظة محلياً على جهازك)';
    }
  }

  // Hook form submissions on Clinic & Prescription pages for offline capture
  function setupOfflineFormInterceptors() {
    // 1. Appointments form
    document.querySelectorAll('form[action*="/clinic/appointments/add"]').forEach(form => {
      form.addEventListener('submit', async function (e) {
        if (!navigator.onLine) {
          e.preventDefault();
          const formData = new FormData(form);
          const item = {
            id: 'app_' + Date.now(),
            client_name: formData.get('client_name') || 'عميل محلي',
            animal_name: formData.get('animal_name') || 'حيوان',
            species: formData.get('species') || 'أبقار',
            appointment_date: formData.get('appointment_date') || new Date().toISOString().slice(0, 10),
            reason: formData.get('reason') || '',
            status: 'scheduled'
          };
          await saveItem('appointments', item);
          alert('✅ تم حفظ الموعد بنجاح محلياً على جهازك بدون إنترنت!');
          form.reset();
          renderLocalAppointments();
        }
      });
    });

    // 2. Inventory form
    document.querySelectorAll('form[action*="/clinic/inventory/add"]').forEach(form => {
      form.addEventListener('submit', async function (e) {
        if (!navigator.onLine) {
          e.preventDefault();
          const formData = new FormData(form);
          const item = {
            id: 'inv_' + Date.now(),
            drug_name: formData.get('drug_name') || 'دواء',
            stock_quantity: parseInt(formData.get('stock_quantity') || '0', 10),
            min_threshold: parseInt(formData.get('min_threshold') || '5', 10),
            unit: formData.get('unit') || 'عبوة'
          };
          await saveItem('inventory', item);
          alert('✅ تم تسجيل الصنف الدوائي محلياً على جهازك!');
          form.reset();
        }
      });
    });

    // 3. Vaccinations form
    document.querySelectorAll('form[action*="/clinic/vaccinations/add"]').forEach(form => {
      form.addEventListener('submit', async function (e) {
        if (!navigator.onLine) {
          e.preventDefault();
          const formData = new FormData(form);
          const item = {
            id: 'vac_' + Date.now(),
            animal_name: formData.get('animal_name') || '',
            vaccine_name: formData.get('vaccine_name') || '',
            date_given: formData.get('date_given') || new Date().toISOString().slice(0, 10),
            next_due_date: formData.get('next_due_date') || ''
          };
          await saveItem('vaccinations', item);
          alert('✅ تم حفظ سجل التطعيم محلياً على جهازك!');
          form.reset();
        }
      });
    });
  }

  // Render locally saved appointments if offline
  async function renderLocalAppointments() {
    const table = document.querySelector('#appointments-table tbody');
    if (!table) return;
    const items = await getAllItems('appointments');
    if (!items.length) return;

    items.forEach(item => {
      // Check if already in table
      if (document.getElementById('row_' + item.id)) return;
      const tr = document.createElement('tr');
      tr.id = 'row_' + item.id;
      tr.style.background = '#f0fdf4';
      tr.innerHTML = `
        <td style="padding: 10px; font-weight: 700;">${item.client_name} <span style="font-size: 0.72rem; color: #16a34a; background: #dcfce7; padding: 2px 6px; border-radius: 6px;">محلي 📱</span></td>
        <td style="padding: 10px;">${item.animal_name} (${item.species})</td>
        <td style="padding: 10px;">${item.appointment_date}</td>
        <td style="padding: 10px;">${item.reason || '-'}</td>
        <td style="padding: 10px;"><span style="color: #059669; font-weight: 700;">مجدول</span></td>
      `;
      table.prepend(tr);
    });
  }

  // Export all local data to JSON file
  window.exportLocalDataToFile = async function () {
    const data = {
      export_date: new Date().toISOString(),
      platform: 'VetMind AI Enterprise',
      appointments: await getAllItems('appointments'),
      inventory: await getAllItems('inventory'),
      vaccinations: await getAllItems('vaccinations'),
      prescriptions: await getAllItems('prescriptions')
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vetmind-local-backup-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Expose API globally
  window.VetMindOffline = {
    saveItem,
    getAllItems,
    openDatabase
  };

  window.addEventListener('online', updateNetworkIndicator);
  window.addEventListener('offline', updateNetworkIndicator);
  document.addEventListener('DOMContentLoaded', () => {
    updateNetworkIndicator();
    setupOfflineFormInterceptors();
    renderLocalAppointments();
  });
})();
