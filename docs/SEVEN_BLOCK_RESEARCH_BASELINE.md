# 七宏RTL集成后的连接/控制研究基线

任务：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，交付：[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)。用户明确要求把PR144 seven-block-v2内容合入现有研究分支，再以此继续。本轮仅做依赖整合、合同复核和轻量检查，没有改写叶宏RTL或启动服务器/EDA。

## 固定来源和分支关系

- 来源PR144：643c6012a11cbf461146ac40fbf61485223fe946，tree e2f910685f6714daa4f5df21889e826d8390013e。
- 合入前研究分支：46b29c7664fefedf2de767ddcfb94a766cf341fb；真实共同祖先：6a681d6632e7f7be537ff96eae1827df834bcfe8。
- 保留双方提交历史，以双父merge commit交付，目标仍为task/151-six-connection-study；不修改PR144分支、不合并到main。实际合入commit由PR152/Issue151最终回执绑定。
- PR152改为依赖PR144的研究PR，base为task/143-seven-block-v2。后续源分支提交不会自动进入本研究分支，需再次同步并核验。
- GitHub compare返回300文件上限不能当完整导入清单。本轮以分层Git树三方比较，源project和相关封存资料按既有tree/blob引用保留；ref-project三方同树，没有展开、重算或修改。

## 当前七类宏的代码入口

| 宏 | 本分支真实RTL入口 | 研究使用约束 |
| --- | --- | --- |
| M | [block_v2_m.sv](../project/rtl/block_v2/block_v2_m.sv) | 行级提交、A128/B512、结果读出与上下文独占 |
| N | [block_v2_n.sv](../project/rtl/block_v2/block_v2_n.sv) | 全组统计/回放；TopK只返回ID |
| E | [block_v2_e.sv](../project/rtl/block_v2/block_v2_e.sv) | op13四S32转四S16，必须保留有效数与尺度 |
| G | [block_v2_g.sv](../project/rtl/block_v2/block_v2_g.sv) | 两lane、四级可背压流水，激活输入/门值角色明确 |
| R | [block_v1_r.sv](../project/rtl/block_library_v1/block_v1_r.sv) | 当前跟踪RTL为临时算术缩窄候选；活动/影子与局部提交合同不等于已获物理资格 |
| S | [block_feed_s_macro.sv](../project/rtl/block_feed_v1/block_feed_s_macro.sv) | 内含四bank存储及loader；宽/窄争用不增加端口 |
| T | [transaction6k.sv](../project/rtl/block_v1/transaction6k.sv) | 6KiB单批填充/提交/消费/释放 |

[接口合同](BLOCK_V2.md)、[上游结果](BLOCK_V2_RESULTS.md)现已在本研究分支实际存在。14份核心RTL/包含表/局部依赖的Git blob和SHA-256见[机器基线](../work/Melodydt/151/rtl-baseline.json)。源project整树按原引用合入，并非仅复制这14份文件；本地隔离验证包只物化检查所需文件，不冒充完整Git clone。

## 与前两阶段研究的关系

七宏逻辑接口与5e787714/aacac923时的固定研究合同一致；最新新增内容为R修复/失败证据。M/N/E/G/S/T已有上游适用叶子证据；R仍未合格。R053/R062全局布线拥塞失败、R076全局hold达到缓冲上限等为新增失败记录，不构成合格R。跟踪的R文件与085/090/093采用的原R4032封存数据库不能混用。

第一阶段source-index/connection-index、旧verification，以及第二阶段system-source-index的aac来源均保留历史身份；本轮用rtl-baseline记录集成来源并重新运行当前静态检查。历史行引用不全局替换成新head，不转移旧物理结果资格。

本次不会自动引入PR133的linkclose/linkfix专用桥或PR146 SystemC。旧shared_services/shared_gdn等历史实现可以作为参考，但不是本总方案NUM、外部状态版本管理或统一协调器已实现的证明。

## 在现有RTL上继续研究的顺序

1. 以[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)、[控制规格](SIX_CONNECTION_CONTROL_SPEC.md)、[六模板](SIX_CONNECTION_TEMPLATE_SPEC.md)为proposed系统设计，逐任务绑定本分支真实端口/opcode；先核验M cmd/rsp与S loader A/B的唯一归属。
2. 首个实现候选仍是S8/no-input-Norm的小FFN：400B S地址预留＋T1字；随后是257元素Softmax：1056B S有效区＋T33字。实例规格已详细列出，尚未实现系统wrapper RTL。
3. 拆母控、M/N/E/G局部适配、S服务与T发布的真实RTL子任务，再按独立参考/随机背压/错误复位验证。新子任务应明确验收、负责人、分支和实验追踪，不在本次同步中暗自启动。
4. GDN/SSM完整链仍需NUM_COEFF、外部多tile状态/history版本与发布协议；MoE仍需gather及宽归并。引入叶宏源码不消除这些能力缺口。
5. 首版数据/事件/取消模型通过后，再按授权开展RTL/SystemC、综合与冻结前控制分布物理比较。本机无可用Verilator/Icarus工具；上游run_rtl.py依赖Linux专用路径/CPU affinity，不在Windows误报执行。

## 验证与隔离

本地集成包：work/Melodydt/151/merge-pr144-643c6012/integrated；父目录保存三方输入与冲突记录，原system-delivery和根管理副本不覆盖。三方共同文档保留main规划及上游实施历史；progress/YUZE-LU只做合并冲突保留，不改写其业务结论。

实际命令：check_project.py、verify_study.py、verify_system_design.py、verify_rtl_baseline.py，以及上游test_input_hold_guard.py轻量Tcl夹具。准确结果以本轮integration-verification.json和当前system-verification.json为准；Tcl夹具不是RTL或物理仿真。PR创建/分支上传、CI、审查、登记和看板分别记录，未合入main或验收前不标done。
