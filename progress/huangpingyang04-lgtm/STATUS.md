# huangpingyang04-lgtm 的进度

- 更新时间：2026-10-23 16:19（Asia/Shanghai）。
- 当前任务：[#43 五个开源加速器的模型规模与资源调研](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/43)，负责人本人；交付后保持 in_review，审查人/优先级待指定，未验收或合并。
- PR：[PR46](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/46)已创建；最新commit与线上CI读回保存在Issue43/PR回执，未自动合并。
- 本轮修订：按用户讨论在正文开头增加五项目“模型规模/计算单元”简表，补充256个INT8乘法位置为一块时的1块/2块算术规模对应、模型大小与复用/速度/带宽的关系及定数量所缺三组输入；原详细表折叠保留。沿用已核对的一手版本，未新增模型支持或性能声明。
- 成果：[正式调研](../../docs/OPEN_ACCELERATOR_CAPACITY_SURVEY.md)、README入口。分开INT8、FP4混合、INT4和BF16，列模型规模/计算/存储/带宽及来源范围；给出容量、MAC和各路径带宽下界、假设数值算例、Block库存与预连线输入。llaccel上游身份已由参考包commit对应到taisirhassan/llaccel。
- 隔离：工作目录 `C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-accelerator-survey`；分支 `task/43-accelerator-capacity`，起点 main `0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d`；commit/PR上传回执与线上CI读回以本任务Issue为准。
- 验证：`python scripts/check_project.py`通过；24个固定commit GitHub文件实际读取，Gemmini DAC2021作者PDF核对§IV/Fig.6；5张Markdown表、引用定义/使用、5个上游commit及表中公式以本机Python复算通过；`git diff --check`通过。管理检查不验证产品行为；未运行模型、量化、完整推理或物理实验，无服务器操作。
- 下一步：团队提供Block粒度/吞吐/可用存储/端口/时钟/物理引脚及INT8状态合同，冻结工作负载与目标吞吐后，把调研输入接到[#41候选合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/41)，决定库存扫描；文中的1/2/4矩阵块不是最终芯片规格。
- 限制：作者板上结果本轮未复现；llaccel限仿真、OpenTallas限规划及局部证据；本地小case不证明整模型支持。Block总量尚无充分输入，不给无依据定值。
- 并行记录：[#25 / PR26](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/26)为INT8功能模块benchmark，仍待审查；[#42](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/42)为独立控制锥算法工作，进展以其Issue/PR为准。本PR未修改其分支；并行PR若新增同名个人进度文件，合并时应保留各任务条目。
- 协作回执：规则rayggxia-project-collab 1.0.0；project_id=llm-hardware-design；本人账号/目标仓库权限已核验。登记沿用[management-hub PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)，未合并为pending。仓库无board.json、当前连接无Projects工具，实际看板unverified、同步pending，不推断账号权限。
- 看板交接：具能力/权限管理员（待指定）先确认组织看板#1受众/字段，复用或加入Issue43；填写Project ID=llm-hardware-design、Status=In review，核对assignee并读回条目ID/状态/时间；Priority、日期待指定，不猜值。恢复工作先读最新Issue43/PR及本调研，不以本地记录代替线上状态。
