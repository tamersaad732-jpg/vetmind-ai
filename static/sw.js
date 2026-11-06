/**
 * VetMind AI - Service Worker
 * Enables full offline functionality, asset caching, and offline-first performance.
 */

const CACHE_NAME = 'vetmind-offline-v10';

// Core routes and assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/symptom-checker',
  '/vision-detect',
  '/rx-prescription',
  '/dashboard',
  '/pharmacy',
  '/references',
  '/contraindications',
  '/interactions',
  '/clinic',
  '/tools',
  '/clinic/prayer-times',
  '/about',
  '/terms',
  '/static/manifest.json',
  '/static/favicon.svg',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/apple-touch-icon.png',
  '/static/offline-storage.js',
  '/favicon.ico'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.all(
        PRECACHE_ASSETS.map((url) => {
          return cache.add(url).catch((err) => {
            console.warn('Pre-cache skip for:', url, err.message);
          });
        })
      );
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Skip Groq external API or non-http
  if (!url.protocol.startsWith('http')) return;
  if (url.origin.includes('groq.com') || url.origin.includes('api.openai.com')) return;

  // 1. Navigation requests (HTML pages)
  if (event.request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        // Immediate cache check if offline
        if (!navigator.onLine) {
          const cached = await caches.match(event.request, { ignoreSearch: true })
                      || await caches.match(url.pathname, { ignoreSearch: true })
                      || await caches.match('/');
          if (cached) return cached;
        }

        try {
          // Attempt network with 2.5s timeout
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 2500);
          const networkResponse = await fetch(event.request, { signal: controller.signal });
          clearTimeout(timeoutId);

          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache).catch(() => {});
            });
            return networkResponse;
          }
        } catch (netErr) {
          // Network failed or timed out -> Fallback to Cache
        }

        const cachedFallback = await caches.match(event.request, { ignoreSearch: true })
                            || await caches.match(url.pathname, { ignoreSearch: true })
                            || await caches.match('/')
                            || await caches.match('/vision-detect');
        if (cachedFallback) return cachedFallback;

        return new Response(
          `<!DOCTYPE html>
          <html lang="ar" dir="rtl">
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VetMind AI - وضع العمل بدون إنترنت</title>
            <style>
              body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 40px 20px; line-height: 1.6; }
              .card { background: #1e293b; border: 1px solid #334155; border-radius: 16px; max-width: 500px; margin: 30px auto; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
              h1 { color: #38bdf8; font-size: 1.6rem; margin-bottom: 10px; }
              p { color: #94a3b8; font-size: 0.95rem; }
              .btn { display: inline-block; background: #0d9488; color: white; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: 700; margin: 6px; }
              .btn-outline { background: transparent; border: 1px solid #475569; color: #cbd5e1; }
            </style>
          </head>
          <body>
            <div class="card">
              <div style="font-size: 3.5rem; margin-bottom: 10px;">⚡</div>
              <h1>أنت تعمل الآن في وضع بدون إنترنت (Offline)</h1>
              <p>جميع بياناتك وسجلات عيادتك مخزنة محلياً بأمان على هاتفك / جهازك. يمكنك متابعة استخدام الأدوات المحفوظة.</p>
              <div style="margin-top: 24px;">
                <a href="/" class="btn">🏠 الرئيسية</a>
                <a href="/symptom-checker" class="btn btn-outline">🩺 المشخص السريري</a>
                <a href="/vision-detect" class="btn btn-outline">🔬 فاحص الصور</a>
                <a href="/rx-prescription" class="btn btn-outline">📋 الروشتة</a>
                <a href="/pharmacy" class="btn btn-outline">💊 الصيدلية</a>
                <a href="/clinic" class="btn btn-outline">🏥 العيادة</a>
              </div>
            </div>
          </body>
          </html>`,
          { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
        );
      })()
    );
    return;
  }

  // 2. Static Assets (CSS, JS, Images, Icons) - Cache-first with background revalidation
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cachedResponse) => {
      if (cachedResponse) {
        if (navigator.onLine) {
          fetch(event.request).then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, networkResponse).catch(() => {});
              });
            }
          }).catch(() => {});
        }
        return cachedResponse;
      }

      return fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const resClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, resClone).catch(() => {});
          });
        }
        return networkResponse;
      }).catch(async () => {
        const pathFallback = await caches.match(url.pathname, { ignoreSearch: true });
        if (pathFallback) return pathFallback;
        return new Response('Asset not available offline', { status: 503, statusText: 'Offline' });
      });
    })
  );
});
