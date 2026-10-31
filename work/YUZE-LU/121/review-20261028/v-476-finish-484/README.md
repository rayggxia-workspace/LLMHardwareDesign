# V476原生最终报告：拒收

Refs #121 / PR122。2026-10-30 11:24 CST采集24份原始文件。源528c08c824eb08aad003e8eeb74641459bbaea9e、归档014cf47ff1c3fa8930af8fe09dadc7ec64ff03465b6c5867cab38a60d91b7ff5，311 Git blob与远端逐SHA、receipt全部输入及捕获输出核验。完整六阶段自然完成，内部最终LEC53478输入/53467输出，diff0/1均0、UNSAT/IDENTICAL。

实际最终setup WS−0.0682414ns/TNS−0.959171ns、35违例，hold WS+0.0154107ns/0违例，maxcap2、maxslew0。因此流程成功不等于物理接收。外框1260×1260µm，标准单元面积717740µm²；包含全部缓冲与新增资源。原生路由DRC和后继完整DRC分别保存，不以一种代替另一种。

最差setup首路径norm_product[1]→group_unit.denominator[127]，原输入网表精确cell映射见path-source-mapping.json。maxcap两个实际驱动为wire186429/Z（255.61fF对242.31fF）及$abc$1371512$auto$blifparse.cc:397:parse_blif$1415840/ZN（110.54fF对106.81fF），未放宽Liberty限值。477独立最终源/物理/DRC/功能/严格LEC仍正常执行；不转移旧464或476任何资格到修复源。
