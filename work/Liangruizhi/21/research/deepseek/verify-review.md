# Issue 21 归档验证器只读复核

2026-10-22。未修改 root 工作树；所有复制源码、变异 ZIP、脚本和结果仅位于 `D:/Projects/Codex/operator-partition-20261022/deepseek/archive-audit/`。

所审 `verify.py` SHA-256：`d4bf3460f3df4f6ea3f4750499d5e301cf4bb4e48cf8afd9c79e6c417c6290de`。它依赖的 `run.py` 为 `9c67cf02568b19f89cea27033b1a6cdf25509a13bf6949afde664faff76462bc`，`ledger.py` 为 `37658c6aca44d7909ce52c1a0f1b559a5249e6304716a5329aac0f617ccb6026`。精确文件列表见 `archive-audit/source-snapshot.json`。

原归档为仓库 `results/issue-21-run01/evidence.zip`，233685 字节，SHA-256 `f85b1f120065f91d13df95cdf343d35eb48640d9a56d2755b46da5c6ed82306d`。试验前后读取的 SHA 均相同。

| 负例 | 重封装与哈希处理 | 实际拒绝 |
|---|---|---|
| 错误归档 SHA | 原归档不改，提供全零 expected SHA | `ValueError: archive SHA mismatch` |
| 成员与 manifest 不一致 | rows.json 追加换行，重算 ZIP SHA，保留旧成员 SHA | `ValueError: member SHA mismatch` |
| 错误事件计数 | 首个 compute.read 加 4；重算 events 成员 SHA、manifest 与 ZIP SHA；rows 保持原值 | `AssertionError: counter mismatch` |

三个指定负例全部拒绝。第三个负例已越过 ZIP 和成员哈希一致性检查，由事件计数与 rows 的交叉校验发现错误。没有重复运行整套模型/调度实验。

流程复核确认：工具先匹配调用者提供的归档 SHA，要求恰好七个预定 ZIP 成员，检查声明解压总大小、成员 SHA 与完整索引，然后逐 case 重放账本和闭式 MAC/外部字节/engine transfer，核对 case 覆盖与记录的数值检查状态。ZIP 在内存读取，不落盘解压，三个负例只改独立副本。

必须保留的证明边界：

- expected SHA 的可信来源由调用者负责；对方同时提供 ZIP 和一个新 SHA，不能单凭匹配就证明来源真实。
- capacity.json、pareto.json 目前检查成员哈希，没有重新推导其语义；manifest 的源码 commit / inputs 索引没有在此工具内对源码再核验。
- numerical.json 检查已记录的 PASS/负例 detected 状态，不执行新的数值实验。
- `audit_events` 与 `closed_form` 复用 run.py 的检查实现；独立实现的计数复核见此前 ledger-review，不应把此验证器本身称作完全独立的实现。

因此结果可表述为“给定可信 SHA 的归档完整性与事件/闭式账本重放通过”，三个指定篡改均能拒绝；不能表述为任何自洽重封装的不可信归档都必定被拒绝，也不构成模型精度或物理实现资格。

复现脚本：`archive-audit/negative_archive_checks.py`，SHA-256 `9bf73e92bda94afa4078cbb7f577e095b0977a3c6d13e43bb855c878da071044`。

结果：`archive-audit/negative-archive-results.json`，SHA-256 `edf2414ef64accfaab23267dfa003705b46f4d4737abaccd2341e3fa6399de84`。结果逐项记录实际变异 ZIP SHA、是否重算 manifest、异常类型和拒绝原因。两个变异 ZIP 保留在独立 D 盘目录作为负例证据，未写入仓库。
