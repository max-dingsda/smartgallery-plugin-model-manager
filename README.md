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
