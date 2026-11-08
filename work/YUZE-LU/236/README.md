# Issue236：decode容量的独立硬件改进入口

2026-11-09 CST，负责人YUZE-LU；[Issue236](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/236)，
独立task/236-decode-capacity，基于main c4d7b960599b9d292f27eb4429d5f226a7156c95。
正式工具/选项/阶段门见[容量说明](../../../../project/experiments/decode_capacity/README.md)。

已完成源绑定的容量必要条件和6项检查。结果见[capacity-result.json](capacity-result.json)：
Qwen2.5配置与完整图253个静态Dot形状独立匹配；Qwen3有效Q维4096，密集工作量4,022,272,000 MAC/token。
三颗当前64路M在理想300MHz的密集S8计算上界14.3203token/s；作者U280 Qwen3-4B Q4_K_M参考72.5。
必要规模至少16颗当前M等价、4bit权重理想流量145.807GB/s；这些不是推荐或已闭合硬件。
保留对手原生量化和证据缺口，不称同质量实测胜负。

M源SHA与Issue219冻结原生输入相同，64个物理S8乘积/ISSUE拍、row顺序复用。
不从低效标量程序推断硬件失败；当前结论明确限于已注册密集M服务与理想容量条件。
更多实例、扩大阵列或低比特能力的RTL/控制/S/接口/物理还未实施，保持in_progress。
未更改PR220的三M算法基线，也未修改#234或其他活动工作树/作业。

证据：官方配置原始字节在正式目录configs，固定URL/revision/SHA在workloads.json。
inventory-summary.json为PR220 d20029b4已提交九组审计原件；graph-dense-check.json从已资格化S2图抽取形状，
完整大IR仍在原任务获授权目录，不复制权重或大IR。source-receipt.json记录固定配置重新下载核验和M源来源。

实际检查：项目结构、6项单元检查、容量CLI及diff检查；没有执行新模型数值/RTL/SystemC/EDA，未声称系统达标。
当前PR为部分交付、待独立审查；审查人待指定，不自合并/关闭。
规则rayggxia-project-collab1.0.0，project_id llm-hardware-design。
登记沿用management-hub PR5 pending；缺board配置/Projects能力，看板unverified/同步pending，沿用Issue7交接。
下一步按正式说明先结合#234实际原生tile校准，再筛规模/接口和低比特候选并实施独立RTL/物理门；总目标不缩减为本次分析。
