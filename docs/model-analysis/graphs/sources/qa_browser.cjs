const {chromium}=require('C:/Users/wine10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const path=require('path');
(async()=>{
 const root=path.dirname(__dirname);const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1760,height:1120},deviceScaleFactor:1});let errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.join(root,'operator-graphs.html').replaceAll('\\','/'));console.log(JSON.stringify({errors,title:await page.title(),panels:await page.locator('.panel').count()}));if(errors.length){await browser.close();throw new Error(errors.join('\n'))}await page.waitForSelector('#panel-sim svg');let checks=[];
 for(let i=0;i<10;i++){
  await page.locator('#models button').nth(i).click();
  let x=await page.evaluate(()=>({name:document.querySelector('#models .active').textContent,svgs:document.querySelectorAll('#graphs svg').length,nodes:[...document.querySelectorAll('.panel')].map(p=>p.querySelectorAll('.node').length),text:document.querySelector('#note').textContent}));
  if(x.svgs!==3||x.nodes.some(n=>n<50))throw new Error('Missing graph '+JSON.stringify(x));checks.push(x);
 }
 await page.locator('#models button').nth(1).click();await page.locator('#search').fill('q_norm');if(await page.locator('.node.match').count()<1)throw new Error('Search did not highlight');
 await page.locator('#search').fill('');await page.locator('#panel-sim .node').filter({has:page.locator('title', {hasText:/^n\d+$/})}).first().dispatchEvent('click');if(!(await page.locator('#detail').textContent()).includes('outputs'))throw new Error('Node detail missing: '+await page.locator('#detail').textContent());
 await page.locator('#panel-sim [data-act=plus]').click();if(await page.locator('#zoom-sim').textContent()!=='125%')throw new Error('Zoom failed');await page.locator('#panel-sim [data-act=minus]').click();
 await page.locator('#phase').selectOption('decode');if(!(await page.locator('#decodewarn').textContent()).includes('prefill'))throw new Error('Decode boundary warning missing');await page.locator('#phase').selectOption('manual');
 await page.screenshot({path:path.join(root,'preview.png'),fullPage:false});
 await page.locator('#models button').nth(9).click();await page.screenshot({path:path.join(root,'preview-falcon.png'),fullPage:false});
 let result={errors,checks,search:true,node_inspector:true,zoom:true,decode_scope_warning:true};fs.writeFileSync(path.join(root,'qa-browser.json'),JSON.stringify(result,null,2));await browser.close();if(errors.length)throw new Error(errors.join('\n'));console.log(JSON.stringify({variants:checks.length,errors,qa:'pass'}));
})().catch(e=>{console.error(e);process.exit(1)});
