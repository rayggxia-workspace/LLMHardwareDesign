from pathlib import Path
import json,hashlib,collections,time
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);args=parser.parse_args()
r=Path(__file__).resolve().parents[3];w=r/'work/YUZE-LU/162';canonical=w/'block-delivery-r256-current363/index.json';d=json.loads(canonical.read_text(encoding='utf-8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
snap=d['actual_selection_snapshots']['topology/boundary-graph.json'];graph_path=r/snap['path'].replace('\\','/');assert sha(graph_path)==snap['sha256'];g=json.loads(graph_path.read_text());assert g['passed']and g['no_unassigned_active_logic']and len(g['instances'])==345
audit_path=w/'continuation-proof-48/r256-reset53-final-function-audit-392/receipt.json';audit=json.loads(audit_path.read_text());assert audit['passed']and audit['actual_new_scene']==g['scene']=='r256-seven-native/2'
roles={
'control_c_r8':'程序/描述符存储与有效位、PC/GPR/循环、完成槽、租约、配置和发射状态；八端点。',
'control_axil_bridge':'AXI-Lite AW/W/AR请求保持、配置事务及B/R应答/背压状态。',
'control_d':'有限搬运描述符、地址/长度/ID/4KiB切分、读写FIFO与握手、错误排空及S确认。',
'control_endpoint_queue':'两条256bit任务、两条64bit完成、224bit组包及指针/计数/错误状态；每个实例独立。',
'control_route_r8':'八路派发选择、两flit完成的owner/next_owner、轮转和事务锁定。',
'control_status_r8':'八队列及D/T错误的同步采样/sticky错误状态。',
'control_s_arbiter_r7':'七客户轮转/owner、命令与读写控制快照、地址/128bit数据及返回保持、准备/确认状态。',
'control_reset_distribution_r53':'恰好一位同步复位状态，共享到28原叶分支和25个最多16-Link8分支；53输出驱动无新增状态。',
'control_link8':'每实例恰好一位同步复位隔离状态；八条组合payload lane无数据寄存器。',
'control_adapter_m':'M任务字段、原生操作/位置/握手、输入与结果交接、完成/错误保持。',
'control_adapter_n':'N任务字段、多遍统计/回放位置、有限包槽、握手及完成/错误保持。',
'control_adapter_e':'E任务字段、格式/功能流水交接、有限包槽、位置/握手及完成/错误保持。',
'control_adapter_g':'G任务字段、输入/输出包槽、位置/握手及完成/错误保持。',
'control_adapter_s':'S任务字段、有限命令/包槽与位置/确认、两位预测ready状态、完成/错误保持。',
'control_adapter_t':'T任务字段、生产/消费和完成/释放的协议位置、有限包槽及完成/错误保持。',
'control_adapter_r':'R描述符、计数/索引/握手、128bit交接与512bit原生响应保持、完成/错误保持。',
'block_v2_m':'分块矩阵计算的数据/操作数缓冲、局部归约累加及原生协议流水状态。',
'block_v2_n':'归一化/Softmax等的统计上下文、有限回放/中间结果和原生协议流水状态。',
'block_v2_e':'逐元素/数值转换函数计算的数据与流水、上下文及原生协议状态。',
'block_v2_g':'激活/门运算的数据与流水、上下文及原生协议状态。',
'block_feed_s_macro':'16KiB标准单元工作存储、feeder及访问/确认状态；S1350内部788个BUF_X32不新增状态。',
'transaction6k':'6KiB标准单元结果暂存、生产/消费位置、背压和完成/释放生命周期。',
'r_stream_local':'R256双版本状态、点积/更新向量、局部统计、四抽头卷积历史及原生协议流水。'}
assert set(roles)==set(d['leaves'])==set(audit['actual_fixed_pg_full_view_sha256']);owners=[]
for name,top in sorted(g['instances'].items()):
 leaf=d['leaves'][top];assert leaf['qualified_individually']and len(leaf['six_files'])==6
 owners.append(dict(instance=name,physical_type=top,sequential_cell_owner_prefix=name+'/',state_responsibilities=roles[top],fixed_active_layers='M1-M10',qualified_individually=True,canonical_leaf_ref='block-delivery-r256-current363/index.json#/leaves/'+top,full_final_functional_view_sha256=audit['actual_fixed_pg_full_view_sha256'][top]))
counts=dict(collections.Counter(v['physical_type']for v in owners));assert counts['control_link8']==316 and counts['control_endpoint_queue']==8 and counts['control_reset_distribution_r53']==1
out=args.out or w/'state-ownership-current396.json';assert not out.exists();out.write_text(json.dumps(dict(passed=True,whole_system_qualified=False,captured_at=time.time(),scene=g['scene'],instance_count=345,leaf_types=23,instances_by_type=counts,ownership_rule='Every sequential cell in each bound complete final functional leaf view belongs to that explicitly instantiated fixed M1-M10 macro. Upper M11/M12 adds passive interconnect only. No clock/queue/arbiter/register state is attributed to an unlisted block. Descriptions summarize responsibilities, not exhaustive flop name inventories.',inputs={canonical.relative_to(r).as_posix():sha(canonical),graph_path.relative_to(r).as_posix():sha(graph_path),audit_path.relative_to(r).as_posix():sha(audit_path)},known_explicit_isolation_state_bits=dict(link8_total=316,reset_distribution_total=1,reset_output_branches=53),owners=owners,scope='Current closed345instance topology and all23 individually qualified fixedPG leaf identities match actual final-cell eight-program audit. State owner assignment and leaf qualification only; actual whole-system layout/PG/threeRC300MHz acceptance remains outstanding.'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(owners=len(owners),types=len(counts),path=out.name,sha256=sha(out))))
