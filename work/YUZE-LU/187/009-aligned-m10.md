# 009 · 对齐 M10 与发现 J 电源通道限制

- `009-aligned-m10/source.sha256` 摘要 `d05efe942e33f9081138c2af8f262c7a23a758ca5eb4d4719aecc130b331e365`，采用 008 RTL。作业 97478，c96 node15 两个 12 核步骤。
- 由 4 µm 后制网格与 1.6 µm 原生 M10 节距计算交集，使用 8 µm 网格并对齐宏位移。J 的 S→T 水平间隙缩到 8 µm，PDN-0179 报无法修复 M7 通道。J `do-floorplan.log` 摘要 `61090921a6a1cac6a4c77add8ec5e324a40e475c6eb022cb975adece2985657e`。
- P 到 CTS；最差 `store→io_rsp_data[30]` −2.39 ns，路径到达 4.82 ns，其中 store 时钟 1.14 ns，叶 clock-to-output 1.16 ns，余下为父层长线和重缓冲。P CTS 日志摘要 `779a6b0fe5612b093e76bccd4df0b063b9974a267e8233e10f3bfa9f57934721`。该工作步继续尝试接入，未验收。