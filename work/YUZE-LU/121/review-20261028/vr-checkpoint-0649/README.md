# V/R 完成检查点的只读长路径诊断

302/93054在node17两个16CPU任务同时启动，实际自然COMPLETED/0:0。UTC22:48:27.614061捕获19原始小文件、14输出SHA匹配回执；源ca5914adfa217cbc6ad0f87cd2d0fca69fff3936，归档4244bb14c3e88fcd56ad461b28cec1409ece87cd6d0699ebd0a78d7930f4fba5。全部原始ODB/SDC/RTL/config/原生setRC/Lib字节前后不变。

| 源检查点 | 实际最差setup/hold(ns) | setup/hold违规 | 最差setup映射 |
| --- | --- | --- | --- |
| V291 3_5_place_dp，理想时钟 | −2.256069422/−0.005594442 | 9367/3 | scalar_c[2]→output_mem[6][20] |
| R236 4_cts，传播时钟 | −1.139706612/−0.191516921 | 12558/24 | row[4]→product[4][63] |

这是原生setRC的placement估计；既非最终抽取RC，也非最终验收。报告passed仅表示只读诊断完整执行，没有把负裕量写成通过；中间SDC原生序列化周期3.3333ns也非最终exact10/3ns门。原291/236继续，未改其任何源码/布局/约束或停止作业。cell到RTL信号的定位来自receipt绑定input.v，并在path-source-mapping.json保存确切实例片段和SHA。

V point_b修订后仍有scalar_c→FMA加法→舍入/饱和长组合链，因此拟对128bit加/减及RNE进位做字节分组重构。保持全部128结果位、原舍入/饱和、寄存器、命令与周期；先全比特SAT/真实单bit错误负例，再新源完整数值/映射/端口测量。未执行新源测试、未声称新源时序已修好，最终需要fresh P&R和同源所有门。R先保留当前源，待最终物理和实际路径决定是否还需操作数预取级，不能用诊断替代验收。
