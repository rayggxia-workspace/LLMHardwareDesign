# Issue248 联合研究交接

## 最新恢复入口：全实验与未决方案（2026-11-10 Asia/Shanghai）

先读[主台账D01–D24](../experiments/issue-248-followup-design-ledger.md)、[完整配置](../experiments/issue-248-followup-all-cases.md)和[followup证据](../../work/YUZE-LU/248/followup/README.md)。旧41个run仍在原处；新11包584成员涵盖窄化、小表、四银行/流式/FIFO、X位置/读口、负例、取消及所有未测组合说明。服务器53根覆盖清单在followup/inventory.json。以下旧交接中的S128/S64与102.4GB/s是历史基线，不是当前选定设计。

当前用户只确定51.2GB/s、新设计不用S128并尽量避免持续S64；S32持续状态和Mid已通过本轮部分语料筛查。G表项数/实现、权重供数/FIFO/信用窗/仲裁、X位置、上下文数、额外SRAM、Mid保存/重算等仍未决，不得默认捆绑选定。所有新RTL、实际S地址/端口和M lane排列、联合控制/MC、物理与能耗/FPGA对照仍待做。PR251旧合同须先按新profile修订；本请求仅更新PR249，不修改该PR。恢复时先核对在线head和台账，按需运行followup_report.py只读核验；重跑必须新root且6×10或8×12。发布commit不是历史未提交脚本的执行commit，准确字节看原source.sha256。

入口：[报告](../experiments/issue-248-integrated-closure.md)、[PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)、[硬件合同草稿PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)。负责人YUZE-LU；审查人与后续实现安排待指定。Issue248/250为in_review，不done；PR249父分支已前进并有合并冲突，不能把当前研究上传视为可直接合并主线。

## 已完成与准确口径

公开Qwen2.5-3B-Instruct-GPTQ-Int8 revision固定，权重/scale/zero解包和SHA逐次核验；W8A16/group128、head W8/group16在部分语料通过预设门槛。head128、head32及A8失败都保留，禁止降低阈值代替修复。四个完整FFN的整数参考与有限Down逐位一致；G/M/宽scale/RNE、有限控制与上下文、B bank有独立RTL证据。

最终条件SystemC 10.1028284571token/s（B1/context512/300MHz/总102.4GB/s，双通道每通道双64B发起槽、3P、4B bank/P、新寄存器）；51.2GB/s为9.24067472228，context2048为6.41254883481。同资源去屏障收益3.8756%，没有20%纯DP收益。生产RTL未改，没有整机实测token/s、J/token或新物理资格。

## 恢复与核验

先读取AGENTS/Skill、在线Issue248/250/PR249/251及父分支最新状态。运行`closure_report.py --root work/YUZE-LU/248/closure`：22包1537成员。质量run38/102029、时间run40/102031、RTL run41/102032；均终态COMPLETED，失败历史另保留。原13包958成员、DMA3包185成员、精度3包138成员仍可离线核验。

服务器本人任务root统一为`/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-<tag>`，不得覆盖。公开工件在`issue248-public-w8-20261110-01`；Git保留每文件SHA，模型与大向量未放Git。所有EDA/ML/SystemC只在Slurm分配节点执行。旧root/source、工具、输入与commit全部有manifest；以原job.sh和stage重跑，用全新tag。

获取回执的source_commit有已披露工作树改动记录缺口，不可回填：首次本机纯I/O下载时`--fetch-local`尚未提交，后来进入d34db101c。工件字节/公开revision及后续Slurm执行源码分别核验；本地重复大下载已清理，服务器与回执保留。

## 下一步不可跳过

1. 把归一化、RoPE、Attention/Softmax、KV、残差、head纳入共同逐位整数参考。当前质量筛查这些路径仍有浮点，不能宣布所有精度问题解决；扩完整语料与长decode。
2. 按PR251合同接局控描述符、M/scale/RNE/G、真实SRAM及DMA。独立服务通过不能替代联合P。重点校准head的16子组、每拍吞吐、首字延迟、ACK、背压、满槽和reset/flush。
3. 用联合RTL校准SystemC，再决定10量级是否保留；当前M/G/feeder/bank是新有源资源，必须重新实现M1–M10。维持独立叶宏/控制分组及后制M11/M12，不重新硬化五个大框。
4. 重建真实pin/负载/路径和完整静态网并集，再接#220动态状态成本和布线反馈。研究固定FFN配方并非完整图综合/布线器。
5. 实际活动/存储/外存表征能耗，固定同模型/精度/上下文再与FPGA/ASIC对照。未验证不填实测字段。

登记management-hub PR5仍pending；缺board配置与Projects能力，看板unverified、同步pending，管理员待指定。CI此前账单额度导致未启动，上传后按最新head读回；不能把本地管理检查说成GitHubCI已通过。未自合并或代批。
