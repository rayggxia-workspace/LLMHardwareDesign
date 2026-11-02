# F1024 独立全尺寸整数参考与流式 provider

本包对应 Issue151/PR152 的 L4，父版本 `75d99a5ba01adba1e978db3933a41e1d43c49c30`，native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。H1024、I3072、单 token 的完整 RMS→gate/up→SiLU×up→down→原残差整数计算。参考和 TB 已生成；本代理仅执行 Python 数学/静态检查，不启动任何 RTL 仿真。

X/gamma/Norm/mid/输出均 S16 Fin10，权重 S8 Fin7。RMS 使用完整1024元素统一统计、epsilon code1：`rad=floor((sum(x²)<<16)/1024)+65536`，floor sqrt，`factor=floor(2^38/root)`，每元素 signed RNE30/clipS16。gate、up、down 每个输出在完整 K1024/K3072 归约完成后统一 RNE7/clipS16；中途 K32 chunk 不量化、不清除累加结果。G 使用已交付独立数学表重建的 SiLU×up、RNE10/clipS16；最后直接与原 X 相加/clipS16。

## 全尺寸 fixtures 和权重数据

两组完整 fixtures 为 dense（seed37，gamma 非恒定）和 gamma0（seed91，输出精确等于完整原始1024S16残差）。权重公式为 `((13*n+7*k+seed+41*matrix)%251)-125`，matrix gate0/up1/down2。它是 dense 配方，每251个值有一个零，不是稀疏 shortcut。

参考利用 n/k 周期251作整数代数合并。每 fixture 的 gate/up/down 各8个输出另外使用不合并的完整 K 点积独立检查，共48项；确认没有把逐 chunk 量化混为全 K 量化。这个参考加速不改变 RTL 工作量。

provider 严格按 group0..383 的 gate32chunk/up32chunk，然后 down group0..127×96chunk 请求顺序供给。每个请求16拍、每拍16B，tile-major/n-major/k-minor，完整36864请求、589824拍、9437184B（9MiB）。没有把9MiB literal 权重放入 Git。

| fixture | canonical 9MiB stream SHA-256 |
| --- | --- |
| dense | `517ac145591b956ac3244eb6b544a003ea08b3d8b6bda2972d5c48f1cc3b4bb9` |
| gamma0 | `9468c51a67818d1ef20f1f095cc391a1e6f60f49006cd29d1afc93ca8ba6cbfc` |

`build_f1024_vectors.py --weight-directory DIR` 可在获准的服务器任务目录生成 canonical 二进制镜像；默认只流式 hash，不把大数据写入仓库。TB 使用 `+out_dir=DIR`，仅在两组完整正常 fixture 的正确 job/seq/index/version 返回真实握手时逐 byte 生成 `weights-dense.bin`、`weights-gamma0.bin`。故障与第三次 prefix-abort 计算不混入这两个 dump。服务器 runner 还必须核验实际 dump 长度及 SHA，才能把 canonical 预期与实际 accepted 权重来源绑定。

## 检查与生命周期

每个完整 fixture 独立要求 S888076 请求/真实 ACK（739084W/148992R）、M40448（其中36864 EXEC）、N258、G384服务/1536对、E128、loader36864/宽读294912/A147456拍/B147456拍、T128字/RELEASE1。

TB 检查全部128个 Norm 字、384个 mid 字、128个最终输出字、每组 gate/up/down，以及每个 chunk 的4个真实 A word、16个 B word和 ACK 后读取版本。新请求必须在前16个 weight write ACK 后出现；当前返回不能在其上一拍尚未写 ACK 时被吞掉。M READ 只允许在每组最后 K chunk；首 chunk clear-result，其余保持 raw 累加。provider 在 posedge 用 NBA 推进字段，握手边沿前保持 payload/tag；请求与返回背压均有稳定断言。

26 项 CASE 包含两个完整正常 fixture、一次完整计算后的输出 prefix-abort，其他负例大多早停：错 index/last/future job/future seq/version/error，旧 job/seq drain，跨取消旧 job 隔离，weight 写 ACK 背压，请求停顿与版本捕获，prestart/RUN abort、partial/reset、N/M/G 原生错误、S helper 错误、零版本拒绝、job耗尽不回绕、DONE 保持和 abort+ready 同拍。原生 E 错误没有在本新顶层单独注入；旧 E 的资格不扩大为本轮全部负例覆盖。S 错误是 helper 响应边界注入，不代表 native S 错误检测。

## 复现与边界

正式仓库根可执行：

```text
python work/Melodydt/151/build_f1024_vectors.py --root . --directory OUT
python work/Melodydt/151/build_f1024_tb.py --directory OUT
python work/Melodydt/151/check_f1024_oracle.py --root . --directory OUT
```

脚本目录需有 `f1024_integer_reference.py`；正式依赖 `work/Melodydt/151/f16_integer_reference.py` 已列 SHA。输出目录只选择输出，不选择参考来源。`--observed-weight-directory DIR` 可额外核验实际 accepted dump。服务器编译清单及 include 路径以 `f1024-tb-contract.json` 为准，严格结束行 `PASS_W4_F1024 cases=26`。

检查器读取正式project/tb中的TB并核对合同SHA；临时生成TB需另核对SHA。本轮服务器95245的64项实际测试和两份9MiB accepted SHA见[实施报告](W4_F1024_IMPLEMENTATION.md)。这只签收固定整数profile的真实维度执行，不能写成trained Qwen3推理、源epsilon1e-6或量化质量通过；实际MEM带宽、通用跨岛、完整程序/模型族、M11/M12及面积/时序仍待验收。

附加 `f1024_fp32_diagnostic.py` 对同两组 synthetic 参数给出 FP32 counterpart 诊断：逐 product 和逐 K 累加都 round-to-FP32，只复用相同 n 周期，不合并 K；SiLU 用数学函数并在相应操作后 round-to-FP32，不加 S16 clipping。epsilon 为整数 code1 的实数对应值 `2^-20`，不是源模型精确 `1e-6`。dense 的整数饱和明显，相对这个未 clip 的 FP32 输出 maxAbs=`122676.7734375`、RMSE=`43916.28786715324`；gamma0 两项均为0。这些值只描述两组 fixtures，直接说明当前统一 scale 的 dense 例不能当作 FP32 精度或 trained Qwen3 质量通过，也没有定义模型可接受误差阈值。
