# 局控RTL边界与状态机候选 v0.1

[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)第6步；正式[研究合同](../../docs/local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)。这是可审查的RTL接口候选，尚无功能控制器DUT。

- contract.json：92个逻辑信号、9个生命周期／13个顺序机状态、配置操作码、转移guard、容量和资源账；不是原生宏pin或物理/MMIO冻结。
- lc_boundary_v0_1.sv／lc_contract_v0_1_pkg.sv：[生成器](generate.py)产生interface/modport／常量声明，没有控制逻辑。
- [PORTS.md](PORTS.md)：方向／位宽／用途，均相对局控；程序存储8320B，payload寄存器下界688B，其他成本另计。
- check_cycles.py：只读取边沿观察，检查合同；不会生成DUT输出或执行完整控制器。
- examples.py／timing_examples.json：4份人工期望时序及1份16flit示例，明确非RTL执行。
- test_boundary.py：36组边界／拒绝检查，与既有137组合计173组。

在仓库根，仅Python标准库及既有image/codec等：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B project/control_rtl_contract_v0_1/generate.py --check
python -X utf8 -B project/control_rtl_contract_v0_1/examples.py --check
python -X utf8 -B -m unittest discover -s project/control_rtl_contract_v0_1 -p test_boundary.py -v
```

修改合同后可先无--check重新生成，再审查差异；不要修改期望时序来掩盖DUT失败。既有六套单测和两个执行campaign仍须回归，见[ARCHITECTURE](../../docs/ARCHITECTURE.md)。

采样为边沿前值，握手效果在下一采样可见。PM和服务均只1在途，禁止同拍响应/refill；WAIT不能在完成响应同拍消费。局控内部512bit整包与外部32bit/16flit串行链路分开，整包接收不能按第一flit计。

监测器正向向量只覆盖部分成功／取消边界；完整状态语义、错误响应、对象和真实provider复位仍待实现与DUT验证。无tag原生响应不能靠内部tag或软件epoch识别所有迟到情况。

本轮PATH未发现iverilog／verilator／yosys，HDL编译／lint／仿真未执行；SystemVerilog声明只作静态重建核对，不能声称编译通过或控制器已实现。未启动服务器／物理作业或自动监测。

