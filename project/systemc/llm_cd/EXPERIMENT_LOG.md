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

## 同日继续：七模型实际重跑（执行记录）

9. 新增 `remote_suite.py` / `remote_suite.sbatch`，直接运行同一 C/D 可执行文件，沿用七份已冻结 checkpoint、九个输入位置及独立参考验证器。六个单线程模型任务动态补位；不是再次运行旧 TensorLink 二进制。
10. 首轮 job95067 因服务器缺少 libubsan.so 链接失败；第二轮 job95068 因 GCC8 对内联 std::optional 空返回的 maybe-uninitialized 诊断失败。原始失败日志保留于 `results/remote-failures/1`、`2`，均未启动真实模型。没有降低数值门或关闭 -Werror。
11. 服务器使用 Release、不启用不可用的 UBSan runtime；本地同源 phase07 仍启用 UBSan，通过 2/2。生成副本仅给 DmaPlanner::completion 添加 noinline，避免 GCC8 误诊；上游 control 工作树不修改，生成文件 SHA 随回执保存。
12. 第三轮 job95069（独立目录 `cd-full-20261102-03`）构建及 2/2 selftest 通过后启动七模型。该记录先保存执行事实，全部模型最终资格以之后归档的 suite-final、逐模型 execution/validation/numerical-gates 为准，不以运行中日志宣称通过。

范围仍为外层 Tensor 边界的实际 C/D/S 运输。静态权重、原始 KV/R 状态与计算任务发射仍由 host 路径承担；这些不能因七模型数值通过而自动转成硬件实现结论。此次 SystemC 模型覆盖 R，不修改 RTL 生产选择。

## 同日最终：C/D 新通路七模型全部通过

job95069 / node1 / 8CPU 自然 COMPLETED/0:0，19分13秒；六个独立单线程模型任务动态补位，Granite在Qwen3完成后立即开始。封存审计95083 / node1 / 2CPU，自然 COMPLETED/0:0，51秒。实际采样峰值RSS约45.9GiB，启动前MemAvailable约491GiB；未以单任务扩核代替模型并发，不改其他作业。

七模型使用同一新 `llm_cd_bench`，每种完整层数、完整词表、九位置。同prefix Top1 63/63及七条独立greedy序列一致，全部hidden/logits满足原冻结门；本地从原始validation重算再次通过，不拼接旧轮次。

| 模型 | Top1 | 最大logits rel-L2 | 最大hidden rel-L2 | C提交/完成 |
|---|---:|---:|---:|---:|

| Phi4-mini | 9/9 | 1.088324% | 2.446650% | 641898/641898 |

| Gemma3-4B文本 | 9/9 | 0.726607% | 1.179374% | 261684/261684 |

| Qwen3-0.6B | 9/9 | 0.952697% | 0.972752% | 376056/376056 |

| Qwen3.5-4B文本 | 9/9 | 0.895226% | 4.115569% | 343440/343440 |

| Falcon-H1-3B | 9/9 | 0.686298% | 1.181841% | 317496/317496 |

| Qwen2.5-3B | 9/9 | 0.733802% | 0.889142% | 493992/493992 |

| Granite3.3B | 9/9 | 0.059899% | 0.084723% | 685872/685872 |


累计1560219窗口、286760256个128bit服务字、20471748突发，C提交/完成3120438/3120438，每窗口恰好两项且窗口末信用归零；字数包含LOAD/STORE及padding，不能当作全模型外存流量。

新执行程序SHA256：`ed4dfb27a26ced566cb1349ab91de063153fa789ac3e3f64e8f62a2584a6c5c5`；执行源包SHA256：`492e30e23de27382d4c5cd1967a85a67f71dd1d5ee17c4ef881c75c86016c2ec`。封存包SHA256：`2111d6b08435fe414861538c526eb6812c8d76e014cb492e763a5cfa714711ce`。24份实际编译源逐项绑定，当前22份原始代码/runner逐字节匹配执行归档，无仅换行差异。后加审计/文档单独记录，不伪称进入执行包。

证据入口：`results/seven-cd-03/index.json`、`suite-final.json`、逐模型`execution.json`/`validation.json`/`numerical-gates.json`、`sealed-index.json`、`source-audit.json`。全部原始大输出和源包仍保留授权服务器路径，输入/输出字节数与SHA可核对。当前本地UBSan证据见`results/local-phase07`；服务器Release无UBSan。

复核命令：`python project/systemc/llm_cd/verify_evidence.py project/systemc/llm_cd/results/seven-cd-03`；取回同SHA源包后执行 `verify_source.py SOURCE_TAR project/systemc/llm_cd/results/seven-cd-03`。

结论仅为本轮Tensor边界C/D/S载荷接入及七模型短序列数值通过。权重、原始KV/R状态、计算宏发射、双S/AXI错误排空/复位和真实系统性能未验收；不以本轮替代PR163的RTL/物理合同。R按用户授权参与本SystemC推理，RTL生产发射不改。继续同一PR154，提交独立审查，不自合并。
