# 七模型200MHz公开评估成果

Issue #293 / PR #294；负责人 Melodydt；2026-11-18 Asia/Shanghai。

本次公开范围经用户明确授权：200MHz报告、逐模型结果、轻量仿真及校验回执。额外输入归档和新增复算脚本没有纳入本次发布；因此公开结果包不能单独用于从头复算。此前分支中的脚本属于阶段性版本，以本次结果和报告说明的范围为准。

- [七页评估PDF](../../../docs/experiments/seven-model-200mhz-evaluation.pdf)
- [DAC论文Word合并表](../../../docs/experiments/seven-model-200mhz-dac-table.docx)
- [逐模型结果](results-200mhz.json)及[CSV](summary-200mhz.csv)
- [轻量样本与散列回执](results/accepted-results.zip)、[数值和单位核验](validation.json)、[文档检查](artifact-validation.json)、[Slurm终态](job-final.txt)

核心200MHz，DDR周期630ps固定；三路P和512-bit SRAM配置延续冻结基线。七模型28份样本、192次层输出核验、14个功耗窗口分项守恒通过。完整窗口和512-token Prefill为代表层支撑的估算，真实全模型及长序列误差未实测；能耗仍为已覆盖硬件小计，无完整物理签核。Prefill能耗对应2-token短窗口。

本轮本地评估完成；PR待独立审查，不自合并。登记PR5 pending；缺看板配置和Projects能力，状态unverified、同步pending，待具权限维护者补齐。发布散列见public-release-manifest.json；最终提交与Issue状态以PR294的最新回执为准。
