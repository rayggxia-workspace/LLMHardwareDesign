// Headless Edge QA in a new isolated profile; never touches a user's browser.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const [report,out]=process.argv.slice(2);
await fs.mkdir(out,{recursive:true});
const edge=process.env.EDGE_BINARY||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port=9346+Math.floor(Math.random()*1000);
const child=spawn(edge,['--headless=new','--disable-gpu','--no-first-run','--disable-extensions',`--remote-debugging-port=${port}`,`--user-data-dir=${path.resolve(out,'edge-profile')}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
let socket,command;
try {
 let targets;
 for(let i=0;i<100;i++){try{targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();break;}catch{await new Promise(r=>setTimeout(r,100));}}
 if(!targets)throw Error('New Edge debugger unavailable');
 socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
 let id=0;const pending=new Map(),errors=[];
 socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params);};
 const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}));});
 command=call;
 const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await call('Page.enable');await call('Runtime.enable');
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:pathToFileURL(path.resolve(report)).href});
 for(let i=0;i<300;i++){if(await evaluate('document.readyState==="complete" && !!document.querySelector("#count") && document.querySelector("#count").textContent.includes("24767")'))break;await new Promise(r=>setTimeout(r,100));}
 await evaluate('document.querySelectorAll("img").forEach(i=>i.loading="eager")');
 for(let i=0;i<200;i++){if(await evaluate('[...document.images].every(i=>i.complete && i.naturalWidth>0)'))break;await new Promise(r=>setTimeout(r,100));}
 const all=await evaluate('({title:document.title,count:document.querySelector("#count").textContent,images:[...document.images].map(i=>({src:i.getAttribute("src"),loaded:i.complete&&i.naturalWidth>0})),overflow:document.documentElement.scrollWidth>innerWidth})');
 if(!all.count.includes('24767')||all.images.some(i=>!i.loaded)||all.overflow)throw Error(JSON.stringify(all));
 await fs.writeFile(path.join(out,'report-top.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 if(await evaluate('!!document.querySelector("#latest-physical-gates")')){
  await evaluate('document.querySelector("#latest-physical-gates").scrollIntoView()');
  await fs.writeFile(path.join(out,'report-latest-gates.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 }
 await evaluate('document.querySelector("#case").value="vector";document.querySelector("#search").value="vec_wr_wdata[300]";render()');
 const query=await evaluate('({count:document.querySelector("#count").textContent,rows:document.querySelectorAll("#rows tr").length,text:document.querySelector("#rows").textContent})');
 if(query.rows!==1||!query.text.includes('vec_wr_wdata[300]'))throw Error(JSON.stringify(query));
 await evaluate('document.querySelector("#search").value="";document.querySelector("#case").value="";render();document.querySelector("#physical").scrollIntoView()');
 await fs.writeFile(path.join(out,'report-physical.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 for(const [name,heading] of [['cohort','完整C同组实际'],['gds','独立GDS合并'],['revision','真实失败驱动'],['parent','补建受控父层'],['models','基于实际SPEF导出'],['rules','原deck规则实现适用性']]){
  await evaluate(`(()=>{const e=[...document.querySelectorAll('h3')].find(e=>e.textContent.includes(${JSON.stringify(heading)}));if(!e)throw Error('Missing result section');e.scrollIntoView()})()`);
  await fs.writeFile(path.join(out,`report-${name}.png`),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 }
 if(errors.length)throw Error(JSON.stringify(errors));
 const result={status:'PASS_BROWSER_RENDER_FILTER_AND_IMAGES',...all,query,exceptions:errors};
 await fs.writeFile(path.join(out,'browser_qa.json'),JSON.stringify(result,null,2)+'\n');
 console.log(result.status,all.images.length,'loaded images; exact constant-bit query passed');
} finally {
 if(command&&socket?.readyState===1){try{await Promise.race([command('Browser.close'),new Promise(r=>setTimeout(r,1000))]);}catch{}}
 if(socket&&socket.readyState===1){socket.close();}
 child.kill();
}
