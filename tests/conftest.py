"""
Pytest configuration for Playwright E2E tests.
Manages test server lifecycle, dummy model files, and browser fixtures.
"""
import subprocess
import sys
import time
import os
import tempfile
import shutil
import requests
import pytest
from pathlib import Path


SERVER_SCRIPT = Path(__file__).parent.parent / "test_server.py"
SERVER_URL = "http://127.0.0.1:5001"
API_BASE = f"{SERVER_URL}/plugins/model_manager"


@pytest.fixture(scope="session")
def models_dir():
    """Create a temporary directory with dummy model files for scanning."""
    tmpdir = tempfile.mkdtemp(prefix="mm_test_models_")

    for subdir in ["checkpoints", "loras", "embeddings", "diffusion_models"]:
        os.makedirs(os.path.join(tmpdir, subdir))

    dummy_files = [
        "checkpoints/test-checkpoint-v1.safetensors",
        "checkpoints/test-checkpoint-v2.safetensors",
        "loras/test-lora-style.safetensors",
        "loras/test-lora-character.safetensors",
        "embeddings/test-embedding.safetensors",
        "diffusion_models/test-diffusion.safetensors",
    ]
    for f in dummy_files:
        Path(os.path.join(tmpdir, f)).touch()

    yield tmpdir

    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_server(models_dir):
    """Start test_server.py before tests, stop after all tests complete."""
    # Don't set BASE_MODELS_PATH — tests configure path via /settings API
    env = os.environ.copy()
    env.pop("BASE_MODELS_PATH", None)
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )

    max_wait = 15
    for i in range(max_wait):
        try:
            response = requests.get(f"{API_BASE}/list", timeout=2)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            time.sleep(1)
    else:
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError(f"Test server failed to start within {max_wait}s")

    yield SERVER_URL

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture(scope="function")
def page(test_server, page):
    """Playwright page — navigates to Model Manager before each test."""
    page.goto(f"{test_server}/plugins/model_manager/")
    return page


@pytest.fixture(scope="function")
def loaded_page(test_server, models_dir, page):
    """
    Page with models directory configured and models loaded.
    Configures the path via API, reloads, and waits for tables to render.
    """
    requests.post(
        f"{test_server}/plugins/model_manager/settings",
        json={"models_path": models_dir},
        timeout=5
    )
    page.reload()
    page.wait_for_selector(".mm-type-section", timeout=15000)
    return page
