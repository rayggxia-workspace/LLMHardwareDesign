# Issue27 正式 run-01 独立审计

结论：PASS，未发现当前数据的同资源、O/m/l顺序、静态选择、case重漏或删边单调性错误。审计没有导入或执行项目graph/run/scheduler模块，也没有修改主工作树。冻结源码从本地Git对象 `6ffb9417f0f01f614b733ce6c3ca9837906b3203` 读取；数据目录 `D:/Projects/Codex/state-port-study-20261022/run-01`。

机器报告 `run-01-audit.json`；纯stdlib脚本 `audit_development.py`（同一脚本也可审正式数据）；补充策略范围 `run-01-policy-invariance.json`。原development-01审计遇到配置改版的绑定失败记录仍保留；它不是正式run的数据失败，不得改写旧manifest。

## 实际核验

- manifest中的5个数据文件全部SHA/字节吻合；固定config SHA吻合，正式标志development_run=false、dirty_at_start=false，源码commit匹配。
- 原始trace archive SHA与4条唯一观测重新读取核对：layer0、single_prefill、call0/16的query/key形状、FP32 dtype及完整观测记录相同。这仅证明元数据绑定，不证明在线服务图是eager实际执行轨迹。
- 独立重建全部3456个Cartesian key，无重漏；1224可行、2232失败。独立静态槽、scratch、所需直连规则与所有状态一致。
- 失败的首个阻塞：B0容量432、B1容量864、缺V0直连648、缺D1直连288。它们是按构造顺序遇到的首个阻塞，不是唯一原因或全局不可映射证书。
- 所有可行case的解析MAC数、M/V/D逻辑流量、task数量、静态bank预留、scratch及policy-min记录一致。
- 108个静态组的每个候选、两phase配对、sum、平局顺序、best及phasewise lower envelope全部独立重建一致。
- 24份归档witness逐任务检查ids/duration/deps；在每个开始时间直接累加所有重叠区间检查资源峰值，不复用项目调度器的availability或sweep。每个transfer的端点/link/bank/address预留及ceil(byte/rate)+setup时长与合同一致；静态地址不重叠，RAW/WAR/WAW与初始化字节版本一致。
- 12对000/111 witness的计算/存储/端点/连接库存相同，M/V/D流量、MAC数、scratch、bank容量和总预留相同；除resource归属外，各task的id、duration、deps及元数据相同，非状态槽不变。

## 静态放置和删边解释

审计始终显式按 `(O,m,l)` 提取，而不使用JSON字典values顺序。JSON sort_keys把键排成O,l,m；run.py当前是在序列化前处理由zip(O,m,l)创建的字典，实际结果没有换位。但未来若改成读回JSON再分组，必须改用显式名字。当前所有case覆盖也独立确认，不依靠该惯例。

一个O/m/l放置贯穿两个observed phase；a固定跟随m，所以改变m也改变a的位置。两个phase可以各自从同四策略预算中选最短调度，不能把它描述为固定同一schedule或已实现同一硬件调度器。static sum是同等计数的一个prefill query-head tile与一个decode query-head tile之和，不是整prompt、16次decode或完整模型端到端延迟。

删边不提供绕路，只拒绝必需直连：504个disabled保留可行case的全部policy cycles和best events SHA与full完全相同；936个由可行变失败；864个在full已失败。72个disabled静态组中42个best不变、12个变差、18个没有共同可行放置。所有disabled候选严格是full候选的同值子集。不能用无候选证明任意其他架构或重布线也无解。

## 数值口径和条件性

固定key_tile16、bank各65536B、bank/link64B每服务单位、external32B每服务单位时：

| bank合同 | Oml000 prefill/decode | Oml111 prefill/decode |
|---|---:|---:|
| 1RW | 7094 / 2625 | 6774 / 2522 |
| 1R1W | 6698 / 1872 | 6680 / 1809 |
| 2RW | 6680 / 1809 | 6680 / 1809 |

表值是best-of-four的未校准模型服务时间。1RW的decode000选择shortest而111以critical打平胜出；同一critical也从2641降到2522，四个策略在该对放置上都降低。全体可行case的best选择为critical699、shortest273、fifo252，不能笼统说全部都由critical产生。

全sweep的48个full 2RW workload-config组，所有可行放置的best-of-four均相同。单独shortest在2组会随放置改变，critical/fifo/longest均未变。因此“2RW全部一样”应限定为当前四策略最小值。方向更灵活的端口消除了这个抽象图中的placement收益，是有条件的零效应结果；没有证明真实硬件中端口/存储/布局不重要。

本轮是FP32全操作数的single-buffer在线attention服务模型；容量、MAC/向量吞吐、setup、链路/外存带宽、端点staging均为假设。它不是INT8整数模型，不含真实端口RTL、仲裁/时钟/物理校准、GQA多头共享、完整投影/模型、语言质量、真实PPA或端到端收益。2RW与1RW本身是不同资源合同，公平placement对照在同一合同内部成立，不能当作同资源端口升级收益。

没有独立重放全部4896条原始调度：数据仅归档24个完整witness，其余case提供makespan与event SHA。本审计对全体case做独立解析元数据检查，对全部归档witness做完整事件检查；其他调度的执行合法性仍由正式runner内全量checker及其他独立oracle差分证据支撑。
