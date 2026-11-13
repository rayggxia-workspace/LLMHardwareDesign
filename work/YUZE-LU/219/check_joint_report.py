"""Lightweight local browser QA; all compiler/RTL/model runs remain Slurm jobs."""
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
checks = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    for width in (1100, 360):
        page = browser.new_page(viewport={'width': width, 'height': 850})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto((a.results / 'report.html').resolve().as_uri())
        assert page.locator('#model-graph rect').count() == 37
        page.select_option('#layer', 'layer 0')
        assert page.locator('#model-graph rect').count() > 50
        assert '范围内依赖' in page.locator('#graph-count').inner_text()
        page.screenshot(path=str(out / f'model-{width}.png'))
        page.click('#native-tab')
        assert page.locator('#native-panel').is_visible()
        assert page.locator('#native-graph rect').count() == 8
        assert page.locator('#timeline rect').count() == 4
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(out / f'native-{width}.png'))
        assert not errors, errors
        checks.append({'width': width, 'passed': True, 'js_errors': errors,
                       'scope': 'layer selector, plan tab, SVG content and outer-page overflow; diagrams pan horizontally on small screens'})
        page.close()
    browser.close()
(out / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks))
