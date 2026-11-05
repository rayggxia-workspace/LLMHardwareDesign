# Issue177：每个 Block 的私有 S 局部仲裁

- 任务：[Issue177](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/177)，负责人/执行账号 huangpingyang04-lgtm。
- 设计入口：[文档PR176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)。
- 实现PR：[178](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/178)，待独立审查、未合并。
- 实现分支：`task/177-local-s-arbitration`，基于 main `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`；RTL最终测试源码 `8b92b67ea88dc651a151b3f265e72d97487545fc`。
- 正式说明：[接口与局部控制](../../../docs/BLOCK_LOCAL_S.md)、[服务器结果](../../../docs/experiments/issue-177-local-s-results.md)。
- 精确接收：[LOCAL_RECEPTION](evidence/LOCAL_RECEPTION.json)、[远程原件/作业索引](evidence/remote-index.json)、[最终结果](evidence/job-96410/result-r01/results.json)。80份原文件/1,574,128字节逐个SHA及本地落盘读回核验；另两份为本地生成的索引与接收回执。

原RTL阶段的服务器新任务目录均在 `/public/home/yuzelu/PingyangHuang/issue177-local-s-*`；没有修改已有源工程或其他人的作业。五个任务的源码归档、完整structural netlist、构建及可执行文件仍在各自目录，大小/SHA见远程索引；旧失败保留。96403仅在核对本人UID、job名和完整任务路径后，为切换已验证的ABC批处理方式取消，不是硬件通过。

验证本地接收和源绑定：

```powershell
python -X utf8 -B work/huangpingyang04-lgtm/177/check_evidence.py
python -X utf8 -B scripts/check_project.py
```

当前RTL及追加的三种16KiB局部S叶宏物理验收均完成，PR待独立审查，不自行合并或标done。32KiB、完整计算Block/模型/控制接入、M11/M12与制造签核不在通过范围。

协作规则rayggxia-project-collab1.0.0；2026-11-03 23:27 CST在线读回management-hubPR5仍open/unmerged，登记pending。本仓库无config/board.json，当前连接器无Projects条目/字段能力，条目unverified、同步pending；管理员和独立审查人待指定，见[持久交接](../../../docs/handoffs/2026-11-03-issue-177-projects.md)。

## 三配置物理证据

[正式物理结果](../../../docs/experiments/issue-177-local-s-physical.md)；[完整远程索引](physical-evidence/remote-index.json)、[实收回执](physical-evidence/LOCAL_RECEPTION.json)、[提交的原始子集](physical-evidence/COMMITTED_SUBSET.json)。P4/N4/N5各四门绑定相同封存SHA；保留ECO前失败来源及精确修复证明。原始报告、小日志及实际版图在`physical-evidence/raw`，所有原始字节保持；大物理数据库不进入Git。

完整接收在`C:/Users/86188/Documents/ChatGPT/2026DAC/deliveries/issue177-local-s-20261103/rx-20261104T133110Z`：`evidence/raw`保存完整小原件，`files`保存三配置六文件/版图，四个归档另存；服务器归档在`/public/home/yuzelu/PingyangHuang/issue177-s-package-20261104T132358Z`。默认只重读Git中的报告子集，完整复核须指定两条参数：

```powershell
python -X utf8 -B work/huangpingyang04-lgtm/177/check_physical_evidence.py
python -X utf8 -B work/huangpingyang04-lgtm/177/check_physical_evidence.py --raw-root "C:/Users/86188/Documents/ChatGPT/2026DAC/deliveries/issue177-local-s-20261103/rx-20261104T133110Z/evidence/raw" --files-root "C:/Users/86188/Documents/ChatGPT/2026DAC/deliveries/issue177-local-s-20261103/rx-20261104T133110Z/files"
```

2026-11-04 21:41 CST重新核验登记PR5 open/unmerged，pending；仓库已读status-mapping但无board.json，当前连接器无Projects条目/字段能力，条目unverified/同步pending。独立审查和接入处理人待指定。
