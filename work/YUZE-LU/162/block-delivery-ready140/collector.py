"""Collect the exact actually selected/qualified adapter plus 20 exact leaves."""
from pathlib import Path
import subprocess,shlex,json,hashlib,collections,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control')
q=r"""from pathlib import Path
import json,hashlib,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/s-ready-upper-source140.json'
if not record.exists():print(json.dumps(dict(ready=False,reason='Actual qualified/native-STA/residual selection unfinished')));raise SystemExit(0)
selection=json.loads(record.read_text());candidate=selection['selected_adapter_candidate'];assert candidate in (1390,1391)
base=b/'s-ready-composition-01'/str(candidate);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=base/'selected/physical.json';graph=base/'topology/boundary-graph.json';m=json.loads(manifest.read_text());g=json.loads(graph.read_text());assert g['passed']and g['S_external_link_instances']==0 and g['S_internal_drive']['all_four_gates_fresh']
receipt=base/'topology/receipt.json';r=json.loads(receipt.read_text());assert r['passed']and r['operation']=='topology-generation'and r['outputs']['boundary-graph.json']==sha(graph)and r['inputs'][str(manifest)]==sha(manifest)
counts=dict(collections.Counter(g['instances'].values()));assert set(counts)==set(m['leaves'])and len(counts)==21
entry=m['leaves']['control_adapter_s']['fixed_pg_delivery'];path=Path(entry['path']);receipt=Path(entry['receipt']);assert sha(path)==entry['sha256']and sha(receipt)==entry['receipt_sha256']
r=json.loads(receipt.read_text());d=json.loads(path.read_text());assert r['passed']and r['native_leaf_qualified']and d['passed']and d['native_leaf_accepted']and r['outputs']['delivery.json']==sha(path)
for item in d['final_files'].values():assert Path(item['path']).stat().st_size==item['bytes']and sha(item['path'])==item['sha256']
image=path.parent/'layout.png';assert sha(image)==d['image_sha256']
print(json.dumps(dict(ready=True,candidate=candidate,manifest=dict(path=str(manifest),sha256=sha(manifest),data=m),graph=dict(path=str(graph),sha256=sha(graph)),topology_receipt=dict(path=str(base/'topology/receipt.json'),sha256=sha(base/'topology/receipt.json')),counts=counts,instance_count=len(g['instances']),replacement_delivery=d,replacement_entry=entry,image=str(image),selection=dict(path=str(record),sha256=sha(record)))))
"""
data=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
if not data['ready']:print(json.dumps(data));raise SystemExit(0)
oldroot=repo/'work/YUZE-LU/162/block-delivery-s1350';old=json.loads((oldroot/'index.json').read_text(encoding='utf-8'))
out=repo/'work/YUZE-LU/162/block-delivery-ready140';assert not out.exists();out.mkdir();(out/'layouts').mkdir()
attr=repo/'.gitattributes';rule='work/YUZE-LU/162/block-delivery-ready140/** -text'
if rule not in attr.read_text(encoding='utf-8'):
 with attr.open('a',encoding='utf-8')as f:f.write('\n'+rule+'\n')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for row in old['leaves']:
 row=dict(row);top=row['top'];actual=data['manifest']['data']['leaves'][top]
 if top!='control_adapter_s':
  assert actual['final_files']==row['final_files']and actual['fixed_pg_delivery']['sha256']==row['delivery']['sha256']and actual['fixed_pg_delivery']['receipt_sha256']==row['receipt']['sha256']
  src=oldroot/row['image']['path'];assert sha(src)==row['image']['sha256'];shutil.copyfile(src,out/row['image']['path']);row['reused_exact_qualified_baseline']=True
 else:
  d=data['replacement_delivery'];e=data['replacement_entry'];image='layouts/control_adapter_s.png'
  for target,remote,digest in [(image,data['image'],d['image_sha256']),('delivery.json',e['path'],e['sha256']),('receipt.json',e['receipt'],e['receipt_sha256'])]:
   subprocess.run(['scp','yuzelu@10.129.166.172:'+remote,str(out/target)],check=True);assert sha(out/target)==digest
  row.update(die_um=d['die_um'],active_area_um2=d['active_area_um2'],minimum_setup_ns=d['minimum_setup_ns'],minimum_hold_ns=d['minimum_hold_ns'],delivery=dict(path=e['path'],sha256=e['sha256'],local_proof='block-delivery-ready140/delivery.json'),receipt=dict(path=e['receipt'],sha256=e['receipt_sha256']),final_files=d['final_files'],image=dict(path=image,sha256=d['image_sha256']),original_delivery=d['original_delivery'],original_delivery_sha256=d['original_delivery_sha256'],fresh_physical_receipt=d['fresh_physical_receipt'],fresh_physical_receipt_sha256=d['fresh_physical_receipt_sha256'],fresh_timing_receipt=d['fresh_timing_receipt'],fresh_timing_receipt_sha256=d['fresh_timing_receipt_sha256'],readiness_state=dict(owner='control_adapter_s M1-M10',bits=2,extra_protocol_cycles=0,extra_packet_slots=0,scope='Look-ahead predicates, independently checked against actual producer/consumer occupancy on every tested cycle; entire new native and fixedPG qualification required.'))
  row.pop('reused_exact_qualified_baseline',None)
 row['instances']=data['counts'][top];rows.append(row)
shutil.copyfile(Path(__file__),out/'collector.py')
index=dict(scope='21 actual individually qualified types for selected S-ready repair. No system/upper qualification inferred; R preserved separately.',collector_sha256=sha(out/'collector.py'),leaves=rows,declared_instances=data['instance_count'],adapter_candidate=data['candidate'],selection=data['selection'],actual_manifest={k:v for k,v in data['manifest'].items()if k!='data'},actual_graph=data['graph'],topology_receipt=data['topology_receipt'],whole_system_qualified=False,total_native_die_area_um2=sum(r['instances']*r['die_um'][0]*r['die_um'][1]for r in rows),total_native_active_area_um2=sum(r['instances']*r['active_area_um2']for r in rows))
(out/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
table=['| 物理块 | 功能 | 实例数 | die（µm） | 活动面积（µm²） | setup/hold（ns） | 版图 |','|---|---|---:|---:|---:|---:|---|']
for r in rows:
 w,h=r['die_um'];table.append(f"| {r['top']} | {r['function']} | {r['instances']} | {w:g}×{h:g} | {r['active_area_um2']:,.2f} | {r['minimum_setup_ns']:.6f}/{r['minimum_hold_ns']:.6f} | [图](../work/YUZE-LU/162/block-delivery-ready140/{r['image']['path']}) |")
doc='# Issue162 最终单块交付（S内部驱动及S适配器ready修复）\n\n21类物理块全部原生四门及固定PG/新鲜RC/300MHz验收通过。S1350内部788个BUF_X32无新增状态；S适配器两个预测ready状态位明确归该物理宏，保持原协议拍和有限包槽。其余19类型、S本体均复用精确已合格文件。S/T为标准单元存储。R保留并由并行任务修改，此表不宣称已接入。\n\n**单块通过不代表系统通过。** 全网M11/M12/真实全PG/low-base-high分布RC/300MHz/实际代表程序及联合交付须独立验收。旧失败/基线索引完整保留。\n\n[六文件、SHA和全部源绑定索引](../work/YUZE-LU/162/block-delivery-ready140/index.json)。所有图片均为实际交付PNG。\n\n'+'\n'.join(table)+f"\n\n实际图共{data['instance_count']}实例、{data['counts']['control_link8']}个Link8。原生die面积加总{index['total_native_die_area_um2']:,.2f}µm²，活动面积加总{index['total_native_active_area_um2']:,.2f}µm²，不含宏间留白。\n"
(repo/'docs/CONTROL_V1_BLOCK_DELIVERY.md').write_text(doc,encoding='utf-8',newline='\n')
p=repo/'docs/CONTROL_V1.md';s=p.read_text(encoding='utf-8');s='## 当前S适配器物理修复\n\nS适配器两个预测ready状态位均归control_adapter_s固定M1–M10，不增加协议拍或包槽。实际所选候选及六文件见CONTROL_V1_BLOCK_DELIVERY.md和block-delivery-ready140索引；其余20类精确复用，其中S1350已完整重新验收。所有M11/M12仍仅承载连线与过孔，不隐藏状态。单块与组合资格分开。\n\n'+s;p.write_text(s,encoding='utf-8',newline='\n')
print(json.dumps(dict(ready=True,candidate=data['candidate'],qualified_types=21,actual_instances=data['instance_count'],out=str(out))))
