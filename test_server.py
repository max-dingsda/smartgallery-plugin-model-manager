#!/usr/bin/env python
"""
Test server for smartgallery-plugin-model-manager.
Simulates the SmartGallery plugin loader for local testing.

Usage:
    pip install flask requests
    python test_server.py

Then open: http://127.0.0.1:5001/plugins/model_manager/list
"""

import sys
import os
import types
import importlib.util
from flask import Flask

# ---------------------------------------------------------------------------
# SETUP: Register this directory as an importable package.
# Required because backend.py uses relative imports (from .config import ...).
# ---------------------------------------------------------------------------
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_NAME = "model_manager"

# 1. Create and register the package
package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [PLUGIN_DIR]
package.__package__ = PACKAGE_NAME
package.__file__ = os.path.join(PLUGIN_DIR, "__init__.py")
sys.modules[PACKAGE_NAME] = package

# 2. Load config as submodule
spec_config = importlib.util.spec_from_file_location(
    f"{PACKAGE_NAME}.config",
    os.path.join(PLUGIN_DIR, "config.py")
)
config_mod = importlib.util.module_from_spec(spec_config)
sys.modules[f"{PACKAGE_NAME}.config"] = config_mod
spec_config.loader.exec_module(config_mod)

# 3. Load backend as submodule
spec_backend = importlib.util.spec_from_file_location(
    f"{PACKAGE_NAME}.backend",
    os.path.join(PLUGIN_DIR, "backend.py")
)
backend_mod = importlib.util.module_from_spec(spec_backend)
sys.modules[f"{PACKAGE_NAME}.backend"] = backend_mod
spec_backend.loader.exec_module(backend_mod)

# 4. Execute __init__.py in the package context
spec_init = importlib.util.spec_from_file_location(
    PACKAGE_NAME,
    os.path.join(PLUGIN_DIR, "__init__.py")
)
spec_init.loader.exec_module(package)

# ---------------------------------------------------------------------------
# TEST DATABASE (local, not the real gallery_cache.sqlite)
# ---------------------------------------------------------------------------
TEST_DB = os.path.join(PLUGIN_DIR, "test_gallery.sqlite")

# ---------------------------------------------------------------------------
# FLASK TEST APP — simulates what SmartGallery core plugin loader does
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['MM_DATABASE_FILE'] = TEST_DB

# Call setup_plugin exactly like the core would
plugin_data = package.setup_plugin(app)
app.register_blueprint(plugin_data['blueprint'], url_prefix='/plugins/model_manager')

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  Model Manager Plugin — Test Server")
    print("=" * 60)
    print(f"  Database : {TEST_DB}")
    print(f"  Plugin   : {plugin_data['name']}")
    print()
    print("  Endpoints:")
    print("    GET   /plugins/model_manager/list")
    print("    POST  /plugins/model_manager/scan")
    print("    POST  /plugins/model_manager/update-civitai")
    print("    POST  /plugins/model_manager/calculate-full-hash")
    print()
    print("  Quick test:")
    print("    http://127.0.0.1:5001/plugins/model_manager/list")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5001, debug=True)
