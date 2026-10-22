# Issue16 工作索引

- 任务：[Issue16](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/16)，主要负责人 Liangruizhi。
- 分支：`task/16-macro-endpoints`；工作目录 `D:/Projects/LLMHardwareDesign-lef`。解析器独立审阅工作目录 `D:/Projects/LLMHardwareDesign-lef-review`，分支 `task/16-lef-parser-review`，没有独立上传或 PR。
- 本轮范围：三份普通 LEF 原字节捕获与 SHA-256、保留 PORT/PG/OBS 的几何导出、重放与交接。正式工具在 `project/experiments/macro_endpoints/`，正式记录在 `docs/experiments/`，不修改 Issue7/15 的物理工程。
- 临时目录：`D:/Projects/Codex/lef-endpoint-export-20261022`；正式运行前必须提交源码。输入来源和缺项见工具 `inputs.json`。
- 并行核对：Issue15由YUZE-LU推进ACT/MXU同资源物理对照，与本任务分离；PR12/14待审查，不另开重复任务。
- 分支清理待办：创建Issue时15刚被他人使用，本会话误建了空远端分支`task/15-macro-endpoints`，立即停用并改用真实Issue16。该空分支停留在`a2769bf9fc6409816c16d5cbea1e5c8c45bc2d58`，没有本任务提交或PR；当前GitHub插件没有删除分支能力、CLI未认证。维护者待指定，清理前须再核对head及无新工作；它不是Issue15的工程分支。
- 登记：management-hub PR5未合并，pending。看板缺本地配置且本会话无Projects工具，在线权限未核验，条目及同步pending；管理员待指定。
- 交付：[PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)；[正式实验](../../../docs/experiments/issue-16-macro-endpoints.md)及[独立审计说明](review.md)。机器生成SVG保留Matplotlib原始字节，按二进制成果管理；PNG布局已人工查看，PNG/SVG均核对SHA，源代码和手写文档继续执行diff空白检查。
- 清理限制：离线重放通过后尝试清理本任务offline-replay-01、figures-01、pycache、matplotlib四个临时目录，已核对绝对路径均在任务D盘范围；自动审批返回blocked by policy，未执行删除、未绕过，暂保留这些目录，维护者待指定。
