/* Render local Mermaid sources; no project RTL, git or remote job operations. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('playwright');
const args = process.argv.slice(2);
function option(name, fallback) {
  const i = args.indexOf(name);
  return i < 0 ? fallback : args[i + 1];
}
const mermaidPath = option('--mermaid', process.env.MERMAID_JS);
const browserPath = option('--browser', process.env.DIAGRAM_BROWSER);
const screenshotDir = option('--screenshots', null);
if (!mermaidPath || !fs.existsSync(mermaidPath)) {
  throw new Error('Supply --mermaid with local Mermaid 11.4.1 dist/mermaid.min.js');
}
const base = __dirname;
(async () => {
  const browser = await chromium.launch({ headless: true, ...(browserPath ? { executablePath: browserPath } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1100 }, deviceScaleFactor: 1 });
    await page.setContent('<html><head><meta charset="utf-8"></head><body style="margin:20px;background:white"></body></html>');
    await page.addScriptTag({ path: path.resolve(mermaidPath) });
    await page.evaluate(() => mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'base', htmlLabels: false,
      fontFamily: 'Microsoft YaHei, Noto Sans CJK SC, sans-serif',
      flowchart: { htmlLabels: false, useMaxWidth: false, curve: 'basis', nodeSpacing: 24, rankSpacing: 34, wrappingWidth: 280 },
      themeVariables: { fontSize: '17px', lineColor: '#496780', primaryColor: '#f0f5fb', primaryTextColor: '#142c43' }
    }));
    fs.mkdirSync(path.join(base, 'assets'), { recursive: true });
    if (screenshotDir) fs.mkdirSync(screenshotDir, { recursive: true });
    const receipts = [];
    const sources = fs.readdirSync(path.join(base, 'diagrams')).filter(x => x.endsWith('.mmd')).sort();
    for (let i = 0; i < sources.length; i++) {
      const name = sources[i];
      const src = fs.readFileSync(path.join(base, 'diagrams', name), 'utf8');
      const rendered = await page.evaluate(async ({ src, i }) => {
        await mermaid.parse(src);
        const { svg } = await mermaid.render('flow' + i, src);
        return svg;
      }, { src, i });
      const svgName = name.replace(/\.mmd$/, '.svg');
      fs.writeFileSync(path.join(base, 'assets', svgName), rendered + '\n', 'utf8');
      await page.evaluate(svg => { document.body.innerHTML = svg; }, rendered);
      await page.evaluate(() => document.fonts.ready);
      const measured = await page.locator('svg').evaluate(el => {
        const vb = el.viewBox.baseVal;
        const text = [...el.querySelectorAll('text')];
        const nodeLabels = [...el.querySelectorAll('g.node .label')];
        return { width: vb.width, height: vb.height,
          text_elements: text.filter(t => t.textContent.trim()).length,
          empty_labels: nodeLabels.filter(t => !t.textContent.trim()).length,
          foreign_objects: el.querySelectorAll('foreignObject').length };
      });
      if (!measured.width || !measured.height || !measured.text_elements || measured.empty_labels || measured.foreign_objects) {
        throw new Error('Invalid SVG/labels: ' + name);
      }
      if (screenshotDir) await page.locator('svg').screenshot({ path: path.join(screenshotDir, name.replace(/\.mmd$/, '.png')) });
      receipts.push({ source: 'diagrams/' + name, svg: 'assets/' + svgName, ...measured });
      console.log('PASS ' + name + ' ' + Math.round(measured.width) + 'x' + Math.round(measured.height));
    }
    if (screenshotDir) fs.writeFileSync(path.join(screenshotDir, 'render-receipt.json'), JSON.stringify({
      mermaid_version: '11.4.1', mermaid_sha256: crypto.createHash('sha256').update(fs.readFileSync(mermaidPath)).digest('hex'),
      node: process.version, playwright: require('playwright/package.json').version,
      browser: browser.version(), diagrams: receipts
    }, null, 2) + '\n');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
