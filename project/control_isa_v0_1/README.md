# 两级控制 ISA 编码工具

对应[母控/局控方案](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)和[位编码规范](../../docs/local-blocks/CONTROL_ISA_V0_1.md)；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人Melodydt。

- `isa.json` 记录版本 1 的 24 种操作码和 9 类记录。
- `compact.py` 编解码版本 2 的 64 bit 指令、版本化镜像头和 16 B 对齐的指令段。
- `test_compact.py` 检查全部操作码的边界往返、BRANCH 指令字、非法字段和奇数条填充。
- `codec.py`：Python标准库指令编码/解码、程序所列PC检查和记录pack/unpack。
- `examples.json`：两个控制骨架及独立手工机器码向量；不是已完成原生数值程序。
- `test_codec.py`：独立预期机器字/小端字节/对象记录，非法编码、角色、保留位、范围及控制目标拒绝检查。

从仓库根运行：

```powershell
python -X utf8 -B -m unittest discover -s project/control_isa_v0_1 -p test_codec.py -v
python -X utf8 -B project/control_isa_v0_1/codec.py examples --output work/Melodydt/179/control-example-programs.json
python -X utf8 -B project/control_isa_v0_1/codec.py decode --role mother --word 0x10000200010000000000000000000000
python -X utf8 -B project/control_isa_v0_1/codec.py encode --role local --input local-program.json
python -X utf8 -B project/control_isa_v0_1/codec.py pack-record --record object --input object-record.json
```

最后两条需要调用者提供合法JSON；local-program.json为指令对象数组，object-record.json字段见规范，不是仓库中已经存在的运行输入。工具错误退出码2；未执行服务器、RTL或EDA。

本版本是proposed控制编码参考，不兼容宣称旧PR152/163二进制。pack-record检查字段/常量/保留字节；check_program检查角色/编码/所列分支范围，没有实现完整镜像装配/段检查、循环上界证明、原生ABI注册、数值lowering、对象/资源/令牌语义、执行解释器或RTL。编译器必须在后续阶段落实这些检查，不能只调用codec就报告大模型已经可执行。

指令word_hex是高位在左的32个十六进制字符（128位）；二进制内存为16B小端。所有保留位为0，未知/越界不截断。修改ISA时同时更新JSON、文档、独立向量和验证，不静默改变现有编码。
