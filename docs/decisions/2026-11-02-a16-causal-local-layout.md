# A16使用真实因果前缀与岛内K/V布局转换

状态：所选H8/Sq2/head1整数profile的服务器RTL验证通过，外部审查/真实样本/物理未接收。Issue151 / PR152；Melodydt；2026-11-02 Asia/Shanghai。输入f665230a，实际源a32e5f1a61d137e9e2338b7717b66d5c18085351。

旧A8从Q/K/V操作数开始，缺hidden入口的preNorm、QKV、RoPE、Wo和原始残差。因此新增A16固定局部流程，组合M/N/E/S/T各一，不修改旧A8/F16/native。两个token可验证真实因果性；单token会使Softmax退化，无法检查未来信息隔离。

所有hidden中间值及原残差采用所选S16Fin10；权重S8Fin7，RoPE系数为输入的adjacent-pair S16Fin14。M单context按完整保存两行后再clear的次序复用；N用count1与2计算前缀Softmax；E执行旋转和残差。K列与V转置通过新local holding/selector及真实S读写ACK生成，必须预制这些有源逻辑，M11/M12不能补算术、状态机或转置器。

预留S448..529包络1312B及T32B，保持X/参数/各阶段生存期；不将孔洞视为可免费并发使用，也未缩减S16KiB/T6KiB原宏面积。输入仍为含权重/系数的27拍固定帧，没有独立权重驻留/MEM接口，芯片母控和跨岛storedACK待L5。

job95235/node1/c64/8CPU/Verilator5.042、30CASE实际通过，未来token变化反例和零gamma原残差均核验。36条警告保留，非lintclean。pair-interleaved与真实模型split-half、GQA/QKnorm、位置/cache、epsilon/量化质量、H/head规模与供参仍为准入门；不得以缩小模型宣称完整样本通过。当前仍L4，详见[实现报告](../W4_A16_IMPLEMENTATION.md)。
