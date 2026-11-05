from pathlib import Path
import datetime,json
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');w=r/'work/YUZE-LU/162';proof=w/'continuation-proof-56';d=json.loads((proof/'index.json').read_text(encoding='utf-8'));now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
s=f'''# Issue162：现有双向与独立普通代价实际回归通过，四组完整链继续

更新时间：{now}。Checkpoint56保存{len(d['rows'])}项服务器原字节及{len(d['helpers'])}项辅助材料；[索引](../work/YUZE-LU/162/continuation-proof-56/index.json)保留执行源、实际回归、完整候选队列、精确步骤替换和输入/进程绑定。系统物理验收仍未通过，失败继续定位，不合并。

500原有完整实际路由回归通过，包括120组原搜索、9组双向搜索、独立Dijkstra/有限资源oracle、预算拒绝与默认源字节回放；5010已发射当前453完整七阶段链。511新普通代价实际回归通过，包括原9方向/3资源/2前缀/3高权重和3普通代价混合网案例、26项拒绝、原默认字节回放和120独立完整状态oracle。每个新增混合案例实际产生普通代价计算步数，原受限前缀4网、有限scale1逐轮保持；不是只检查命令行枚举。

5120使用原4850同一实际453摆放4610/RNG4661/cost2/权重256/adaptive/逐轮前缀，仅对普通网使用独立代价64。515已逐字核对全部16个真实trial输入与4850相同，并通过自有node6的实际exe路径/UID过滤核对16个真实子进程都带普通代价64、8百万标签及逐轮前缀参数。有限资源分支逐字不变，resource_search.h及九项原最终验收源SHA不变。515切面尚无5120完整第一轮结果，不宣称速度或收敛改进。原生/输出电气预算不因代价参数改变。

当前453的真实最终单元三初态8程序与472独立视图/接线审计已通过；473三条实际外部握手轨迹仍运行，480协议/内存及六项破坏审计待其完成。这些功能证据不替代实际M11/M12完整路由、几何/原生XOR、PG、low/base/high分布RC、300MHz setup/hold/电气与联合源绑定。

520在所有替换前重新核对本人UID10011、父JobName/NodeList、精确SrunHost PID/命令/输出、345实例含R、冻结源/图和队列SHA。旧3890/3891/3841各16次固定尝试中至少5/7/7项已退出且不支持补位；仅取消对应95341.73/95098.141/95204.171子步骤，保留全部失败/存活部分输出、源和规格，不取消父作业，也不称其余尝试不可能。三条source510新完整链5190/5191/5192已先入队，再替换这些步骤，与5120组成两组必要条件合格摆放4610/4611 × 两种实际测试普通代价64/256的四组搜索；每项64次有限总尝试、16项活动、失败动态补位。没有增加硬件宏类型或放宽验收。

513此前只替换本人旧source388的3931步骤95101.108，以实际453程序通过和494具体寻路诊断为依据，原证据保留；这是为验证特定算法假设的资源重分配，不是该旧搜索失败/不可行结论。其他当前搜索、外部R和其他任务不动。

源510为6f497101199b00c7aea0d01e91d32989e64493b7，冻结994文件，归档SHA d4e0025498ec8b59fe452e0981e577bb350fc3cc3f1cd7fe7ff34e39e593a695；505/510精确非强推发布均已读回通过。Issue514新鲜完整正文读回相符、open且仅status:in_progress；PR正文读回相符、Draft/open/未合并、head为该源。看板仍unverified/同步pending，登记PR5仍pending，管理员/审查人待指定；未把这些正文更新称为看板同步。

固定物理单块规范仍23类/138文件，S1350内部驱动/R256及状态宿主绑定保留。七父节点运行、第八Resources排队，c64 4×16/c96 6×16与实际1.2倍预测+16GiB内存门不变。队列发射和小例通过都不能代替完整组合最终验收。
'''
(w/'continuation-checkpoint-56.md').write_bytes(s.replace('../work/YUZE-LU/162/','').encode())
for name in ['docs/CONTROL_V1.md','docs/STATUS.md','progress/YUZE-LU/STATUS.md']:
 p=r/name;p.write_bytes((s+'\n'+p.read_text(encoding='utf-8')).encode())
p=r/'.gitattributes';p.write_bytes(p.read_bytes()+b'\nwork/YUZE-LU/162/continuation-proof-56/** -text\n')
q=Path(__file__).with_name('control162-verify-stage47.py').read_text(encoding='utf-8').replace('continuation-proof-47','continuation-proof-56');Path(__file__).with_name('control162-verify-stage56.py').write_bytes(q.encode());print(now)
