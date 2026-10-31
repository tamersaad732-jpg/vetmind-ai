// VetMind AI - Global Client-Side Live Autocomplete / Typeahead Engine
(function() {
    let debounceTimer;

    function setupLiveAutocomplete(input) {
        if (!input || input.getAttribute('data-vet-autocomplete')) return;
        input.setAttribute('data-vet-autocomplete', 'true');
        input.setAttribute('autocomplete', 'off');

        const parent = input.parentElement;
        if (window.getComputedStyle(parent).position === 'static') {
            parent.style.position = 'relative';
        }

        const drop = document.createElement('div');
        drop.className = 'vet-suggest-dropdown';
        drop.style.cssText = 'position: absolute; top: calc(100% + 4px); right: 0; left: 0; z-index: 99999; background: #ffffff; border: 2px solid #047857; border-radius: 10px; max-height: 320px; overflow-y: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.18); display: none; text-align: right; font-family: inherit;';
        parent.appendChild(drop);

        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();
            if (query.length < 1) {
                drop.style.display = 'none';
                drop.innerHTML = '';
                return;
            }

            debounceTimer = setTimeout(() => {
                fetch('/api/drugs/autocomplete?q=' + encodeURIComponent(query))
                    .then(r => r.json())
                    .then(data => {
                        drop.innerHTML = '';
                        if (!data || data.length === 0) {
                            drop.style.display = 'none';
                            return;
                        }

                        data.forEach(item => {
                            const row = document.createElement('div');
                            row.style.cssText = 'padding: 10px 14px; border-bottom: 1px solid #f1f5f9; cursor: pointer; transition: background 0.15s; background: #fff;';
                            row.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <strong style="color: #047857; font-size: 0.95rem;">💊 ${item.trade_name}</strong>
                                    <span style="background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 800;">${item.category}</span>
                                </div>
                                <div style="font-size: 0.82rem; color: #475569; margin-top: 3px;">
                                    🧬 <strong>المادة الفعالة:</strong> ${item.active_ingredient}
                                </div>
                                <div style="font-size: 0.78rem; color: #059669; margin-top: 2px; font-weight: 700;">
                                    (${item.function})
                                </div>
                            `;
                            row.addEventListener('mouseenter', () => row.style.background = '#f0fdf4');
                            row.addEventListener('mouseleave', () => row.style.background = '#ffffff');
                            row.addEventListener('click', () => {
                                input.value = item.trade_name;
                                drop.style.display = 'none';
                                if (input.form && input.getAttribute('data-submit-on-select') === 'true') {
                                    input.form.submit();
                                }
                            });
                            drop.appendChild(row);
                        });
                        drop.style.display = 'block';
                    })
                    .catch(err => console.error(err));
            }, 180);
        });

        document.addEventListener('click', function(e) {
            if (!parent.contains(e.target)) {
                drop.style.display = 'none';
            }
        });
    }

    function initAll() {
        const targets = document.querySelectorAll('input[name="search"], input[name="q"], input[name="trade_name"], input[name="drug_query"], input[name="drug_input"], .vet-autocomplete');
        targets.forEach(setupLiveAutocomplete);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
})();
