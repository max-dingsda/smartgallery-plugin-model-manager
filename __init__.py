# smartgallery-plugin-model-manager
# Plugin entry point — registers Blueprint, initializes database table

import os
import sqlite3
import importlib
from flask import Blueprint

# Map pip package names to their import names
REQUIRED_PACKAGES = {
    'requests': 'requests',
    'safetensors': 'safetensors',
}


def _check_dependencies():
    """Check that all required packages are installed.
    Returns a list of missing pip package names (empty if all OK)."""
    missing = []
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)
    return missing

def _init_database(app):
    """Create mm_models and mm_settings tables if they don't exist."""
    db_path = app.config.get('MM_DATABASE_FILE', './gallery_cache.sqlite')
    conn = sqlite3.connect(db_path, timeout=60)

    # Models table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mm_models (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            size INTEGER NOT NULL,
            hash TEXT,
            mtime INTEGER NOT NULL,
            scanned_at INTEGER NOT NULL,
            trigger TEXT,
            tags TEXT
        )
    ''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mm_models_type ON mm_models(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mm_models_mtime ON mm_models(mtime)")

    # Settings table (key-value store)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mm_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def setup_plugin(app):
    """
    Plugin entry point — called by SmartGallery core plugin loader.
    Registers the blueprint and returns metadata for frontend injection.
    """
    plugin_dir = os.path.dirname(__file__)
    missing = _check_dependencies()

    if missing:
        # Log warning to terminal
        req_file = os.path.join(plugin_dir, 'requirements.txt')
        pkg_list = ', '.join(missing)
        print(f"   ⚠️ Model Manager: missing packages: {pkg_list}")
        print(f"   ⚠️ Install with: pip install -r \"{req_file}\"")
        print(f"   ⚠️ If you are using a virtual environment, make sure it is activated before running.")

        # Build a self-contained error page (no JS needed).
        # The host wraps this in a modal — when the user clicks the plugin
        # button the modal opens and shows this error directly.
        error_html = f'''
        <style>
          .mm-dep-error {{ padding: 40px; text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #e0e0e0; }}
          .mm-dep-error-box {{ display: inline-block; text-align: left;
            background: rgba(220,53,69,0.1); border: 1px solid #dc3545;
            border-radius: 12px; padding: 30px; max-width: 600px; }}
          .mm-dep-error-box h3 {{ color: #dc3545; margin: 0 0 15px 0; }}
          .mm-dep-error-box p {{ margin: 0 0 10px 0; }}
          .mm-dep-error-box code {{ background: rgba(255,255,255,0.1);
            padding: 4px 10px; border-radius: 4px;
            font-size: 1rem; font-weight: 600; }}
          .mm-dep-error-box pre {{ background: rgba(0,0,0,0.3);
            padding: 12px 16px; border-radius: 8px; overflow-x: auto;
            margin: 0 0 15px 0; font-size: 0.9rem; color: #4a9eff; }}
        </style>
        <div class="mm-dep-error">
          <div class="mm-dep-error-box">
            <h3>⚠ Missing Dependencies</h3>
            <p>The Model Manager plugin requires packages that are not installed:</p>
            <p><code>{pkg_list}</code></p>
            <p style="font-weight: 600; margin-top: 20px;">Install with:</p>
            <pre>pip install -r "{req_file}"</pre>
            <p style="color: #888; font-size: 0.85rem;">
              If you are using a virtual environment (venv, conda, etc.),
              make sure it is activated before running the install command.
            </p>
            <p style="color: #888; font-size: 0.85rem;">
              After installing, restart SmartGallery to activate the plugin.
            </p>
          </div>
        </div>
        '''

        return {
            "blueprint": Blueprint('model_manager', __name__),
            "name": "Model Manager",
            "description": "Manage AI model catalogs — Checkpoints, LoRAs, Embeddings",
            "frontend": {
                "menu_button": '<button onclick="mm_openModelManager()">🧠 Models</button>',
                "js_files": [],
                "html_panel": error_html
            }
        }

    bp = Blueprint(
        'model_manager',
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    # Register API routes from backend.py
    from . import backend
    backend.register_routes(bp)

    # Initialize database table on first load
    _init_database(app)

    # --- FRONTEND INJECTION LOGIC ---
    # We read the template file directly from the disk to avoid
    # Blueprint registration context issues during startup.
    html_content = ""
    template_path = os.path.join(plugin_dir, 'templates', 'model_manager.html')

    try:
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            print(f"   ⚠️ Model Manager: Template not found at {template_path}")
    except Exception as e:
        print(f"   ⚠️ Model Manager: Error reading template file: {e}")

    return {
        "blueprint": bp,
        "name": "Model Manager",
        "description": "Manage AI model catalogs — Checkpoints, LoRAs, Embeddings",
        "frontend": {
            "menu_button": '<button onclick="mm_openModelManager()">🧠 Models</button>',
            "js_files": ["model_manager.js"],
            "html_panel": html_content
        }
    }