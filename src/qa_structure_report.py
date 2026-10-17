"""Optional browser QA. Requires Playwright and its Chromium browser."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
report = ROOT / 'reports/structure_reversal.html'
errors = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1300}, device_scale_factor=1)
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto(report.as_uri(), wait_until='load')
    assert page.locator('h1').inner_text() == '允许横盘等待：结构反转参考测试'
    tables = page.locator('table')
    assert tables.count() == 5
    counts = [tables.nth(i).locator('tbody tr').count() for i in range(5)]
    # This report's shared HTML table helper does not require explicit tbody markup.
    assert counts[:4] == [10, 10, 10, 20], counts
    assert '71.05%' in tables.nth(0).inner_text()
    assert '41.67%' in tables.nth(1).inner_text()
    page.screenshot(path=str(ROOT / 'reports/qa_structure_overview.png'))
    tables.nth(0).screenshot(path=str(ROOT / 'reports/qa_structure_daily.png'))
    desktop_overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
    assert not desktop_overflow
    page.set_viewport_size({'width': 390, 'height': 844})
    mobile_overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
    assert not mobile_overflow
    assert not errors
    browser.close()

checks = dict(status='PASS', table_count=5, body_row_counts=counts,
              desktop_width=1440, mobile_width=390,
              document_horizontal_overflow=False, browser_errors=errors,
              screenshot_files=['reports/qa_structure_overview.png', 'reports/qa_structure_daily.png'])
(ROOT / 'results/structure_reversal/report_checks.json').write_text(
    json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(checks, ensure_ascii=False))
