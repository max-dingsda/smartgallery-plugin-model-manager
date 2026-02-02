# smartgallery-plugin-model-manager
# Configuration variables for the Model Manager plugin
# All other SmartGallery settings live in the core application

import os

# Base path where models are stored
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
