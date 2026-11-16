# 算法 2 的直连、中继筛选和分段布线

本文以 [方案 PR #258](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/258) 和 [实现 PR #259](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/259) 为准，先用一个驱动引脚 `S`、一个接收引脚 `T` 说明流程。M1–M10 底座和预置 buffer 已固定。算法从端点的合法 M10 接点进入上层，生成 M11/M12 走线及 via10/via11。可选 buffer 来自底座资源清单，清单包含输入、输出接点和可用的电气数据。 [冻结边界与输入清单](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ddf9353d9b1538480423d2a14616a6558f31e46c/docs/plans/m11-m12-routing-plan.md#L24-L45)

**流程**　排定布线次序 → 直连试布 → 检查负载或接收布后违规 → 粗筛 buffer → 对入围方案分段试布 → 比较完整方案 → 重新提取并复测

第 0–4 节描述现有 A* 实现。第 5 节的 [CUGR 细粒度布线优化流程](#5-顶层拥塞时的补充优化)定义了激光直写 M11/M12 的几何搜索和修复方式。试布结果仍交给算法 2 做负载比较和布后核验。

## 0. 多根线争用通道时，先布可选路线少的线

整批网按最受限端点的**合法出口数**从少到多排队。先根据合法 M10 落点和固定障碍判断能从哪些位置、朝哪些方向伸出第一段线或换层，用独立出口数估计有多少绕路选择。同一落点同一方向的粗步和细步合计为一个出口。出口数相同时参考线束压力。选择少的短线也优先；选择多的线在剩余通道中找路。

同一根多端点网内，每接完一个端点，就按当前几何重新比较其余接收端的合法出口，把选择最少的接收端接入整棵已布连线树。近端短支路也可以第一个接上。直连和使用 buffer 时的各物理分段都按这套规则试布。

实际路线仍按当前占用、间距和过孔规则核验。后续重布沿用算法 2 的失败网优先和反馈修复。全板布通率需要在相同网表、摆位和规则下比较。

实现见 [合法出口优先补丁](algorithm2-scarce-access-first.patch)。补丁以 [PR #259 的 `4ebd2a2f`](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/4ebd2a2fc845ccc6a1c17ed1751f208bb5791a8f) 为基线，覆盖直连和中继入口。应用后可在仓库根目录复跑 Python 布线回归。

```bash
git apply --check /path/to/algorithm2-scarce-access-first.patch
git apply /path/to/algorithm2-scarce-access-first.patch
PYTHONPATH=project/experiments/block_synthesis python -X utf8 -B -m unittest discover -s project/experiments/upper_router
```

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

## 5. 顶层拥塞时的补充优化

冻结实例位置、朝向、障碍与固定铜线。顶层试布沿用 CUGR 最后一阶段的细粒度迷宫搜索，由实际几何生成候选线段和换层位置。排序、入口预留和局部修复负责给搜索提供不同的约束。

### 激光直写层的布线位置

M11/M12 采用无掩膜激光直写，**线中心、拐点和 V11 可放在制造坐标分辨率允许的任意合法位置，无须对齐预设主轨道或主轨道交点**。以实际几何为准，检查线宽、同层金属边缘间距、固定障碍、过孔切孔间距和上下层金属包围。V10 按已核验的 M10 端点及包围规则接入。

搜索图可由端点、障碍和已有铜线的安全边界、局部通道中的可用位置生成，拥塞区可按制造坐标精度补充候选。图节点用于控制搜索量，线与孔的最终位置由几何核验确认。回归应至少包含一条只有偏离旧主轨道才能通过的合法线路，以及因边缘间距或过孔规则不足而必须拒绝的候选。

### 拥塞处理

1. **密集接点从下层扇出，并给新入口留空间。** 先枚举每个引脚合法的 M10 接点、V10 和顶层出口。入口不足时，底座准备阶段可按批准范围把信号引到更分散的 M10 接点，核对它与原引脚的连通、间距和 V10 包围后再冻结绑定。顶层算法读取更新后的固定底座和端点清单。底座已冻结时，用已核验的 M10 候选，避免顶层路由擅自修改 M1–M10。对选择少的接点预留一小段上层入口；本次试布只释放本网络的预留。
2. **过孔优先挪位，必要时才增加。** 保持已绑定的 V10 接入，定位发生间距冲突的 V11。尝试把 V11 移到上下层都能满足包围与间距的其他坐标。绕路确实需要额外换层时再增加 V11。检查过孔对同网和相邻网的间距、上下金属包围与整网连通。
3. **先保护绕路选择少的网和分支。** 按第 0 节的规则，对当前合法出口更少的网和支路优先试布，短支路也包含在内。结合通道可用宽度为稀缺出口留空间。多端点网从整棵已布连线树接入下一个受限端点，选择多的网使用其他可行通道。
4. **按共同堵点成组拆线重布。** 从失败候选定位相互占用通道、入口或过孔空间的已布网，保存该组原路线和占用，再试布失败网和被拆的整组。独立检查整网连通、固定几何及新旧路线之间的间距，并确认已有网没有退化为断网，才提交整组。任一项失败就恢复原路线与占用，然后尝试另一组或另一个候选。
5. **对失败点尝试不同方向、横向偏移和换层位置。** 扩展局部搜索窗口，尝试其他入口方向及满足实际间距的偏移位置。过孔冲突时切换换层位置，避免反复返回同一冲突。每条候选仍用同一细粒度迷宫搜索。预算用完时按入口、通道或几何违规记录原因。

试布与修复应覆盖完整逻辑网的全部接收端，也适用于预置 buffer 划分出的各个物理分段。比较优化前后时，使用同一摆位、网表和几何规则，并分别报告布通网数和点到点连接数。若调整了 M10 接点，保存各自的接点版本并注明变更。历史实验中的参考实现可查 [入口预留与成组重布](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0205e639a2a63d0be9bb454b49c3d26481809708/work/huangpingyang04-lgtm/250/pr271-top-route-study/clean-1184/trunk-engine.cpp)、[V11 备选位置搜索](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0205e639a2a63d0be9bb454b49c3d26481809708/work/huangpingyang04-lgtm/250/pr271-top-route-study/focus-77/focus-via.inc)及[下层扇出](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0205e639a2a63d0be9bb454b49c3d26481809708/work/huangpingyang04-lgtm/250/pr271-top-route-study/full-1834/escape/lower-escape.cpp)。本节定义补充流程，接入 PR #259 的通用路由器仍待联合回归。

### 九实例压力测试依据

2026-11-16 的九实例测试采用新版 ODB 和已经过重叠检查的摆位。服务器作业 `118567` 在 976 条点到点连接、967 个网中独立核验通过 539 条、539 个网。作业 `118568` 复查剩余 428 个网，观察到顶层通道受阻 296 个、V11 间距冲突 78 个、顶层入口受阻 54 个。结果回执 SHA‑256 为 `9b50b24c94b1c46d56b70b20f738ab8263834a92f3b854fb3e1f723ed91d2988`。本轮数据是采用固定主轨道的研究基线，按实际几何选位的实现及其对照结果待验证。核验覆盖交接提供的固定几何。交接未提供跨块固定铜线实体，产品级寄生和 STA 待另验。

## 两点距离具体用在哪里

**粗筛 buffer 时**，距离是两个引脚代表坐标之间的估计，用来比较分段方案。**A* 试布时**，距离是当前待选点到本段最近合法接点的估计，用来排序待选点。两处都使用平面曼哈顿距离，例如横差 `3`、纵差 `4` 就记作 `7`。绕障碍后走出的金属线可能更长，负载估算和布后验证使用具体路线及过孔。
