"""Render eight-field records from bundled evidence; never launches CAD."""
from pathlib import Path
import argparse,html,json
FIELDS=[('stage','1. 卡在什么阶段'),('object','2. 具体对象'),('function','3. 原本负责什么'),('expected_vs_actual','4. 预期与实际'),('consequence','5. 会造成什么后果'),('attempts','6. 已尝试的修改与结果'),('remaining_work','7. 还缺什么才能完成'),('evidence','8. 证据与实际版本')]
def render(out):
 out=Path(out);d=json.loads((out/'data/incidents.json').read_text(encoding='utf-8'));e=html.escape
 top='回顾Issue126在2026年10月29日21:19至30日09:19（北京时间）的排障尝试，另如实记录逾期收集。原完整工程目标未完成；12小时硬交付与后半程每小时报告也未完成。“修复成功”只指列出的范围，不能扩展为芯片、系统或功能全部通过。'
 md=['# Issue126：逐次阻塞、修复尝试与实际结果','',top,'','这是用户要求的新文档PR，从main创建独立分支；只引用原工程的实际证据，不修改PR129或原始参考报告，不启动物理试验。','',f"共{len(d['attempts'])}条逐次记录；每条含8项、原因假设、修改与验证结果。试验时间来自闭合回执；本地求解和流程观察分别标注。job/driver/source SHA来自证据，不用文档生成时间替代试验时间。",'','[中文HTML](report.html) · [逐次台账JSON](data/incidents.json) · [证据SHA清单](data/evidence_manifest.json) · [原工程证据来源PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)','', '## 当前主要未完成项','']
 page=['<h1>Issue126：逐次阻塞、修复尝试与实际结果</h1><p class="warn">'+e(top)+'</p><p>新文档PR；共'+str(len(d['attempts']))+'条逐次记录。<a href="README.md">Markdown</a> · <a href="data/incidents.json">台账JSON</a> · <a href="data/evidence_manifest.json">证据/SHA</a>。</p>']
 def fields(r):
  rows=[];hh=[]
  for k,label in FIELDS:
   v=r[k]
   if k=='evidence':m='；'.join('['+x['label']+']('+x['path']+')' for x in v);h=' · '.join('<a href="'+e(x['path'])+'">'+e(x['label'])+'</a>' for x in v)
   else:m=v;h=e(v)
   if k=='remaining_work':m+=' 剩余估计：'+r['remaining_estimate'];h+=' 剩余估计：'+e(r['remaining_estimate'])
   rows+=['**'+label+'：** '+m,''];hh+=['<dt>'+label+'</dt><dd>'+h+'</dd>']
  return rows,'<dl>'+''.join(hh)+'</dl>'
 for r in d['remaining']:
  m,h=fields(r);md+=['### '+r['title'],'']+m+['**比喻及对应对象：** '+r['analogy'],''];page+=['<details><summary>'+e(r['title'])+'</summary>'+h+'<p>'+e(r['analogy'])+'</p></details>']
 md+=['## 真实物理图','', '![真实M5补线前后：100降至6项，仍失败](assets/llsys_actual_gap_residual6.png)','', '[SVG](assets/llsys_actual_gap_residual6.svg) · [图来源/SHA](data/llsys_actual_gap_residual6_figure.json)','','## 每次尝试索引','', '| 编号 | 闭合时间（北京时间） | 具体步骤 | 状态 |','| --- | --- | --- | --- |']
 page+=['<h2>真实施工图：100→6项，仍未通过</h2><img src="assets/llsys_actual_gap_residual6.png" alt="真实补线及残余6项"><p><a href="assets/llsys_actual_gap_residual6.svg">SVG</a>；实际矩形按尺寸绘制，红框是违规范围；未绘的层/OBS不能视为空白。</p><h2>逐次时间索引</h2><ol>']
 for r in d['attempts']:
  md+=['| ['+r['id']+'](#'+r['id'].lower()+') | '+r['completed_Asia_Shanghai']+' | '+r['title']+' | '+r['status']+' |'];page+=['<li><a href="#'+r['id']+'">'+e(r['completed_Asia_Shanghai']+' '+r['title'])+'</a> — '+e(r['status'])+'</li>']
 page+=['</ol>'];md+=['','## 逐次记录','']
 for r in d['attempts']:
  m,h=fields(r);meta=r['completed_Asia_Shanghai']+'（'+r.get('time_kind','闭合时间')+'） | '+r['status']+' | job '+r['job'];version='driver '+r['driver_commit']+'；回执/观察证据SHA256 '+r['receipt_SHA256']
  md+=['<a id="'+r['id'].lower()+'"></a>','', '### '+r['id']+' '+r['title'],'',meta,'']+m+['**原因假设（区别已证实和未知）：** '+r['hypothesis'],'','**比喻及对应对象：** '+r['analogy'],'',version,'']
  page+=['<section id="'+r['id']+'"><h2>'+e(r['id']+' '+r['title'])+'</h2><p>'+e(meta)+'</p>'+h+'<p><b>原因假设：</b>'+e(r['hypothesis'])+'</p><p><b>比喻及对应对象：</b>'+e(r['analogy'])+'</p><details><summary>绑定版本</summary><code>'+e(version)+'</code></details></section>']
 ending='已通过/实际失败/尚未验证/未执行分别保留。未降时钟、放宽负载阈值、删检查或虚构SRAM GDS。固定底座冻结、两模式完整功能及公平完整系统对照未完成。结构/文档检查不是物理签核。大型ODB/SPEF/GDS留授权服务器，精选原生回执/脚本/日志随PR提供。登记沿用management-hub PR5 pending；缺config/board.json，Projects unverified/同步pending；审查人待指定。Refs #126，Issue不标done。'
 md+=['## 提交边界和协作回执','',ending,''];page+=['<h2>提交边界和协作回执</h2><p>'+e(ending)+'</p>']
 (out/'README.md').write_text('\n'.join(md),encoding='utf-8',newline='\n')
 css='body{margin:0;background:#f3f6fa;color:#17283c;font:16px/1.75 "Microsoft YaHei",sans-serif}main{max-width:1200px;background:white;margin:24px auto;padding:30px}h1{font-size:28px}h2{margin-top:30px}img{max-width:100%;height:auto}a{color:#176c9c}.warn{padding:15px;background:#fff1df;border-left:5px solid #ae741e}dt{font-weight:bold}dd{margin:0 0 12px}section{border-top:1px solid #d8e1eb;margin-top:30px}code{overflow-wrap:anywhere;font-size:12px}'
 (out/'report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Issue126逐次排障记录</title><style>'+css+'</style><main>'+''.join(page)+'</main></html>',encoding='utf-8',newline='\n')
 print('RENDERED_EIGHT_FIELD_RECORDS',len(d['attempts']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');render(p.parse_args().output)
