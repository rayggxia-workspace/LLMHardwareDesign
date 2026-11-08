# 标量 NExp 的原生合同

`NExp(x)`的整数参考是 N 的 `exp(x-max(x,0))`，输入取低 S16（Q5.10），输出为 U16（Q1.15）零扩展到低 S32。
旧模板只有 `Stats(x)`，最大值变成 x；例如 x=-32768 时旧原生命令输出32768，正确输出0。
完整向量整数回放一直使用正确的独立参考，因此“向量回放逐位通过”不能替旧原生模板证明语义。

现行循环逐元素执行：

```text
Begin(mode=Softmax)
Stats(count=1, source=input.low_s16)
Stats(count=1, source=native_constant:0.low_s16)
Finalize()
Exp(count=1, source=input.low_s16)
```

标量记录只保证低S32；负S16可以符号扩展，第二个S16未必是0。因此不直接把count改成2，
也不假设存在免费拼包。零包已经在显式外存常量区，新增一次真实LOAD、S读和Stats命令。
每输出的增量模型成本为 `measured Stats(count=1) + io_read_ticks + descriptor_ticks(load, io_write_ticks)`；
新增一条128位读记录，写回不变，所有基线共同承担。N上下文保持到Exp响应后，再允许Begin替换。

`verify_primitive_cost.py`独立检查命令、输入来源、零常量、循环顺序与覆盖；旧IR显式拒绝。
`recompile_ir.py`从保存的向量程序重新生成服务、地址和候选，并重新审计；不修改旧计划中的ticks冒充重编译。
原列分片上限及静态/动态候选族保留，支持历史两种上限字段名，缺失/矛盾则失败。

`nexp_probe.py`读取真实编译模板产生命令；`nexp_probe.cpp`驱动不变N RTL，与独立NEngine的[x,0]双元素参考对照。
N输入记录的高位故意非零，响应加入背压；三个初态各653例（329负输入）全部通过，输出高位为0。
删除零Stats的历史模板必须失败，不能通过重用正确参考隐藏错误。

这是N叶宏及该命令配方的证据，不是完整MC/LC/DMA、物理、系统时序或能耗资格。
原件见[迭代8](../../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_8.md)。
