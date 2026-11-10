# Issue248：公开 W8 权重、宽范围 G 与有限 FFN 的联合研究

> **后续更新（2026-11-10）**：本页记录的是原S128/S64、大表、四银行候选的历史证据，以下数字不改写。9.24起点之后所有讨论、实验和未决项已集中到[完整台账D01–D24](issue-248-followup-design-ledger.md)及[全部配置](issue-248-followup-all-cases.md)。用户现确定总51.2GB/s、新设计不用S128并尽量避免持续S64；S32/Mid32筛查通过。G表、FIFO/银行、X位置、上下文和仲裁等仍未定案，不能把本页旧合同当成已确认的新生产设计。

关联 [Issue248](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/248) / [PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)。实验源码位于 `project/experiments/stream_quant_synthesis/`，不可变回执位于 `work/YUZE-LU/248/closure/`。生产 `project/rtl/`、其他成员的工作树和作业未修改。

**这是下一版底座候选的研究，不是当前 main 的整机验收。** 条件 SystemC、浮点 Attention 的模型质量筛查、四个 FFN 的精确整数参考和若干独立 RTL 服务分别记录。完整整数模型、联合 P/局控/DMA、300MHz 物理资格和能耗仍未完成。

## 1. 输入与原有误解

直接使用公开 [Qwen/Qwen2.5-3B-Instruct-GPTQ-Int8](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GPTQ-Int8)，固定 revision `1fed15cb34975bc0bd699e62b95a539bb06eed42`。配置为 GPTQ 8bit、group128、无 activation reorder。原始工件、逐文件 SHA、配置与数据行获取回执留在本人服务器 `/public/home/yuzelu/project-circuit/issue248-public-w8-20261110-01`。此前自生成 W8 的实验保留，不再把它当成原生公开 INT8 工件。

INT8 checkpoint 主要规定**权重**。本工件的嵌入/输出词表共享矩阵仍为 FP16；其他线性层有 W8、FP16 scale、zero-point 和 group 索引。按官方 GPTQ 的 packed zero 加一规则解包；每个模块另做64个标量坐标检查，检查全部 W8 范围及 group 索引。正负号、scale 和 group 不能靠文件名猜测。

本候选把密集输出词表矩阵也转成 W8；嵌入查表保留原 FP16，单列例外。词表 W8 不是公开工件原生参数，必须另外验证质量。head128、head32 没过预先设定的一致率门槛，不能隐去；head16 是后续候选。

模型质量输入固定为 WikiText2 test 前100行中前1024个 token（8段128 token），另加 Hello；共1025个输入位置、1016个 loss 位置。另验证512 token 提示加16步、沿相同参考 token 的 decode，使用真实但仍为 FP32 的 KV。该结果是**部分语料筛查**，不是完整 WikiText 困惑度、任务能力或长期生成验收。

## 2. 数值合同

| 边界 | 候选的实际语义 |
|---|---|
| 权重 | 其余投影沿用公开 W8/group128；head 候选重新量化为 W8/group16；正的 FP16 scale 精确拆成整数 mantissa 和二进制 exponent |
| M 输入 | A16；每128个激活求一个二进制移位，明确 RNE；A16 是有符号整数容器，不是 FP16 |
| M 核 | K16×N8，即每拍处理16个 K 输入、8个输出列，共128个乘积；分组部分和 S40 |
| scale 合并 | 整数部分和乘 FP16 scale 的整数 mantissa，再移位；S128 累加；全 K 完成后才统一 RNE，避免每组反复舍入 |
| 投影输出 | S32/Q16，bias 在声明的位置加入；溢出报错，不默默截位或钳位 |
| G 输入 | gate/up 都为 S32/Q16；2049点 SiLU 表、整数线性插值及 RNE；x≥16 用 x，x≤−16 用0 |
| 门乘输出 Mid | S64/Q32，完整保留 S32×S32 乘积；随后按128元素重新归一化为 Down 的 A16 |
| Down | 同样做分组 M、scale 合并、有限 S128 部分和和最终 RNE |

`closure_contract.py` 给出算术包络：在 K≤16384、W8、有限正 FP16 scale、S32 gate/up 和其 S64 乘积范围内，S40 组和及 S128 合并不溢出。最终 S32 的范围仍须检查，包络不保证任意权重/输入都能输出 S32。LUT 数学抽样最大绝对误差小于4×10⁻⁵；四个实际 FFN 的输出相对 L2 约9.46×10⁻⁵～1.39×10⁻⁴。

**这修正了旧 G 的固定 Q5.10 接入和 S16 门乘饱和问题，需要新的 G 有源实现。** 并非改一个移位就让已验收 G 获得这些能力。归一化、RoPE、Attention/Softmax 的整图筛查仍用浮点参考；不能由这张表推断已得到完整整数 LLM。

最终 W8A16/head16 相对**原公开 GPTQ 参考**：PPL比值1.000601912（增加约0.0602%），平均KL9.81684×10⁻⁵，最差序列logit余弦0.99997782，1025个位置首选token一致率99.5122%。context512的16步首选token全部一致。它通过预设PPL≤1.01、余弦≥0.999、KL≤0.01、一致率≥99%、无S32钳位的筛查门槛；A8一致率约96.68%，仍拒绝。head128/32原门槛失败记录均保留，未修改门槛。

## 3. FFN 有限存储和控制怎样闭合

Qwen FFN 为 `X[2048] → gate/up[11008] → Mid[11008] → Y[2048]`。每次只生成128个 Mid：

1. X 转为 A16，4KiB；经真实计费的 U→P 单播，保留在每个 P 新增的4KiB feeder中。
2. 三个 P 分配 gate/up 输出列；每个 P 最多16个带标签、每个8路 S128 的投影上下文，共2KiB有源寄存器。不同 P 各自推进 K，不在每个 K128 后强制全局同步。
3. 该128元素片段的 gate/up 完成后，汇到 P0 旁的新 G。G 两路每拍处理，128值为67周期；S 读写和跨组搬运另外计费。
4. Mid 为1024B；在有限窗口归一化成256B A16，送往三个 P。source lease 保留到所有消费者真实提交，不在计算刚结束时释放。
5. Down 输出2048维按688/680/680分给三个 P；每个 P 的完整 S128 状态为11008/10880/10880B，一次只取8个输出上下文。第一片初始化，后续片读旧和、加本片贡献、写回；最后一片统一 RNE。

因此无需存下整个44KiB S32 Mid，也没有凭空无限累加器。代价是**每个 FFN 的私有存储读、写各2,785,280B**，36层累计各100,270,080B。它是本地存储流量；不能误记成 DDR 流量，也不能删除。

每 P 的保守 SRAM 同时生存预算：11008B Down 部分和 +2304B 原双 B 槽的最大记录预算 +512B 双 A +1024B gate/up +1024B Mid +512B 控制 = **16384B**。模型另外登记新增 feeder、投影上下文及额外 B/结果槽。实际 B bank 是独立候选资源；当前保守预算把原双槽也预留在16KiB预算中，最终物理绑定需去除重复计量，不能据此冒称原 S 宏已有该端口。

两/四/八个 bank 有有限分配、generation、完整 fill、消费确认和释放检查。17个64B拍的普通权重记录为1024B W8 +16B scale +48B padding；head16 用18拍，末128B放分组 scale。真实 W8 片段的打包/逐拍消费另有24个独立审计。新 RTL bank 输出128B/拍给 M、64B/拍接 DMA；**原有 S 并没有因此变成128B/拍端口**。

## 4. 迭代及吞吐口径

下表均为 batch1、context512 decode、300MHz 条件服务模型。吞吐为完整36层 trace 的单输出 token 时间倒数，包括 KV 相关 trace 服务；不是 FPGA/芯片实测。

| 轮次 | 改动 | 条件 token/s |
|---|---|---:|
| 旧服务对照 | S32、修正 DMA 排队/输入释放；不代表新精度合格 | 7.17145 |
| 初版联合候选 | 分组量化、scale 单独取、有限 FFN | 约5.05～5.64 |
| packed scales +有限寄存器上下文 | 同一记录预取尺度，减少投影 S 往返 | 7.46459 |
| X 驻留+4 B bank | 新资源单列，head128 尚未过质量门槛 | 10.05161 |
| 同资源去掉逐K全局屏障 | head128，质量仍未过门槛 | 10.45474 |
| 加 head32 的实际服务费用 | 质量仍未过门槛 | 10.37787 |
| 加 head16、最大记录和容量预留 | 通过预设部分语料筛查；仍是条件模型 | **10.10283** |

102.4GB/s 是总外存预算，另需**每通道每核心周期两个64B请求发起槽**；只提高名义 DDR 带宽不能达到上述结果。两个通道的总请求上限为76.8GB/s，实际利用率再受 bank、行冲突、FIFO 和消费者影响。4 B bank 比8 bank快，所有反例保留。

51.2GB/s、单请求槽、长上下文分别做消融。已知 head32 的51.2GB/s结果9.48836，context2048结果6.52227；不能把 context512 的10量级推广到所有上下文。head16 的51.2GB/s结果为 **9.24067**，context2048为 **6.41255**。同资源仅取消逐K屏障为9.72589→10.10283（**+3.876%**）。完整表、阶段费用和字节数以 `closure/summary.json` 为准。

这些是有限流式执行与资源组织的收益，**不是 #220 的可布线路径 DP 的收益，也未证明20%纯 DP 收益**。下一步应把这些服务作为编译器候选，使用相同状态转移计费；现在的 FFN识别/固定128片段调度不是自动图映射或布线闭合算法。

最终98.9822ms/token的阶段和：FFN52.1731ms，其余Dot26.3904ms，归约8.3766ms，向量7.0111ms，NExp4.2492ms，其他约0.782ms。外存读3,388,365,824B、写8,191,232B/token；仍以逐token读取W8权重为主。它没有靠把全部权重放进片上来规避DDR。相对于该模型的16KiB保守预算，每P另外登记4KiB X、2KiB投影上下文、256B A寄存器及2560B额外B/结果槽，共8.75KiB；这些不是主线已有资源或已测面积。

## 5. 已有证据与不能转移的资格

独立 RTL：真实 W8A16 M192包/24输出；实际 G2048包、连续/背压/复位；S128合并600例；带SRAM读/写ACK的有限控制600例；16上下文1025例；最终RNE/bias/范围1200例；B bank 2/4/8分别48/96/192次宽读及晚到响应拒绝。四个完整整数 FFN 的有限调度逐位一致。它们尚未串成完整 P/局控/物理 SRAM/DMA RTL。

归档包含失败：compute节点DNS、NumPy打包、严格TB诊断、扩bank旧检查、bank索引宽度、无效S128测试向量、代码生成锚点。修复后使用新 commit/root/job，不覆盖旧回执。离线脚本验证每个成员 SHA 和真实 Slurm 终态。

没有修改现有生产宏或硬化五个大框。P/U/C/F/J 仍为独立叶宏加局控的控制分组；新 M/G、coefficient/RNE适配、feeder/bank 是**新有源底座版本**，必须在 M1–M10 冻结前落实。不是在已冻结主线底座上仅改 M11/M12 就能获得10 token/s。后续合同另列真实端点、源保持、选择器、驱动、时钟/电源、SRAM端口、描述符版本、完整静态网集合和物理验收。

能耗、完整整数生成、真实MC/DDR、联合RTL、最终P&R、OpenTPU/LLAccel同模型/同精度的公平对照仍待验证。能耗和实测 token/s 字段保持 null，不从字节数猜功耗。

## 6. 复现

本地只做标准库证据核验：

```sh
python -B project/experiments/stream_quant_synthesis/closure_report.py --root work/YUZE-LU/248/closure
python -B scripts/check_project.py
```

质量：提交源码后，用新 tag 的 `deploy.py <tag> --out <本地回执目录> --closure`；读取锁定公开工件，在 Slurm 4CPU ML 环境执行 `closure_quality.py`。

RTL/时间：`--closure-backend` 按已归档 `closure_backend_job.sh` 的 stage 执行。历史 stage/配置不同，复跑应选择对应源码 commit，并用全新 tag；不能改历史 SHA 或复用旧 root。`--stage rtl` 与 `--stage timing` 分别执行，相互绑定通过输入向量 SHA 另验。所有 EDA/SystemC 在 Slurm 计算节点容器中运行。

原始向量、大模型和 build 留本人服务器；Git 保留压缩证据、SHA、源码及可重建命令。首次compute下载失败后改为本机纯网络I/O获取再传服务器；模型执行始终在Slurm。本地重复的3.46GB下载已清理，服务器工件与获取回执保留。

## 7. 本轮交付回执

22个不可变包、1537个成员SHA与Slurm终态核验通过。最终质量run38/102029（源2c7de21c5），时间run40/102031（源46a51f527），RTL run41/102032（源219466ffa）。独立RTL输入绑定run22，离线再次确认其M/G/LUT字节SHA与最终run38相同。该绑定不覆盖未导出的head/Attention整机RTL。

纯标准库管理检查、旧13包958成员、DMA3包185成员、精度3包138成员、原190个整数参考检查全部通过。生产RTL差异为空。新硬件合同由[Issue250/草稿PR251](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/251)独立交付，后续整机/物理资格不在本轮完成。

本机首次下载的获取回执记录f3c3b8cd，而当时`--fetch-local`改动尚未提交（后进入d34db101c）；不能把那个commit当成获取工具的精确源码快照。工件逐文件SHA/公开revision、已提交后续执行源码与每次Slurm输入校验分别保留。该获取源记录缺口不改变已校验的模型字节，但必须披露，不能回填旧SHA。
