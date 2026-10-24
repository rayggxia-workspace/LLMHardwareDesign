# Issue64：先固定语义合同，物理归属保留分叉

日期2026-10-24；负责人Liangruizhi；Issue64/PR65。[完整方案](../BLOCK_PARTITION_V2.md)、[实际证据](../experiments/issue-64-block-v2.md)。

1. 制造库候选保留M/V/A/R/S/D，A/R首先是逻辑闭包；只有数值函数、单位/round和state commit等价的物理方案才能排名。完整K有混合scale时需显式ALIGN_REDUCE，不能一律INT32。受检范围内可用32bit，guard失败保留宽回退/拒绝。
2. M输出保留ACT8/ACT16及版本化scale接口，不把单一Y8或动态delta固化。理由：固定acc改变Y合同可改善Llama/Q35误差，Gemma同范围Y16仍可饱和；动态delta每16输出tile，后继K16单位/残差/norm未验证。通信按声明packet字段和物理粒度计算，不把1B元数据称免费或统一FP字节除4。
3. A主路径P15，KV8/16独立。整数softmax实际闭包及受检PV32已核，但Q25 KV8原误差仍大；P7不作为任意长度默认。LUT8196/16388B与单口、head128宽scale、U64除法成本单列，不能从函数名推已有硬件。
4. 不以省header固化M+A。相同库存576调度/96配对的纯colocation零差；声明stream省header条件收益0.083%–0.167%，受保守pack/div/逐头读取主导假设限制，不是物理合宏测量。先校准布局/SFU，再与其他成员物理工程配对。
5. Q35 R保持单owner/连续history/完整投影后commit；当前真实状态只是浮点证据，整数合同/同资源归属未通过，暂不固定独立R。制造前总库存和端点仍需冻结；产品只可启用/绑定已有实例、定制允许金属/过孔，不能增加有源资源。

旧FP/BF16、原失败和不同服务边界保持原条件。Phi封存不调优，原版R1 MLA/MoE未覆盖。下一步只围绕后继scale、R整数化、布局/SFU与物理资格补证，不增加品牌矩阵或用CPU/GPU时间换目标周期/PPA。
