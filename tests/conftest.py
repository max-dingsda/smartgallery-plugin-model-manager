"""
Pytest configuration for Playwright tests.
Manages test server lifecycle and browser fixtures.
"""
import subprocess
import time
import requests
import pytest
from pathlib import Path


# Path to test_server.py
SERVER_SCRIPT = Path(__file__).parent.parent / "test_server.py"
SERVER_URL = "http://127.0.0.1:5001"


@pytest.fixture(scope="session")
def test_server():
    """Start test_server.py before tests, stop after all tests complete."""
    print("\n🚀 Starting test server...")

    # Start server as subprocess
    process = subprocess.Popen(
        ["python", str(SERVER_SCRIPT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server to be ready (max 10 seconds)
    max_wait = 10
    for i in range(max_wait):
        try:
            response = requests.get(f"{SERVER_URL}/plugins/model_manager/list", timeout=1)
            if response.status_code == 200:
                print(f"✅ Test server ready after {i+1}s")
                break
        except requests.exceptions.RequestException:
            time.sleep(1)
    else:
        process.kill()
        raise RuntimeError(f"Test server failed to start within {max_wait}s")

    yield SERVER_URL

    # Cleanup: stop server
    print("\n🛑 Stopping test server...")
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="function")
def page(test_server, page):
    """
    Playwright page fixture that navigates to the Model Manager before each test.
    Depends on test_server fixture to ensure server is running.
    """
    page.goto(f"{test_server}/plugins/model_manager/")
    return page
