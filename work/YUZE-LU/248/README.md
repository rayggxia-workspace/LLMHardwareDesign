# Issue248 执行与证据索引

[Issue248](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/248) · [PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)，负责人/执行身份 YUZE-LU。

正式实现：`project/experiments/stream_quant_synthesis/`；[研究报告](../../../docs/experiments/issue-248-stream-quant-synthesis.md)。冻结父 PR243@9d987151ee687322c0ce52d69a0a14f2275bd52b；只读复用其 run23 冻结输入与原生成链，不修改 Melodydt 的目录/分支/作业。

服务器根目录 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-<tag>`，每次新目录。Slurm partition c64/c96，4 CPU，任务 `yl-sq-four-rounds` / `yl-sq-quality`。作业实际节点、用时、CPU、终态在每包的 `collection-sacct.txt` 与 allocation 文件；未操作其他任务。

| run | Slurm | 用途与结果 |
| --- | --- | --- |
| 01 | 101974 | 工具 PATH 失败，不是业务通过 |
| 02 | 101975 | 严格 lint 失败，修复树级连线和临时赋值 |
| 03 | 101976 | C++ VlWide 接口失败；此前 Python3.6 text 参数部署失败未启动作业 |
| 04 | 101977；质量 101978 | 整数乘法失败；真实权重幂次静态量化筛查完成 |
| 05 | 101979 | 增强定位后复现同一符号错误，定位三元表达式的无符号传播 |
| 06 | 101980 | RTL 与 43 个 SystemC case 通过；逐 tile 重复转换很慢，负结果保留 |
| 07 | 101981；质量 101982 | SSA 一次转换与独立 DMA 描述符，43 case 通过；幂次尺度5种精度筛查完成 |
| 08 | 101983；质量 101984 | 条带化/耦合 DP，55 case 通过；普通线性尺度5种精度筛查完成 |
| 09 | 101985 | 新增定点转换测试严格 lint 失败；未屏蔽检查 |
| 10 | 101986 | 修复测试信号宽度，55 case 与转换 RTL 通过 |
| 11 | 101987 | 八上下文交错与全 K 极值加强，55 case；结果以原回执为准 |
| 12 | 101988 | 增加同资源 S32 对照，65 case；正式摘要来源 |
| 13 | 101989 | 仅修正候选core_K标签与需求位宽，两条精度路径完整RESULT除标签外精确复现run12；48秒COMPLETED 0:0 |

每个 `runNN/receipt.json` 保存源 commit、Slurm 原回执及嵌入文件 SHA；`evidence.tar.gz.b64` 是不可变压缩包，含原始结果 JSON、日志、生成后的候选模型、研究源码快照、源检查和工具/分配回执。`verify.py` 对压缩字节和每个成员逐项核验，不启动 EDA，也不声称重新验证远端仍存在。生成构建目录、二进制、完整大 trace/vector 留在上述服务器对应 root；输入/向量 SHA 和重建源在回执中，不能把这个索引说成全部大 raw 已进 Git。

正式 `summary.json` 由 `report.py` 从 run12 的真实输出自动汇总，能耗与完整原生整机吞吐为 null。`bundle-*.json` 是按实际 64 B 入口重导出的部分操作数需求，执行文本与原回执逐字节相同；它不是原生 ISA、完整静态网表或物理 pin 合同。旧包中的原文件不改写。

最终离线核验：13个run包、958个嵌入文件逐项通过，正式65case、12次基线精确检查、2次标签修正整RESULT回归、190个RNE检查和4968路径DP穷举通过。新矩阵A8/A16各5782packet/44完整Dot；转换S8/S16/S32各512向量。失败包仍为失败，文件核验通过不将其变为业务通过。

离线入口（仅 Python 标准库）：

```powershell
python -B work/YUZE-LU/248/verify.py
python -B project/experiments/stream_quant_synthesis/report.py --root work/YUZE-LU/248 --run 12 --quality-run 08
```

生产 RTL/已有底座未替换，新候选没有综合、STA、P&R、完整局控/DMA 集成、全整数生成和能耗资格。10 token/s 与20%纯算法收益未取得。审查人待指定；本 PR 不自行合并，Issue 不标 done。

协作接入：rayggxia-project-collab 1.0.0；project_id `llm-hardware-design`。登记沿用 management-hub PR5 pending；缺 `config/board.json` 与 Projects 条目能力，看板 unverified/同步 pending，管理员待指定。
