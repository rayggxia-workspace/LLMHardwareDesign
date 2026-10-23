# P1–P15参考能力清单到Block与证据的映射

Issue47，2026-10-23，Liangruizhi。来源是用户本轮提供的[截图](../sources/primitive-capabilities-2026-10-23.png)，
原始出处未提供；它是分类参考，**不是标准、已有硬件合同或扩权指令**。不修改PR26作者的功能benchmark文档。
截图SHA256 `a034a5b9ae2ef986d831e810a6858df363a8071c1bae298e0ca0de202d4e7c06`。
对接[六类Block候选](BLOCK_CANDIDATE_V1.md)及[最小决策实验](BLOCK_MINIMAL_EXPERIMENTS_V1.md)。

| 编号/用户参考定义 | 候选归属与预连线 | 实际已有/本轮证据 | 未覆盖或需计费项 |
| --- | --- | --- | --- |
| P1 乘加、点积、分块累加 | M累加反馈；A/R宽归约 | C1/Issue39及本轮QK8、P15×V8整数oracle | 高位digit合并/完整K屏障；参考代码不是矩阵RTL吞吐 |
| P2 ADD/SUB/MUL/FMA、标量/行/列广播 | V lane；R更新与A输出 | C1整数加减/宽乘；共享参数在软件引用 | 浮点FMA不由整数乘加证明；舍入次序/广播端口及扇出不得免费 |
| P3 分段归约、平方和、行点积 | V reduce、A softmax/PV、R projection | C1 RMS候选与本轮组内逐行归约 | 分段axis、u48/i64/u64范围及跨tile生命周期 |
| P4 EXP或EXP2 | A exp ROM；V门控参数 | 显式4097项EXP表参与本轮整数softmax | EXP2未实现；ROM端口/截止范围/带宽/延迟须计费 |
| P5 倒数、倒平方根 | V isqrt/div；A normalization | C1整数开方/恢复除法，softmax用u64除法 | 不等价于任意精度浮点rsqrt；32/64迭代、宽寄存器与误差合同 |
| P6 比较、选择、带索引极值 | V/A mask/max，D控制 | 本轮因果mask/max；C1比较 | indexed argmax/top-k硬件未验证，不能凭max宣称MoE路由覆盖 |
| P7 转换、量化/反量化、缩放/饱和/打包 | M RQ与V格式路径 | RQ32旧RTL，RQ33/本轮整数RNE与饱和参考 | norm/RoPE及FP32→codes、Q scale/M/r编译为浮点辅助；无在线整数前端或新RQ33 RTL |
| P8 查表与可选插值 | A/V ROM→lane | EXP表整数访问，旧C1 SiLU插值 | 新GELU表与全域误差未定，ROM复制/多端口不能免费 |
| P9 stride分块load/store、二维DMA | S地址/仲裁＋D DMA | 当前只有软件数组布局/地址语义 | 本轮不测DMA/硬件stride服务；跨stride物理span、64B拍与反压待E2 |
| P10 gather/scatter、间接寻址 | D descriptor、S页表 | 仅候选映射；本轮未实现通用间接访问 | 页表、有效性、乱序/热点冲突、缓存miss；原生MoE/MLA不在完整覆盖 |
| P11 转置、重排、切分、合并 | V shuffle/pack、M operand入口 | 捕获的明确head/token轴与软件切分 | NumPy/Torch view不证明零搬运硬件；物理重排scratch/读写另计 |
| P12 一对多分发、数据保留与重复读取 | S KV→M行tile；V共享g | 本轮一个KV头供其Q0/Q1，参数冻结、逻辑数据只存一份 | 不证明物理多播或省两次bank读取；需端口/调度/扇出验证 |
| P13 状态/累加上下文读改写 | R/A内部反馈，S backing | 本轮不可变KV追加、epoch、旧前缀不重写、chunk等价 | 递推/多上下文/滑窗ring、实际read-modify-write端口与backing仍待测 |
| P14 循环、地址步进、动态索引控制 | D循环/依赖→M/V/A/R | 本轮连续token与chunk序的参考校验 | Python循环不是控制器RTL；变长/动态路由范围未验 |
| P15 命令队列、事件/信号量、完成/同步 | D credit/完成→state commit | 本轮软件拒绝过期epoch、乱序/重复追加、发布前读取 | 未证明异步命令队列、内存一致性、死锁自由或多生产者硬件 |

## 由此补强的划分理由

不能把15类能力变成15个Block。P1/P3/P7/P13在局部归约处强耦合，P9/P12/P14/P15决定它能否被持续供数。
因此继续保留M/V/A/R/S/D候选，补上每条边的格式/复用/状态发布合同，而非只列算术名字。
当前能验证的P12/P13/P15是一个真实GQA组的**数值与软件状态契约**，物理广播/端口/队列仍待E2/E4。
有浮点辅助的规范边界应显式保留和计账；验证给定计算语义的拆分/整数模块不必被扩大成等待完整整数语言质量通过。
若论文主张模型质量，仍需对应独立评价，不能把本轮局部误差写成语言质量已验收。

## 当前最小执行与分工

本机Issue47只补E1a的冻结校准/GQA共享/因果KV/epoch；不会因一张能力表就逐项新增昂贵实验。
E1b模型质量与较长输入按原任务实际范围处理，不构成本轮EDA固定语义比较的额外等待条件。
师兄Issue32/PR36已in_review，本机只核范围，未整合其数值包。给师兄的请求收敛为复用已有数据索引、必要时补
短代表切片，**不恢复其已取消的追加完整语言质量任务**。
用户随后要求师兄尽量一次完成有界模型批次，可纳入Qwen3-4B/Gemma12B/Phi等代表；
前述最小请求不构成禁止。本机仍不下载/执行这些较大模型，不提前整合师兄结果。
