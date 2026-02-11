// smartgallery-plugin-model-manager
// Frontend logic for the Model Manager plugin
// All functions and variables are namespaced with mm_ to avoid conflicts

// ---------------------------------------------------------------------------
// 1. Notification (fallback if SmartGallery core doesn't provide showNotification)
// ---------------------------------------------------------------------------
function mm_showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('mm-notifications');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'mm-toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

// ---------------------------------------------------------------------------
// 2. Entry point — called by SmartGallery plugin loader menu button
// ---------------------------------------------------------------------------
function mm_openModelManager() {
    mm_loadModels();
}

// ---------------------------------------------------------------------------
// 3. Helpers
// ---------------------------------------------------------------------------
function mm_formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function mm_formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

function mm_formatModelPath(path) {
    if (!path) return '';
    return String(path).replace(/[\\\\/]/g, '/');
}

function mm_buildModelSearch(model, type, label) {
    const parts = [model.name, model.type || type, label, mm_formatModelPath(model.path), model.trigger, model.tags];
    return parts.filter(Boolean).join(' ').toLowerCase();
}

function mm_escapeAttr(value) {
    return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---------------------------------------------------------------------------
// 4. Search
// ---------------------------------------------------------------------------
function mm_getSearchInputs() {
    return document.querySelectorAll('#mm-search-input');
}

function mm_getSearchValue() {
    let value = '';
    mm_getSearchInputs().forEach(input => { if (input && input.value) value = input.value; });
    return value;
}

function mm_setSearchValue(value) {
    mm_getSearchInputs().forEach(input => { if (input) input.value = value; });
}

function mm_applySearch(rawQuery) {
    const query = (rawQuery || '').trim().toLowerCase();
    document.querySelectorAll('#mm-content tbody tr').forEach(row => {
        const haystack = row.dataset.search || '';
        row.style.display = !query || haystack.includes(query) ? '' : 'none';
    });
}

// ---------------------------------------------------------------------------
// 5. Load Models
// ---------------------------------------------------------------------------
async function mm_loadModels() {
    const loading = document.getElementById('mm-loading');
    const content = document.getElementById('mm-content');

    if (loading) loading.style.display = 'block';
    if (content) content.innerHTML = '';

    try {
        const response = await fetch('/plugins/model_manager/list');
        const data = await response.json();

        if (loading) loading.style.display = 'none';

        if (data.status === 'error') {
            // Show error message (e.g. missing dependencies)
            content.innerHTML = `
                <div style="padding: 40px; text-align: center;">
                    <div style="display: inline-block; text-align: left; background: rgba(220,53,69,0.1);
                                border: 1px solid #dc3545; border-radius: 12px; padding: 30px; max-width: 600px;">
                        <h3 style="color: #dc3545; margin: 0 0 15px 0;">⚠ Plugin Error</h3>
                        <p style="color: #e0e0e0; margin: 0 0 15px 0;">${data.message || 'An unknown error occurred.'}</p>
                        ${data.install_hint ? `
                            <p style="color: #e0e0e0; margin: 0 0 8px 0; font-weight: 600;">Install with:</p>
                            <pre style="background: rgba(0,0,0,0.3); padding: 12px 16px; border-radius: 8px;
                                        overflow-x: auto; margin: 0 0 15px 0; font-size: 0.9rem;
                                        color: #4a9eff;">${data.install_hint}</pre>
                            <p style="color: #888; font-size: 0.85rem; margin: 0;">
                                After installing, restart SmartGallery to activate the plugin.
                            </p>
                        ` : ''}
                    </div>
                </div>
            `;
        } else if (data.status === 'success' && data.models) {
            if (data.models.length === 0) {
                // No models found - show settings hint
                content.innerHTML = `
                    <div style="padding: 40px; text-align: center;">
                        <h3 style="color: var(--text-muted); margin-bottom: 20px;">No models found</h3>
                        <p style="color: var(--text-muted); margin-bottom: 20px;">
                            The models directory is empty or not configured.
                        </p>
                        <button onclick="mm_openSettings()" class="mm-btn" style="background: var(--primary-color); border-color: var(--primary-color); color: white;">
                            ⚙️ Configure Models Path
                        </button>
                    </div>
                `;
            } else {
                mm_renderModels(data.models);
            }
        }
    } catch (error) {
        console.error('Failed to load models:', error);
        if (loading) loading.style.display = 'none';
    }
}

// ---------------------------------------------------------------------------
// 6. Render Models
// ---------------------------------------------------------------------------
function mm_renderModels(models) {
    const content = document.getElementById('mm-content');
    if (!content) return;

    // Group by type
    const grouped = {};
    models.forEach(model => {
        if (!grouped[model.type]) grouped[model.type] = [];
        grouped[model.type].push(model);
    });

    const typeLabels = {
        'checkpoints': '🎨 Checkpoints',
        'diffusion_models': '⚡ Diffusion Models',
        'loras': '🎭 LoRAs',
        'embeddings': '📝 Embeddings'
    };

    content.innerHTML = Object.keys(grouped).sort().map(type => {
        const typeModels = grouped[type];
        const label = typeLabels[type] || type;

        // LoRAs: special columns (trigger + tags)
        if (type === 'loras') {
            return `
                <div class="mm-type-section">
                    <h3>${label} <span class="count">(${typeModels.length})</span></h3>
                    <table class="mm-table">
                        <thead><tr>
                            <th style="width:40px;"><input type="checkbox" class="mm-checkbox mm-select-all" data-type="${type}" style="cursor:pointer;"></th>
                            <th>Name</th>
                            <th>Trigger</th>
                            <th>Tags</th>
                            <th>Size</th>
                            <th>Path</th>
                        </tr></thead>
                        <tbody>
                            ${typeModels.map(model => `
                                <tr data-model-hash="${model.hash || ''}" data-model-id="${model.id}" data-search="${mm_escapeAttr(mm_buildModelSearch(model, type, label))}">
                                    <td><input type="checkbox" class="mm-checkbox mm-select-cb" data-model-hash="${model.hash || ''}" data-model-id="${model.id}"></td>
                                    <td>${model.name}</td>
                                    <td class="mm-trigger-cell" title="${model.trigger || ''}">${model.trigger || '-'}</td>
                                    <td class="mm-tags-cell" title="${model.tags || ''}">${model.tags || '-'}</td>
                                    <td>${mm_formatSize(model.size)}</td>
                                    <td class="mm-path-cell" title="${mm_formatModelPath(model.path)}">${mm_formatModelPath(model.path)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>`;
        }

        // Checkpoints, diffusion_models, embeddings: standard columns
        return `
            <div class="mm-type-section">
                <h3>${label} <span class="count">(${typeModels.length})</span></h3>
                <table class="mm-table">
                    <thead><tr>
                        <th style="width:40px;"><input type="checkbox" class="mm-checkbox mm-select-all" data-type="${type}" style="cursor:pointer;"></th>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Modified</th>
                        <th>Path</th>
                    </tr></thead>
                    <tbody>
                        ${typeModels.map(model => `
                            <tr data-model-hash="${model.hash || ''}" data-model-id="${model.id}" data-search="${mm_escapeAttr(mm_buildModelSearch(model, type, label))}">
                                <td><input type="checkbox" class="mm-checkbox mm-select-cb" data-model-hash="${model.hash || ''}" data-model-id="${model.id}"></td>
                                <td>${model.name}</td>
                                <td>${mm_formatSize(model.size)}</td>
                                <td>${mm_formatDate(model.mtime)}</td>
                                <td class="mm-path-cell" title="${mm_formatModelPath(model.path)}">${mm_formatModelPath(model.path)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
    }).join('');

    mm_setupSelectAll();
    mm_applySearch(mm_getSearchValue());
}

// ---------------------------------------------------------------------------
// 7. CivitAI Integration
// ---------------------------------------------------------------------------
let mm_selectedModels = [];
let mm_civitaiCancelled = false;
let mm_abortController = null;

function mm_updateSelection() {
    mm_selectedModels = [];
    document.querySelectorAll('.mm-select-cb:checked').forEach(cb => {
        // Only count visible (not filtered) rows
        const row = cb.closest('tr');
        if (row && row.style.display !== 'none') {
            mm_selectedModels.push({ hash: cb.dataset.modelHash, id: cb.dataset.modelId });
        }
    });

    const fetchBtn = document.getElementById('mm-civitai-btn');
    if (fetchBtn) {
        fetchBtn.style.display = mm_selectedModels.length > 0 ? 'inline-flex' : 'none';
        fetchBtn.textContent = `🔍 Fetch CivitAI Metadata (${mm_selectedModels.length})`;
    }
}

function mm_setupSelectAll() {
    document.querySelectorAll('.mm-select-all').forEach(selectAll => {
        selectAll.addEventListener('change', function() {
            const rows = this.closest('table').querySelectorAll('tbody tr');
            rows.forEach(row => {
                // Only toggle checkboxes in visible (not filtered) rows
                if (row.style.display !== 'none') {
                    const cb = row.querySelector('.mm-select-cb');
                    if (cb) cb.checked = this.checked;
                }
            });
            mm_updateSelection();
        });
    });

    document.querySelectorAll('.mm-select-cb').forEach(cb => {
        cb.addEventListener('change', mm_updateSelection);
    });
}

async function mm_fetchCivitAI() {
    if (mm_selectedModels.length === 0) return;

    mm_civitaiCancelled = false;
    mm_abortController = new AbortController();

    const overlay = document.getElementById('mm-civitai-overlay');
    const statusText = document.getElementById('mm-civitai-status');
    const progressBar = document.getElementById('mm-civitai-progress');
    const cancelBtn = document.getElementById('mm-civitai-cancel');

    overlay.style.display = 'flex';

    const total = mm_selectedModels.length;
    const successfulModels = [];
    const failedModels = [];

    // Cancel handler
    cancelBtn.onclick = function() {
        mm_civitaiCancelled = true;
        if (mm_abortController) mm_abortController.abort();
        overlay.style.display = 'none';
        mm_showNotification('CivitAI fetch cancelled', 'warning');
    };

    // PHASE 1: Calculate full SHA256 hashes (one by one for cancellation support)
    progressBar.style.width = '0%';

    let hashProcessed = 0;
    for (const model of mm_selectedModels) {
        if (mm_civitaiCancelled) return;

        hashProcessed++;
        statusText.textContent = `Calculating SHA256 hash: ${hashProcessed}/${total} models`;
        progressBar.style.width = (hashProcessed / total * 10).toFixed(0) + '%';

        try {
            const hashResponse = await fetch('/plugins/model_manager/calculate-full-hash', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ modelIds: [model.id] }),
                signal: mm_abortController.signal
            });

            if (mm_civitaiCancelled) return;

            const hashData = await hashResponse.json();

            if (hashData.status === 'success' && hashData.results.length > 0) {
                const result = hashData.results[0];
                if (result.status === 'success') {
                    model.hash = result.hash;
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error(`Hash error for ${model.id}:`, error.message);
        }
    }

    if (mm_civitaiCancelled) return;

    // PHASE 2: Fetch from CivitAI
    let processed = 0;
    progressBar.style.width = '10%';

    for (const model of mm_selectedModels) {
        if (mm_civitaiCancelled) {
            statusText.textContent = 'Cancelled by user';
            break;
        }

        if (!model.hash) {
            failedModels.push({ model, reason: 'Hash calculation failed' });
            processed++;
            continue;
        }

        statusText.textContent = `Fetching metadata: ${processed + 1}/${total} models`;

        try {
            const response = await fetch(`https://civitai.com/api/v1/model-versions/by-hash/${model.hash}`, {
                signal: mm_abortController.signal
            });

            if (response.ok) {
                const data = await response.json();

                let triggerWords = data.trainedWords || data.triggers || data.activationText || data.triggerWords || [];
                const triggerString = Array.isArray(triggerWords) ? triggerWords.join(', ') : (triggerWords || '');

                successfulModels.push({
                    modelId: model.id,
                    civitaiData: {
                        name: data.model?.name || '',
                        versionName: data.name || '',
                        description: data.description || '',
                        tags: triggerString,
                        thumbnailUrl: data.images?.[0]?.url || '',
                        civitaiModelId: data.modelId,
                        civitaiVersionId: data.id
                    }
                });
            } else {
                failedModels.push({ model, reason: `HTTP ${response.status}` });
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            failedModels.push({ model, reason: error.message });
        }

        processed++;
        progressBar.style.width = (10 + (processed / total * 90)).toFixed(0) + '%';
        statusText.textContent = `Fetching metadata: ${processed}/${total} models`;

        // Rate limiting — 200ms pause between requests
        await new Promise(resolve => setTimeout(resolve, 200));
    }

    if (mm_civitaiCancelled) return;

    // Finish
    setTimeout(function() {
        overlay.style.display = 'none';

        const message = `Successfully fetched ${successfulModels.length}/${total} models`;
        if (failedModels.length > 0) console.warn('Failed models:', failedModels);
        mm_showNotification(message, successfulModels.length === total ? 'success' : 'info');

        // Save to backend
        if (successfulModels.length > 0) {
            fetch('/plugins/model_manager/update-civitai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates: successfulModels })
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log(`Saved ${data.updated} models to database`);
                    mm_loadModels();
                }
            })
            .catch(err => console.error('Error saving to database:', err));
        } else {
            mm_loadModels();
        }
    }, 500);
}

// ---------------------------------------------------------------------------
// 9. Settings Management
// ---------------------------------------------------------------------------
async function mm_openSettings() {
    const overlay = document.getElementById('mm-settings-overlay');
    const pathInput = document.getElementById('mm-settings-path');

    // Reset suggestions from previous open
    const suggestionsContainer = document.getElementById('mm-path-suggestions');
    if (suggestionsContainer) suggestionsContainer.innerHTML = '';

    // Load current settings
    try {
        const response = await fetch('/plugins/model_manager/settings');
        const data = await response.json();
        if (data.status === 'success') {
            pathInput.value = data.settings.models_path || '';
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }

    overlay.style.display = 'flex';
}

async function mm_detectPaths() {
    const suggestionsContainer = document.getElementById('mm-path-suggestions');
    const detectBtn = document.getElementById('mm-detect-btn');

    detectBtn.disabled = true;
    detectBtn.textContent = '🔍 Searching...';
    suggestionsContainer.innerHTML = '';

    try {
        const detectResponse = await fetch('/plugins/model_manager/detect-paths');
        const detectData = await detectResponse.json();

        if (detectData.status === 'success' && detectData.paths.length > 0) {
            const currentPath = document.getElementById('mm-settings-path').value.trim();
            suggestionsContainer.innerHTML = detectData.paths.map(pathInfo => {
                const isActive = currentPath && pathInfo.path === currentPath;
                const statusIcon = isActive ? '✓' : '📁';
                const statusColor = isActive ? 'var(--primary-color)' : 'var(--text-muted)';
                const modelText = pathInfo.model_count > 0
                    ? `${pathInfo.model_count} models found`
                    : 'has model folders';

                return `
                    <div class="mm-path-suggestion" data-path="${pathInfo.path.replace(/"/g, '&quot;')}"
                         style="display: flex; align-items: center; gap: 10px; padding: 10px;
                                background: var(--glass-bg); border: 1px solid ${isActive ? 'var(--primary-color)' : 'var(--glass-border)'};
                                border-radius: 8px;">
                        <span class="mm-path-icon" style="font-size: 1.2rem; color: ${statusColor};">${statusIcon}</span>
                        <div style="flex: 1;">
                            <div style="font-weight: 600; color: var(--text-color);">${pathInfo.path}</div>
                            <div style="font-size: 0.85rem; color: var(--text-muted);">${modelText}</div>
                        </div>
                        <button
                            class="mm-btn"
                            style="background: var(--primary-color); border-color: var(--primary-color); color: white;"
                            onclick="mm_selectPath('${pathInfo.path.replace(/\\/g, '\\\\')}')"
                        >
                            Select
                        </button>
                    </div>
                `;
            }).join('');
        } else {
            suggestionsContainer.innerHTML = `
                <p style="color: var(--text-muted); font-size: 0.85rem; margin: 4px 0 0 0;">
                    No model directories found automatically. Please enter the path manually below.
                </p>
            `;
        }
    } catch (error) {
        console.error('Failed to detect paths:', error);
        suggestionsContainer.innerHTML = `
            <p style="color: var(--danger-color); font-size: 0.85rem; margin: 4px 0 0 0;">
                Detection failed: ${error.message}
            </p>
        `;
    }

    detectBtn.disabled = false;
    detectBtn.textContent = '🔍 Auto-detect model directories';
}

function mm_selectPath(path) {
    const pathInput = document.getElementById('mm-settings-path');
    pathInput.value = path;

    // Update visual indicators: checkmark only on selected path
    document.querySelectorAll('.mm-path-suggestion').forEach(el => {
        const icon = el.querySelector('.mm-path-icon');
        const isSelected = el.dataset.path === path;
        if (icon) {
            icon.textContent = isSelected ? '✓' : '📁';
            icon.style.color = isSelected ? 'var(--primary-color)' : 'var(--text-muted)';
        }
        el.style.borderColor = isSelected ? 'var(--primary-color)' : 'var(--glass-border)';
    });
}

async function mm_saveSettings() {
    const pathInput = document.getElementById('mm-settings-path');
    const path = pathInput.value.trim();

    if (!path) {
        mm_showNotification('Please enter a models directory path', 'error');
        return;
    }

    try {
        const response = await fetch('/plugins/model_manager/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ models_path: path })
        });

        const data = await response.json();

        if (data.status === 'success') {
            mm_showNotification('Settings saved! Reloading models...', 'success');
            document.getElementById('mm-settings-overlay').style.display = 'none';
            mm_loadModels();
        } else {
            mm_showNotification(data.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        mm_showNotification('Error saving settings: ' + error.message, 'error');
    }
}

function mm_closeSettings() {
    document.getElementById('mm-settings-overlay').style.display = 'none';
}

// ---------------------------------------------------------------------------
// 8. Wiring — runs once on page load
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    // Refresh button
    const refreshBtn = document.getElementById('mm-refresh-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', mm_loadModels);

    // CivitAI button
    const civitaiBtn = document.getElementById('mm-civitai-btn');
    if (civitaiBtn) civitaiBtn.addEventListener('click', mm_fetchCivitAI);

    // Settings button
    const settingsBtn = document.getElementById('mm-settings-btn');
    if (settingsBtn) settingsBtn.addEventListener('click', mm_openSettings);

    // Settings modal handlers
    const settingsSaveBtn = document.getElementById('mm-settings-save');
    const settingsCancelBtn = document.getElementById('mm-settings-cancel');
    const detectBtn = document.getElementById('mm-detect-btn');
    if (settingsSaveBtn) settingsSaveBtn.addEventListener('click', mm_saveSettings);
    if (settingsCancelBtn) settingsCancelBtn.addEventListener('click', mm_closeSettings);
    if (detectBtn) detectBtn.addEventListener('click', mm_detectPaths);

    // Search input
    const searchInput = document.getElementById('mm-search-input');
    if (searchInput) {
        // Restore saved query
        const saved = localStorage.getItem('mm_searchQuery') || '';
        mm_setSearchValue(saved);

        searchInput.addEventListener('input', () => {
            localStorage.setItem('mm_searchQuery', searchInput.value);
            mm_applySearch(searchInput.value);
        });
    }

    // Search clear button
    const clearBtn = document.getElementById('mm-search-clear');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            mm_setSearchValue('');
            localStorage.removeItem('mm_searchQuery');
            mm_applySearch('');
            if (searchInput) searchInput.focus();
        });
    }

    // Initial load
    mm_loadModels();
});
