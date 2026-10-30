# S完整验收拒绝记录

原92920作业实际FAILED/1:0，队列S DRC=FAILED、delivery/geometry=BLOCKED。原生全片DRC有一项Metal Spacing，net words[674][3]，bbox(181.1300,903.3850)-(181.2300,903.4150)µm，metal2。完整未修改FreePDK45 GDS deck为0；两者分别都必须通过，不用GDS0豁免原生违例。S其他三门通过不覆盖此失败，S仍未最终接收。

6份捕获长度/SHA保持，3条输出绑定实际核对，原始full-deck.lyrdb保留。来源为258封存最终S；大GDS466218154B/e7969fee…仍在授权服务器。完整来源与工具版本、输入、失败原文、GDS及deck SHA见receipt/five-macro-drc.json。

276/92977使用独立不可变源68ce1d6，对246原生5_2_route、5_3_fillcell、6_final三个封存ODB各用16CPU并行只读全片native DRC与目标网络wire/via/pin导出。目的为定位引入阶段，之后再选最小合法修复；不会回写旧数据库或复用旧源资格。修复后的S还需重新finalize、物理/完整DRC/最终网表三初态/严格LEC、交付与几何。当前诊断完成不等于DRC通过。
