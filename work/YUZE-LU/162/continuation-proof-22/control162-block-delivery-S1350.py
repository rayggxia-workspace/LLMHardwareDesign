"""Collect only actually qualified new-S fixed-PG leaves, never a system pass."""
from pathlib import Path
import subprocess,shlex,json,hashlib,shutil,collections
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control')
q=r'''from pathlib import Path
import json,hashlib,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-escape-composition-02/1350'
required=[base/'selected/receipt.json',base/'topology/receipt.json']
if not all(p.exists()for p in required):print(json.dumps(dict(ready=False,reason='New S full native/fixed-PG qualification and actual selected topology unfinished.')));raise SystemExit(0)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(json.loads(p.read_text())['passed']for p in required)
manifest=base/'selected/physical.json';graph=base/'topology/boundary-graph.json'
m=json.loads(manifest.read_text());g=json.loads(graph.read_text());assert g['passed']and g['S_external_link_instances']==0
assert g['S_internal_drive']==m['leaves']['block_feed_s_macro']['S_internal_drive']
assert g['S_internal_drive']['all_four_gates_fresh']
counts=dict(collections.Counter(g['instances'].values()));assert set(counts)==set(m['leaves'])and len(counts)==21
row=m['leaves']['block_feed_s_macro'];entry=row['fixed_pg_delivery'];path=Path(entry['path']);receipt=Path(entry['receipt'])
assert sha(path)==entry['sha256']and sha(receipt)==entry['receipt_sha256']
r=json.loads(receipt.read_text());d=json.loads(path.read_text());assert r['passed']and r['native_leaf_qualified']and d['passed']and d['native_leaf_accepted']
assert r['outputs']['delivery.json']==sha(path)
assert d['S_internal_drive']==g['S_internal_drive']and d['signal_pin_plan_unchanged']
for item in d['final_files'].values():assert Path(item['path']).stat().st_size==item['bytes']and sha(item['path'])==item['sha256']
image=path.parent/'layout.png';assert sha(image)==d['image_sha256']
print(json.dumps(dict(ready=True,manifest=dict(path=str(manifest),sha256=sha(manifest),data=m),graph=dict(path=str(graph),sha256=sha(graph)),selected_receipt=dict(path=str(required[0]),sha256=sha(required[0])),topology_receipt=dict(path=str(required[1]),sha256=sha(required[1])),counts=counts,instance_count=len(g['instances']),S_delivery=d,S_entry=entry,S_receipt=r,image=str(image))))
'''
data=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]))
if not data['ready']:print(json.dumps(data));raise SystemExit(0)
old=json.loads((repo/'work/YUZE-LU/162/block-delivery-11/index.json').read_text())
out=repo/'work/YUZE-LU/162/block-delivery-s1350';assert not out.exists();out.mkdir();(out/'layouts').mkdir()
attr=repo/'.gitattributes';rule='work/YUZE-LU/162/block-delivery-s1350/** -text'
if rule not in attr.read_text(encoding='utf-8'):
 with attr.open('a',encoding='utf-8')as stream:stream.write('\n'+rule+'\n')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
for record in old['leaves']:
 record=dict(record);top=record['top'];actual=data['manifest']['data']['leaves'][top]
 if top!='block_feed_s_macro':
  assert actual['final_files']==record['final_files']
  assert actual['fixed_pg_delivery']['sha256']==record['delivery']['sha256']
  assert actual['fixed_pg_delivery']['receipt_sha256']==record['receipt']['sha256']
  source=repo/'work/YUZE-LU/162/block-delivery-11'/record['image']['path'];assert sha(source)==record['image']['sha256']
  shutil.copyfile(source,out/record['image']['path'])
  record['reused_exact_qualified_baseline']=True
 else:
  d=data['S_delivery'];e=data['S_entry'];source=out/'layouts/block_feed_s_macro.png'
  subprocess.run(['scp','yuzelu@10.129.166.172:'+data['image'],str(source)],check=True);assert sha(source)==d['image_sha256']
  for name,remote,digest in [('delivery.json',e['path'],e['sha256']),('receipt.json',e['receipt'],e['receipt_sha256'])]:
   subprocess.run(['scp','yuzelu@10.129.166.172:'+remote,str(out/name)],check=True);assert sha(out/name)==digest
  record.update(die_um=d['die_um'],active_area_um2=d['active_area_um2'],minimum_setup_ns=d['minimum_setup_ns'],minimum_hold_ns=d['minimum_hold_ns'],
   delivery=dict(path=e['path'],sha256=e['sha256'],local_proof='block-delivery-s1350/delivery.json'),receipt=dict(path=e['receipt'],sha256=e['receipt_sha256']),
   final_files=d['final_files'],image=dict(path='layouts/block_feed_s_macro.png',sha256=d['image_sha256']),
   original_delivery=d['original_delivery'],original_delivery_sha256=d['original_delivery_sha256'],
   fresh_physical_receipt=d['fresh_physical_receipt'],fresh_physical_receipt_sha256=d['fresh_physical_receipt_sha256'],
   fresh_timing_receipt=d['fresh_timing_receipt'],fresh_timing_receipt_sha256=d['fresh_timing_receipt_sha256'],S_internal_drive=d['S_internal_drive'])
 record['instances']=data['counts'][top];rows.append(record)
shutil.copyfile(Path(__file__),out/'collector.py')
index=dict(scope='Exact individually qualified native/fixed-PG deliveries for actual new-S reference. No M11/M12/system pass inferred. R preserved under parallel modification; S/T standard-cell storage.',collector_sha256=sha(out/'collector.py'),
 leaves=rows,declared_instances=data['instance_count'],actual_manifest={k:v for k,v in data['manifest'].items()if k!='data'},actual_graph=data['graph'],
 selected_receipt=data['selected_receipt'],topology_receipt=data['topology_receipt'],whole_system_qualified=False,
 total_native_die_area_um2=sum(r['instances']*r['die_um'][0]*r['die_um'][1]for r in rows),
 total_native_active_area_um2=sum(r['instances']*r['active_area_um2']for r in rows))
(out/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
table=['| 物理块 | 功能 | 实例数 | die（µm） | 活动面积（µm²） | setup/hold（ns） | 实际版图 |','|---|---|---:|---:|---:|---:|---|']
for r in rows:
 w,h=r['die_um'];table.append(f"| {r['top']} | {r['function']} | {r['instances']} | {w:g}×{h:g} | {r['active_area_um2']:,.2f} | {r['minimum_setup_ns']:.6f}/{r['minimum_hold_ns']:.6f} | [图](../work/YUZE-LU/162/block-delivery-s1350/{r['image']['path']}) |")
doc='''# Issue162 新S与复用单块的最终交付

此表只接收实际全部原生四门及固定PG/新鲜RC/300MHz通过的物理块；S在内部增加788个BUF_X32驱动，无新增寄存器或协议延迟。其他20类精确合格实现复用。S/T均为标准单元存储。原S和旧335实例结果保留在历史索引。

**单块通过不代表系统通过。** 实际M11/M12/全场景PG/low-base-high分布RC/整机300MHz及真实组合程序仍由独立联合交付证明。R保留并由并行任务修改，此表不宣称其接入。

[全部六文件、实际源、SHA及最终PG/时序回执索引](../work/YUZE-LU/162/block-delivery-s1350/index.json)。下列图片均为实际交付PNG逐字节复制。实例数来自新S真实boundary-graph，非旧图估算。

'''+ '\n'.join(table)+f"\n\n实际原生实例共{data['instance_count']}，其中Link8为{data['counts']['control_link8']}。原生die面积加总{index['total_native_die_area_um2']:,.2f}µm²、活动面积加总{index['total_native_active_area_um2']:,.2f}µm²，均不含宏间留白。\n"
(repo/'docs/CONTROL_V1_BLOCK_DELIVERY.md').write_text(doc,encoding='utf-8')
# The current ownership table must follow the actual qualified graph. Keep
# historical checkpoints and the original 335-instance proof unchanged.
links=data['counts']['control_link8'];instances=data['instance_count']
assert instances==26+links and links<309
core=repo/'docs/CONTROL_V1.md';text=core.read_text(encoding='utf-8')
old_row='| boundary_links清单中的309个实例 | 同一种合格control_link8的309个独立实例 | 每实例1bit同步复位隔离状态，合计309bit；8条组合payload lane无数据寄存器。各实例的clk/reset取对应源分支，源pin、接收pin及填充lane逐项在boundary-graph中绑定，驱动及状态均属于固定原生宏 |'
new_row=f'| 新S实际boundary_links清单中的{links}个实例 | 同一种合格control_link8的{links}个独立实例 | 每实例1bit同步复位隔离状态，合计{links}bit；8条组合payload lane无数据寄存器。各源pin、接收pin、填充lane与clk/reset在实际新S boundary-graph中绑定；S内部788个BUF_X32无新增状态，S旁外置Link8为0。原309实例隔离状态表作为历史基线保留于checkpoint10/11 |'
old_summary='基础参考为20种、26实例；当前增加309个独立固定驱动/复位隔离实例后为21种、335实例。两种拓扑及新增状态分别索引，不借基础组合通过替代当前组合。'
new_summary=f'基础参考为20种、26实例；实际新S图增加{links}个独立固定驱动/复位隔离实例，为21种、{instances}实例。S原存储与控制状态保持归S，新增788个输出驱动亦归S M1–M10且不引入状态。旧309个Link8/335实例是保留基线；新旧拓扑分别索引，不能互相转授资格。实际新图及逐块六文件见CONTROL_V1_BLOCK_DELIVERY.md，系统M11/M12联合资格仍独立验收。'
assert text.count(old_row)==text.count(old_summary)==1
core.write_text(text.replace(old_row,new_row).replace(old_summary,new_summary),encoding='utf-8')
print(json.dumps(dict(ready=True,qualified_native_types=21,actual_instances=data['instance_count'],scope='individual blocks only, complete system still separate',out=str(out))))
