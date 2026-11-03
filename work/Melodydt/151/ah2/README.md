本轮实收：源70611916736ae547f7c25e7acbc100116582ab49，95327/node1/c64/8CPU首r01/COMPLETED0:0/1:16，32CASE/9actualSHA；17输入/14文本/63生成件重核。[正式报告](../../../../docs/W4_AH2_IMPLEMENTATION.md)、[当前路线](roadmap-update.json)、[实际回执](evidence/runs/r01/results/run-receipt.json)。以下源冻结阶段说明保留当时范围，尚不代表完整A/质量/物理。

# Issue151 L4-A-H2：一个KV头服务两个Q头

负责人Melodydt，PR152；研究输入a0610aff，历史正文已在7436dc0d逐字归档。当前为新切片准备，源冻结不表示仿真通过；结果仅按实际服务器回执更新。

目标保持H1024/Sq2/D128，使用真实M/N/E/S及已有helper/N-long/E controller，计算完整输入RMS、四个选定K/V/Q0/Q1投影、Q/K逐头RMS、split-half RoPE、因果Softmax及PV。512KiB选定S8权重通过有序chunk实际供给，输出64字/1024B的两个Q头context。不包含完整KV8/Q16、Wo/残差、ATSP集成、模型质量或系统物理。

本目录放独立整数golden/固定fixture合同、TB合同、服务器runner及轻量证据。生成的权重/二进制/build保留本人服务器新目录，不提交Git。旧48RTL/TB/include和历史source-lock/运行receipt不改。Issue原64972字符正文完整保存在issue151-history-through-atsp.md，SHA/字符数见issue-history-archive.json；在线Issue整理并未撤销历史要求。

仅服务器Verilator/Slurm，作业名zenanyan-ah2/8CPU，任务根/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/ah2-a0610af-20261103，独立input-rNN/runs/rNN，提交前固定commit并核输入SHA。实际job/节点/命令/日志/终态另行实收；不得覆盖尝试目录或将候选当已完成。
