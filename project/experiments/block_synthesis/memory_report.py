"""Standalone input/result visualization for the revised algorithm scope."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('results', type=Path)
    a = p.parse_args()
    def read(name):
        return json.loads((a.results / name).read_text(encoding='utf-8'))
    comparisons = read('evaluation/comparison.json')
    data = {'comparison': comparisons, 'full': read('evaluation/full-input.json'),
            'native': read('native/plan.json'), 'ng': read('native/graph.json'),
            'virtual': read('native/virtual-result.json')['plan'],
            'cases': {r['case']: read('evaluation/' + r['case'] + '/plan.json') for r in comparisons}}
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>综合算法：零预连与虚拟外存</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f6f8fb;color:#203047;font:15px/1.7 system-ui,sans-serif}main{max-width:1100px;margin:28px auto;padding:0 18px}h1{font-size:26px}h2{font-size:20px;margin-top:30px}p{max-width:90ch}.scroll{overflow:auto}svg{display:block;min-width:800px;width:100%;background:white}svg text{font:13px system-ui;fill:#203047}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:9px;border-bottom:1px solid #dbe2ec;white-space:nowrap}select{font:inherit;padding:8px;max-width:100%}.tag{display:inline-block;background:#e2edf8;border:1px solid #b2c9e0;padding:8px;margin:4px}.muted{color:#536278}a{color:#225e96}summary{cursor:pointer}@media(max-width:500px){h1{font-size:22px}main{padding:0 12px}}</style>
<main><h1>综合算法：零数据预连、虚拟外存与真实宏程序</h1>
<p>本阶段验收算法产生的映射、时间、存储和连接需求。MC/LC 机器码、原生 DMA 回放和最终布线均可后接。已有控制器不是本报告断言的硬件缺口。</p>
<div class="tag">数据预连：0</div><div class="tag">私有 S：每实例16 KiB</div><div class="tag">外存：PR182 来源的有限资源模型</div>
<h2>真实输入与原生回放</h2><p>2048元素 RMSNorm 与残差加法衔接，另有16元素 Softmax。数值为显式原生整数语义；这是宏服务集成测试，不是完整 LLM benchmark。</p><div class="scroll" id="dag"></div><p id="native-summary"></p><div class="scroll" id="native-time"></div>
<h2>输入资源与算法对照</h2><p>四行2048元素 RMS，共享 gamma 和 epsilon。比较相同模型下的一/二实例、通道、信用和逻辑连接预算。所有结果都包含显式外存读写和确认，均通过独立检查；时间属于记录的模型，不是HBM器件实测。二实例是同一IP的资源清单配置，不表示新顶层物理验收。</p><div class="scroll"><table><thead><tr><th>配置</th><th>串行初解</th><th>改进计划</th><th>缩短</th><th>外存字数</th><th>逻辑线束</th></tr></thead><tbody id="comparison"></tbody></table></div>
<p><label for="case">查看计划：</label><select id="case"></select></p><p id="case-summary"></p><div class="scroll" id="timeline"></div>
<details><summary>外存抽象的具体边界</summary><p>采用PR182源码中的时钟、延迟、信用、队列和银行参数。描述符之间按共享通道与S IO资源串行；同一描述符内有限在途。随机背压关闭，冷银行与切换规则记录。没有宣称等价复现其逐字轮询、CDC或真实HBM时序。S读/写4/6周期来自本轮实际客户端测量。</p></details>
<h2>完整 Qwen2.5-3B 的覆盖边界</h2><p id="full"></p><p>该模型的真实权重、36层及输出前端对照已在先前记录通过。本次没有完成矩阵/G/R/T、尺度和布局的完整编译规则，因而不能把这里的局部对照冒充整网综合。它属于软件未完成，不是已经查明硬件不够、控制未实现或16KiB不可行。</p><p><a href="../joint-v1/report.html">查看完整3B模型的真实算子依赖图</a> · <a href="receipt.json">本轮作业、来源与输出索引</a></p>
</main><script type="application/json" id="data">PAYLOAD</script><script>
const d=JSON.parse(document.getElementById('data').textContent),el=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tasks=d.ng.tasks,producer=new Map(tasks.flatMap(t=>t.outputs.map(v=>[v,t.id]))),pos=new Map(tasks.map((t,i)=>[t.id,{x:40+(i===2?480:0),y:30+(i===1?100:0)}]));let dag='<svg viewBox="0 0 950 230" aria-label="真实服务依赖图" role="img">';for(const t of tasks){let p=pos.get(t.id);for(const v of t.inputs){if(producer.has(v)){let q=pos.get(producer.get(v));dag+='<path d="M'+(q.x+310)+' '+(q.y+30)+' L'+p.x+' '+(p.y+30)+'" stroke="#456f9e" fill="none"/>'}}dag+='<rect x="'+p.x+'" y="'+p.y+'" width="310" height="60" rx="5" fill="#dceaf8"/><text x="'+(p.x+14)+'" y="'+(p.y+36)+'">'+esc(t.op+' · '+d.ng.values[t.outputs[0]].words+' words')+'</text>'}el('dag').innerHTML=dag+'</svg>';
function chart(plan,moves){let rows=Object.entries(plan.tasks).map(([id,r])=>({...r,label:id+' / '+r.site,color:'#4477a9'}));if(moves)rows.push(...plan.moves.map(m=>({...m,label:(m.src==='MEM'?'LOAD':'STORE')+' '+m.value,color:'#609384'})));rows.sort((a,b)=>a.start-b.start||a.end-b.end);let h=50+rows.length*34,s='<svg viewBox="0 0 1000 '+h+'" role="img" aria-label="执行与搬运时间轴">';for(let i=0;i<5;i++){let x=220+i*187;s+='<path d="M'+x+' 20 V'+(h-10)+'" stroke="#d7e0e9"/><text x="'+x+'" y="16" text-anchor="end">'+Math.round(plan.makespan*i/4)+'</text>'}rows.forEach((r,i)=>{let y=32+i*34;s+='<text x="6" y="'+(y+18)+'">'+esc(r.label)+'</text><rect x="'+(220+748*r.start/plan.makespan)+'" y="'+y+'" width="'+Math.max(1,748*(r.end-r.start)/plan.makespan)+'" height="23" fill="'+r.color+'"><title>'+esc(r.label+' ['+r.start+', '+r.end+')')+'</title></rect>'});return s+'</svg>'}
el('native-summary').textContent='三初态原生客户端回放通过，计算程序 '+d.native.makespan+' 周期；包含虚拟外存的算法计划为 '+d.virtual.makespan+' 模型周期。两种时间边界分别记录。';el('native-time').innerHTML=chart(d.native,false);
el('comparison').innerHTML=d.comparison.map(r=>'<tr><td>'+esc(r.case)+'</td><td>'+r.baseline_ticks+'</td><td>'+r.optimized_ticks+'</td><td>'+((1-r.optimized_ticks/r.baseline_ticks)*100).toFixed(1)+'%</td><td>'+r.baseline_external_words+' → '+r.optimized_external_words+'</td><td>'+r.selected_bundles+' / '+r.bundle_budget+'</td></tr>').join('');el('case').innerHTML=d.comparison.map(r=>'<option>'+esc(r.case)+'</option>').join('');
function render(){let key=el('case').value,p=d.cases[key],r=d.comparison.find(x=>x.case===key);el('timeline').innerHTML=chart(p,true);el('case-summary').textContent=r.instances+' 个实例 × 16KiB，'+r.channels+' 通道，信用 '+r.credits+'；选用 '+p.nets.length+' 个逻辑通道束。执行 '+p.makespan+' 模型周期。'}el('case').addEventListener('change',render);render();el('full').textContent=d.full.runtime_nodes+' 个运行时节点，'+d.full.offline_weight_recipes+' 项离线只读权重布局配方。整网状态：compiler_lowering_missing。';
</script></html>'''
    (a.results / 'report.html').write_text(page.replace('PAYLOAD', encoded), encoding='utf-8')


if __name__ == '__main__':
    main()
