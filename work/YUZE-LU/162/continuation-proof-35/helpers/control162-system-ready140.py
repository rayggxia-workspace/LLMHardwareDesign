"""Collect only an actual jointly accepted new-S scene; no gate relaxation."""
from pathlib import Path
import subprocess,shlex,json,hashlib,collections,shutil,sys
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control')
subprocess.run([sys.executable,str(Path(__file__).with_name('control162-final-receipts-retry140.py'))],check=True,stdout=subprocess.DEVNULL)
q=r'''from pathlib import Path
import json,hashlib,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');selection_path=b/'route-selection-102/s-ready-upper-source140.json'
if not selection_path.exists():print(json.dumps(dict(ready=False,reason='Actual qualified selection unfinished')));raise SystemExit(0)
selection=json.loads(selection_path.read_text());base=b/'s-ready-composition-01'/str(selection['selected_adapter_candidate'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
accepted=[]
seeds=list(range(1410,1414))
for record_name in ['s-ready-capacity-upper-source140.json','s-ready-capacity-refill-source140.json','s-ready-cap-proof141-refill-source140.json','s-ready-congestion-source142.json','s-ready-congestion-followup-source142.json','s-ready-halo-routes-source142.json','s-ready-cache-source143.json','s-ready-cache-refill-source143.json','s-ready-history-product-source144.json','s-ready-history-product-refill-source144.json','s-ready-segment-source145.json','s-ready-openroad-source156.json','s-ready-openroad-halo-source156.json','s-ready-openroad-source157.json','s-ready-internal-channel-openroad-source157.json']:
 alternative=b/'route-selection-102'/record_name
 if not alternative.exists():continue
 extra=json.loads(alternative.read_text());assert extra['source']in ['source-140','source-142','source-143','source-144','source-145','source-156','source-157']and extra['selected_adapter_candidate']==selection['selected_adapter_candidate']and extra['instance_count']==235
 for task in extra['tasks']:
  spec=task['spec']
  if spec['script']!='system_upper.py':continue
  args=spec['args'];seeds.append(int(args[args.index('--seed')+1]))
for seed in seeds:
 for delivery_name in ['delivery','delivery-after-final-receipts']:
  p=base/'upper-candidates'/str(seed)/delivery_name;receipt=p/'receipt.json'
  if not receipt.exists():continue
  r=json.loads(receipt.read_text(encoding='utf-8'))
  if r.get('passed')and r.get('whole_system_qualified'):accepted.append((seed,p,r))
if not accepted:print(json.dumps(dict(ready=False,reason='No actual joint geometry/PG/programs/three-corner300MHz acceptance yet.')));raise SystemExit(0)
seed,p,r=accepted[0]
assert all(r[k]for k in ['passed','whole_system_qualified','declared_composition_qualified','system_pg_qualified','system_timing_qualified'])
report=p/'system-acceptance.json';assert sha(report)==r['outputs'][report.name]
a=json.loads(report.read_text(encoding='utf-8'));assert all(a[k]for k in ['passed','declared_composition_qualified','whole_system_qualified','all_actual_geometry_pg_function_rc_bound'])
assert set(a['timing'])=={'low','base','high'}
assert all(t['minimum_setup_ns']>=0 and t['minimum_hold_ns']>=0 for t in a['timing'].values())
gpath=base/'topology/boundary-graph.json';mpath=base/'selected/physical.json'
g=json.loads(gpath.read_text(encoding='utf-8'));m=json.loads(mpath.read_text(encoding='utf-8'));assert g['passed']and g['S_external_link_instances']==0
assert g['S_internal_drive']==m['leaves']['block_feed_s_macro']['S_internal_drive']
assert len(g['instances'])==a['instance_count']and len(m['leaves'])==a['native_types']==21
counts=dict(collections.Counter(g['instances'].values()));files={}
for name in ['6_final.v','6_final.sdc','6_final.def','6_final.odb','6_final.spef','6_final.gds','layout.png']:
 f=p/name;digest=sha(f);assert digest==r['outputs'][name]
 files[name]=dict(path=str(f),sha256=digest,bytes=f.stat().st_size)
print(json.dumps(dict(ready=True,seed=seed,folder=str(p),receipt=dict(path=str(p/'receipt.json'),sha256=sha(p/'receipt.json')),report=dict(path=str(report),sha256=sha(report)),acceptance=a,files=files,
 manifest=dict(path=str(mpath),sha256=sha(mpath)),signal_graph=dict(path=str(gpath),sha256=sha(gpath)),counts=counts,instance_types=g['instances'])))
'''
data=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45))
if not data['ready']:print(json.dumps(data));raise SystemExit(0)
assert (repo/'work/YUZE-LU/162/block-delivery-ready140/index.json').exists(),'Collect actual individual-block package first'
out=repo/'work/YUZE-LU/162/system-delivery-ready140';assert not out.exists();out.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name,remote,digest in [('receipt.json',data['receipt']['path'],data['receipt']['sha256']),('system-acceptance.json',data['report']['path'],data['report']['sha256']),('layout.png',data['files']['layout.png']['path'],data['files']['layout.png']['sha256'])]:
 subprocess.run(['scp','yuzelu@10.129.166.172:'+remote,str(out/name)],check=True);assert sha(out/name)==digest
shutil.copyfile(Path(__file__),out/'collector.py');data['collector_sha256']=sha(out/'collector.py')
helper=Path(__file__).with_name('control162-final-receipts-retry140.py');shutil.copyfile(helper,out/helper.name);data['receipt_retry_helper_sha256']=sha(out/helper.name)
(out/'index.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
attr=repo/'.gitattributes';rule='work/YUZE-LU/162/system-delivery-ready140/** -text'
if rule not in attr.read_text(encoding='utf-8'):
 with attr.open('a',encoding='utf-8')as stream:stream.write('\n'+rule+'\n')
a=data['acceptance'];table=['| RC角点 | 最差setup（ns） | 最差hold（ns） |','|---|---:|---:|']
for corner in ['low','base','high']:
 t=a['timing'][corner];table.append(f"| {corner} | {t['minimum_setup_ns']:.9f} | {t['minimum_hold_ns']:.9f} |")
files=['| 最终文件 | 字节数 | SHA-256 |','|---|---:|---|']
for name,entry in data['files'].items():files.append(f"| {name} | {entry['bytes']} | {entry['sha256']} |")
doc=f'''# Issue162 新S实际组合联合交付

实际候选{data['seed']}的同一新S场景已通过完整M11/M12几何、原生mask XOR、真实ODB/DEF/GDS连通、全场景PG、low/base/high分布RC及300MHz、最终单元三初态真实程序与联合源绑定。21类原生物理块共{a['instance_count']}个实例，计数来自同一真实boundary-graph；S内部788个BUF_X32驱动归固定M1–M10，S适配器两个预测ready状态位归该适配器M1–M10，不增加包槽或协议拍。R仍由并行任务修改，本交付的R_integrated={a['R_integrated']}，不宣称其接入。

验收范围是仓库现行研究M11/M12 RC模型下的明确参考组合；未进行制造工艺校准或EM/IR签核。原始失败全部保留，PR供审查，不自行合并。

[逐块六文件和版图](CONTROL_V1_BLOCK_DELIVERY.md) · [组合完整源绑定索引](../work/YUZE-LU/162/system-delivery-ready140/index.json) · [实际联合验收报告](../work/YUZE-LU/162/system-delivery-ready140/system-acceptance.json)

三初态均完成三条真实程序，CPU张量搬运为0；具体计数和轨迹按验收报告逐项绑定。布局与时序不是RTL替代模型或旧335组合结果。

'''+ '\n'.join(table)+ '\n\n六文件及实际PNG保存在获授权远程项目目录；下面索引中的路径/字节/SHA均由交付回执再读回核对。\n\n'+ '\n'.join(files)+ '\n\n![实际最终组合版图](../work/YUZE-LU/162/system-delivery-ready140/layout.png)\n'
(repo/'docs/CONTROL_V1_SYSTEM_DELIVERY.md').write_text(doc,encoding='utf-8')
print(json.dumps(dict(ready=True,jointly_accepted_seed=data['seed'],actual_instances=a['instance_count'],out=str(out))))
