# Issue76 执行前协议：Granite有限expert→merge与微实现成本

2026-10-24 UTC+08；负责人Liangruizhi；[Issue76](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/76)。base PR75@ce2d08f257d4052da875d73938b3090f7f214f3e，已核ready/open/in_review、两CI success和远端报告/索引/精选字节。原74完整数学和Falcon服务不改写、不重复模型。新root D:/Projects/LLMHardwareDesign-granite-ports，task/76-granite-ports；子worktree D:/Projects/LLMHardwareDesign-76-service、-76-micro、-76-audit，对应独立task/76-*。

全部实际模型数据、完整整数/微程序/RTL/服务仅本人既有CPU服务器新/public/home/yuzelu/RuizhiLiang/issue76-granite-ports-20261024、Slurm lrz-i76-*。PC仅源码、小型合成边界、JSON和字节接收，进程临时D:/Projects/Codex/granite-ports-20261024-01。旧70/72/74权重和产物只读，无新模型/其他机器/Phi解封，不接管成员55/63或中断其他作业；不安装新软件。

## 数值与最小比较

固定74已独立PASS的Granite层0/13、R16、evaluation72两条件；ID/gate/单位、完整gate/up/down K、LUT、RNE/guard/merge顺序、0.22残差和完整nextnorm均不改。起点为current integer norm/router已发布的显式cut，入口数据IO计价；norm/router本身在此服务边界外。不是整模型E2E或重新cached-decode调度。服务不能仅用原FP或按rank配错expert。

最小三个merge累加窗口128/256/1536×M/V驻留×split/shared无功能标签×两层，共24配置；矩阵阵列微tile/有效PE和Kblock不因输出窗口增大而改变。每个同配置标签应科学轨迹逐字节零差；跨层、跨tile和真实驻留变化单列。若某窗口无法满足容量，保留拒绝；不能临时扩大RAM。

覆盖实际8expert完整gate/up→整数SiLU/门乘→512 mid完整扫描及A8→down→共同Q12宽8路merge→0.22真实残差→1536完整nextnorm。所有权重/静态scale、当前delta、单位、宽临时、gamma、LUT及最终消费者读写、外部backing和同步入账；完整8×1536 S32输出49152B无法免费驻V16KiB，必须流式tile/明确spill/背压。输出窗口选择不能改变每expert down先RQ再merge的函数。

## 资源与成本校准资格

两侧相同M256(16×16/B1有效16PE)、VR共8个S8/byte lane、单SFU和单ROM端口、M32KiB/V16KiB/R32KiB/S8×32KiB/EXT128MiB、128bit1RW银行/单BUS/2KiB有限FIFO。不得赠M私有宽ALU或无穷寄存器。SFU若采用额外专用byte ALU，需在库存明确标出SFU1且所有配置相同；不能把它混成VR8免费并行。bank-select/端点是候选连线，不代表已通过物理线长/时序。

宽乘、S8 digit提取、byte carry/shift/RNE/guard和128bit norm除法/isqrt必须绑定可执行微程序/独立参考；每标量依赖周期和动作数量分别记录，不能无条件将串行carry总量除8。跨输出的8lane并行须有合法任务/暂存/端口证明。所有operand/temp存储及IO计价，不用原生CPU宽乘速度推目标时隙。

优先用已有只读Verilator5.042/ORFS容器核实际S8/byte算术与同步ROM候选接口。禁止以原生宽乘/除/开方代替受限实现。ROM的返回宽度/容量/latency/II和SFU资源/暂存明确；RTL核验证、宽微程序解释执行、静态成本与未实现完整FSM分开。同步ROM的仿真周期不是工艺ROM时序。未校准/漏费条目拒绝用于排名，保留准确失败/工具阻塞，继续独立工作。

## 验证和交付

先工具探测和微实现pilot，再以冻结成本表做24服务。独立接收不导入producer，重构数值绑定、完整生命周期、affine地址/1RW/BUS/FIFO/ROM/宽成本与计数；至少port/capacity/numeric/widthfee/ROM五种实际artifact重SHA负例，旧整8路驻V例必须容量拒绝。配对/标签/实际瓶颈与归档source/input/output SHA可复查。

每phase干净commit/源SHA/source.zip，独立新out、实际命令/Slurm/环境/模型revision；不得覆盖旧运行。适当小测试、相关旧模块回归、check_project、diffcheck；完整证据留授权服务器、仓库精选与索引/报告/Block取舍/个人进度/交接。同一PR持续交付，不自合并/done。登记PR5 pending；board.json404/无Projects能力，看板unverified/同步pending、管理员/审查人待指定。


## 正式服务执行前的唯一范围修订

在工具探测/静态pack阶段、正式service尚未执行时增加fullH1536累加窗口。原因：12288B完整S64 merge与完整6144B Q12输出不一定同时live；先完成全部expert mid缓存S0，释放front向量临时，down保持物理O16输出/RQ且即merge，最后分片直接EXT后nextnorm，可使完整acc合法驻V16KiB。必须由独立生命周期/offset/1RW检查给结论，不能用静态总和人为拒绝，也不能把8路49152B返回变成合法。物理M/RQ tile16、全部精度/库存/函数不变。其余128/256控制保留，只扩这一真正影响边界的分叉，不扫更多tile；原执行前初版16配置作为历史，正式最小集24。
