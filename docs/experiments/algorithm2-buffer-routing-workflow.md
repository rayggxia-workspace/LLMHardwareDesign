# 算法 2 的直连、中继筛选和分段布线

本文以 [方案 PR #258](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/258) 和 [实现 PR #259](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/259) 为准，先用一个驱动引脚 `S`、一个接收引脚 `T` 说明流程。M1–M10 底座和预置 buffer 已固定。算法从端点的合法 M10 接点进入上层，生成 M11/M12 走线及 via10/via11。可选 buffer 来自底座资源清单，清单包含输入、输出接点和可用的电气数据。 [冻结边界与输入清单](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ddf9353d9b1538480423d2a14616a6558f31e46c/docs/plans/m11-m12-routing-plan.md#L24-L45)

**流程**　直连试布 → 检查负载或接收布后违规 → 粗筛 buffer → 对入围方案分段试布 → 比较完整方案 → 重新提取并复测

## 1. 先试两个引脚直连

A* 在 M11/M12 上试布 `S → T`，同时选合法接点和路径。走通后，用**搜出的金属线长换算的电容、过孔电容和接收端输入电容**估算 `S` 所带的负载。首次布线中，直连能布通且估算未超载时，可以直接保留。直连布不通或估算超载时，继续尝试允许的中继候选。

即使估算通过，布后提取和静态时序分析（STA）仍可能发现电容、转换时间或时序违规。修复入口会根据与旧路线绑定的违规记录重搜受影响的网，可以改走线，也可以改用预置 buffer。这就是旧 P16 的 VALID 案例所走的分支。 [直连与负载估算](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f/project/experiments/upper_router/resource_search.py#L50-L95) · [实测反馈入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f/project/experiments/upper_router/repair.py#L10-L39)

## 2. 用两段距离初筛 buffer

一个候选 `B` 对应一种分法：`S → B.in` 和 `B.out → T`。`S` 驱动前段及 `B` 的输入；`B` 的输出负责后段及 `T`。对可用的每个 `B`，先用两端的平面坐标粗估前段距离 `d1` 和后段距离 `d2`，距离是横向差与纵向差之和。

默认按 **`(max(d1, d2), d1 + d2)` 从小到大**排序，留前若干个候选试布。先压低最远的一段，因为两边驱动能力和线路条件相近时，长的那一段往往更难带。最长段相同时，再优先总距离更短的候选。

| 候选 | 前段距离 | 后段距离 | 最长段 | 总距离 |
| --- | ---: | ---: | ---: | ---: |
| A | 1 | 9 | 9 | 10 |
| B | 5 | 6 | **6** | 11 |

例子中先试 B，尽管 A 更靠近起点。若起点驱动较弱、buffer 输出更强，试布后也可能是 `3 + 7` 比 `5 + 5` 更合适。默认粗筛使用坐标计算，入围后才跑 A* 检查实际走线。允许多个中继时，按配置从已入围的短链继续增加中继，每级保留有限数量的候选。 [距离和排序实现](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f/project/experiments/upper_router/resource_search.py#L12-L47)

## 3. 对入围候选分段试布

- **前段 `S → B.in`。** A* 从 `S` 的合法接点出发。任一待选点 `n` 的启发函数 `h(n)`，是它到 `B.in` 最近合法接点的曼哈顿距离。
- **后段 `B.out → T`。** A* 从 `B.out` 的合法接点重新出发。这里 `h(n)` 改为 `n` 到 `T` 最近合法接点的曼哈顿距离。

两段都按 `g(n) + h(n)` 决定先展开哪个点。`g(n)` 累计已经走出的线长、换层过孔罚分和历史阻塞罚分，`h(n)` 估计从待选点到**本段目标**还要走多远。沿途检查实际轨道、金属和过孔的占用及间距，任何一段布不通就放弃这套候选。对比不同的 buffer 时，切换的是前后段端点，A* 的公式相同。 [A* 选点与接点检查](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f/project/experiments/upper_router/search.py#L19-L110) · [中继如何生成物理分段](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f/project/experiments/upper_router/repeaters.py#L83-L101)

## 4. 用试布结果比较方案，再做电气复测

两段都布通后，重新用各段的实际试布线长、过孔和接收端电容估算负载。前段计入 `B.in` 的输入电容，后段按 `B.out` 的驱动上限判断。默认依次比较**超载段数、超载总量**；反馈修复时接着优先有改动的路线；之后再比**总线长加中继罚分、过孔数量**。粗筛名次和最终试布评分有各自的作用。候选数量和搜索预算有限，最终方案没有全局最优保证。

布后按新几何重新提取寄生并跑 STA。旧 P16 的 VALID 在 300 MHz、高研究 RC 下，直连为 `4800 µm`，setup 裕量 `−238.876 ps`。用预置的 `BUF_X32` 之后，前后段分别为 `2416 µm` 和 `2400 µm`，总线长增加了 `16 µm`，但后半段由中继接力驱动，setup 裕量变为 `+33.879 ps`。这些数据来自历史 P16 的复跑。 [试布评分](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f/project/experiments/upper_router/resource_search.py#L59-L95) · [VALID 分段延迟与证据](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/642361aa404c76b7128c60777a184d47a83fa5e3/work/huangpingyang04-lgtm/228/valid-p16-timing-114157.md)

## 两点距离具体用在哪里

**粗筛 buffer 时**，距离是两个引脚代表坐标之间的估计，用来比较分段方案。**A* 试布时**，距离是当前待选点到本段最近合法接点的估计，用来排序待选点。两处都使用平面曼哈顿距离，例如横差 `3`、纵差 `4` 就记作 `7`。绕障碍后走出的金属线可能更长，负载估算和布后验证使用具体路线及过孔。
