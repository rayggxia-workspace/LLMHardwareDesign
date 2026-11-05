# 007 · 唯一 LEF 名称与首轮到 CTS

- 源清单摘要 `868f6333d30534c87f8980c31836ef9618f7da46af0e2621ad475f7920b0d58b`。同一批 005 视图和 004 RTL。作业 97476，node17 上 P/J 两个 12 核步骤。目录 `007-unique-lefs/pnr`。
- 唯一 LEF 文件名修复 OpenDB 导入，两块均完成综合、floorplan、放置和 CTS。P 的 CTS 报告最差外部响应路径 `store→io_rsp_data[22]` 为 −2.11 ns。J 的最差 `reset→out_valid` 为 −0.57 ns。均是布局估算，用于确定流水和端口接入改动。
- 两块在 GRT 前引脚接入停留多分钟。截至记录时作业仍在运行。该物理实验作为基线保留，未达到验收。