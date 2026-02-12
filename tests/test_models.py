"""
End-to-end tests for Model Manager plugin.

Two page fixtures are available:
  - page:        navigates to /plugins/model_manager/ (models may or may not exist)
  - loaded_page: same, but with dummy models configured and rendered

Tests are grouped by functionality and ordered so that independent checks
(startup, settings UI) run before tests that rely on loaded models.
"""
from playwright.sync_api import Page, expect
import requests


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

    # After save the JS calls mm_loadModels() automatically.
    # Wait for rendered table rows to avoid timing races with transient content updates.
    page.wait_for_selector(".mm-type-section", timeout=15000)
    visible_rows = page.locator(".mm-table tbody tr:visible")
    expect(visible_rows.first).to_be_visible(timeout=15000)
    assert visible_rows.count() > 0, "No visible model rows after configuring path"


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


def test_row_click_opens_model_details_overlay(loaded_page: Page):
    """Clicking a row (outside checkbox) opens model details overlay."""
    overlay = loaded_page.locator("#mm-model-overlay")
    expect(overlay).not_to_be_visible()

    first_name = loaded_page.locator(".mm-table tbody tr td").nth(1).inner_text()
    loaded_page.locator(".mm-table tbody tr td").nth(1).click()

    expect(overlay).to_be_visible()
    expect(loaded_page.locator("#mm-model-overlay-content")).to_contain_text(first_name)
    expect(loaded_page.locator("#mm-model-overlay-content")).not_to_contain_text("Hash")
    expect(loaded_page.locator("#mm-model-overlay-content")).to_contain_text("Copy SHA256")


def test_checkbox_click_does_not_open_model_details_overlay(loaded_page: Page):
    """Clicking a checkbox selects model but does not open details overlay."""
    overlay = loaded_page.locator("#mm-model-overlay")
    expect(overlay).not_to_be_visible()

    loaded_page.locator(".mm-select-cb").first.check()
    expect(overlay).not_to_be_visible()


def test_model_overlay_shows_na_defaults_and_disabled_copy_without_hash(loaded_page: Page):
    """Overlay always renders defined fields with n/a fallback and disabled copy when hash is missing."""
    loaded_page.locator(".mm-table tbody tr td").nth(1).click()
    expect(loaded_page.locator("#mm-model-overlay")).to_be_visible()

    content = loaded_page.locator("#mm-model-overlay-content")
    expect(content).to_contain_text("Base Model")
    expect(content).to_contain_text("Creator/Username")
    expect(content).to_contain_text("License")
    expect(content).to_contain_text("CivitAI")
    expect(content).to_contain_text("n/a")

    copy_btn = loaded_page.locator("#mm-copy-sha-btn")
    expect(copy_btn).to_be_disabled()
    expect(loaded_page.locator("#mm-copy-sha-status")).to_have_text("n/a")


def test_type_specific_overlay_sections(loaded_page: Page):
    """Checkpoints hide trigger/tags; LoRAs keep trigger/tags metadata."""
    checkpoints_first_name = loaded_page.locator(".mm-type-section:has(h3:has-text('Checkpoints')) tbody tr td").nth(1)
    checkpoints_first_name.click()
    checkpoint_content = loaded_page.locator("#mm-model-overlay-content")
    expect(checkpoint_content).to_contain_text("Checkpoint Metadata")
    expect(checkpoint_content).not_to_contain_text("Trigger")
    expect(checkpoint_content).not_to_contain_text("Tags")
    loaded_page.locator("#mm-model-overlay-close").click()

    lora_first_name = loaded_page.locator(".mm-type-section:has(h3:has-text('LoRAs')) tbody tr td").nth(1)
    lora_first_name.click()
    lora_content = loaded_page.locator("#mm-model-overlay-content")
    expect(lora_content).to_contain_text("LoRA Metadata")
    expect(lora_content).to_contain_text("Trigger")
    expect(lora_content).to_contain_text("Tags")


def test_diffusion_models_use_checkpoint_overlay_metadata(loaded_page: Page):
    """Diffusion models should be rendered with the same metadata section as checkpoints."""
    diffusion_first_name = loaded_page.locator(".mm-type-section:has(h3:has-text('Diffusion Models')) tbody tr td").nth(1)
    diffusion_first_name.click()
    diffusion_content = loaded_page.locator("#mm-model-overlay-content")
    expect(diffusion_content).to_contain_text("Checkpoint Metadata")
    expect(diffusion_content).not_to_contain_text("LoRA Metadata")
    expect(diffusion_content).not_to_contain_text("Trigger")
    expect(diffusion_content).not_to_contain_text("Tags")


def test_overlay_shows_source_badges(loaded_page: Page):
    """Overlay shows source badges for local and CivitAI-derived fields."""
    loaded_page.locator(".mm-table tbody tr td").nth(1).click()
    expect(loaded_page.locator("#mm-model-overlay")).to_be_visible()
    expect(loaded_page.locator("#mm-model-overlay-content .mm-source-badge.local").first).to_be_visible()


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


# ---------------------------------------------------------------------------
# 7. Metadata Priority (API-level, no external CivitAI calls)
# ---------------------------------------------------------------------------

def _configure_and_list_models(test_server: str, models_dir: str):
    requests.post(
        f"{test_server}/plugins/model_manager/settings",
        json={"models_path": models_dir},
        timeout=5
    ).raise_for_status()

    response = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10)
    response.raise_for_status()
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] > 0
    return data["models"]


def test_civitai_values_have_priority_for_effective_fields(test_server, models_dir):
    """Effective name/trigger/tags should prefer CivitAI values over local values."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "loras")
    model_id = target["id"]

    update_response = requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {
                        "name": "CivitAI Preferred Name",
                        "triggerWords": "alpha, beta",
                        "modelTags": "style, portrait",
                    },
                }
            ]
        },
        timeout=10,
    )
    update_response.raise_for_status()

    refreshed = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10).json()["models"]
    updated = next(m for m in refreshed if m["id"] == model_id)

    assert updated["name"] == "CivitAI Preferred Name"
    assert updated["trigger"] == "alpha, beta"
    assert updated["tags"] == "style, portrait"


def test_update_civitai_keeps_local_values_unchanged(test_server, models_dir):
    """Updating CivitAI fields must not overwrite *_local values."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "loras")
    model_id = target["id"]

    before_name_local = target.get("name_local")
    before_trigger_local = target.get("trigger_local")
    before_tags_local = target.get("tags_local")

    update_response = requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {
                        "name": "Other CivitAI Name",
                        "triggerWords": "gamma",
                        "modelTags": "cinematic",
                    },
                }
            ]
        },
        timeout=10,
    )
    update_response.raise_for_status()

    refreshed = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10).json()["models"]
    updated = next(m for m in refreshed if m["id"] == model_id)

    assert updated.get("name_local") == before_name_local
    assert updated.get("trigger_local") == before_trigger_local
    assert updated.get("tags_local") == before_tags_local


def test_force_rescan_preserves_civitai_values(test_server, models_dir):
    """A forced rescan should keep previously stored CivitAI values."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "loras")
    model_id = target["id"]

    requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {
                        "name": "Persistent CivitAI Name",
                        "triggerWords": "delta, epsilon",
                        "modelTags": "anime, detail",
                    },
                }
            ]
        },
        timeout=10,
    ).raise_for_status()

    requests.post(
        f"{test_server}/plugins/model_manager/scan",
        json={"force": True},
        timeout=15,
    ).raise_for_status()

    refreshed = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10).json()["models"]
    updated = next(m for m in refreshed if m["id"] == model_id)

    assert updated.get("name_civitai") == "Persistent CivitAI Name"
    assert updated.get("trigger_civitai") == "delta, epsilon"
    assert updated.get("tags_civitai") == "anime, detail"
    assert updated["name"] == "Persistent CivitAI Name"
    assert updated["trigger"] == "delta, epsilon"
    assert updated["tags"] == "anime, detail"


def test_type_is_stored_from_civitai_and_not_local_fallback(test_server, models_dir):
    """Type for details overlay should come from CivitAI and stay empty without API value."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "loras")
    model_id = target["id"]

    assert target.get("type_civitai") in (None, "")

    requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {
                        "name": "Type Test",
                        "modelType": "LORA",
                    },
                }
            ]
        },
        timeout=10,
    ).raise_for_status()

    refreshed = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10).json()["models"]
    updated = next(m for m in refreshed if m["id"] == model_id)
    assert updated.get("type_civitai") == "LORA"


def test_additional_civitai_fields_are_persisted(test_server, models_dir):
    """Base model, creator, license and CivitAI link should be stored from API data."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "checkpoints")
    model_id = target["id"]

    requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {
                        "name": "Checkpoint API Name",
                        "versionName": "Refiner v1.0",
                        "modelType": "Checkpoint",
                        "baseModel": "SDXL 1.0",
                        "creatorUsername": "demo_creator",
                        "license": "OpenRAIL",
                        "civitaiModelUrl": "https://civitai.com/models/12345?modelVersionId=67890",
                    },
                }
            ]
        },
        timeout=10,
    ).raise_for_status()

    refreshed = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10).json()["models"]
    updated = next(m for m in refreshed if m["id"] == model_id)

    assert updated.get("version_name") == "Refiner v1.0"
    assert updated.get("base_model") == "SDXL 1.0"
    assert updated.get("creator") == "demo_creator"
    assert updated.get("license") == "OpenRAIL"
    assert updated.get("civitai_model_url") == "https://civitai.com/models/12345?modelVersionId=67890"


def test_civitai_not_found_marks_model_as_checked(test_server, models_dir):
    """A not-found update should still mark the model as queried on CivitAI."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "embeddings")
    model_id = target["id"]

    requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {},
                    "civitaiNotFound": True,
                }
            ]
        },
        timeout=10,
    ).raise_for_status()

    refreshed = requests.get(f"{test_server}/plugins/model_manager/list", timeout=10).json()["models"]
    updated = next(m for m in refreshed if m["id"] == model_id)
    assert updated.get("civitai_checked_at") is not None


def test_table_name_shows_name_plus_version_when_available(page: Page, test_server, models_dir):
    """Overview table should display 'name - version' when version exists."""
    models = _configure_and_list_models(test_server, models_dir)
    target = next(m for m in models if m["type"] == "checkpoints")
    model_id = target["id"]

    requests.post(
        f"{test_server}/plugins/model_manager/update-civitai",
        json={
            "updates": [
                {
                    "modelId": model_id,
                    "civitaiData": {
                        "name": "SD XL",
                        "versionName": "Refiner 1.0",
                    },
                }
            ]
        },
        timeout=10,
    ).raise_for_status()

    page.goto(f"{test_server}/plugins/model_manager/")
    page.wait_for_selector(".mm-type-section", timeout=15000)
    expect(page.locator(".mm-table tbody tr td", has_text="SD XL - Refiner 1.0").first).to_be_visible()
