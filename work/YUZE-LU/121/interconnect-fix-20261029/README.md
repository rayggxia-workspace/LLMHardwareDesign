# 完整总线与真实原生驱动修复

Issue [121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，侧线交付到现有[PR133](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/133)。正式说明见[报告](../../../../docs/reports/2026-10-29-block-v1-full-bus-driver-repair.md)。本目录不替换主线交付，原18份生产文件保持。

本轮针对两项已定位的问题：原BUF_X4到宏外第一级缓冲的长线负载，以及完整275/281根总线未布通。M/T/S独立副本的132/140/1个选定驱动换为真实BUF_X16，保留原pin和外框，继承GRT后重新合法化/增量GRT/DRT/fill/finish/RCX，再单独检查原生物理、完整未修改DRC和严格LEC。宏内活动器件属于预制M1–M10，定制M11/M12仍只有线和通孔。

## 证据读取方式

- `repair-results.json`：完整原生验收、两个完整总线的三种RC条件、精确源与回执关联；仅在全部独立结果收齐后生成。
- `closure-evidence.tar.gz`、`closure-evidence-manifest.json`：全部已关闭回执与有界原始报告，按成员字节SHA核对。大数据库、原始SPEF及被限长报告仍在授权服务器，索引保留原SHA。
- `closure-source-and-resource-audit.json`：925起的不可变执行源归档、队列/资源记录和原18文件末次核验；最终审计要求本侧线allocation已全部结束。
- `figures/`：实际OpenDB上层矩形图，SVG含几何和输入SHA；PNG由同批矩形绘制。M使用最终932/MQ1，T/S使用最终940/TQ3；完整路线、原生源及几何均由独立回执关联。
- `evidence/closure-run*/index.json`：本地捕获入口，忽略展开的大量副本，打包时逐项验证；失败/中断和未执行方案保留，不能视为通过。

本轮已完成：M/T/S增强驱动实验副本完整原生验收通过，M→T275根、T→S281根全宽连接的三种RC情景共6项通过。最终940/TQ3使用修补后S940及新寄生，逐项关联其独立完整验收source receipt；旧935的S928不合格结果保留为历史。共同理想时钟根、外部阶段控制、研究层RC情景仍是假设，不授予完整系统、动态SI、foundry RCX或制造资格。

## 重现入口

先按源/资源审计中的不可变`source.tar`恢复当次代码；正式EDA只在获授权Slurm计算节点执行。每个任务由`worker.sh`接收16CPU，完整验收使用普通96CPU节点队列；有限短步骤只有完全关闭回执有效。不得直接修改旧源或覆写其任务目录。

```powershell
# 在仓库根目录执行；这个控制命令将脚本目录加入模块搜索路径。
python -m unittest discover -s project/experiments/block_v1 -p test_interconnect_spef.py
python -m unittest discover -s project/experiments/block_v1 -p test_linkclose.py
python -m unittest discover -s project/experiments/block_v1 -p test_linkfix_channel.py
python -m unittest discover -s project/experiments/block_v1 -p test_linkfix_s_patch.py
python scripts/check_project.py

# 实际完整捕获须用尚不存在的新目录；下面示例不能覆盖已有快照。
python project/experiments/block_v1/interconnect_collect.py block-v1-20261029-940 .local/new-capture940 --closure

# 展开证据到本目录evidence后，重算封装和跨源汇总。
python project/experiments/block_v1/linkclose_package.py work/YUZE-LU/121/interconnect-fix-20261029
python project/experiments/block_v1/linkfix_report.py work/YUZE-LU/121/interconnect-fix-20261029 --function-run 937 --patched-s-run 940
```

结果以实际回执为准；本地控制和打包成功不能代替硬件验收。登记pending（management-hub PR5未合并），看板unverified/同步pending（未配置board.json），管理员及独立审查人待指定。
