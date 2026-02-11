#!/usr/bin/env python
"""
Standalone test server for smartgallery-plugin-model-manager.

Usage:
  python standalone_test_server.py

Environment:
  BASE_MODELS_PATH  Optional override for model directory
  MM_DATABASE_FILE  Optional override for sqlite DB path
  PORT              Optional port (default: 5001)
"""

import os
import sys
import types
import importlib.util
from flask import Flask, redirect

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_NAME = "model_manager"


def _ensure_package():
    if PACKAGE_NAME in sys.modules:
        return sys.modules[PACKAGE_NAME]
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [PLUGIN_DIR]
    package.__package__ = PACKAGE_NAME
    package.__file__ = os.path.join(PLUGIN_DIR, "__init__.py")
    sys.modules[PACKAGE_NAME] = package
    return package


def _load_submodule(name, filename):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.{name}",
        os.path.join(PLUGIN_DIR, filename),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PACKAGE_NAME}.{name}"] = module
    spec.loader.exec_module(module)
    return module


package = _ensure_package()
_load_submodule("config", "config.py")
_load_submodule("backend", "backend.py")

spec_init = importlib.util.spec_from_file_location(
    PACKAGE_NAME,
    os.path.join(PLUGIN_DIR, "__init__.py"),
)
spec_init.loader.exec_module(package)

app = Flask(__name__)
app.config["MM_DATABASE_FILE"] = os.environ.get(
    "MM_DATABASE_FILE",
    os.path.join(PLUGIN_DIR, "standalone_test_gallery.sqlite"),
)

plugin_data = package.setup_plugin(app)
app.register_blueprint(plugin_data["blueprint"], url_prefix="/plugins/model_manager")


@app.route("/")
def root():
    return redirect("/plugins/model_manager/")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    print("=" * 60)
    print("  Model Manager Plugin — Standalone Test Server")
    print("=" * 60)
    print(f"  Database : {app.config['MM_DATABASE_FILE']}")
    print(f"  Plugin   : {plugin_data.get('name', 'Model Manager')}")
    print(f"  URL      : http://127.0.0.1:{port}/plugins/model_manager/")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
