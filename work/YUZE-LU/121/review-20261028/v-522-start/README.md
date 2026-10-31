# V522 新源原生六阶段启动

Refs #121 / PR #122。522/93639/node23实际RUNNING，源3333d155/归档d477eae4与520/521完全相同。7份启动原始/311份归档Git blob和远端SHA核验，见index.json。全新综合、floorplan、placement、CTS、route、finish，未从507继承物理checkpoint；实际520八项检查与521七测量、未改变的348组证明为真实前置。

这是一项独立16CPU任务，192GiB预测*1.2加16GiB保护与liveRSS，其他独立任务按6×16即完即补；后续523全部最终门/六文件/完整几何、524全部端口/有限RC须各自通过。不能据启动、映射或行为PASS宣称300MHz/DRC合格。
