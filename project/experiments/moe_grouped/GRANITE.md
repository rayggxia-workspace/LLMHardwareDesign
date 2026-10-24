# Issue74 Granite完整MoE整数链最小合同

仅服务器Slurm真实计算，不新增下载，不改变原Issue70 native32失败。层0是完整专家来源/结构基线，层13覆盖原最早路由敏感位置，不从模型名推测结构。固定官方revision a02780686e08a03fe0d2679a293b5c74a90efa89、原cal/eval各72token，评价分prefill64/decode8。矩阵主合同W8A8/INT32，宽router候选单列额外资源。

## 真实切口采集

granite_capture.py复用Issue72已过原双门的model64条件参考和对应冻结源码。重新跑相同full72，不再重复全部cached/chunk；只两层保存完整专家和真实前后norm。所有32层仍按原model64 router/eager执行；norm/RoPE/attention内部FP32 cast保持，不能称全FP64 oracle。新最终LM与两层norm/router/MoE/hidden逐项原2e-4/2e-3门，ID完全相同才接受，原native FAIL永不翻案。

已核安装模型真实顺序：layer.inputnorm→Attention→residual+A×0.22→post_attention_norm→MoE→同残差+MoE×0.22→下一层inputnorm。capture使用post-attn norm的真实inputs[0]取得残差，不由差分重建；nextnorm直接hook下一层inputnorm，输入就是当前layer_output。post_gamma属于层0/13 post-attn norm，next_gamma属于层1/14 inputnorm。0.22来自实际config residual_multiplier，两个残差分支位置保留；本链外部cut已经包含Attention残差分支，不在链中再乘Attention。

capture.npz：weight.L{0|13}.{router,gate_up,down,post_gamma,next_gamma}；前三完整[40,1536]/[40,1024,1536]/[40,1536,512]。静态参数原BF16精确值导出FP32；真实新版loader对旧input_linear/output_linear/router.layer键的转换、实际shard/header shape/dtype/SHA均记录，不能假设shard本来用新键。每case.L{L}.{residual,norm,moe,layer_output,next_norm}[72,1536]，router_logits[72,40]，ids/gate[72,8]；expert_gate/up/silu/mid[72,8,512]及expert_down[72,8,1536]是显式eager实际forward中间值，覆盖参考真实全部所选专家。runtime可能选不同专家，故静态40专家完整保留。{case}.tokens[72]。

~~~sh
python -B project/experiments/moe_grouped/granite_capture.py --model PINNED_WEIGHTS --reference ISSUE72_ACCEPTED_MODEL64 --reference-producer FROZEN_GRANITE_REFERENCE.py --binding BINDING.json --out NEW --threads 8
~~~

binding含commit与granite_capture_sha256，参考source SHA必须匹配其manifest；原模型所有文件逐一核大小/SHA，框架implementation同源。原权重只读，不在本机运行模型。

## 下一phase冻结数值合同

两层×R8/R16 router×cal/eval共8任务。以真实残差I32Q12编码切入，完整postnorm(U128平方和/整数sqrt/div/RNE)→真实integer top8/Q15 gate→所选全部8专家gate/up完整K1536 W8A8→SiLU整数LUT/乘门→当前mid整512维动态A8→down完整K512 W8A8→每expert RQ共同I32Q12→Q15 gate×8完整I64加和→一次RNE15→0.22 Q20 RNE20→残差相加→下一完整H1536 norm。Attention/其他层保持外部切口，非整模型整数化。

R8/R16当前norm码用最小RNE右移变为对称A8/A16，router W8/W16 perout power2单位，真实40logits排序。R16全行实际signed-magnitude base128三digit×三digit共9份S8 dot+宽合并，不免费INT16；共同logit单位、shift/overflow及gate LUT/divider均明确。专家静态perout W8 scale编译Q31/I16，norm码同源同时用于router和专家，不拼不同参考输入。

SiLU复用[-32,32]、step2^-8、I32Q12，负域外0/正域外identity，域外计数保留。所有在线scale只看当前整数row，不用评价误差/未来native。编译float静态参数/LUT与runtime整数隔离；诊断float只运行完成后观察。唯一merge舍入顺序先各down RQ Q12后Q15宽merge，不把lateRQ当等价placement。

要记录native/同当前integer输入FP64两类route差异，分开输入norm误差与router量化。归一化完整分母/平方和、所有dot/RQ、gate/mid/down码与delta、8路prefix merge都需可独立逐位重算，改SHA后的负例必须拒绝。应用质量没有预定整体误差预算，局部数字不宣布quality PASS。

容量提示：单层expert W8=94,371,840B；两层不能免费同驻EXT128MiB。当前mid512维动态scale须2KiB I32缓存或重读。8路S32输出49,152B、S64整merge12,288B+一份output6,144B超过V16KiB，必须tile/stream并计端口，数字闭合不代表物理划分定稿。


## 编译与运行命令（来源绑定）

~~~sh
python -B project/experiments/moe_grouped/granite_chain.py compile --capture CAPTURE74 --binding PHASE.json --out NEW_COMPILED
python -B project/experiments/moe_grouped/granite_chain.py run --compiled COMPILED --layer 0 --router-bits 8 --split evaluation --binding PHASE.json --out NEW_RUNTIME
~~~

binding含commit和granite_chain_sha256。layer0/13、router-bits8/16、split calibration/evaluation共8条件。完整compile只从静态原参数产生scale/LUT；cal/eval residual都仅按预先固定I32Q12编码。静态参数Q20、epsQ24，routerW perout power2，expertW perexpert/perout maxabs/127→Q31/I16；无bias专家不能凭空加bias。

runtime.npz保留全72row实际norm平方和/variance高低U64 limb及denom；router输入codes/delta、全40dot、R16全部9份真实S8 partial、共同logits/exp、top8/Q15/LUT index；同一norm的expert A8/delta；完整gate/up/down dot32和Q31 product64、所有中间Q12、mid A8/delta、8路merge products/prefix64、最终MoE/scaled/residual/nextnorm。所有数组为整数；所有float参考文件在完整runtime文件写完后才打开。

两种route差异分别对原model64 native IDs及“同当前integer norm解码输入的FP64 router”计算，后者纯事后诊断。下游中间误差只对同token相同expert ID的native路径匹配，禁止不同expert按rank硬对比。全MoE/join/nextnorm向量误差直接报告，并分prefill64/decode8，不设置事后质量门。

格式宽度实际检查：gate为U16 Q15，可等于32768，不误认signed16；operand逐个检查32/16位域后再宽乘。router exponent先I64计算/界检再castI16，避免wrap。R16 signed-magnitude3digit全行lower9次，S8partial全K INT32、重组S64；log2e乘积受signedI128候选guard并记录实际幅度，不免费64×32。norm signedI128分子、U128平方和/radicand及所有I64/I32输出守卫明确。失败不clip掩盖，不退回float。
