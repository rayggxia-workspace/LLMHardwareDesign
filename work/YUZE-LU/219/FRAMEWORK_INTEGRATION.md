# 九组底座上的 Algo1 框架收敛

2026-11-14 CST，Issue #219。比较基于快照提交 `5efa7c26e`。保留远端 PR #257
的图编译、控制 IR 和布线交接基线 `a326d04e`。两条分支的前沿、执行和验证实现
发生冲突，合流后须同时通过两边的回归。

## Tile 交接和候选排序

从同一组服务和 SRAM 窗口试排两个 16 B tile。
`benchmark_tile_handoff.py handoff` 通过编译器和独立计划检查，导出实际等待边。

| 配方 | 模型周期 | 两个输出 tile 的峰值活跃字节 | 依赖 |
| --- | ---: | ---: | --- |
| 整算子屏障 | 16 | 32 B | 消费者第 12、14 拍开始，分别等对应数据发布和整算子退休 |
| 阶段交接 | 12 | 16 B | 消费者第 4、10 拍开始，只等对应 tile 发布 |
| 独立提交命令的假设配置 | 10 | 16 B | 两条生产命令各自以 tile 提交结束，只需命令完成级等待 |

前两行使用同一硬件模型。第三行使用另一份服务合同，单独说明原生接口须怎样支持独立交接。
活跃字节从写阶段开始到最后一位消费者读取结束统计，只覆盖这两个输出窗口。
测试的两个窗口仍是固定物理地址，峰值下降未被计作 SRAM 面积或分配器收益。

`benchmark_tile_handoff.py placement` 固定两个计算候选，分别强制试排并从同池搜索。
空闲时单宏 24 拍、双宏 16 拍，加入占用 P1 同通道的后台请求后，分别是 24、29 拍，
搜索切回单宏。这是声明资源下的模型排序反转。外存字节分别为 64 B 和 128 B，
差额来自后台请求，同一压力下两个候选的搬运量相同。

## 两个后端

- 算法 2 当前实现 `4ebd2a2fc` 的 `--handoff` 已读取 #257 U 组真实 M10
  端点样本。130 根待布线通过研究几何规则，物理资格仍为 false。接口读取
  `upper-router/1`、`handoff.json`、`program.json`、`wiring.json`
  和 `requirements.json`。产品范围还核对冻结底座、逐位端点和控制镜像。
  main `7a809d1e` 的 Block V2 九组位置是候选图，项目有六类组级 DEF 的散列，
  仍需将九个实例及主控的变换、顶层端点、预连、障碍和时钟/复位/数据网络绑定到同一个底座。
- #260 `1ea06be2` 的消费者读取封存的程序页、原生 CALL/WAIT、128 B 描述符、
  局控资产、初始 DDR 镜像及 KV 合同。现有 `link_native_program.py`
  的输入是同一计划生成的 `block-event-control/1` 和 `block-event-demands/1`，
  现有 WAIT 等目标返回整条命令完成。对阶段边先验证目标 ABI，能独立提交的服务按 tile
  生成真实指令；无法观测的阶段边须明确报出。现有封存请求经消费端审核
  184,927 页和 8,273,243 次 CALL；同包一页 TLM 跑通，141 笔 DDR 请求均回调，
  无 token 退休。两项用于验证消费接口，尚无新 Algo1 计划贯通到该请求包的证据。

快照分支接入了 #257 的控制、线束发射器和基于硬件配方的图 lowering。
`run.py MODEL HARDWARE OUT --event-graph` 从类型化图生成计划、控制和线束需求。
本轮以两节点图走完新编译路径与算法 2 入口。内部阶段的串行配方可以使用，任意阶段 DAG
仍待合流。完成级等待可导出，无法由命令 ABI 表达的阶段边会被拒绝。下一步接入
完整图配方、实际底座准入和原生链接，验证能独立确认的 native tile。产品计时以真实
权重、自产 KV、合法程序、联合事务和 token 实际退休为验收。参考
[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)、
[PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260)。

## 远程回执

目录 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em`。

| 作业 | 结果 | 输出 SHA-256 |
| --- | --- | --- |
| 108990 | 整算子屏障与 tile 阶段交接 | `0d0ab7d9f6118343bf9096b025b267928fe448f1b06c88bc7cbf730e85605943` |
| 108991 | 同候选池 DDR 压力排序反转 | `fc4f6b36fd6c4c9c063f75641907eef9d5aaa034ed2fcc5e0238b77f39ca5a98` |
| 108992 | 项目结构及 396 项算法测试通过，源 `9242b5ab2` | `7681b5b0928ac79511c88f54c9404a3f2f846d5c0cae6c5032960e5fdf9c3217` |
| 109000 | 加入独立提交命令模型和 ABI 缺口报告 | `5e1699f97a9376d2e80f6aa9c343574fa51dc3a376f4c66cf63922ec9c4336b7` |
| 109010 | 当前算法 2 接口回放，`route-current-u.json` | `22a17a3e05d779a3c1471d589266d9aa30e8ac90b7371436518411ec7a7c444b` |
| 108968 | #260 母控页和 CALL 读取检查 | `3898d96c3dd1e988a9cb8d95dba0d7070ffce6dadbb2ff2865fafd100a97c219` |
| 109009 | #260 一页回放，`execution.json` | `cdec2acc56348b638c1e8cfb269d5e1a5b647590008e567f2135360aacd419ca` |
| 109035 | 类型化图经快照编译和当前算法 2 消费、控制 IR 正负对照 | `111708d475d995f7cc09643b35064f66399ac3145bd9b76706cef1b1a5d1f22a` |

以上作业均 `COMPLETED 0:0`。一页 TLM 的早期启动失败（108995、108998、109006）
已保留，分别修正了 Slurm 下的路径和归档依赖。

项目 `llm-hardware-design`，协作规则 `rayggxia-project-collab 1.0.0`，Issue #219
继续进行，负责人 YUZE-LU，独立审查人待指定。登记沿用 management-hub PR #5。
当前无 `config/board.json`，看板 unverified，同步 pending。
