# Issue99 R 状态单元：发布与恢复交接

日期：2026-10-25，Asia/Shanghai。仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign ，任务 [Issue99](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/99)，负责人 Liangruizhi / 182389313 / 2663955430@qq.com。交付前认证查询再次核对为本人；Issue 仍为 `status:in_progress`，未创建 PR。主会话负责统一推送、PR、Issue/看板读回，不自行合并或标 done。

## 分支、来源与范围

- 独立分支 `task/99-r-state`，工作目录 `D:/Projects/LLMHardwareDesign-r-state`，临时目录 `D:/Projects/Codex/r-state-20261025-01`；基线93 `f660e3538be9c07ff4ee1f105db0cfee5f0bfcab`。
- 实验冻结源码 `af2f7fb171ad04158ed861c72c87133dfc5454d4`（phase7）；归档及门级严格接收 `b32136000cb4aab0690374866767f307151b567b`（phase8）。最终文档/结果提交位于其后的本任务 HEAD；发布者用 `git rev-parse task/99-r-state` 记录准确 SHA，不能以本段科学源码 SHA 替代交付 HEAD。
- r99 RTL 在 map04 的 phase6 源 `5eccf820d29a8a2e7af9353843a55ab08817de63` 及 phase7/8 逐字节相同，SHA-256 `5c8481c1db635ed3fb22335b605a211be7646726ff4d8c81c3c49fc111aa9113`。
- 只实现既有 Falcon 整数合同的一个完整 head D128/N256 状态路径、有限外存事务和消费者发布接口。没有 conv/coeff 生成、其它31head、4096norm、与97/102实际资源共享或物理签核。
- 未修改93/97/98/102工作目录。全部数值/RTL/map/rawgate在本人授权服务器执行；本机仅源码、文档、结构和字节验收。无下载、Phi解封、GPU或其它机器作业。

## 证据入口

先读[报告](../experiments/issue-99-r-state.md)、[协议](../../project/experiments/r_state/PROTOCOL.md)、[工具命令](../../project/experiments/r_state/README.md)、[实际作业命令](../../work/Liangruizhi/99/execution.json)。服务器根为 `/public/home/yuzelu/RuizhiLiang/issue99-r-state-20261025`。

- 正式输入 `inputs06`；全72连续 `real005/real105`；协议 `protocol005/protocol105`；边界 `boundary005/boundary105`，对应六份 `receipt-*.json` 均严格接收。
- 每路真实82记录 = INIT + 72步 + 9 RESTORE，完整状态/Y逐码对独立 bigint、原72输出/单位/最终状态。位置27→28发生真实重标，本地epoch1；原32head共同epoch25不可混用。原72批次跨head wide_guard 已检查为0。
- `negative02` 是实际修改文件并重算 artifact SHA 后，由完整 receiver 拒绝的三个语义负例，非hash失败。
- `map04` 是最终RTL实际网表；`gateprep01` 从已接收完整轨迹取位置0与27的状态/descriptor；四个 rawgate 与四个同driver RTL 均比较完整32768状态码/128输出码。门级严格 schema/metadata/cycle/IO 见 `gate-schema01.json`；不含72连续门级、终止epoch门级或STA。
- `work/Liangruizhi/99/final-slurm.json` 记录83个本任务作业全为终态：73 completed、4早期 failed、6本人依赖未满足的 pending 作业取消。失败与日志保留，未将失败写成通过。无待运行99作业。

完整包 `delivery01/full.zip`，125,298,753B，SHA-256 `f5cb47e12c4b15320b5e26f30ee165d0b03e9bcf48f7a6b3cc8829b0b8b833bd`。675成员、291嵌套artifact、8phase101份原Git源码通过独立服务器字节接收。

仓库[精选包](../../project/experiments/r_state/results/issue-99/selected.zip) 1,183,475B，SHA-256 `e325e0a83099c203f547987867ff5a79d7476f2904959c2e9a3f2ced064297d7`，226成员、40份源；server/local byte receipt均PASS。[索引](../../project/experiments/r_state/results/issue-99/index.json) SHA-256 `25d4f67ad81586f7e09920e3538742a459367d3093323b74d59cce2e0a61c97c`。原index生产者状态不重写，以后续独立receipt表示接收。

## 成本与不可省略的限制

真实72连续+INIT+RESTORE：quiet148,909,146周期、背压175,736,069周期；5,371,650外部事务、7,171,328 S32乘法。每事务五128bit拍，payload85,946,400B，线字节429,732,000B；请求/回复32bit generation sideband另列。debug/canary、初始输入装载、后继Y读512B/head/token没有算成端到端性能。

单16KiB128bit1RW、一个共享S32，实际map为41,708.534µm² logic-only、28,221 cells、3,084 DFF_X1、3,285 generic register bits。外部固定1MiB、控制槽及consumer head上下文另列；不含SRAM宏/fabric/STA/RC。不得把本独立R预算与97/102各自预算相加后声称一个共享原型。

consumer accept是不可撤销点，descriptor ACK才committed。硬reset之前必须协调peer与fabric排空；恢复真实已生效descriptor。原子128bit写/ACK语义是外部接口义务，不是目标宏已验证事实。INIT仅用于调用者授权丢弃旧context。

## 下一步与责任

恢复第一步：读取本任务最新 Issue/PR及成员进度，再核 `git status --short`、`git rev-parse HEAD`；从index/receipt校验selected与服务器full。需要复查科学结果时按README固定目录接收，不能覆写已有run目录或重复启动作业。先读现有receipts，按实际变化决定是否重跑。

主会话/发布者：接收干净提交，核目标origin/身份/基分支和任务文件，完成PR与Issue同步；继承登记PR5 `pending`、Projects配置/read:project权限缺项，交给管理员（待指定），不能记为synced。PR审查/合并/正式验收尚未完成。

下一研究只读规划（未实现）：从实际97、102、99抽离controller、共享一个16KiB1RW/8S8/1S32/SFU/外部桥，先串行owner lease与排空、scratch覆盖/恢复、R提交不可取消语义及真实operand/result mux；不扩写通用ISA/16×16或新建Issue。先交设计范围给主会话审阅。

## 协作回执

规则版本 rayggxia-project-collab 1.0.0。科学实验与本地交付有证据；远端任务分支/PR待主会话发布。登记 pending（既有PR5）；看板 unverified，动作 pending（现有配置/read:project缺项）。Issue当前 in_progress，要求的PR审查/合并未完成。结构与最终差异检查见 work/Liangruizhi/99/local-checks.json；本文件不得被解释成已经远端交付或整个R/Block库完成。
