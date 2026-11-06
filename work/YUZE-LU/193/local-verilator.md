# 本地 Verilator 5.006 回归回执

2026-11-06 Asia/Shanghai。工具兼容处理和远程验收范围见 [执行记录](README.md)。

| 运行 | SHA-256 | 实测 |
| --- | --- | --- |
| -1 normal | 80454134100362c4798a6bac520f248d1f0857f62adca2e1c272862fa6bd58c0 | PASS native kind=-1 stall=0 fault=0 transfers=2 |
| -1 stalled | 23c336fcbde6d2cc2287744b167c08c81ba43bb52de553fea86a1d3a1ca68be0 | PASS native kind=-1 stall=1 fault=0 transfers=2 |
| -1 fault | b3296fcd148b9133022ab13e731327a60a60a7c4cc7921d1bf998b54c508a54f | PASS native kind=-1 stall=0 fault=1 transfers=2 |
| -1 stalled-fault | f9604daf418c9877f7921438e8ce9cca07e8a255eeb87e9a53a1decb6995aee7 | PASS native kind=-1 stall=1 fault=1 transfers=2 |
| -1 reset | d7849831eaaf9b44896296598b20444586287666816e15aff26e599942e93fe4 | PASS native kind=-1 stall=1 fault=0 transfers=2 |
| 1 normal | 639126079204cca03a14cc9ca8a61aabf3522a24cc81bfae267e54bc15fd1f07 | PASS native kind=1 stall=0 fault=0 transfers=0 |
| 3 normal | 013b1a34b7f06645b90292d1d5b68991af0efc39f56fb46cf73294a30c6983f1 | PASS native kind=3 stall=0 fault=0 transfers=0 |
| 4 normal | 862867ed822fc77a861de9bbbc09444e8b2bed7f69f20662569790fe4755d0a4 | PASS native kind=4 stall=0 fault=0 transfers=0 |
