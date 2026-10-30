// Render only this local report in an isolated headless Edge; no user session.
import fs from 'node:fs/promises';import path from 'node:path';import{pathToFileURL}from'node:url';import{spawn}from'node:child_process';
const[report,out]=process.argv.slice(2);await fs.mkdir(out,{recursive:true});const port=10400+Math.floor(Math.random()*1000);
const proc=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--disable-extensions',`--remote-debugging-port=${port}`,`--user-data-dir=${path.resolve(out,'edge-profile')}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
let socket,call;
try{
 let tabs;for(let i=0;i<100;i++){try{tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();break;}catch{await new Promise(r=>setTimeout(r,100));}}
 if(!tabs)throw Error('Isolated Edge unavailable');socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
 let id=0;const pending=new Map();socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}};
 call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}));});
 const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await call('Page.navigate',{url:pathToFileURL(path.resolve(report)).href});
 for(let i=0;i<100;i++){if(await evaluate('document.readyState==="complete" && document.querySelectorAll("section").length===60 && [...document.images].every(i=>i.complete&&i.naturalWidth>0)'))break;await new Promise(r=>setTimeout(r,100));}
 const result=await evaluate('({sections:document.querySelectorAll("section").length,images:[...document.images].map(i=>({src:i.getAttribute("src"),loaded:i.complete&&i.naturalWidth>0})),overflow:document.documentElement.scrollWidth>innerWidth,title:document.title})');
 if(result.sections!==60||result.images.some(i=>!i.loaded)||result.overflow)throw Error(JSON.stringify(result));
 await fs.writeFile(path.join(out,'report-top.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));await evaluate('document.querySelector("img").scrollIntoView()');await fs.writeFile(path.join(out,'report-actual-gap.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await fs.writeFile(path.join(out,'browser_qa.json'),JSON.stringify({status:'PASS_BROWSER_RENDER',...result},null,2)+'\n');console.log('PASS_BROWSER_RENDER',result.sections,'records;',result.images.length,'loaded image; no overflow');
}finally{if(call&&socket?.readyState===1){try{await Promise.race([call('Browser.close'),new Promise(r=>setTimeout(r,1000))]);}catch{}}socket?.close();proc.kill();}
