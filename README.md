# SmartGallery Plugin: Model Manager

A plugin for [SmartGallery](https://github.com/biagiomaf/smart-comfyui-gallery) to manage AI model catalogs (Checkpoints, LoRAs, Embeddings, Diffusion Models).

## 🚧 Development Status

**Current Version:** v0.1.0

![Tests](https://github.com/max-dingsda/smartgallery-plugin-model-manager/actions/workflows/test.yml/badge.svg)

**Status:** Plugin code complete, awaiting SmartGallery core plugin loader implementation

This plugin is ready for integration but cannot be installed yet. SmartGallery's plugin architecture is currently being developed by [@biagiomaf](https://github.com/biagiomaf). Once the core plugin loader is merged, this plugin will be installable.

## ✨ Features

- **Model Scanning:** Automatically scans ComfyUI model directories
- **Multi-Type Support:** Checkpoints, LoRAs, Embeddings, Diffusion Models
- **Fast Indexing:** Uses head+tail hash for quick model identification
- **CivitAI Integration:** Fetch metadata (trigger words, tags) directly from CivitAI
- **Search & Filter:** Real-time search across all model properties
- **Batch Operations:** Select multiple models for CivitAI metadata fetching

## 📦 Installation

**Not yet available** – requires SmartGallery plugin loader (in development).

Once available:
1. Place this repository in `SmartGallery/plugins/model_manager/`
2. SmartGallery will auto-detect and load the plugin
3. Access via the "🧠 Models" button in the SmartGallery UI

## 🧪 Local Testing

You can test the plugin standalone before SmartGallery integration:

```bash
# Install dependencies
pip install flask requests

# Set your ComfyUI models path (optional, defaults to ./models)
set BASE_MODELS_PATH=F:/AI/ComfyUI/models

# Run test server
python test_server.py

# Open in browser
http://127.0.0.1:5001/plugins/model_manager/
```

The test server simulates SmartGallery's plugin loader and creates a local `test_gallery.sqlite` database.

## 🧪 Automated Tests

End-to-end tests using [Playwright](https://playwright.dev/python/) verify the plugin in a real browser against a live test server.

```bash
pip install -r requirements-dev.txt
playwright install chromium
pytest tests/ -v
```

| # | Test | Description |
|---|------|-------------|
| 1 | `test_page_loads` | Page renders with correct title and toolbar |
| 2 | `test_initial_state_is_valid` | Shows "No models found" or model tables after load |
| 3 | `test_settings_button_opens_modal` | Settings button opens the settings overlay |
| 4 | `test_settings_cancel_closes_modal` | Cancel button closes the settings overlay |
| 5 | `test_configure_path_loads_models` | Setting a valid path triggers scan and shows tables |
| 6 | `test_all_model_types_displayed` | All 4 model type sections are rendered |
| 7 | `test_correct_model_count` | Total row count matches the 6 dummy model files |
| 8 | `test_model_names_displayed` | All dummy model names appear in the tables |
| 9 | `test_search_filters_models` | Search hides non-matching rows |
| 10 | `test_search_clear_restores_all` | Clearing search restores all rows |
| 11 | `test_search_no_results` | Non-existent search term hides all rows |
| 12 | `test_checkbox_shows_civitai_button` | Checking a model shows the CivitAI button with count |
| 13 | `test_select_all_in_section` | Select-all toggles all checkboxes in a section |
| 14 | `test_refresh_reloads_models` | Refresh button reloads and re-renders all models |

## 🏗️ Architecture

- **`config.py`**: Configuration variables (model paths, file extensions)
- **`backend.py`**: Flask Blueprint with 4 API routes
  - `/scan` – Trigger model directory scan
  - `/list` – Get all indexed models
  - `/update-civitai` – Update CivitAI metadata for models
  - `/calculate-full-hash` – Calculate full SHA256 for CivitAI lookup
- **`__init__.py`**: Plugin entry point, database initialization
- **`templates/model_manager.html`**: Standalone frontend page
- **`static/js/model_manager.js`**: UI logic (namespaced with `mm_`)

All database operations use the `mm_models` table to avoid conflicts with SmartGallery core.

## 🔗 Related Projects

- **SmartGallery** by @biagiomaf: [smart-comfyui-gallery](https://github.com/biagiomaf/smart-comfyui-gallery)

## 📝 License

MIT License – same as SmartGallery core

## 🤝 Contributing

This plugin is part of the SmartGallery ecosystem. For core plugin loader development, see the main [SmartGallery repository](https://github.com/biagiomaf/smart-comfyui-gallery).
