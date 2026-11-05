from pathlib import Path
import json,datetime
h=Path(r'D:\Data\电路实验');r=h/'LLMHardwareDesign-worktrees/issue-162-control';w=r/'work/YUZE-LU/162';d=json.loads((w/'continuation-proof-69/index.json').read_text(encoding='utf-8'));now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
s=f'''# Issue162：保护引脚出口与受限网络分阶段布线，继续最终组合验收

更新时间：{now}。Issue162 / PR163，任务继续，不合并。[原字节与源绑定索引](continuation-proof-69/index.json)保存{len(d['rows'])}项服务器记录（{sum(x['copied']for x in d['rows'])}项原字节）及{len(d['helpers'])}项辅助材料。**仍无完整零冲突布线及几何、PG、三档分布RC300MHz联合通过。** 保留current363的23类/138个已验收单块文件、S1350内部驱动/R256、345项状态归属和当前453三初态8程序/473-480轨迹；不操作外部R修订。

source828=7daab15ae41bd116922eb318f252df130404f929，1004文件，归档SHA4c052f7e5c82a2dcb313a8776add82d02b08dd42705eddef5ce60a23181464cd。实际829通过51案例/27拒绝及原回归；835核对关闭功能的45份实际输入、路由输出与过滤计时日志相对实际810逐字一致。每二进制增加800项独立小网格BFS、路径、障碍和展开预算检查，原132端点/166730堆顺序/1200weighted及精确/资源检查保留。8300/8301真实16次首轮平均excess为2924048.125/2923316.4375，第7轮仍约254万，均未收敛。

841/848在独立16CPU槽内各重放16份真实首轮完整路径，保留所有11149网、24760端点、原输入/搜索决策/失败，要求所有首轮计数与原运行完全一致。观测相对其他当前树保持固定、减去自身占用后的免费出口：native前缀后平均35.375个普通端点无出口，16K/64K maze完整首轮后分别1830.125/1852.625；native前缀自身平均excess20065.5。860逐trial核对两组native前缀观测完全相同。完整路径逐边/过孔/连通/线长检查通过不等于无短路或物理通过；这些快照本来有冲突。大文件保留远端，索引复用实际计算节点检查时记录的SHA并复核当前字节长度，未在登录节点重哈希。840静态全局唯一匹配覆盖全部24760端点，但忽略真实同时布线与原生预算，只是搜索候选。

source854=320b76e74ddff029dc58802c8b091604afd7c182，1005文件，归档SHAba2d96b85b4f7f47dad29b688c77dc453bdcd3064755dfd8c42ffd4743285c7d。默认关闭的`--route-native-prefix-first`先让1229条受限网用原有限资源搜索收敛，仅在真正零冲突时冻结实际路径，再独立开始普通网完整80轮；日志分开，native通过绝不作为全局通过。`--route-pin-access all/after-native/none`采用全局最大匹配保护一步M11与合法偶数M12出口，保留同网别名，失败不宣称全局不可行；预留点只是搜索约束，不冒充实际导线。无新增网格大小工作数组，无宏、数值格式、物理预算或最终门变更。

实际855完整通过57案例、35项非法/失败案例，包括native通过但完整图必须失败且无最终输出；六个新增分阶段案例检查真实端点所有权、奇偶过孔、冻结前缀与最终路径逐字相同及原独立完整路径检查。每二进制增加200项独立穷举小邻域最大匹配对照。858核对原51案例实际输入、输出、过滤计时日志与829逐字一致；17项最终门/resource/场景/预尝试/pool/weighted头文件、原精确类和有限分支字节不变。33组std堆、3trace、3权重1回放及全部原检查保留。新8560/8561分别提前保护全部出口、在native后保护普通出口；864核对14份完整七阶段规格及原六键验收配置/函数/轨迹绑定，866核对32个实际本人子进程、32份逐字输入、16CPU亲和和实际内存准入。当前native余冲突仍需继续消除；软件正确不替代组合物理验收。

我把855规格在854冻结结束前加入旧node6队列，触发source62旧调度器对缺manifest的断言，父作业95101于11:50退出，三个本任务子步骤被终止。这是排队顺序错误，不是服务器、物理或资源失败。859完整保留旧日志、状态、作业记录和所有部分输出，使用已实测source269稳健队列恢复父作业97097；三个完整七阶段链以原源和参数在新目录8590/8591/8592重跑。855从已冻结854执行并通过。以后提交队列前必须先等待冻结完成并验证manifest。原7个父节点及外部任务未改。首版本地证据复制遇Windows长路径限制，已原样移存workspace外的control162-proof69-incomplete-01，随后用长路径访问重取并逐字校验，无远程结果改写。

861/863按完整规格SHA、UID/job/实际node5/PID/命令/冻结源/out/453图核对，只替换本人旧5451的95155.117子步骤，所有旧源/规格/失败/部分输出保留。仍是8父节点；c64 4×16、c96 6×16动态补位。node5/6各192GiB最终预测需要246.4GiB实际MemAvailable，控制器实际准入另核验；未因单任务扩核而降低独立任务并发。实际855及858通过后才发射新完整组合。825/836/857精确非强推读回；登记PR5 pending、缺board.json故看板unverified/同步pending、审查人待指定。继续真实M11/M12零冲突布线、几何/原生XOR、PG、low/base/high分布RC下300MHz setup/hold/电气及原联合门，最终六文件/版图/组合验证/源绑定索引仍待整体验收。
'''
(w/'continuation-checkpoint-69.md').write_bytes(s.encode())
brief=f'''# Issue162：分阶段布线及引脚出口保护进入真实组合

更新时间：{now}。[Checkpoint69](PLACEHOLDERcontinuation-checkpoint-69.md) / [原字节与源绑定索引](PLACEHOLDERcontinuation-proof-69/index.json)。实际855通过57案例/35非法或失败案例，包含native通过而完整图必须失败；858核对原51组实际输入/输出/过滤日志逐字一致，17项最终门与原有限分支不变。841/848各16份真实全路径重放证明首轮存在约1800个失去免费出口的普通端点，继续针对出口和布线顺序修复。8560/8561已进入原完整七阶段链，**当前没有完整零冲突布线、三档RC300MHz联合物理通过。** 不合并、不放宽门，保留23类已验收单块、S内部驱动/R256及外部R工作。

node6旧父队列因我提前排入尚未冻结完的源触发断言，所有原始失败与部分输出保留；859用已验收调度器恢复第8父节点97097，三个中断候选只在新目录8590/8591/8592重跑。c64 4×16/c96 6×16动态补位及实际1.2倍加16GiB内存门保持。继续完成全部组合最终几何、PG、真实M11/M12、300MHz及六文件/版图/源索引交付。登记PR5 pending；缺board.json，看板unverified/同步pending；审查人待指定。

'''
for rel,prefix in [('docs/CONTROL_V1.md','../work/YUZE-LU/162/'),('docs/STATUS.md','../work/YUZE-LU/162/'),('progress/YUZE-LU/STATUS.md','../../work/YUZE-LU/162/')]:
 p=r/rel;p.write_bytes((brief.replace('PLACEHOLDER',prefix)+p.read_text(encoding='utf-8')).encode())
p=r/'.gitattributes';p.write_bytes(p.read_bytes()+b'\nwork/YUZE-LU/162/continuation-proof-69/** -text\n')
p=r/'docs/ARCHITECTURE.md';p.write_bytes(p.read_bytes()+'''\n## Issue162 受限网络分阶段与全局引脚出口保护\n\nsource854新增默认关闭的`--route-native-prefix-first`及`--route-pin-access {none,all,after-native}`，要求原critical/finite/negotiated/deferred上下文。匹配只预留搜索点，不计作真实导线；native先按原80轮预算搜索，只有零冲突才冻结实际路径，普通网另从原第0轮开始；两个阶段日志分离。最终wrapper独立核对冻结前缀与最终输出路径相同，仍要求所有原全图边/过孔/连通/线长/几何/PG/三档RC300MHz和联合验收。native零冲突不是系统通过。软件回归仍用`system_upper.py --directional-regression-only --route-regression-baseline <source735/tree_router.cpp>`及完整manifest/graph/新out；实际855通过57案例/35非法或失败案例，858对旧51组真实输入/输出/过滤日志逐字对照actual829。每二进制附加200个最大匹配对独立穷举的小网格案例。生产8560/8561各16active/64attempts/16CPU，完整七阶段配置及当前453函数/轨迹绑定见Checkpoint69，不允许继承软件检查为物理通过。提交任何队列规格前必须等待源码冻结进程完成并实际核验source-manifest.json和freeze-import.json；不可依赖排队延迟保证源准备完成。\n'''.encode())
s=(h/'control162-verify-stage68.py').read_text(encoding='utf-8').replace('continuation-proof-68','continuation-proof-69');(h/'control162-verify-stage69.py').write_bytes(s.encode())
print(json.dumps(dict(remote_rows=len(d['rows']),staged_hashes_expected=sum(x['copied']for x in d['rows'])+len(d['helpers']))))
