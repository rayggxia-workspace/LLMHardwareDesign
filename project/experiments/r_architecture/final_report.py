"""Generate final research tables from immutable measured receipts, never estimates as measurements."""
from pathlib import Path
import json,csv,hashlib,gzip,collections,datetime
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def text(name,s):(D/name).write_text(s.strip()+'\n',encoding='utf-8')
def table(headers,rows):return '|'+ '|'.join(headers)+'|\n|'+ '|'.join(['---']*len(headers))+'|\n'+''.join('|'+ '|'.join(str(v)for v in row)+'|\n'for row in rows)
def csvwrite(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with(D/name).open('w',newline='',encoding='utf-8-sig')as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def main():
 stamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
 inv={p.stem:load(p)for p in(E/'attempt030/results').glob('*.json')if p.stem!='INVENTORY'}
 inv.update({p.stem:load(p)for p in(E/'attempt041/results').glob('*.json')if p.stem not in ['INVENTORY','A2_ELIGIBILITY']})
 # An A2 receipt is consumed only after the complete proof and same-source map passed.
 a2proof=None
 for n,kind in [(51,'A2h'),(43,'A2g'),(36,'A2g')]:
  p=E/f'attempt{n:03d}/results/{kind}-full-proof/receipt.json';mp=E/f'attempt{n:03d}/results/{kind}-map/receipt.json'
  if p.exists():
   a2proof=load(p)
   ip=E/f'attempt{n:03d}/results/{kind}-map/INVENTORY.json'
   if a2proof.get('passed')and mp.exists()and load(mp).get('passed')and ip.exists():inv['A2']=load(ip)
   break
 native=E/'attempt055/unit/c_wide_native/INVENTORY.json'
 if native.exists():inv['C-N-native']=load(native)
 for p in (E/'attempt058/results').glob('*.json'):
  if p.stem not in inv:continue
  x=load(p);old=inv[p.stem];assert x['mapped_sha256']==old['mapped_sha256']and x['cell_count']==old['cell_count']and abs(x['area_um2']-old['area_um2'])<1e-6
  inv[p.stem]=x
 costs={k:inv[k]['area_um2']for k in ['block_v2_m','block_v2_e','block_feed_s16k','txn_ctrl','control_support','link_router']}
 common=sum(costs.values());sys={k:common+inv[k]['area_um2']for k in ['A0','A1','B256','B512','B1024','B2048']+(['A2']if'A2'in inv else[])}
 sys.update({'C-M':common+inv['C-wide']['area_um2']-costs['block_v2_m']+inv['C-finish']['area_um2'],'C-E':common+inv['C-E-wide']['area_um2']-costs['block_v2_e']+inv['C-finish']['area_um2']})
 if 'C-N-native'in inv:sys['C-N']=common+inv['C-N-native']['area_um2']+inv['C-finish']['area_um2']
 sr=[];fan=[]
 for k,v in inv.items():
  if'area_um2'not in v:continue
  root=next(iter(v.get('bank_role',{}).values()),{});c=v['cells'];detail=v.get('module_details',{}).get(v['top'],{})
  row=dict(candidate=k,mapped_sha256=v['mapped_sha256'],area_um2=v['area_um2'],cells=v['cell_count'],DFF=sum(n for t,n in c.items()if t.startswith('DFF')),MUX=sum(n for t,n in c.items()if t.startswith('MUX')),BUF=sum(n for t,n in c.items()if t.startswith(('BUF','CLKBUF'))),INV=sum(n for t,n in c.items()if t.startswith('INV')),AOI=sum(n for t,n in c.items()if t.startswith('AOI')),OAI=sum(n for t,n in c.items()if t.startswith('OAI')),bank_role_direct=root.get('direct_pins','N/A'),bank_role_nominal_pin_C_ff=root.get('nominal_input_capacitance_ff','N/A'),bank_role_reachable_comb_cells=root.get('transitive_combinational_cells','N/A'),bank_role_reachable_sequential_input_pins=root.get('transitive_sequential_input_pins','N/A'),system_component_sum_um2=sys.get(k,''),read_D_max_allfanin_logic_depth=detail.get('max_logic_depth_all_fanins',{}).get('operand_read_D','未测'),write_D_max_allfanin_logic_depth=detail.get('max_logic_depth_all_fanins',{}).get('state_write_D','未测'))
  high=detail.get('high_fanout_summary',{})
  row.update(nonclock_high256_nets=high.get('nonclock_nets_fanout_ge256','未测'),nonclock_high256_input_pins=high.get('direct_input_pins_sum','未测'),nonclock_high256_pin_C_ff=high.get('pin_capacitance_sum_ff','未测'),all_nonclock_signal_nets=high.get('all_nonclock_nets','未测'),all_nonclock_signal_input_pins=high.get('all_nonclock_input_pins','未测'),all_nonclock_signal_pin_C_ff=high.get('all_nonclock_nominal_pin_C_ff','未测'))
  sr.append(row)
  for module,d in v.get('module_details',{}).items():
   for rank,n in enumerate(d['top20_nonclock'],1):fan.append(dict(candidate=k,module=module,rank=rank,net=n['net'],loads=n['direct_pins'],nominal_pin_C_ff=n['nominal_input_capacitance_ff'],upstream_first_register_or_port=';'.join(n['first_sequential_or_input_sources'])))
 csvwrite('SYNTHESIS_RESULTS.csv',sr);csvwrite('HIGH_FANOUT_TOP20.csv',fan)
 common_cells=sum(inv[k]['cell_count']for k in costs);area_rows=[]
 for k,area in sys.items():
  if k in ['C-M','C-E']:
   engine='block_v2_m'if k=='C-M'else'block_v2_e';wrapper='C-wide'if k=='C-M'else'C-E-wide';cells=common_cells+inv[wrapper]['cell_count']-inv[engine]['cell_count']+inv['C-finish']['cell_count'];bits=0
  elif k=='C-N':cells=common_cells+inv['C-N-native']['cell_count']+inv['C-finish']['cell_count'];bits=0
  else:cells=common_cells+inv[k]['cell_count'];bits=2*(int(k[1:])if k.startswith('B')else 2048)*32
  area_rows.append(dict(candidate=k,component_sum_um2=round(area,6),component_sum_cells=cells,R_state_bits=bits,R_state_DFF_X1_only_area_um2=round(bits*4.522,6),S_work_storage_bits=131072,S_full_mapped_area_um2=costs['block_feed_s16k'],scope='measured standalone component sum; not integrated chip area; state DFF area included, do not add twice'))
 csvwrite('SYSTEM_AREA_RESULTS.csv',area_rows)
 allrows=[];summary=[]
 for n in [15,22,27,38,45,53,55,56]:
  p=E/f'attempt{n:03d}/results/RESULTS.json'
  if not p.exists():continue
  raw=load(p);summary.append([n,len(raw),sum(x.get('status')=='PASS'for x in raw),sum(x.get('status','').startswith('UNSUPPORTED')for x in raw)])
  for r in raw:
   a=r.get('architecture');a=('A0'if a==0 else'B'+str(r['capacity'])if a==1 else'C-M'if a==2 else'C-E'if a==3 else'C-N'if a==4 else str(a));q=dict(attempt=n,candidate=a,workload=r['workload'],input_sha256=r.get('input_sha256',''),status=r.get('status','未测'),policy=r.get('policy','cache'),latency=r.get('latency',''),bandwidth=r.get('bandwidth',''))
   q.update({k:v for k,v in r.items()if not isinstance(v,(dict,list))and k not in ['architecture','capacity','workload','policy','input_sha256','latency','bandwidth']})
   if r.get('status')=='PASS':
    cycles=r['cycles'];fullcycles=sum(r['stages'].values());q.update(system_component_sum_um2=sys[a],cycles_including_setup=fullcycles,one_time_setup_cycles=fullcycles-cycles,cycle_window='recurrence window excludes initial reset/context creation; includes state loads, compute, transfer, commit/rollback',cycles_per_complete_token=cycles/r['tokens'],complete_tokens_per_simcycle=r['tokens']/cycles,cycles_per_layer_token=cycles/(r['layers']*r['tokens']),layer_tokens_per_simcycle=r['layers']*r['tokens']/cycles,DRAM_total_bytes=r['DRAM_read_bytes']+r['DRAM_write_bytes'],DRAM_average_bytes_per_cycle=(r['DRAM_read_bytes']+r['DRAM_write_bytes'])/fullcycles,R_mul_slots_utilization=r.get('R_wide_mul_events',0)/(8*fullcycles),native_S32_slots_utilization=r.get('E_native_S32_mul_events',0)/(8*fullcycles),M_physical_slots_utilization=r.get('M_S8_physical_mul_events',0)/(64*fullcycles),E_physical_slots_utilization=r.get('E_S16_physical_mul_events',0)/(8*fullcycles),M_useful_fraction_of_executed_products=r.get('M_S8_useful_mul_events',0)/max(1,r.get('M_S8_physical_mul_events',0)),E_useful_fraction_of_executed_products=r.get('E_S16_useful_mul_events',0)/max(1,r.get('E_S16_physical_mul_events',0)))
   for family in ['stages','traffic','ports']:
    for k,v in r.get(family,{}).items():q[family+'.'+k]=v
   allrows.append(q)
 csvwrite('SYSTEMC_RESULTS.csv',allrows)
 # Default measured comparisons, with separate evidence-derived A1 points.
 default=[dict(r)for r in allrows if r['attempt']in [15,38,55]and r['status']=='PASS']
 for r in list(default):
  if r['candidate']=='A0':
   for a in ['A1']+(['A2']if'A2'in inv else[]):
    x=dict(r,candidate=a,system_component_sum_um2=sys[a],performance_provenance='derived from complete cycle/ISA equivalence to A0; not a separate '+a+' cosimulation');default.append(x)
 frontier=[]
 groups=collections.defaultdict(list)
 for r in default:groups[(r['workload'],r['policy'])].append(r)
 for group,rs in groups.items():
  for r in rs:
   dims=['system_component_sum_um2','cycles','DRAM_total_bytes'];dom=[s['candidate']for s in rs if all(s[k]<=r[k]for k in dims)and any(s[k]<r[k]for k in dims)]
   frontier.append(dict(workload=group[0],policy=group[1],candidate=r['candidate'],non_dominated=not dom,dominated_by=';'.join(dom),area_um2=r['system_component_sum_um2'],cycles=r['cycles'],DRAM_bytes=r['DRAM_total_bytes'],performance_provenance=r.get('performance_provenance','RTL/SystemC measured')))
 csvwrite('PARETO_RESULTS.csv',frontier)
 picks=['W0-m0-n2048-t128.bin','W1-m0-l24-t128.bin','W2-m0-n8192-t16.bin','W3-t128.bin'];compact=[]
 for w in picks:
  for a in ['A0','B256','B512','B1024','B2048','C-M','C-E']+(['C-N']if'C-N'in sys else[]):
   r=next((r for r in default if r['workload']==w and r['candidate']==a and r['policy']=='cache'),None)
   compact.append([w.removesuffix('.bin'),a,r['cycles']if r else'不支持',r['DRAM_read_bytes']if r else'—',r['DRAM_write_bytes']if r else'—',f'{sys[a]:.3f}'])
 comp=table(['工作负载','候选','周期','DRAM读B','DRAM写B','组件面积和µm²'],compact)
 root=inv['A0']['bank_role']['block_v1_r'];root1=inv['A1']['bank_role']['block_v1_r'];a2status='完整证明尚未完成，未授权标准单元综合；未测面积/扇出，不能淘汰或判优。'if not a2proof else json.dumps(a2proof,ensure_ascii=False)
 if'A2'in inv:
  v=inv['A2'];rt=v['bank_role']['block_v1_r'];top=v['module_details']['block_v1_r']['top20_nonclock'][0]
  a2status=f"最终A2h（源SHA {a2proof['rtl_sha256']}）完整146137状态bit+132输出bit、772/772义务通过；回归和同配置映射通过。面积{v['area_um2']:.3f}µm²，cells={v['cell_count']}，role直接{rt['direct_pins']}、pin-C={rt['nominal_input_capacitance_ff']:.6f}fF；最大非时钟net {top['net']} 有{top['direct_pins']}负载。未做其物理实现；不能把综合结果当最终布线结果。"
 bp=load(D/'baseline-evidence/physical-analysis.json');categories=[]
 for label,family,key in [('active','by_category','active_bank_pair'),('shadow','by_category','shadow_bank_pair'),('共享/优化读取','remaining400_categories','optimized_read_selection_shared_or_not_unique'),('写目标控制','remaining400_categories','write_target_control'),('共享读取/提交反相器','remaining400_categories','shared_read_and_commit_control')]:
  v=bp[family][key];categories.append([label,v['loads'],f"{v['pin_capacitance_ff']:.6f}",v['occupied_128um_bins'],json.dumps(v['bbox_cell_origins_um'])])
 electrical=[]
 for k in ['A0','A1','A2','B256','B512','B1024','B2048']:
  if k not in inv:continue
  h=inv[k]['module_details'][inv[k]['top']]['high_fanout_summary'];electrical.append([k,h['nonclock_nets_fanout_ge256'],h['direct_input_pins_sum'],h['pin_capacitance_sum_ff'],h.get('all_nonclock_nominal_pin_C_ff','未测')])
 comparisons=[]
 for k in ['A0','A1']+(['A2']if'A2'in inv else[]):
  v=inv[k];rt=v['bank_role']['block_v1_r'];md=v['module_details']['block_v1_r'];comparisons.append([k,f"{v['area_um2']:.3f}",v['cell_count'],rt['direct_pins'],f"{rt['nominal_input_capacitance_ff']:.3f}",md['top20_nonclock'][0]['direct_pins'],md['max_logic_depth_all_fanins']['operand_read_D'],md['max_logic_depth_all_fanins']['state_write_D']])
 text('FANOUT_ROOT_CAUSE.md',f'''# R 高扇出根因与证据

生成：{stamp}。历史GP与新映射严格分开；完整历史分类/实例/坐标在baseline-evidence/REPORT.md及其JSON/CSV。新映射SHA见SYNTHESIS_RESULTS.csv，不能和历史ODB混用。

原始bank_role=92,059输入pin：active读取65,536，shadow读取26,123，其他/共享读取396，写控制3，共享反相器1。共享反相器不强制归为写入。91686个MUX2_X1/S加373个其他pin；direct不是可达组合门数，不包含跨DFF的下一周期影响。

实际源为bank_role寄存器Q，原映射DFF_X1实例`$auto$ff.cc:337:slice$2874097`；历史GP中同实例已resize为DFF_X2，位置约(377.7525,541.767)µm。92059输入pin也恰好对应92059个不同负载单元。全部逐实例/类型/pin/坐标与映射绑定保存在baseline-evidence/direct-loads.tsv.gz及bank-role-direct-categories.json.gz，压缩前后SHA在COMPLETE_DIRECT_EVIDENCE.json。

{table(['逻辑类别','单元/输入pin','pin-C fF','128µm bins','单元原点bbox µm'],categories)}

{table(['标准单元类型','直接输入pin数'],sorted(collections.Counter({}).items())) if False else table(['类型/pin','数量'],sorted(root['load_types'].items(),key=lambda x:-x[1]))}

直接nominal Liberty pin-C={root['nominal_input_capacitance_ff']:.6f}fF。历史GP根net估计C=232347.91fF，不是布线提取。历史578是Σceil(每128µm空间bin负载/256)，实际占用bin376，不能把578称为实际地理bin数。GP没有dbWire，无法给出该GP的实际路由金属层/线长。

A1完整等价后，role直接{root1['direct_pins']}，pin-C={root1['nominal_input_capacitance_ff']:.6f}fF。直接374个通向读取、3个通向写入、1个共享read/write/commit。组合可达{root1['transitive_combinational_cells']}cells，首次顺序端点{root1['transitive_sequential_input_pins']}pins；原始为{root['transitive_combinational_cells']}cells和{root['transitive_sequential_input_pins']}pins。端点相同但拓扑变化，不能把间接扇出加到直接负载作92059核对。

{table(['A1新高扇出net','直接pin','pin-C fF','首层顺序/输入来源'],[[x['net'],x['loads'],f"{x['nominal_pin_C_ff']:.3f}",x['upstream_first_register_or_port']]for x in fan if x['candidate']=='A1'][:8])}

{table(['候选','≥256负载非时钟net数','该集合总输入pin','该集合pin-C fF','所有非时钟信号net pin-C fF'],electrical)}

合计排除clock及常量连接，只统计实际整数net ID上的输入pin-C，不含wire-C。A1的全部非时钟信号pin-C较A0降低9.06%，虽然≥256负载集合略升0.63%；A2该集合更低，但全部pin-C比A1高约2.09%。不能用任一个阈值集合替代全部网络成本，也不能把静态pin-C当切换能量。

64,551/64,545负载网确实来自row[2]/cmd_index[3]/phase组合选择；32,784/32,778来自row[0]/cmd_index[1]/phase。不是凭abc临时名猜测。完整前20、所有标准单元类型、≥256负载网总pin-C、全扇入逻辑深度均见CSV和attempt041/results/*.json。该总pin-C包含数据net，不是role等效电容或切换能量。

历史key相关2056/4352负载来自8位生成寄存器 `$\\key$rdreg[0]$q` 的bit0/bit2，另有2696负载的反相网。其D首层时序来源是row和context/valid/phase控制，不是key/query数值寄存器；真实MUX分别选择key[72][14]/key[73][14]以及query[146][15]/query[150][15]。首次顺序下游均为operand_b，没有bank写入D。负载集中在x约64..715、y约94..829µm，而bank_role全片展开。对应pin-C为3411.673141/7025.745635/4381.457737fF（精确值见原JSON）。共同根因是寄存器数组的动态读地址选择/译码，不是同一条net，也不是key数值的广播。

A2：{a2status}

{table(['同容量结构','面积µm²','总cells','role直接pin','role pin-C fF','最大非时钟fanout','读取全扇入深度','写入全扇入深度'],comparisons)}

最终A2h实际仍保留64811负载的row/cmd_index/phase译码，role也回升到18765，面积比A1增加4.44%，没有解决最大广播网。按完整等价对应相同周期行为，A1在面积/周期/外存流量三维投影支配A2；但A2高扇出集合pin-C更低，不等于所有电气维度均劣。分组命名本身不能保证局部物理控制，也不能因此绕过综合筛选直接增加一次昂贵P&R。
''')
 text('ARCHITECTURES.md',f'''# 候选架构及统一边界

两条实验轴不能混为一个ISA等价问题。用户要求的具体组合共八个基础点：A0/A1/A2，B256/B512/B1024/B2048，C；C分别保留M、E整数分解及新增宽整数扩展C-N三个实现。

{table(['候选','实际结构','保持与变化'],[['A0','原始双2048×S32、8lane','冻结源码，不更改命令/延迟'],['A1','bank内地址选择，再选择active/shadow','全部动态读点、状态读出、两种状态路径；写控制逐字不变'],['A2h','每bank32个64-word组，局部读写译码/银行选择','容量、8lane、接口时序和原子提交不变；完整证明为准'],['B256/512/1024/2048','每bank容量如名，8×S32×S33、跨块dot/error上下文','新流式ISA，必须以端到端完整任务比较'],['C-M','冻结M的S8数位乘法+真实96bit归并+65bitfinish','15或25发射，64乘积仅8有用'],['C-E','冻结E的S16数位乘法+同类归并/finish','base128数位积≤16129，避免S16饱和，8乘积均有用'],['C-N','E旁新增8×精确S32×S33宽乘法+同一finish，无本地状态bank','显式新增73074.190µm²，2cycle乘法，完整外部状态事务']])}

S严格16KiB：4个256×128单1RW bank，但只有一个窄请求口；共享512bit宽读独占全部bank，窄口受仲裁，响应受背压。模型不提供额外并发窄口。所有存储均为标准单元寄存器映射，不称SRAM宏。

GDN跨块顺序：全状态decay→全状态预测dot→一次全局RNE/误差→广播→全部块更新→完整读出归约→全事务提交。SSM为decay/注入→全读出/skip。四抽头卷积保留3×8 S32历史；任意块溢出拒绝整个事务。R-stream的dot/error在块交换时保留，绝不是每块独立执行原R EXEC/COMMIT。

外存old/candidate双版本、context/owner/epoch/position和pending write ack由实际txn_ctrl检查。所有写回完成及计算检查通过才发布一个版本；失败不修改旧版本。S使用显式窄口搬运，R/S交换双方bank，容量峰值由reserve检查。分块scratch、控制元数据和一个128bit搬运缓存计入S保留1536B；C缓存条件同时计旧/新状态和系数，否则使用256B流式scratch。

control_support是512B微码+384B并行RF的可综合成本模型，router为4源4目的128bit、单flit、有背压的轮转共享链路。两者单独RTL测试/映射；尚未把全部kernel微程序和DMA做成完整集成RTL系统。SystemC调度器逐拍驱动算术和txn RTL，S模型与真实S逐信号校准；DRAM为参数化服务模型。这是经校准的架构研究，不是新完整芯片验收。

CSV中cycles为初始reset/context创建之后的递推窗口，包含状态/系数载入、运算、搬运及提交/回滚；cycles_including_setup=全部stages之和给出含一次性初始化的总周期。端口/乘法事件计数覆盖初始化，因此平均带宽和利用率用总周期分母；逐token trace给出每层token的真实起止，不用平均值替代尾延迟。

任务边界从Q/K/V/系数就绪开始，到递推输出和状态发布/回滚完成为止；W1包含全部指定层和token，未包括投影/归一化等完整LLM计算。模拟1ns仅时间单位，周期不能直接套用物理300MHz失败候选的时钟。
''')
 proof=load(E/'attempt035/results/A1-full-proof/receipt.json')
 text('FUNCTIONAL_VALIDATION.md',f'''# 功能、数值和事务验证

生成：{stamp}。PASS仅针对所列范围；没有将未执行检查标通过。

{table(['attempt','总记录','实际PASS','原R容量不支持'],summary)}

上述为最终逐拍RTL/SystemC联合模型，不把早期未校准attempt003/005架构扫描混入最终计数。全部case的文件SHA、seed、完整输入与期望状态在远程attempt003/results/corpus/MANIFEST.json；63份共93954508B。W0 256/1024/2048×1/16/128 token；W1 8/24层×1024×1/16/128；W2 4096/8192×1/16/128；GDN/SSM均覆盖；W3卷积1/16/128。另零值、极值/溢出、拒绝提交、reset、无效命令、连续递推及响应背压。都是合成负载。

原始A0/A1/早期A2各3种初始化回归，每次240递推+100卷积、379979检查、178456周期。A2g在attempt028、最终A2h在attempt048均完成三初始化回归通过。原始R独立corpus交叉检查51PASS/12W2不支持，57377526检查、29225412驱动周期。R-stream四容量各63实际RTLcase全部通过，每容量28174656检查。C-N新增宽乘法240组1920乘积验证通过，2cycle延迟；完整任务126组及敏感性/真实strip额外94组联合模型结果另列attempt055/056，不使用窄E实测结果替代。原始R不能执行W2，不列为通过。

A1严格完整顺序等价：{proof['state_bits']}个状态bit及{proof['original_output_bits']}个外部输出bit，{proof['partitions']}个封闭精确组合锥义务全部SAT通过。覆盖SHA={proof['coverage_sha256']}。每个状态D和每个输出恰好覆盖；所有Q按相同已定义初值/任意未初始化值逐bit配对，证明任意相应状态与输入的一步转移，因而归纳建立全时序等价。没有假定内部不变量、黑盒乘法或忽略银行状态。正例及错误银行负例真实运行。分区是完整证明分解，不是用局部证明代替整体。源/证书/每个分区回执见attempt035；完整证明成功后才执行原map.ys。

A2h完整证明：{a2status}

S实际RTL对照：21024周期、1009154信号检查、6600仲裁冲突、3044窄响应保持及4926宽响应保持检查。M/E冻结bench通过。M宽重构240组1920乘积、finish1000组8000检查；E宽重构240组1920乘积通过。txn_ctrl 162544检查/20000随机命令，包括在途写/错误身份/迟到ack/reset drain；control_support400试验9938检查，router30000周期通过。

整数oracle采用独立Python任意精度RNE、逐阶段fits32和S32回绕；RTL及C++实现独立复核全部状态/输出，而不是只比摘要。超过2048的扩展沿8lane增加row数，先完整归约再RNE，不按块舍入；W2最大行数1024，S32×S16归约范围仍适合S64。S32误差/状态转换及错误标记与冻结R一致。

统一事务失败保持上个已发布版本；reset按原始接口使上下文失效，必须重新加载。没有承诺掉电恢复尚未写回的dirty resident状态。边界flags发生位置固定并存档，不能推广为穷尽任意周期故障注入。attempt022/045实际加入三周期响应保持，主attempt015不把其旧flags8当成已测保持开销。

真实配置attempt027（E见045）：Qwen3.5 key128×value8的单状态strip，维度来自冻结算子图7.2/7.3；输入/系数仍为固定合成整数，不是真实权重或完整头/层精度测试。完整32头×128×128状态每层单版本2MiB、双版本4MiB，24递推层96MiB；一个strip1024S32，完整层512strips。2048原R不能免费把两个独立strip拼一个EXEC，否则8路dot会混合两个输出组。
''')
 text('SYSTEM_COST_MODEL.md',f'''# 统一组件和能量边界

{table(['共同组件','映射单元面积µm²'],[[k,f'{v:.3f}']for k,v in costs.items()])}

共同面积和={common:.3f}µm²。各R候选总组件和=共同组件+对应R；C-M/E为共同组件+宽重构包装整体−被复用M/E+finish。全部来源是实际Liberty单元面积，并非裸RTL运算符估算。S面积已含在共同组件，R内部bank已含在R映射面积，不再重复添加bit面积。

C共享M/E的和是假设支持独占借用已有引擎的架构组件和，不是完整集成测量：微程序、普通E/M与重构的仲裁/旁路没有完成集成版RTL。保持原M/E并把完整重构模块另加的保守重复引擎组件和分别为C-M={sys['C-M']+costs['block_v2_m']:.3f}、C-E={sys['C-E']+costs['block_v2_e']:.3f}µm²；这不是未知集成控制开销的全系统面积上界。实际完整共享控制面积须后续集成验证，不用组件预算冒充实际系统验收面积。controller/router单独映射的成本已计入所有点，但不代表所需完整系统控制恰好等于该成本。

{table(['候选','组件面积和µm²'],[[k,f'{v:.3f}']for k,v in sys.items()])}

所有DDR流量经S的128bit暂存并各消耗一次写和一次读，是本轮统一选择的搬运策略；DDR直接经有限寄存器旁路R没有建模，不能把此S瓶颈当作R-lite不可改变的物理下限。普通M/E与递推任务的同时混部未测；cache_shared只校准S宽读竞争。端口计数为有效载荷，不含完整路由包头、ready/valid翻转、时钟树及完整DMA RTL集成开销。

没有工艺校准的每操作动态能量，所有功耗/能耗列均为未测。采用可复现参数式：E_dyn = e_R65*N_Rmul + e_M8*N_Mphysical + e_E16*N_Ephysical + e_merge96*N_merge + e_finish65*N_finish + Σ(e_link,port*B_port) + e_Srd*B_Srd + e_Swr*B_Swr + e_Drd*B_Drd + e_Dwr*B_Dwr + e_ctrl*N_ctrl + e_native32*N_native32。各事件/字节在SYSTEMC_RESULTS.csv，单位系数需真实校准后才能给焦耳或能量Pareto。ORFS默认toggle估计功耗和IRdrop不充当能量校准。

模型串行调度，因此无DMA/计算重叠收益；报告的是固定可复现策略，不是各架构最优调度极限。端口平均带宽=B/cycles，瞬时上限按实际口宽和服务拍数；1个128bit DMA staging packet/单flit链路及最多1个未完成写的约束明确。共享S策略额外竞争宽口，记录真实S_conflicts、S_port_wait及S_background_wide。通用多源并发网络仲裁FIFO峰值、全芯片布线面积和DDRC/PHY面积未测，不编造为零。外部DDRC/PHY视为共同边界；DRAM双版本容量/读写量纳入，不算成片上SRAM面积。
''')
 text('BOTTLENECK_ANALYSIS.md',f'''# 瓶颈转移与系统净收益

{comp}

默认外存latency40cycle、16B/cycle、cache策略。CSV保留全部其他策略/带宽/延迟/边界，不按挑选的一张表替代完整结果。cycles排除初始上下文创建；cycles_including_setup给全部阶段和。每层token延迟和吞吐见CSV，完整逐事务trace记录首尾周期。

空间：B256本体比A0小80.64%，组件和仅降低40.18%，共同S16K面积1,059,287.278µm²已经成为主项；缩R不能消掉S、DMA和版本控制。B2048 role降到494但本体面积只减1.58%，单元数反而772736对709124，说明扇出下降不等于总成本显著下降。

时间：2048状态连续128token，A0=213442cycle；B256=1399616，慢6.56倍，B2048=220224也没有超过原R。小R省面积但失去驻留、增加分块和R/S交换。24层×1024×128token，B1024和B2048均10380288，A0=11870208；这时增大本地容量没有改善1024的独立8输出任务。W2无原R合法对照：B256779344，B2048715728，增大R收益有限，完整状态流量成为瓶颈。

通信：A1消除了原role广播，却将约64551负载移到row/cmd_index/phase译码；state-write/read全扇入逻辑深度56/18变57/20，并无逻辑深度收益。≥256负载非时钟网的pin-C合计，A0为755798.294fF、A1为760569.775fF（约+0.63%），A2为625587.611fF；该集合包含数据网且阈值固定，不是总网络电容或总控制能量。全部非时钟信号net pin-C为A0 3002587.365、A1 2730520.880（−9.06%）、A2 2787523.150fF；A1在总pin-C上仍有实际收益。B也存在rd_index/局部译码广播，见HIGH_FANOUT_TOP20.csv。必须联合看物理wire、pin-C、缓冲/拥塞，不能只看role。

存储：W1所有候选须逐层换上下文；24层状态远超本地容量。W2每个token必须维护全局预测、一次误差及全局提交，不是独立tile事务。old/candidate外存和S占用均显式计入；真实模型一层4MiB双版本、24层96MiB，所有本地R都必须依赖更高层存储。cache/dram、latency20/BW4和latency100/BW8以及共享S竞争实际扫描见CSV，不能把DRAM访问量下降等同无争用。

无R的窄引擎复用：C-E比C-M更快，仍在W0慢约156倍、W1慢约37.8倍于B1024，主要在宽整数数位分解/归并与握手，不是DDR带宽。执行期间独占E，影响其它向量工作；M路径64乘积仅8有用，浪费更显著。八路小乘法的100%有效乘积比例不代表每cycle利用率100%。即使C面积略省，不能拿这个局部收益抵销所有负载的百倍延迟。

新增宽整数的无R：C-N真实增加73074.190µm²宽乘法硬件，总组件和1555837.458µm²；W0=3622656cycle、W1=35180544、W2=1803744、W3=33416，所有63负载×cache/dram共126PASS。它比C-E快约9～11倍，但W1仍为B1024的3.39倍，面积低30.68%；W0比A0慢16.97倍。W1的S端口9532440cycle、finish本体12681216cycle、宽乘法含握手6303744cycle，出现明确的宽乘法→finish/S搬运瓶颈转移。C-N是合法Pareto候选，不能沿用窄M/E方案的百倍延迟结论。其预布局零wire pin-load STA尚未满足300MHz，最终物理时序未测，不能把周期优势直接当作同频硅片速度。

卷积：W3 B=27912cycle，A0=32790，C-E=132744、C-N=33416。单看卷积不足以证明需要完整2048状态R；专用小卷积单元可能更经济，但本轮未新增该候选，面积/完整物理结果未测。

物理结果见PHYSICAL_RESULTS.md；单独R宏完成route不代表全部M/E/S系统完成布局布线或新宏通过生产验收。所有结论限定固定数值语义和调度策略。
''')
 text('PARETO_ANALYSIS.md','''# 面积、延迟和通信Pareto

PARETO_RESULTS.csv逐workload/策略比较实际组件面积和、完整任务周期、DRAM读写字节，三个维度全部不劣且至少一维更优才构成支配。没有跨不支持工作负载强行比较；A1性能点来自完整时序等价，明确标明不是独立SystemC运行。物理面积、线长和可用Fmax未齐全时不混入该架构Pareto。能量无校准，不给伪造能量Pareto。所有Pareto的延迟维度是cycle；特别C-N和finish的预布局时序未满足300MHz，不能当作相同频率的最终芯片时间Pareto。

C-E/C-N与B256构成不同面积/延迟端，B1024适合1024状态多层、A1保留2048驻留优势；不产生一个脱离工作负载的万能赢家。A1对A2的支配只在该三维投影成立；A2的高扇出集合总pin-C更低，电气或能量维度不能忽略，也没有其物理线长证据。若需要实际普通M/E共享接入，C-E面积下界尚需补充集成控制，保守重复引擎组件预算见SYSTEM_COST_MODEL.md。最终应在明确工作负载权重、延迟上限、可用带宽后选点，不能用任意加权平均替用户决定。
''')
 text('FINAL_RECOMMENDATION.md',f'''# R 架构研究结论

**延迟优先建议保留8路专用R：1024状态多层任务优先R-lite1024，2048连续驻留任务保留A1/2048。面积优先且可承受额外搬运/延迟时，显式新增宽整数能力的无R C-N也是可行Pareto点，不能一概排除。** 这是一项有适用条件的架构推荐，不是新宏物理验收。

1. **读取重排值得保留，但不能宣称已经解决布线。** 原92059主要是读取选择；A1完整顺序等价通过，role降至378，R面积1458349.256→1289693.818µm²（−11.56%）。新64551负载地址/phase译码证明瓶颈确实转移。实际匹配物理结果和限制见PHYSICAL_RESULTS.md。
2. **R-lite1024是本轮较均衡的容量点。** 24层1024状态×128token与B2048同为10380288cycle，组件和2244540.984对2903992.224µm²，减少约22.71%；Qwen3.5的key128×value8 strip正好1024状态。它不等同完整GDN头/层，一层仍有512strips和外存状态。
3. **不要为面积统一选256。** 本体最小但2048状态驻留负载慢6.56倍；总组件面积收益约40%，外存/S/控制没有消失。若任务主要256状态、面积优先且延迟可接受，B256仍是合法Pareto点。
4. **2048有明确驻留价值。** W0 2048×128token原R213442cycle，B10241289024；应保留容量或选择调度能让较小R真实驻留的方案，不能用W1结果外推所有任务。A1完整等价故保留A0周期行为，但物理300MHz仍须实测确认。
5. **区分窄引擎复用和显式新增宽算术。** C-E比C-M快但仍有显著分解代价。C-N实际新增73074.190µm²、8路宽乘法，乘法2cycle；126组全负载联合仿真通过。它在W1需要35180544cycle，约为B1024的3.39倍，组件和1555837.458µm²、低30.68%；W3只有33416cycle。面积优先时值得选，但S搬运、串行finish与双版本状态仍有代价，不是免费复用原E，也没有物理验收。
6. **4096/8192必须采用跨块全局事务。** 原R不支持，B/C已以独立完整整数扩展逐值验证。该范围不同R容量的周期接近，系统流量开始主导，继续优化单条bank_role不是主要收益来源。

{comp}

C-N的新增宽乘法单元已单独RTL测试并映射，实际总组件和采用保留原M/E、额外加宽乘法和finish的成本，不减去任何原E面积；仍不是集成全芯片面积。

没有校准能量，不能给最低焦耳的赢家；没有集成全芯片RTL/布局布线，组件面积和不等于最终芯片面积。建议的可操作决策是保留8路专用R、按1024为常见工作集选点，同时保留A1/2048的驻留场景；最终投产点必须以真实任务分布和独立物理验收决定。A2状态：{a2status}

PR144及Issue143的原始RTL/物理数据库/验收目录不修改；新候选不继承已有验收资格。历史失败和资源限制均保留，最终未测项见各报告，未把流程exit0写成timing/signoff通过。
''')
 text('README.md',f'''# Issue157：R 架构探索与端到端代价分析

生成：{stamp}。独立研究分支task/157-r-architecture；不修改PR144/Issue143。先读FINAL_RECOMMENDATION.md，然后FUNCTIONAL_VALIDATION.md、FANOUT_ROOT_CAUSE.md、BOTTLENECK_ANALYSIS.md和PHYSICAL_RESULTS.md。

交付：ARCHITECTURES.md、FUNCTIONAL_VALIDATION.md、SYNTHESIS_RESULTS.csv、SYSTEM_AREA_RESULTS.csv、SYSTEMC_RESULTS.csv、BOTTLENECK_ANALYSIS.md、PARETO_ANALYSIS.md、FINAL_RECOMMENDATION.md；另有HIGH_FANOUT_TOP20.csv、PARETO_RESULTS.csv、SYSTEM_COST_MODEL.md及物理证据。大ODB/映射/可执行文件保存在远程不纳入Git；收集manifest逐文件SHA，原始文件位置和映射SHA可复核。

冻结版本见BASELINE.json/EXTRA_INPUTS.json及inputs。R SHA4032c5edcbee9d38e1a51dd9f9c533e414d5263dd2440d7104a1688e73ca382d；A1 d826dc5f562a55ceb1fce6dbbb04e3f21b4ceafe00187607413cbeed97b28b96；最终A2h 3f45ac421563fe7360862bb0056266089895c55e2579c012f92bf2af71e4358e。历史map4df8e33ce3a23efc2c3f1e08f1cae2c474e73391522349cf7fde5b3b8fcfd865与新A0map15d180a81662f629bbecfc756084e0eb7112624bd140d2672820e2ef241d11df不同，不能替换配对。

固定环境：Yosys0.68+post、Nangate45 typical Liberty SHA8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1，容器/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif SHA49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a；Verilator5.042在容器内运行，SystemC3.0.1共享库SHA930767c0ec7a203c38552201a22fa2a27a319c47d4d9019096457a674bca0848。命令及Slurm allocation记录在每attempt/BUNDLE/FILES.sha256和部署回执。

远程根/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture。每个attempt为不可变源归档；不得用当前checkout冒充先前实验源。复现时新建目录并提取对应source.tar，sha256sum --check FILES.sha256，然后在相同容器和Slurm allocation下执行该attempt的sbatch脚本。完整RTL测试/形式证明在标准单元映射前；A1入口partition_run.py，最终A2h入口grouped_local.py（RTL回归/降低）及grouped_prove.py（全状态关系重证/映射）；系统入口cosim_sweep.py，E补充e_followup.py；C-N入口native.sbatch及native_followup.sbatch（新增硬件测试→映射→联合模型）；物理入口physical.py --candidate A0/A1/B256（仅在满足证明/筛选门后）。

本地重新生成统计：python project/experiments/r_architecture/final_report.py。完整数值输入在attempt003/results/corpus（63份固定seed、逐文件SHA），真实维度strip在027/corpus。所有最终周期以实际RTL/SystemC联合运行015/022/027/038/045/053/055/056为主，早期003/005快速模型只保留历史，不混入最终CSV。

调度采用节点内动态独立任务队列，编译每项16线程，形式证明封闭锥并行48项，联合仿真最多96个单核任务；依赖未满足不占满全节点盲目启动P&R。最多两个新物理候选B256和A1，A0为匹配基线控制。仅取消本任务被替代的proof作业，回执记录精确jobid，未取消其它作业。management-hub/Projects看板登记待管理员完成，不影响实验文件复核。
''')
 print(json.dumps(dict(rows=len(allrows),synthesis=len(sr),pareto=len(frontier),common_area=common,system_area=sys,summary=summary),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
