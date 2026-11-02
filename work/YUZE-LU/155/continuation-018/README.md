## 2026-11-02 Issue155：默认轨道下整块接入通过，继续详细布线

真实几何定位及修复源f59fa7d0，M3验证用例d3b75967。95146导出同一实际GDS的1152个M3遮挡矩形；几何及原生读回均通过，全部PIN、其余层及宏尺寸字节保留。267个信号原始落点的同层连通金属彼此独立，纳入覆盖证明；旧抽象遗漏和过度遮挡均有数量证据。原银行GDS/SPICE/Lib没有改动。

95144在真实CTS设计上用原生默认轨道通过pin_access，macroNoAp=0；五个独立候选在8CPU内4×2动态补位均通过，最终选择默认轨道。95142为漏加载TAPCELL的诊断装载失败，修正为真实macro.mod.lef后才得95144，不跳过缺失元件。此前95137仅改轨道四候选均失败，说明几何修复是实际必要因素。

95147完整视图汇合通过，95148/physical-019实际完成全局布线并进入详细布线优化。95150/final-017和95151/formal-015等待完整产物，最终门尚未全过。源f59fa7d0，归档SHA及实际路径见chain.json。七个已核验本人/本任务目录、PENDING且有明确失败前置的死链已退役，保留原始数据和审计；无运行任务或其他任务被动。

真实M3/M4两套夹具各七项破坏控制通过，结构检查通过。任务继续直到整块六文件/版图及300MHz、RCX、DRC、PG、电气、功能和形式全部最终验收。原标准单元S不变，不自行合并；Issue155 in_progress、PR158 Draft，银行内部wire PEX及HL复制LH限制仍保留。

证据：[continuation-018](../../work/YUZE-LU/155/continuation-018/README.md)。


本包为继续执行中的中间证据，不是最终六文件交付。完整任务根：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155`。原始生产m3-abstraction-003/submission.json绑定每一份实际执行脚本SHA，几何证明绑定实际银行GDS及输入LEF，native-m3.tsv逐坐标匹配。pin-tracks-003保留五个候选脚本、原始日志及SHA；同一CTS源ODB输入执行后SHA未变。physical018失败与旧轨道诊断也保留，未用新通过覆盖旧失败。
