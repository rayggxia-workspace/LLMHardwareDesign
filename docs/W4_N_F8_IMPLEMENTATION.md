# 主线四 W4：N组服务与RMS前归一化F8实现报告

关联Issue151 / PR152，负责人Melodydt。本轮新增真实、可综合的N外侧控制器和固定RMS-preNorm F8顶层，在既有M/E/G/S/T骨架中接入N统计、因子计算与S回放。原生N core、其divide/root/EXP实现以及原叶/P2/W1/W3文件保持不变。本轮功能通过范围是有界N服务与F8小核，不是完整Attention、全部F变体或实际样本模型规模验收。

## 1. 版本、基线与交付状态

开发研究输入为 `0101cc7e1e6d5718455fb45b61c7428439efc09a`，原生叶源继续固定 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。根任务已将PR144固定头 `d1f26884b13f8d0466bbaefe2fc6322a14c66df9` 合入研究任务分支，形成双父基线 `0e8e970359452b745cde09f77efeac041df5fd10`，父提交为上述0101与d1。该操作是研究分支吸收上游内容，不代表PR144或本研究PR已经合入main。

两个共享文档的冲突以保留双方内容的方式解决，YUZE进度文件由Git自动合并；本轮没有代写其他成员进展。根任务已读回PR为clean、mergeable=true；这些是分支可合并性状态，不是外部审查批准或任务验收。

实验回执保留运行时的研究parent0101和实际输入SHA。新增W4代码运行时尚未提交，不能将原实验commit倒填为后续merge0e或原生707；最终交付commit应另行记录。原生14源锁和新增文件逐字节SHA共同绑定实验输入，合入更新不扩大原有物理或功能资格。当前新增RTL指纹为：

| 文件 | SHA-256 |
| --- | --- |
| `block_w4_n_ctrl.sv` | `02e6e8f0538c8423481c2f30a3d0a2d392bae583551cbf7ffcc7cd947674cd01` |
| `block_w4_f8_top.sv` | `54905280f8b9dbfcd7440981fd4f4244c509ea8de5e1a8912a050c457ad75a8e` |

本文作为PR152的正式研究交付说明；线上Issue/PR、看板及验收状态按最终回执分别读回，不提前done。作者互查和根任务仿真不代替外部PR审查。

## 2. 为什么需要新增控制器

N的128-bit载荷包含ACK、原始score、EXP、归一化值、概率以及其它异构记录。完成一次N原生命令不等于整个group已经完成，也不等于结果已经存到S。RMS/L2必须先收集整组统计再按因子回放原值与gamma；Softmax必须先得到全组max，再用原score计算EXP，汇总EXP后才能产生概率。直接连总线或逐字独立归一化会破坏算法上下文。

新增模块把这些顺序变成真实RTL：独占上下文、真实读S、捕获响应、按phase选择native op、保持载荷、mask尾部、逐次写入并收ACK、最后才返回服务完成。没有要求所有载荷增加通用运行时role标签，类型由已接受命令和固定阶段保存；没有修改N端口或将新控制状态机放进原生N core。

| 本轮成果 | 实际改动与职责 |
| --- | --- |
| `block_w4_n_ctrl` | 一个S-backed group的BEGIN/STATS/finalize/replay调度；RMS/L2/Softmax；地址/容量/overlap准入；tail、响应分类、真实写ACK、饱和累计和失败poison |
| `block_w4_f8_top` | 新独立固定顶层，复用W3适配器及M/E/G/S/T；新增真实N实例、四路S owner、RMS8前归一化、本地RNE3/clipS8及原始残差分离 |
| 独立整数参考、向量与TB | 按公式独立产生Norm/Softmax、RNE/clip与F8各阶段期望；真实S/helper/native连接；数值、guard、握手、错误与恢复检查 |
| runner与证据 | 实际工具/配置/输入版本、源码快照、完整argv、退出码、日志及SHA；旧P2/W1/W3本轮重新回归 |

N controller的mode/count/address等是内部服务端口，便于本地固定控制器调用；F8对host仍只有16拍可变张量输入及生命周期接口，不提供host opcode、shape、地址、scale或程序装载。

## 3. N服务的准入与存储契约

当前profile只接受mode0 Softmax、1 RMS、2 L2，count1..257，每个普通S字容纳8个S16。令 `W=ceil(count/8)`，最大33字；最后一个native命令count=min(8,remaining)。Norm epsilon必须为非零U32；Softmax忽略epsilon。S为1024个128-bit字，所有实际使用区的末地址必须不超过1023。

RMS/L2的src/gamma/dst三段两两不重叠；Softmax的src/exp/dst两两不重叠，未用区不检查。检查使用扩展加法，不能通过10-bit地址回绕绕过边界。相邻区允许；in-place、overlap及超过257项是本controller当前不支持的profile，不能改写为算法永久非法。count257时每段33字/528B，三段共1584B，均是调用者须真实预约的片上空间，不是自动扩容或外存spill。

caller持有唯一N group和普通S helper lease到服务rsp消费，src/gamma整个服务不可变；不能在统计和回放中间插入另一group、TopK或其它驱动者。每次请求在valid&&ready时快照；S read先被捕获和消费才能发下一笔，native命令/响应也单在途。输入raw/gamma及输出尾部实际mask为零。完成rsp及error/saturated在背压期间保持。

## 4. N phase、数据流与计数

公共前半段为：BEGIN op0 → 全部W字raw STATS op1及ACK → FINALIZE_STATS op2及ACK。控制器不会在第一字统计后就归一化，也不将ACK送入tensor路径。

RMS/L2随后逐字重新读原src、读对应gamma，二者都捕获后发op5；仅将有效S16结果写dst，消费实际普通S写ACK后才下一字。最后一个dst ACK到达后才服务完成。

Softmax随后逐字重新读原score，发op3，返回的U16 EXP原样写exp并消费ACK；所有EXP写ACK完成后才发op4计算factor。然后逐字读exact EXP发op6，将Q14概率写dst并收ACK；最后一个dst ACK后才完成。统计阶段遍历全组，因此最后第257项成为新max时，前256项的EXP仍统一使用该全组max。

| 正常成功路径 | Native N命令/应答 | 普通S读 | 普通S写 | 普通S总请求/ACK |
| --- | --- | --- | --- | --- |
| RMS/L2，W字 | `2+2W` | `3W` | `W` | `4W` |
| Softmax，W字 | `3+3W` | `3W` | `2W` | `5W` |
| RMS/L2，count257/W33 | 68 | 99 | 33 | 132 |
| Softmax，count257/W33 | 102 | 99 | 66 | 165 |

普通S计数包含真正helper请求与读/写ACK；不把等待周期当额外事务，不按native固定延迟猜测完成。`cmd_op_hold`保存响应分类，op3/5/6才作为有效数据，其余本服务使用的op为控制/状态ACK。

## 5. 数值合同：gamma、epsilon与EXP

控制器不重新近似算术，使用未改的native N。RMS按原始整数码计算：

```text
A = floor(sumsq * 2^16 / count) + epsilon * 2^16
factor = floor(2^38 / isqrt(A))
output = clipS16(RNE30(x_raw * factor * gamma_raw))
```

L2不做count除法。gamma_raw=1024表达本profile的数学1，绑定输出Fin10；epsilon单位为输入整数码的平方，不能直接把某模型浮点epsilon填成同样数值，也不能仅凭128-bit接口就默认其它宏的定点单位兼容。

Softmax score为S16 Fin10，op3返回U16 code0..32768；32768的位模式0x8000必须保留，不能将其当负S16 score重新解释。因子为floor(2^44/sumEXP)，op6按EXP无符号码乘因子后RNE30、clip到[0,16384]，结果为非负S16 Q14概率。EXP与概率有不同语义，原始score只能用于op3，exact EXP用于op6。S的无损回放保留同一上下文lineage，不能擅自对EXP做数值变换后仍声称原样。

本轮没有接N统计诊断/TopK服务，N原生其它op和端口保留；函数存在不代表新增controller已经调度全部N功能。

## 6. F8：前归一化、固定窄化与原始残差

F8仍接受原x8与三份8×8 n-major权重，全部S8 Fin7。入口16×128=256B，实际有效200B和56B canonical零padding；16个实际写ACK后才允许start。原x先符号扩展成S16 Fin7保存466，再真实写gamma475={8×1024}。N固定RMS8、epsilon raw1，src466/gamma475/dst474。

N的Fin10结果写474且ACK后，top回读474，用新增真实组合函数逐lane RNE右移3、clipS8，得到Fin7的M输入，低64紧凑存8个S8、上64清零，再实际改写448并收ACK。这个窄化不是金属连线或E12别名：E12没有这里需要的RNE。负数使用算术floor与余数/奇偶作tie-even，例如-4→0、-12→-2；产生S8上溢时clip并累计saturated。它是本核特定窄化电路，不代表通用NUM服务已经实现。

M gate/up使用改写后的448；原始残差一直从466读取，E7左移3转Fin10存467。不能把Norm输出作为残差，否则模型结构改变。随后仍按W3有限合同执行三次投影、G门乘、down与E0残差：

```text
16字输入/ACK → start → 原x16写466/ACK → gamma写475/ACK
→ N RMS8 group → 474写ACK → 回读474/RNE3/clipS8
→ 448写ACK → E7原始残差 → M gate/op5存464
→ M up/op5存465 → G SiLU(gate)*up存468
→ mid三字padding实际写零 → M down(A16/B8)存472
→ E0 down+原残差存473/ACK → 真实S回读
→ T BEGIN1/WRITE/COMMIT/外部TAKE/RELEASE → 保留DONE
```

| S地址 | 内容 |
| --- | --- |
| 448..451 | 输入x容器；RUN后448改为norm窄化值，另3字保留本帧真实零padding |
| 452..463 | gate/up/down三组权重，各64B |
| 464/465 | 已量化gate/up，G使用前保留，M可随后清理复用 |
| 466/467 | 原始x16 / 原始残差Fin10 |
| 468..471 | mid8S16及3字实际零padding，供A16 loader |
| 472/473 | down / 最终残差输出Fin10 |
| 474/475 | N输出Fin10 / gamma8×1024 |

固定预约448..475共28字/448B。实体S仍16KiB、T仍6KiB，本核T只使用一字16B lease；没有把大Block封装当作内存容量增加。

F8正常帧普通S为39请求/39ACK=29写10读，RUN部分23笔=13写10读。相对W3的32笔增加gamma写1、N统计/回放/结果4笔、本地读474与写448各1，共7笔。其余15个M命令/应答、3个loader、2个E服务、1个G服务不变，新增1个N服务/4个native N命令及应答。四路owner LOCAL/E/G/N经真实MUX共享唯一helper，整次N服务直到rsp消费才切回LOCAL，最后写ACK已先消费。

## 7. 错误、poison与不可回滚的写ACK

BEGIN前的本地准入拒绝没有S/N副作用，返回error后可再接受请求。成功服务后下一请求显式发新BEGIN，清理Norm/Softmax group；没有声称BEGIN清理TopK或支持任意上下文互抢。

准入成功后，任何native或mem响应error都停止后续提交，保留error响应并置poison；服务响应消费后仍req_ready0/busy1，必须协调reset N/controller/helper才能再用。这样不会把可能已finalize、部分replay或部分写入的context当成干净新group。

在第一笔dst写前失败时dst未写，但Softmax scratch EXP可能已经可见。若已有目标字写成功，后续失败留下部分前缀；若写请求已被存储接受，WRITE_RSP再报error也不能撤回。N独立TB对第二个dst写ACK注入错误，明确检查前两字保留、第三字未写。真实当前helper没有普通S error信号、rsp_error固定0，TB注入不是新增存储故障检测资格。

F8接到N error后产生顺序internal_reset脉冲，协调N/Ncontroller/helper和其余叶复位，再保留一次error DONE；没有error/ready→reset组合环。prestart abort丢帧不造done，RUN abort返回一份保持的error完成，已有DONE遇abort保留error/sat且同拍ready只消费一次，hard reset取消有效性不造completion。已接受RAM写和外部已消费输出前缀不回滚；error/abort的sat只代表已退休/观察到的阶段。

## 8. 实际验证与局限

根任务实际使用本地ModelSim SE-64 2020.4、Python3.7标准库，在独立运行目录生成source快照、modelsim.ini和work库。本报告作者没有执行仿真，只读回以下日志/回执；所有compile/simulation exit0，CASE_PASS与receipt一致，所核日志SHA相符。

| 本轮实际运行 | 标记与结果 | 可支持的范围 |
| --- | --- | --- |
| `runs/n-r01` | `PASS_W4_N cases=29 cycles=20336` | 有界RMS/L2/Softmax数值、phase、tail、guard、握手、poison/reset、部分写前缀 |
| `runs/f8-r01` | `PASS_W4_F8_FFN8 cases=25 cycles=16323` | 固定RMS8-preNorm F8、独立原残差、RNE3、39事务及有限中断恢复 |
| `runs/regression-p2-w1-r01` | 47个标记，helper6/P2 MST13/W1 MST28 | 旧helper与两级MST真实回归 |
| `runs/regression-w3-r01` | 67个标记，adapter46/FFN21 | 旧E/G服务与无N的W3 FFN8真实回归 |

旧回归合计114个标记是本轮真实重新执行，不将旧目录中历史PASS直接转写成本轮结果。旧runner保留历史parent/new_W1等metadata标签，原回执不倒改；当前执行以本轮source origin、快照、SHA和argv说明。29/25及旧114都是有限检查标记，不是完整模型任务数或合法连接覆盖率。

N的11个数值向量覆盖RMS count1/8/257、L2 count8/257、Softmax count1/8/9/257：包括零、正负gamma、饱和、脏尾部、257末项新max、EXP32768及cutoff/round。另有4个背压、8个guard拒绝、本地拒绝后复用、3类runtime错误poison恢复及2类中途reset。TB逐native命令核对顺序/count/数据与gamma，逐S事务核对地址/读写/期望，成功目的和EXP逐字核验。

F8使用6个冻结参考输入，逐阶段及最终值比较，正常帧39/39、N4/4、M15/15、3loader、T释放都有单帧检查。新增N response保留时禁止提前窄化/投影、真实native op15错误无N目的/投影/T写且协调恢复、保留N response reset、暂停474真实ACK后abort恢复。F8没有因此覆盖L2/Softmax整条F链。

F8作者还读回整数设计检查：65536个S16值及literal边界的RNE3/clip参考比较通过。这是整数表达式验证，不替代8lane HDL展开、接线或时序；真实RTL证据来自F8 suite。独立oracle按公式重建N EXP1025和G2564表节点并核对冻结表，不使用DUT输出构造expected。

运行的完整vlib/vlog/vsim argv、cwd、工具版本/二进制SHA、配置、输入、原始stdout字节SHA、规范化log与退出码在各run-receipt。复跑需新空目录，按正式runner `--help` 和验收索引执行，保留失败尝试；管理结构检查只验证仓库管理格式。生成器的正式输入路径已修复，旧builder字节保留；两向量与两TB在新输出目录重生成逐字节相同，见w4-generator-reproduction.json及根w4-checks.json。

## 9. W4/L4与W5的真实完成边界

本轮落实了主线四的有界N服务，并开始把前归一化接入固定F8组合；触及W5的F链实施，但不能据此关闭完整W5。仍未闭合：

- 完整A的Q/K/V、全局Softmax/PV与长序列数据生存期；完整F的真实H/I、pre/postNorm变体、多字中间值和回放。
- 八个样本的实际尺寸映射、完整定点/质量准入、真实吞吐目标与多tile容量调度。
- TopK服务、N统计/诊断服务、多group交错或上下文切换、任意in-place/overlap。
- 外存/MEM路径、通用NUM、跨岛stored ACK与任意fork/join控制。系统有外存，本轮不实现或评价，并非永久排除。
- 全芯片母控、M11/M12永久产品绑定、CDC、完整复位分配及综合/P&R、PPA。

新N控制器、N实例、MUX、RNE/clip、寄存保持和握手均是真实有源RTL，物理实现必须预制；不能在M11/M12阶段凭连线补造。没有综合结果，不给新增面积/时序数字，也不因RMS8能运行而声称样本完整层已适配。

下一步应按有限家族/算子/格式/shape合同逐项扩展真实A/F链、数据容量与控制计划，并为各项建立独立输入、RTL组合、错误恢复与物理证据。研究分支可合并性、文件上传、外部审查、PR合并、看板同步和完整任务验收继续分别报告。
