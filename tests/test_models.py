"""
End-to-end tests for Model Manager plugin.

Two page fixtures are available:
  - page:        navigates to /plugins/model_manager/ (models may or may not exist)
  - loaded_page: same, but with dummy models configured and rendered

Tests are grouped by functionality and ordered so that independent checks
(startup, settings UI) run before tests that rely on loaded models.
"""
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# 1. Startup & Page Load
# ---------------------------------------------------------------------------

def test_page_loads(page: Page):
    """Page renders with correct title and toolbar — no crash."""
    expect(page).to_have_title("Model Manager")
    expect(page.locator(".mm-toolbar")).to_be_visible()
    expect(page.locator("h2")).to_contain_text("Model Manager")


def test_initial_state_is_valid(page: Page):
    """After loading, the page shows either 'No models found' or model tables."""
    expect(page.locator("#mm-loading")).not_to_be_visible(timeout=10000)

    has_models = page.locator(".mm-type-section").count() > 0
    has_empty_hint = page.locator("text=No models found").count() > 0

    assert has_models or has_empty_hint, (
        "Page shows neither models nor empty-state hint"
    )


# ---------------------------------------------------------------------------
# 2. Settings Modal
# ---------------------------------------------------------------------------

def test_settings_button_opens_modal(page: Page):
    """Clicking the settings button opens the settings overlay."""
    page.locator("#mm-settings-btn").click()

    overlay = page.locator("#mm-settings-overlay")
    expect(overlay).to_be_visible()
    expect(page.locator("#mm-settings-path")).to_be_visible()
    expect(page.locator("#mm-settings-save")).to_be_visible()
    expect(page.locator("#mm-settings-cancel")).to_be_visible()


def test_settings_cancel_closes_modal(page: Page):
    """Cancel button closes the settings overlay."""
    page.locator("#mm-settings-btn").click()
    expect(page.locator("#mm-settings-overlay")).to_be_visible()

    page.locator("#mm-settings-cancel").click()
    expect(page.locator("#mm-settings-overlay")).not_to_be_visible()


def test_configure_path_loads_models(page: Page, test_server, models_dir):
    """Setting a valid path via the modal triggers a scan and shows tables."""
    page.locator("#mm-settings-btn").click()
    page.locator("#mm-settings-path").fill(models_dir)
    page.locator("#mm-settings-save").click()

    # After save the JS calls mm_loadModels() automatically
    page.wait_for_selector(".mm-type-section", timeout=15000)

    sections = page.locator(".mm-type-section")
    assert sections.count() > 0, "No model type sections after configuring path"


# ---------------------------------------------------------------------------
# 3. Model Display  (uses loaded_page — models are guaranteed)
# ---------------------------------------------------------------------------

def test_all_model_types_displayed(loaded_page: Page):
    """All 4 model type sections are rendered."""
    sections = loaded_page.locator(".mm-type-section")
    assert sections.count() == 4, f"Expected 4 sections, got {sections.count()}"

    for label in ["Checkpoints", "Diffusion Models", "LoRAs", "Embeddings"]:
        heading = loaded_page.locator(f".mm-type-section h3:has-text('{label}')")
        expect(heading).to_be_visible()


def test_correct_model_count(loaded_page: Page):
    """Total number of table rows matches the 6 dummy files."""
    rows = loaded_page.locator(".mm-table tbody tr")
    assert rows.count() == 6, f"Expected 6 rows, got {rows.count()}"


def test_model_names_displayed(loaded_page: Page):
    """All dummy model names appear in the rendered tables."""
    text = loaded_page.locator("#mm-content").inner_text()

    expected = [
        "test-checkpoint-v1", "test-checkpoint-v2",
        "test-lora-style", "test-lora-character",
        "test-embedding", "test-diffusion",
    ]
    for name in expected:
        assert name in text, f"Model '{name}' not found on page"


# ---------------------------------------------------------------------------
# 4. Search
# ---------------------------------------------------------------------------

def test_search_filters_models(loaded_page: Page):
    """Typing a query hides non-matching rows."""
    loaded_page.locator("#mm-search-input").fill("checkpoint")
    loaded_page.wait_for_timeout(300)

    visible = loaded_page.locator(".mm-table tbody tr:visible")
    assert visible.count() == 2, f"Expected 2 visible rows, got {visible.count()}"


def test_search_clear_restores_all(loaded_page: Page):
    """Clearing the search shows all 6 rows again."""
    loaded_page.locator("#mm-search-input").fill("checkpoint")
    loaded_page.wait_for_timeout(300)

    loaded_page.locator("#mm-search-clear").click()
    loaded_page.wait_for_timeout(300)

    rows = loaded_page.locator(".mm-table tbody tr")
    assert rows.count() == 6, f"Expected 6 rows after clear, got {rows.count()}"


def test_search_no_results(loaded_page: Page):
    """Searching for a non-existent term hides all rows."""
    loaded_page.locator("#mm-search-input").fill("nonexistent_xyz_999")
    loaded_page.wait_for_timeout(300)

    visible = loaded_page.locator(".mm-table tbody tr:visible")
    assert visible.count() == 0, f"Expected 0 visible rows, got {visible.count()}"


# ---------------------------------------------------------------------------
# 5. Selection & CivitAI Button
# ---------------------------------------------------------------------------

def test_checkbox_shows_civitai_button(loaded_page: Page):
    """Checking a model checkbox makes the CivitAI button appear with count."""
    civitai_btn = loaded_page.locator("#mm-civitai-btn")
    expect(civitai_btn).not_to_be_visible()

    # Check first model
    loaded_page.locator(".mm-select-cb").first.check()
    expect(civitai_btn).to_be_visible()
    expect(civitai_btn).to_contain_text("(1)")

    # Check second model
    loaded_page.locator(".mm-select-cb").nth(1).check()
    expect(civitai_btn).to_contain_text("(2)")

    # Uncheck both — button hides
    loaded_page.locator(".mm-select-cb").first.uncheck()
    loaded_page.locator(".mm-select-cb").nth(1).uncheck()
    expect(civitai_btn).not_to_be_visible()


def test_select_all_in_section(loaded_page: Page):
    """Select-all checkbox toggles all checkboxes in its table section."""
    select_all = loaded_page.locator(".mm-select-all").first
    civitai_btn = loaded_page.locator("#mm-civitai-btn")

    select_all.check()
    expect(civitai_btn).to_be_visible()

    select_all.uncheck()
    expect(civitai_btn).not_to_be_visible()


# ---------------------------------------------------------------------------
# 6. Refresh
# ---------------------------------------------------------------------------

def test_refresh_reloads_models(loaded_page: Page):
    """Refresh button reloads the model list and tables reappear."""
    loaded_page.locator("#mm-refresh-btn").click()

    # Wait for tables to (re-)appear
    loaded_page.wait_for_selector(".mm-type-section", timeout=10000)

    rows = loaded_page.locator(".mm-table tbody tr")
    assert rows.count() == 6, f"Expected 6 rows after refresh, got {rows.count()}"
