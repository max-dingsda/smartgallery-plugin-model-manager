# smartgallery-plugin-model-manager
# Configuration variables for the Model Manager plugin
# All other SmartGallery settings live in the core application

import os

# Will be dynamically resolved via get_models_path()
BASE_MODELS_PATH = os.environ.get('BASE_MODELS_PATH', './models')

# Scan these folders for models
MODEL_SUBFOLDERS = {
    "checkpoints": ["checkpoints"],
    "diffusion_models": ["diffusion_models"],
    "loras": ["loras"],
    "embeddings": ["embeddings"],
}

# Supported model file extensions
MODEL_EXTENSIONS = {".ckpt", ".safetensors", ".pt", ".bin"}

def get_models_path(db_path='./gallery_cache.sqlite'):
    """
    Get models path with priority:
    1. Environment variable BASE_MODELS_PATH
    2. Database setting 'models_path'
    3. Fallback to './models'
    """
    import sqlite3

    # Priority 1: Environment variable
    env_path = os.environ.get('BASE_MODELS_PATH')
    if env_path:
        return env_path

    # Priority 2: Database setting
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        cursor = conn.execute("SELECT value FROM mm_settings WHERE key = 'models_path'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass  # Table might not exist yet

    # Priority 3: Fallback
    return './models'
