# Liangruizhi 的进度

- 更新：2026-10-22（UTC+08:00）。GitHub身份Liangruizhi／2663955430@qq.com。
- 当前任务：[Issue16](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/16)／[PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)，task/16-macro-endpoints，D:/Projects/LLMHardwareDesign-lef；基分支task/13-endpoint-ablation，依赖PR14/12。清洁源码23040b0459cd32297b6562e22f48af5ae812ed25捕获三份真实普通LEF，6791PIN/6956PIN RECT/30OBS RECT导出与逐字节重放通过；67项业务检查通过，轻量原字节与图表已归档。本任务交付待审查，未合并／未标done。
- 本轮证据：[实验记录](../../docs/experiments/issue-16-macro-endpoints.md)／[交接](../../docs/handoffs/2026-10-22-issue-16-macro-endpoints.md)。保留PG多RECT与整块OBS，未将几何矩形当作合法access point；上游逐文件预期SHA、RTL/tool/image精确版本仍待核实，三宏资格false。
- 前序任务：[Issue13/PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14)在D:/Projects/LLMHardwareDesign-endpoints，384例与33项检查交付待审查。清洁源码dc294114运行：restricted44/96、access71/96、capacity44/96、joint71/96；230解、248cut、24精确状态全部验证，9映射有白名单无路径→合法证据。见[实验记录](../../docs/experiments/issue-13-endpoint-ablation.md)及[交接](../../docs/handoffs/2026-10-22-issue-13-endpoint-ablation.md)。
- 已完成：独立副本、venv、模型／基线／全局合法性／映射能力／软件数值／精确小例工具；17项业务检查通过。实际清洁源码6ab796b运行192例，顺序32/96、多顺序44/96；76成功解和81次数值全通过，24小例15可行/9不可行，确定性重放与全部输出SHA读回通过。结果与图表已归档本分支，见[实验记录](../../docs/experiments/issue-11-frozen-routing.md)及[交接](../../docs/handoffs/2026-10-22-issue-11-frozen-routing.md)。
- 下一步：审查PR12/14/18；核对ACT—MXU端口逐bit合同与RTL/Lib匹配、DEF安装方向、技术via/OBS合法访问，条件满足后做总预算固定的端点感知mapping。保留YUZE-LU的Issue7/15物理工作；审查人／后续实施负责人待指定，不自合并。
- 阻塞与局限：本机无可用EDA环境，模型未校准，不提供物理H2/PPA；复用既有工具而不改其他成员工作。登记pending（管理中心PR5）；Projects无工具/无本地board配置，unverified／同步pending，管理员待指定。
- 已有任务：[Issue #5](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/5)协作规则由[PR #6](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/6)交付，仍待审查／未合并。该分支里的详细规则继续有效，不另开重复PR。
