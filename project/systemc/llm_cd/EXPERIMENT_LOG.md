# C/D接入持续记录

## 2026-11-02：建立平行实验

1. 只读核对PR154与PR146的control源：此前七模型推理没有调用C/D。D只有地址/信用合同，没有载荷。
2. 新增 `payload.hpp`：C程序发出真实LOAD/STORE，D burst经原16KiB S读写、响应后回收信用；32KiB有限外存窗；Tensor分窗、完整字节一致性。
3. 新增 `run.py`：在新目录构建原llm的并行副本，原数值算术/序列化保留，仅替换副本Tensor桥的运输入口；输入SHA随实际执行记录。
4. 新增 `payload_test.cpp`：三个SystemC线程争用同一C/D/S，测试1/15/16/17/257/16384/32771字节，预期27个有限窗口。
5. 首次Ubuntu22.04入口缺少cmake，在启动构建前失败；切换到已有SystemC/GCC10.3/CMake的Ubuntu18.04，保留失败说明，不安装或修改其他环境。

本轮结果以同目录 `results/` 的实际日志/receipt为准。完整真实七模型九位置未执行；权重、原始R/KV状态及计算任务控制尚未硬件化。下一阶段优先宏适配器、真实权重/状态运输和原数值门重跑。

6. 增加持续落盘：WSL退出后/tmp构建目录不可依赖，新增--save-evidence在退出前保存原始日志/回执/control源快照。Ubuntu18.04 Python3.6不支持subprocess text=True，改用universal_newlines后重跑。
7. phase04通过2/2测试后增加实际C提交/完成审计，phase05确认模型selftest不是空接入。最终phase06使用当前runner：2/2通过、C完成计数一致且非零，最终回执/原字节SHA见results/phase1。
8. 最终载荷测试：27窗口、18570字、1194突发、54任务完整完成；模型selftest：479窗口、42632字、3504突发、958任务完整完成。M尾部/尺度/长Softmax/RMS/SiLU/S/T/词表argmax原selftest通过。七真实模型九位置尚未执行，未把其旧通过记录转授新通路。
