"""
End-to-end tests for Model Manager plugin.
Tests UI functionality using Playwright.
"""
import re
from playwright.sync_api import Page, expect


def test_page_loads(page: Page):
    """Test that the Model Manager page loads successfully."""
    # Check title
    expect(page).to_have_title("Model Manager")

    # Check toolbar header exists
    header = page.locator("h2:has-text('Model Manager')")
    expect(header).to_be_visible()


def test_models_list_appears(page: Page):
    """Test that models are loaded and displayed."""
    # Wait for loading to disappear
    loading = page.locator("#mm-loading")
    expect(loading).not_to_be_visible(timeout=10000)

    # Check that at least one model type section exists
    sections = page.locator(".mm-type-section")
    expect(sections).not_to_have_count(0)

    # Check that tables have rows
    rows = page.locator(".mm-table tbody tr")
    expect(rows).not_to_have_count(0)


def test_search_filters_models(page: Page):
    """Test that search input filters the model list."""
    # Wait for models to load
    expect(page.locator("#mm-loading")).not_to_be_visible(timeout=10000)

    # Count total rows before search
    all_rows = page.locator(".mm-table tbody tr")
    total_count = all_rows.count()
    assert total_count > 0, "No models loaded"

    # Type into search field (search for "flux")
    search_input = page.locator("#mm-search-input")
    search_input.fill("flux")

    # Wait a bit for filtering
    page.wait_for_timeout(300)

    # Count visible rows after search
    visible_rows = page.locator(".mm-table tbody tr:visible")
    filtered_count = visible_rows.count()

    # Filtered count should be less than total (assuming "flux" doesn't match everything)
    assert filtered_count < total_count, "Search didn't filter anything"

    # Clear search
    clear_btn = page.locator("#mm-search-clear")
    clear_btn.click()

    # All rows should be visible again
    page.wait_for_timeout(300)
    assert all_rows.count() == total_count


def test_checkbox_selection(page: Page):
    """Test that checkboxes can be selected and CivitAI button appears."""
    # Wait for models to load
    expect(page.locator("#mm-loading")).not_to_be_visible(timeout=10000)

    # CivitAI button should be hidden initially
    civitai_btn = page.locator("#mm-civitai-btn")
    expect(civitai_btn).not_to_be_visible()

    # Select first model checkbox
    first_checkbox = page.locator(".mm-select-cb").first
    first_checkbox.check()

    # CivitAI button should now be visible
    expect(civitai_btn).to_be_visible()
    expect(civitai_btn).to_contain_text("Fetch CivitAI Metadata (1)")

    # Select second model
    second_checkbox = page.locator(".mm-select-cb").nth(1)
    second_checkbox.check()

    # Button text should update
    expect(civitai_btn).to_contain_text("Fetch CivitAI Metadata (2)")

    # Uncheck both
    first_checkbox.uncheck()
    second_checkbox.uncheck()

    # Button should hide again
    expect(civitai_btn).not_to_be_visible()


def test_select_all_checkbox(page: Page):
    """Test that 'Select All' checkbox works."""
    # Wait for models to load
    expect(page.locator("#mm-loading")).not_to_be_visible(timeout=10000)

    # Find first section's "Select All" checkbox
    select_all = page.locator(".mm-select-all").first
    select_all.check()

    # All checkboxes in that section should be checked
    # (We can't easily count them all, but CivitAI button should appear)
    civitai_btn = page.locator("#mm-civitai-btn")
    expect(civitai_btn).to_be_visible()

    # Uncheck select-all
    select_all.uncheck()

    # CivitAI button should hide
    expect(civitai_btn).not_to_be_visible()


def test_refresh_button(page: Page):
    """Test that refresh button reloads the model list."""
    # Wait for initial load
    expect(page.locator("#mm-loading")).not_to_be_visible(timeout=10000)

    # Click refresh button
    refresh_btn = page.locator("#mm-refresh-btn")
    refresh_btn.click()

    # Loading indicator should appear briefly
    loading = page.locator("#mm-loading")
    expect(loading).to_be_visible()

    # Then disappear again
    expect(loading).not_to_be_visible(timeout=10000)

    # Models should still be there
    sections = page.locator(".mm-type-section")
    expect(sections).not_to_have_count(0)
