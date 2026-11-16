"""Local browser QA only; algorithm, model and RTL evaluation remain Slurm."""
import argparse
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('playwright_path', type=Path)
p.add_argument('results', type=Path)
a = p.parse_args()
sys.path.insert(0, str(a.playwright_path))
from playwright.sync_api import sync_playwright

out = a.results / 'browser'
out.mkdir(exist_ok=True)
(out / '.gitignore').write_text('*.png\n')
checks = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    for width in (1100, 360):
        page = browser.new_page(viewport={'width': width, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto((a.results / 'report.html').resolve().as_uri())
        assert page.locator('#dag rect').count() == 3
        assert page.locator('#comparison tr').count() == 5
        assert page.locator('#native-time rect').count() == 3
        for option in page.locator('#case option').all_text_contents():
            page.select_option('#case', option)
            assert page.locator('#timeline rect').count() > 4
            assert '16KiB' in page.locator('#case-summary').inner_text()
        assert '2277' in page.locator('#full').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        page.screenshot(path=str(out / f'report-{width}.png'))
        checks.append({'width': width, 'passed': True, 'case_selector': 5, 'native_tasks': 3,
                       'js_errors': errors, 'scope': 'page/selector/actual SVG counts/outer overflow'})
        page.close()
    browser.close()
(out / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks))
