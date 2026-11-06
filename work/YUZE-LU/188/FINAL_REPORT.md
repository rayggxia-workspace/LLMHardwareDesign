# U16 / C16 / F16 独立物理验收

**三块均通过。** 各使用 16 KiB 私有 S（四颗真实 OpenRAM 银行），在 Nangate45 M1–M10、TT 1.1 V、25 °C、300 MHz 下完成独立布局布线和验收。

| Block | 结构 | 尺寸 (µm) | setup 裕量 (ps) | hold 裕量 (ps) | 最小电容裕量 (fF) | 信号端点 | 完整 GDS DRC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| U16 | N / E / N4 | 1300 × 1300 | +11.384 | +7.154 | +0.184690 | 768 | 0 |
| C16 | R256 / G / E / N5 | 1500 × 1500 | +30.087 | +9.640 | +0.046325 | 1009 | 0 |
| F16 | G / E / N4 | 1600 × 1600 | +189.797 | +3.896 | +0.269295 | 768 | 0 |

## 验收证据

- 每块用各自最终 ODB 核对信号与供电连通、M10 父层接点和可读 LEF；用原约束及提取寄生独立复验 setup、hold、电容、转换时间、扇出以及四银行时钟周期和脉宽。
- 原生 DRC 与完整 GDS DRC 均通过。完整检查在各自直接流出的 GDS 上运行，不使用规则删减、标记过滤或改写后的 GDS。DEF、ODB、GDS 实例位置和方向逐项核对，四银行及标准单元掩膜一致。
- 将原映射与最终 ODB 功能网表按四银行的引脚切开逐脚作严格等价；证明无差异（UNSAT），故意翻转银行地址的负控被拒绝。
- RTL 回归 97555 通过。最终 ODB 回归 97702 三种初态（模式/种子：1/121、2/121、2/122）均通过：三块真实 SRAM 计算与写回、C→U→C 保留源直到确认、C 中断后重启。跨块握手在仿真中检查。
- C16 收敛涉及银行时钟支路、具体 hold 端点及实测超限负载的修复，迭代理由、修改和作业号见[记录](README.md)。原 300 MHz SDC 和电气上限用于最终判定。

| Block | 产出目录 | 独立审计目录 |
| --- | --- | --- |
| U16 | pnr-09/run-97523-0-1300-cap60 | audit-13/audit-97607-run-97523-0-1300-cap60 |
| C16 | pnr-21/run-97675-c-skew2-post2 | audit-13/audit-97700-run-97675-c-skew2-post2 |
| F16 | pnr-13/run-97569-1-1600-hold-target2 | audit-13/audit-97607-run-97569-1-1600-hold-target2 |

完整 GDS 规则文件 SHA-256：4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147。KLayout 0.30.9 官方安装包 SHA-256：a5d08a8adfdcf6255001e0ee671671bc0b7807fd9dff01cba3cff10cb479cae2。KLayout 0.30.12 诊断重现了 WELL.4 的版本差异；验收锁定 0.30.9 与完整原版规则，未确定上游差异根因。

| Block | 原生 GDS SHA-256 | 完整 DRC 报告 SHA-256 |
| --- | --- | --- |
| U16 | 72ba69686b2600a6d2d5c0a0504a5072c11bc5e499b42d95362c8806fcab4f68 | b4fd7ee6a3fdecf18db7fa7b99773e04a877da1bd3c9e128e2960ef2ab28f9d0 |
| C16 | a2e51bbaa6b040c5b118e6df9b522ca11cf509de045ac757e7418b03002cfa6c | 9d22c3bc54dfbf90a817f87b70bf8f9ff61d605f81f02fee9af3bf0dc113a0be |
| F16 | 607fa944f35f9d3110bb04fbb1cd4aadfa23a366b6aeb96863951b54dc524316 | bd76c939e1fc50d5bda81d4120e2a35a075ec862ae558387c305c2de08cc0ced |

## 交付及范围

封存作业 97704；远程目录：/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-188-ucf16/accepted-ucf16-01。本地收件目录：C:/Users/wine10/AppData/Local/Codex/deliveries/LLMHardwareDesign-188。从本地压缩包逐成员读回 SHA-256，与根清单、独立回执和执行源清单全部一致。

| 文件 | SHA-256 |
| --- | --- |
| U16.tar.gz | e69bc80d2975f6202f4d16df9fc028e371992566a66a4060d525273d7b0f2c6d |
| C16.tar.gz | 38e330dca611305e93c06f85da0261541f4185bcba569bba77928134c20c7989 |
| F16.tar.gz | f94e7a0525eefb3dfc31f18a3412c249423fcf7b86c29c5c6f3939188b75270e |
| execution-source.tar.gz | a792f672db18018fa0e2c5cbdaf83571c6a37ba16b2e6ba50d895ebb1bf6b927 |
| delivery.json | 9cdf428ae8c08ebf6b818895fc267cdb5671dec9f177fc39d29f34c5682e0f57 |

每块包包括最终 V/SDC/DEF/ODB/SPEF/GDS、LEF、最终 ODB 功能网表、原 Liberty/规则、独立验收回执和报告。时序视图由最终网表、提取 SPEF、SDC 及引用的标准单元/SRAM Liberty 构成。执行源另含输入、RTL、脚本、银行流和所需检查点；三初态回归日志见 gate/。

此验收限于独立 Block 及约定的银行表征边界；九实例共同底座、M11/M12、父层级 Liberty 和多角时序未在本次验收。
