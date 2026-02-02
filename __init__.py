# smartgallery-plugin-model-manager
# Plugin entry point — registers Blueprint, initializes database table

import sqlite3
from flask import Blueprint


def _init_database(app):
    """Create mm_models table and indexes if they don't exist."""
    db_path = app.config.get('MM_DATABASE_FILE', './gallery_cache.sqlite')
    conn = sqlite3.connect(db_path, timeout=60)
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
    conn.commit()
    conn.close()


def setup_plugin(app):
    """Plugin entry point — called by SmartGallery core plugin loader."""
    bp = Blueprint(
        'model_manager',
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    # Register API routes
    from . import backend
    backend.register_routes(bp)

    # Initialize database table on first load
    _init_database(app)

    return {
        "blueprint": bp,
        "name": "Model Manager",
        "description": "Manage AI model catalogs — Checkpoints, LoRAs, Embeddings",
        "frontend": {
            "menu_button": '<button onclick="mm_openModelManager()">🧠 Models</button>',
            "js_files": ["model_manager.js"]
        }
    }
