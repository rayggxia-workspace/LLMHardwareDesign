"""Self-contained graph/mapping/schedule explorer from real evaluation output."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(); p.add_argument('results',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); summary=json.loads((a.results/'summary.json').read_text())
    data={}
    for row in summary:
        name=row['model']
        if name in data:continue
        path=a.results/(name+'.graph.json')
        if not path.exists():continue
        graph=json.loads(path.read_text())
        plans={}
        for f in sorted(a.results.glob(name+'-s*.plan.json')):
            plan=json.loads(f.read_text())
            plans[f.stem]={'status':plan['status'],'at':plan.get('at'),
                          'latency':plan.get('latency_cycles'),'wire_cost':plan.get('static_cost'),
                          'seconds':round(plan.get('seconds',0),3),
                          'links':plan.get('static_links',[]),
                          'calls':[[c['task'],c['instance'],c['start'],c['end']] for c in plan.get('schedule',[])]}
        data[name]={'nodes':[[t['id'],t['op'],t['dependencies']] for t in graph['tasks']], 'plans':plans}
    html=TEMPLATE.replace('__DATA__',json.dumps(data,separators=(',',':')).replace('</','<\\/'))
    if len(html.encode())>1000000:raise ValueError('Inline payload too large')
    a.output.write_text(html,encoding='utf-8')


TEMPLATE='''<div id="block-search-report">
<style>
#block-search-report{color:var(--foreground);display:grid;gap:1em}
#block-search-report .controls{display:flex;gap:.5em;flex-wrap:wrap;align-items:center}
#block-search-report svg{width:100%;display:block;overflow:visible}
#block-search-report .detail{overflow-wrap:anywhere;min-height:2em}
#block-search-report text{fill:var(--foreground);font:inherit}
#block-search-report .node{fill:var(--muted);stroke:var(--border)}
#block-search-report .edge{stroke:var(--muted-foreground);fill:none;opacity:.5}
#block-search-report .mark{fill:var(--viz-series-1,var(--blue))}
</style>
<h2>Block 综合实验 · 分析模型</h2>
<div class="controls">
<label class="form-label">输入模型 <select class="form-select" id="bs-model"></select></label>
<label class="form-label">映射方案 <select class="form-select" id="bs-plan"></select></label>
<label class="form-label">视图 <select class="form-select" id="bs-view"><option value="input">输入算子图</option><option value="mapping">算子与宏分配</option><option value="time">资源时间安排</option><option value="links">静态连接并集</option></select></label>
</div>
<div id="bs-summary" aria-live="polite"></div>
<div class="controls"><button class="btn" id="bs-prev">上一页</button><span id="bs-page"></span><button class="btn" id="bs-next">下一页</button></div>
<svg id="bs-svg" role="img" aria-label="输入图、映射、调度与静态连接"></svg>
<div id="bs-detail" class="detail" aria-live="polite">FP32 分析服务与扩展算子未取得宏合同资格；不是 RTL 或物理通过。</div>
</div>
<script>
(()=>{const root=document.getElementById('block-search-report'),D=__DATA__;
const el=id=>root.querySelector('#bs-'+id),model=el('model'),plan=el('plan'),view=el('view'),svg=el('svg');
let page=0; const NS='http://www.w3.org/2000/svg';
function add(tag,attrs,text){const x=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>x.setAttribute(k,v));if(text!==undefined)x.textContent=text;svg.appendChild(x);return x;}
Object.keys(D).sort((a,b)=>a.startsWith('full')?-1:b.startsWith('full')?1:a.localeCompare(b)).forEach(n=>model.add(new Option(n,n)));
function choices(){plan.replaceChildren();Object.keys(D[model.value].plans).forEach(n=>plan.add(new Option(n,n)));let good=[...plan.options].find(x=>x.value.includes('s4194304-b4'));if(good)plan.value=good.value;page=0;draw();}
function draw(){svg.replaceChildren();const g=D[model.value],p=g.plans[plan.value],width=Math.max(300,root.clientWidth),calls=Object.fromEntries(p.calls.map(c=>[c[0],c]));
el('summary').textContent=`${g.nodes.length} 个计算节点 · ${p.status}${p.at?' @ '+p.at:''} · ${p.latency??'—'} cycles · 静态成本 ${p.wire_cost??'—'} · 编译 ${p.seconds}s`;
let items=view.value==='links'?p.links:g.nodes;const size=view.value==='time'?20:30,total=Math.max(1,Math.ceil(items.length/size));page=Math.min(page,total-1);el('page').textContent=`${page+1} / ${total}`;el('prev').disabled=page===0;el('next').disabled=page+1===total;
items=items.slice(page*size,(page+1)*size);
if(view.value==='links'){const names=[...new Set(p.links.flatMap(x=>x.split('->')))];const positions={};names.forEach((n,i)=>positions[n]=[width/2+Math.cos(i/names.length*2*Math.PI)*width*.32,180+Math.sin(i/names.length*2*Math.PI)*130]);svg.setAttribute('viewBox',`0 0 ${width} 360`);p.links.forEach(l=>{const [a,b]=l.split('->');if(positions[a]&&positions[b])add('line',{x1:positions[a][0],y1:positions[a][1],x2:positions[b][0],y2:positions[b][1],class:'edge'});});names.forEach(n=>{const [x,y]=positions[n];add('rect',{x:x-24,y:y-14,width:48,height:28,rx:3,class:'node'});add('text',{x,y:y+5,'text-anchor':'middle'},n);});return;}
if(view.value==='time'){const present=items.map(n=>[n,calls[n[0]]]).filter(x=>x[1]);svg.setAttribute('viewBox',`0 0 ${width} ${Math.max(80,present.length*32+35)}`);if(!present.length){add('text',{x:4,y:25},'该方案未生成完整调度');return;}
const low=Math.min(...present.map(x=>x[1][2])),high=Math.max(...present.map(x=>x[1][3])),scale=(width-145)/Math.max(1,high-low);present.forEach(([n,c],i)=>{const y=30+i*32;add('text',{x:0,y:y+14},n[0]+' '+c[1]);const bar=add('rect',{x:130+(c[2]-low)*scale,y,width:Math.max(2,(c[3]-c[2])*scale),height:20,class:'mark'});const t=document.createElementNS(NS,'title');t.textContent=`${n[1]} ${c[1]}: ${c[2]}–${c[3]} cycles`;bar.appendChild(t);});add('text',{x:130,y:14},`${low} → ${high} cycles`);return;}
const cols=Math.max(2,Math.floor(width/150)),cell=width/cols,height=Math.ceil(items.length/cols)*80+15,pos={};svg.setAttribute('viewBox',`0 0 ${width} ${height}`);items.forEach((n,i)=>pos[n[0]]=[(i%cols)*cell+cell/2,Math.floor(i/cols)*80+35]);items.forEach(n=>n[2].forEach(dep=>{if(pos[dep]){const [x,y]=pos[dep],[xx,yy]=pos[n[0]];add('line',{x1:x,y1:y+24,x2:xx,y2:yy-23,class:'edge'});}}));
items.forEach(n=>{const [x,y]=pos[n[0]],c=calls[n[0]];const box=add('rect',{x:x-cell*.44,y:y-23,width:cell*.88,height:48,rx:3,class:'node',tabindex:0,role:'button','aria-label':n[0]+' '+n[1]});const select=()=>{el('detail').textContent=`${n[0]} ${n[1]} · 前驱 ${n[2].join(', ')||'模型输入/权重'}${c?' · '+c[1]+' · '+c[2]+'–'+c[3]+' cycles':''}`;};box.onclick=select;box.onkeydown=e=>{if(e.key==='Enter')select();};add('text',{x,y:y-3,'text-anchor':'middle'},n[0]+' '+n[1]);add('text',{x,y:y+16,'text-anchor':'middle'},view.value==='mapping'?(c?c[1]:'未映射'):n[2].length+' 条前驱边');});}
model.onchange=choices;plan.onchange=()=>{page=0;draw()};view.onchange=()=>{page=0;draw()};el('prev').onclick=()=>{page--;draw()};el('next').onclick=()=>{page++;draw()};new ResizeObserver(draw).observe(root);choices();
})();
</script>'''


if __name__=='__main__':main()
