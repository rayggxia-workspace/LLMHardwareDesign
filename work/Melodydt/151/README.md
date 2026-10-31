# 六类连接方案与bridge归属研究

- 任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；负责人Melodydt；更新时间2026-10-31T16:22:44+08:00。
- 任务分支：`task/151-six-connection-study`；基线`a103da352b7e431cedc69f54b9f71c05371be1b3`；正式成果/最新PR由本Issue回执索引。
- 正式文档：[六项连接](../../../docs/SIX_CONNECTION_SCHEMES_STUDY.md)、[bridge归属](../../../docs/SIX_CONNECTION_BRIDGE_AUDIT.md)、[协调候选](../../../docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md)。
- `connection-index.json`保存六项功能依赖、来源与改动位置；不是已路由网表或冻结连接矩阵。`source-index.json`保存固定ref/path/Git blob/SHA-256/行数；发布head与历史运行source_commit分别说明。
- 本地目录`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/`与API交付包`delivery/`隔离。源码快照、草稿和准备脚本只留本地，不作为新正式源码上传；完整来源留在原固定commit。不是完整Git clone，不能从缺失文件推断远端删除。
- 本任务未运行RTL/SystemC或物理实验；没有仿真作业号。原有证据是按范围引用，管理结构检查不能替代业务验证。

核验已提交研究清单（Python3.7+、标准库）：

```text
python -X utf8 work/Melodydt/151/verify_study.py --root .
```

若已用本人认证按source-index重新取得选定原始UTF-8文件，可把它们按snapshot_name放在独立目录，增加`--source-dir <该目录>`逐字节核验Git blob/SHA-256及源码行引用；当前会话的本地来源目录为`work/Melodydt/151/sources/`。无source-dir时只做文档/清单核验，并明确标来源字节核验未执行。

实际结果见`verification.json`；后续提交不因本文件宣称自动监控或测试完成。登记PR5 pending；看板缺配置/工具，unverified/同步pending，处理人待指定；独立审查人待指定。
