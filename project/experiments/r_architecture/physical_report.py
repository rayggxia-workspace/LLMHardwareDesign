"""Summarize actual flow metrics, ODB loads, DEF and SPEF; no signoff inference."""
from pathlib import Path
from collections import Counter,defaultdict
import json,gzip,csv,math
from final_report import table
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended'
def main():
 snap=json.loads((E/'PHYSICAL_METRICS_SNAPSHOT.json').read_text());caps=json.loads((D/'baseline-evidence/lib-pin-capacitance-ff.json').read_text());geometry={};stages={};rows=[]
 for p in sorted(E.glob('attempt*/results/GEOMETRY.json')):
  data=json.loads(p.read_text())
  if isinstance(data,list):
   for r in data:geometry[r['candidate']]=r
 for p in sorted(E.glob('attempt*/results/*/*.tsv.gz')):
  c=p.parent.name
  if c not in ['A0','A1','B256']:continue
  lines=gzip.decompress(p.read_bytes()).decode().splitlines();units=int(lines[0].split('\t')[1]);nets=defaultdict(list)
  for line in lines[1:]:
   v=line.split('\t')
   if v[0]=='LOAD':nets[v[1]].append(v)
  stage=p.name.removesuffix('.tsv.gz');stages[c,stage]=(p,nets,units)
  for name,ls in nets.items():
   bins=Counter((int(x[4])//(128*units),int(x[5])//(128*units))for x in ls)
   rows.append(dict(candidate=c,stage=stage,net=name,loads=len(ls),nominal_pin_C_ff=sum(caps[x[2]+'/'+x[3]]for x in ls),occupied_128um_bins=len(bins),groups_max256_per_bin=sum(math.ceil(v/256)for v in bins.values()),evidence=str(p.relative_to(D))))
 with(D/'PHYSICAL_NETS.csv').open('w',newline='',encoding='utf-8-sig')as f:
  w=csv.DictWriter(f,list(rows[0])if rows else['candidate']);w.writeheader();w.writerows(rows)
 summary=[]
 for c,s in snap.items():
  m=s['metrics'];g=m.get('3_3_place_gp.json',{});route=m.get('5_2_route.json',{});finish=m.get('6_report.json',{});status='流程完成，独立验收未通过'if s['flow_receipt']and s['flow_receipt']['exit']==0 else'运行中/未完成，不能判通过'
  summary.append([c,status,g.get('globalplace__design__instance__area__stdcell','未测'),finish.get('finish__design__instance__area__stdcell','未测'),route.get('detailedroute__route__wirelength','未测'),route.get('detailedroute__route__drc_errors','未测'),finish.get('finish__timing__setup__ws','未测'),finish.get('finish__timing__hold__ws','未测'),finish.get('finish__timing__drv__setup_violation_count','未测'),finish.get('finish__timing__drv__hold_violation_count','未测'),finish.get('finish__timing__drv__max_cap','未测'),finish.get('finish__timing__drv__max_slew','未测')])
 gt=[]
 for c,g in geometry.items():
  for k,um in g.get('selected_def_centerline_um_by_layer',{}).items():
   if k not in ['role','bank_role']:continue
   cap=g.get('selected_spef_D_NET_capacitance',{}).get(k,'未测');gt.append([c,k,g.get('centerline_matches_router_within_2um_each_layer'),round(sum(um.values()),3),json.dumps(um),cap,g.get('spef_capacitance_unit','未测')])
 rootrows=[r for r in rows if r['net']in['role','bank_role']]
 report='''# 独立物理实现与真实几何证据

所有新物理结果只在独立attempt目录，未继承任何PR144资格。统一约束：Nangate45 M1–M10，300MHz（3.33333333333ns），uncertainty0.1ns、transition0.05ns，input/output max0.8ns/min0.2ns，BUF_X2输入驱动，输出50fF；die3000×3000µm、core20..2980，GPL density0.25、timing驱动关闭、后续repair开启，cap_margin40、hold_margin0.020。确定性四边内移两排M10 pin模板。A0/A1接口完全相同，pin坐标和约束相同。这里没有虚构M11/M12工艺层。

仅两个新候选：B256用于最小专用R/数据搬运代价的物理落地，A1用于已完整证明的银行读取重排；A0是匹配控制，不是第三个新候选。B1024虽为架构推荐点，本轮未做其完整P&R，不能称为已经得到最终物理宏。保持相同大floorplan以控制变量，B256只有约3.9%利用率，不能把这次长线结果称为其最优紧凑布局。

'''+table(['候选','实际状态','GP cell area µm²','最终cell area µm²','实际总线长µm','DRC','setup WNS ns','hold WNS ns','setup违规','hold违规','cap违规','slew违规'],summary)+'''
DRC=0只指router该检查，不替代独立LVS/制造DRC。流程exit0也不意味着setup/hold通过。时序失败的候选不能用模拟1ns时间单位冒充物理1GHz或300MHz产品性能。

## 原生ODB实际负载

'''+table(['候选','阶段','根net','直接负载','Liberty pin-C fF','128µm bins','每bin≤256分组和'],[[r['candidate'],r['stage'],r['net'],r['loads'],f"{r['nominal_pin_C_ff']:.6f}",r['occupied_128um_bins'],r['groups_max256_per_bin']]for r in rootrows])+'''
ODB输入sha256前后相同，native Tcl原生getITerms统计；空间点为负载单元原点，不假装是精确pin坐标。GP没有dbWire，绝不能把HPWL称实际线长。布局后的repair/CTS加入缓冲，根net的负载已变化；根net很小不等于其整个缓冲树没有负载。

## 已完成布线的DEF/SPEF

'''+table(['候选','根net','各层中心线与router核对','根net线长µm','实际层/线长µm','SPEF D_NET C','C单位'],gt)+'''
DEF采用完整NETS路径中心线逐层求和，与router逐层整数报告在每层2µm舍入误差以内核对；GEOMETRY.json保留差值、路径/文件SHA及不支持几何项，未通过核对的结果不得当作实测长度。SPEF DESIGN_FLOW PIN_CAP NONE，D_NET是提取线电容，不包含Liberty输入pin-C。不能把它和pin-C、placement估计电容混用。

B256总实际线长9,026,143µm，主要metal3约2,691,973µm、metal2约2,390,459µm、metal4约1,461,022µm。根role本身只有392.44µm、5个直接负载、10.279638fF pin-C，提取wire-C48.2004fF；其余大量控制线已分散到缓冲树/地址译码。每层全量见GEOMETRY.json。根net数值不能单独用来判断系统通信代价。

全局拥塞图片为ORFS真实final_congestion.webp；负载密度图为GP ODB坐标128µm bin计数，只是连接空间分布，不是路由拥塞。原始旧GP拥塞报告和图保留baseline-evidence，不能同新pin模板直接作受控布局对比。

## 时序路径及限制

attempt047预布局STA使用相同实际映射图、固定SDC，只保留JSON原cell名以精确选择131072个bank-Q/D及776个operand-D，逐候选报告STATE_READ_PATH/STATE_WRITE_PATH。这是零wire-RC的Liberty pin-load时序，不能替代上述最终提取时序。全扇入逻辑深度及地址控制路径分析另见SYNTHESIS_RESULTS/HIGH_FANOUT_TOP20；宏最终setup/hold取真实6_report.json。未实现的候选、无完整提取的对照写未测，不用负的未修复pin-load slack预测最终频率。

OpenROAD当前版本不带Python，早期attempt034失败明确保留；Tcl探针及DEF/SPEF读取成功才形成上述物理证据。SWIG wire.getLength返回指针的值不当作数字，采用核对通过的DEF坐标求长度。
'''
 (D/'PHYSICAL_RESULTS.md').write_text(report,encoding='utf-8')
 # Scientific plots, entirely from actual measured CSV and native coordinates.
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.colors import LogNorm
 figures=D/'figures';figures.mkdir(exist_ok=True)
 fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
 for ax,c in zip(axes,['A0','A1','B256']):
  key=(c,'3_3_place_gp');ax.set_title(c+' GP bank role loads');ax.set_xlabel('x (um)');ax.set_ylabel('y (um)');ax.set_xlim(0,3000);ax.set_ylim(0,3000)
  if key not in stages:ax.text(500,1500,'Not measured');continue
  _,nets,u=stages[key];ls=nets.get('bank_role',nets.get('role',[]));xy=[(int(x[4])/u,int(x[5])/u)for x in ls]
  if xy:ax.hist2d(*zip(*xy),bins=[range(0,3073,128)]*2,norm=LogNorm(vmin=1,vmax=4096),cmap='inferno')
 fig.savefig(figures/'gp-role-density.png',dpi=180);plt.close(fig)
 data=list(csv.DictReader((D/'SYSTEMC_RESULTS.csv').open(encoding='utf-8-sig')));fig,axes=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
 names=['W0-m0-n2048-t128.bin','W1-m0-l24-t128.bin','W2-m0-n8192-t16.bin','W3-t128.bin']
 colors={'A0':'#525252','B256':'#1f77b4','B512':'#2ca02c','B1024':'#ff7f0e','B2048':'#9467bd','C-M':'#8c564b','C-E':'#d62728'}
 for ax,w in zip(axes.flat,names):
  for r in data:
   if r['workload']!=w or r['attempt']not in['15','38']or r['policy']!='cache'or r['status']!='PASS':continue
   a=r['candidate'];ax.scatter(float(r['system_component_sum_um2'])/1e6,float(r['cycles']),color=colors[a],label=a);ax.annotate(a,(float(r['system_component_sum_um2'])/1e6,float(r['cycles'])),xytext=(3,3),textcoords='offset points',fontsize=8)
  ax.set_title(w.removesuffix('.bin'));ax.set_yscale('log');ax.set_xlabel('Mapped component area sum (mm2)');ax.set_ylabel('Recurrence job cycles');ax.grid(alpha=.2)
 fig.savefig(figures/'area-latency.png',dpi=180);plt.close(fig)
 print(json.dumps(dict(physical_net_rows=len(rows),figures=2)))
if __name__=='__main__':main()
