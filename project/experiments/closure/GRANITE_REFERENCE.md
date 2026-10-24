# Granite 路由参考闭环（Issue72）

在查看新模型结果前冻结。原Issue70 eval chunk16 FAIL、原2e-4相对L2与2e-3最大绝对双门、原校准和评价各72token保留。不挑样本、不放宽门、无fixed-ID替代算法。

每个精度独立新输出目录，完整32层，calibration/evaluation各跑full72、cached64+8逐token、chunk16（连续KV）。三种精度为：native32原始算子；router64仅实际当前hidden上的router linear/softmax FP64；model64参数/主矩阵FP64且router FP64。两种新参考实际重选top8，只有分数完全相等时专家索引升序，不给近似相等容差。native保留框架torch.topk。参考通过仅说明这两文本的同精度分块自洽，不覆盖应用质量、W8A8、整数链或硬件。

模型FP64仍保留安装框架RMSNorm统计/rsqrt FP32、RoPE相位cos/sin FP32、attention softmax FP32的显式cast，不能称全算子FP64真值。逐profile记录router实际input/weight/logit/softmax输出dtype、全部40logits、完整top8及top8/9 margin、exact ties、逐层hidden/MoE误差、最终logits。完整真实router输入和32组权重供后续整数router分析，不导出其他完整模型权重。

命令（仅由root在服务器Slurm执行）：

~~~sh
python project/experiments/closure/granite_reference.py --model PINNED_WEIGHTS --capture ISSUE70_FAIL_CAPTURE --binding PHASE_BINDING.json --out NEW_OUTPUT --threads 8 --precision native32
~~~

router64/model64分别替换precision并使用独立目录与job。binding必须含commit和granite_reference_sha256，模型固定revision a02780686e08a03fe0d2679a293b5c74a90efa89，校验原capture及每个模型文件SHA/大小和框架sourceSHA。不存在的out才可创建，异常写入manifest；原FAIL留在来源链。

验收分叉：native32失败重现而router64通过，支持高精router是短参考候选；router64仍失败而model64通过，说明上游扰动也需考虑；三者都失败则不能把提高router精度当解决。分层route差异及margin用于解释，误差门对每种精度保持原定义。任何通过都不能反向改写native32 FAIL。

后续W8A8/W16A16/选择性宽router严格使用独立cal冻结scale；只在真实冻结router输入上测算术误差与路由变化，不能将固定hidden诊断冒称全模型量化。S16乘法需要base128三digit×三digit共9个S8产品，以及完整K部分和/重组宽累加，额外算术/状态/metadata/端口都入账。


## 首轮真实失败与显式backend修复

服务器首轮native32原chunk16失败重现；router64使chunk16过原门但cached64失败，不能认为提高router精度已经解决。model64在安装framework grouped_mm拒绝Double处报错，未产生数值验收。保留该失败和原输出，新source/新目录增加显式eager expert实现：与已记录安装source的Python body保持expert排序、同F.linear→SiLU→down→gate→index_add语义，FP64不降格，不改环境/framework。

model64使用此eager backend，同时增加native32_eager独立variant，原native32 router完全不变，运行同六profile。native32_eager每层首次calibration.full对同一当前hidden/routes/gates额外调用原dispatcher，保存完整native/eager输出及误差见证，原同math门relativeL2≤2e-5且maxabs≤2e-3。此控制检查backend数学，不能让model64单独代表仅精度变化；全模型分块误差照旧单列。新增两个小Torch合成测试核验double不降格和near/exact tie差别；未在本机加载真实权重。
