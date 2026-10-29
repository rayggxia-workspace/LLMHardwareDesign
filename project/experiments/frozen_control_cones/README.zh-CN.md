# 冻结底座上的两控制锥：算法提炼与证据重放

任务：[Issue #42](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/42)，负责人 huangpingyang04-lgtm。Python 3.10+，仅标准库。

这次实际完成的是：在同一 INV_X1 + AND2_X1 固定底座上，以 M11/M12 和新增接入通孔的不同连接，实现两个真实 RTL 的 1-bit 组合控制片段，并将物理几何、导出的逻辑和原始表达式对应验证。不是完整 openTPU/llaccel、完整 FIFO、正式 Block 映射或真实工艺签核。

| 案例 | 原 RTL 切片 | 按输入 00/01/10/11 的输出 |
| --- | --- | --- |
| openTPU MXU | `b_req = go_iss && need_b` | 0 / 0 / 0 / 1 |
| llaccel sync_fifo | `do_push = push && !full` | 0 / 0 / 1 / 0 |

`full` 和 `go_iss` 等是切点输入；本实验没有计算或验证产生这些信号的状态机。不能据此说 FIFO、MXU 或两核心完整功能通过。

## 已获得的经验与算法边界

| 已获得经验 | 提炼的方法 | 本目录实现 | 仍缺输入/限制 |
| --- | --- | --- | --- |
| 同样的门、位置和低层线能支持两种小逻辑 | 把冻结约束与可变信号连接分开检查 | `check_frozen` 比较实例、端口、低层几何、旧通孔、PG 和技术定义 | 底座及引出位置仍由案例人工选定；没有自动选出最优 Block |
| 网名相同不保证物理连通；网名不同也可能短路 | 实际导体接触图 + 并查集 | `read_native`、`contact_graph`，同层接触及真实通孔连边 | 只接受当前解析器支持的 Manhattan DEF 子集 |
| 连通不等于正确功能 | 从几何连通分量接到单元引脚，再求值 | `evaluate` 使用配置中的单比特组合单元真值表，全枚举对照 | 新单元需要可信模型；时序单元、存储和多周期协议未实现 |
| 只看成功退出会漏错 | 正例、断线、短路、错误功能和冻结资源变更一起验 | 原生故障导出样本 + 变异测试 | 不能替代完整 DRC/LVS、RC/STA |
| 工艺网格和接入围边会影响可行性 | 有限规则检查 + 明确冻结的 M10 落点 | 本程序重放制造网格、标量金属间距；原实验另检查 cut/OBS/新增轨道和 PG | M11/M12、通孔是研究参数，缺真实 foundry 新层规则及 RC |

现有团队 PR #12/#28 的抽象被动路由/调度算法和此前服务器通用化试验，并不等于这次原生几何验证。本目录不复制一套抽象 router，也不把这些不同层面的测试数量混为一谈。

## 执行入口

先进入仓库根目录。在已授权的新输出目录中设置 HOME/TMPDIR/XDG_CACHE_HOME；服务器所有路径须仍在 PingyangHuang 下。不要在原始输入或旧实验中运行会写文件的程序。

```bash
# 只读校验仓库自带的 35 份轻量原生导出样本
python -B -S project/experiments/frozen_control_cones/check_evidence.py

# 正例、真实断线/短路样本、模型/坐标/名称/底座变异测试
cd project/experiments/frozen_control_cones
python -B -S -m unittest -v test_flow

# out 必须是不存在的新目录；不会覆盖旧结果
python -B -S flow.py --config example.json --out /允许的新任务目录/replay
```

原生导出样本来自最终实际 ODB，而不是为单元测试另画的模拟线路。`check_evidence.py` 校验文件大小和 SHA-256；具备服务器权限时再加 `--archive-root /public/home/yuzelu/PingyangHuang/pending/paired-function-physical-20261023T062933908806Z`，可核对原日志/数据库及导出来源，共 60 个索引项。数据库、原始 RTL 全文、完整日志、LEF/Liberty、工具镜像不随 PR 上传。

`flow.py --fixture-root <目录>` 可替换样本根目录。它接受每案例一组 `native.{layers,vias,terminals,instances,nets,obstructions}.tsv` 和 `native.odb_export.def`。配置字段与算法见 [ALGORITHM.zh-CN.md](ALGORITHM.zh-CN.md)。

## 已验证和未实现

- 已验证：原实验 OpenROAD 读取并保存 ODB；从全局几何重建门连接；Yosys 使用真实 Liberty 进行零延迟穷举和源表达式 SAT；保存 ODB 的独立读回及原生网表/几何网表 SAT。
- 本次提炼的 Python 实现：使用相同实际导出，进行冻结/连通/组合逻辑/有限几何规则重放；显式配置真值表，不是新的 Liberty 解释器，也没有重新运行 SAT 或 EDA。
- 尚未实现：自动底座生成/布局/预连线优化、通用目标图资源映射、多周期调度、自动详细布线、任意 Block/LLM 前端。
- 原实验使用显式生成 DEF 线段和通孔，不能称自动详细布线器已跑通。
- 原实验含 cut/OBS 间距、轨道及原生 PG 检查；本次精简重放没有重新实现这些全部规则，只通过哈希关联其原始证据。完整规则仍未验证。

## 原实验与本次整理的保存位置

- 只读归档：`/public/home/yuzelu/PingyangHuang/pending/paired-function-physical-20261023T062933908806Z`。
- 本次任务：`/public/home/yuzelu/PingyangHuang/pending/control-cone-algorithm-pr-20261023T073506806184Z`，`review_worktree` 是基于 main `0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d` 的局部审查快照；完整未改文件通过 Git 基础 tree 保留，不是下载完整仓库。
- 原生主作业 89888、最终证据复核 89890 成功。89889 在最后访问未绑定的原始源码路径时失败，其前面的原生读回/SAT 已完成；后续使用主机只读 SHA 复核和保存证据补足。不能把 89889 改写成成功作业。
- 完整版本、源码来源、原始工具二进制 SHA、旧脚本和关键文件的索引见 [evidence.json](evidence.json)。完整核心大底座 GRT 的旧超时结果不属于本小目标成功证据。
- 新增工艺、完整 STA/寄生、真实负载、电气/制造验证均缺失，详见算法说明。下一轮在本 PR 归档和核查后，再选择新增功能及对应验收条件。
