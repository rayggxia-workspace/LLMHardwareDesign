# #219 / PR269 宏级指令与连线交接

分支：task/219-framework；本次提交父版本 3e696988d18829a583d573b8cb474ae587301660。账号 YUZE-LU 已由用户明确选择并经连接器认证核实。项目 llm-hardware-design，协作规则 rayggxia-project-collab 1.0.0。

源码：[blockv2_mod](../../project/experiments/blockv2_mod/README.md)；[完整结果和责任](../../project/experiments/blockv2_mod/evidence/architecture-revision-185/RESULTS_ZH.md)。完整预填充及自产 KV decode 的1374个产出张量逐字节一致；20张 benchmark 的首个前端阻断全部记录。PR 待独立审查，不关闭更广泛的 Issue #219，不自批准或合并。

所有重型文件在 /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod/。delivery/review-115203 保存源码、完整计划/指令/候选连线压缩包和逐文件 SHA 索引。模型权重与 DDR 运行镜像仍在原授权远端位置。仓库仅提供源码、小型回执和索引，未将大体积原始工件上传。

此前发布阻塞结论需纠正：连接器调用缺少账号 link_id，完整工具说明已经提供可选账号。传入用户确认的连接 ID 后，身份、Issue 和 PR 读取成功。远端直连 GitHub 仍超时，因此使用 GitHub 连接器按父树增量集成，不读取或转移凭据。

看板：当前父版本 config/board.json 返回404；状态映射存在，未发现可用于此仓库的 Projects 配置，未宣称同步。维护人需补配置并核对 Issue219 卡片。登记沿用原任务既有记录，本轮未修改管理中心。

后续：审查宏/父层资源清单和完整短程证据；修复 benchmark 前端尺寸/operand lowering 前不要归责缺硬件。当前服务时序未校准，不声称完整算术 RTL 联合运行、物理时序/PPA、广泛模型精度或连续请求吞吐通过。
