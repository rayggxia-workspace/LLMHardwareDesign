# V330中间时序与启动证据

Refs #121 / PR #122。2026-10-29 12:18:35 CST捕获9份原始文件，含真实330 manifest/queue/dispatch、原生阶段、CTS/GRT报告、carry证明读回及335状态。93135于10:37:30由335补位启动，当前native已完成synth/floorplan/place/CTS，route运行。独立最终资格仍待完成。

CTS WNS−0.79ns、GRT WNS−0.52ns；原报告未修改，路径源映射见path-source-mapping.json，输入网表服务器SHA见index.json。最差路径进入函数delta1，起点为function_sent[1]或input_mem读寄存器，不再是328的group分母路径。只读文件解析，没有新EDA运行、布局改写或最终资格转移。

原330继续正常收尾；新增函数入口寄存的修正尚待独立验证，不能用330报告代表新RTL结果。
