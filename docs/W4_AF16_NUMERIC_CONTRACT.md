# AF16 独立整数参考与有界 TB

本包为 Issue151/PR152 的 L4 固定纵向集成验证，输入版本 `cd8dfc9a3770f0be04b3e75fe08fe60fd69e47a6`、native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本代理只生成和执行 Python 数学/静态检查，没有启动本地 RTL 或服务器仿真。

数学期望是 `F16(A16(X)[row], Fgamma, Wgate, Wup, Wdown)`，两行依次复用相同 F 参数。通过显式文件路径在内存加载已交付的 `a16_integer_reference.py` 与 `f16_integer_reference.py`；源路径及 SHA 记录于向量/测试合同。输入定义取已冻结 A16 数学向量中的原始 X、gamma、权重与 RoPE 系数，重新计算 A 结果，不用 RTL 输出生成期望。EXP 和 G 表由独立数学函数重建，只把 native 表当版本一致性核对材料。

## 数值与帧格式

- H8、两 causal token、单 head、F I8。隐藏数据及 A/F 输出为 S16 Fin10，权重为 S8 Fin7，RoPE 系数为 S16 Fin14。
- A 的 Q/K/V/Wo 为 RNE7；adjacent-pair RoPE 为 RNE14；QK 乘 11585 后 RNE25；两行 Softmax 分别 count1/count2，概率 Q14；PV 为 RNE14；A 最后加原始 S16 X。
- A 输出逐 bit 成为 F 输入，没有 RNE3/clipS8。F RMS count8、epsilon code1，使用独立 Fgamma；所有 F 投影 RNE7，SiLU×up RNE10/clipS16，最后直接加原始 A hidden S16。
- 父 saturation 为 A、F0、F1 实际已观察值的 OR，不把饱和等同协议错误或模型质量通过。
- 40×128bit 输入：A 原 27 拍，F 三组权重 12 拍，Fgamma 一拍。总 640B，包括 A 的 96B padding；F 重帧每行 17 拍，其 1..3 拍为真实 zero。A gamma 位于父拍24，F gamma 位于父拍39。

10 组向量包括真实 RoPE、仅未来 token 改变的因果对、零 Fgamma 精确保留 A hidden、正负 gamma、全零、正负饱和、quarter-turn 稀疏布局和两组确定性随机输入。因果对保持 F 参数相同；第 0 行 AF 最终结果相同，第 1 行不同。至少一个正常 hidden lane 不是 8 的倍数，因此 S8 窄化/还原不能冒充逐 bit 传递。

## 正常路径与 TB 检查

每个正常父任务要求 181 个普通 S 请求及真实 ACK（131W/50R）、72 个 M 命令/响应、28 个 N 原生命令/响应、10 个 E 服务、2 个 G 服务/8 对输入输出、12 次 loader/26 次宽读/A18拍/B14拍；子 T 共 4 次输出 take、3 次 RELEASE，host 只收到 2 行。父成功 DONE 必须在 A 和两次 F 的正常 DONE 已消费后出现。

TB 内嵌独立 literal，无额外 SVH。A S 检查保留每地址写入历史，包括原址 RoPE 的前后两个版本；F 两行分别检查每次写入及真实 ACK 后的读取。F 的 34 拍入口逐拍比对 golden，检查原始 A hidden、padding、权重和 gamma 复用。输入 stored 不能早于真实 A 第27写 ACK；F start 不能早于其实际 stored；正常全局计数不能代替上述局部条件。

33 项预声明 CASE 覆盖输入 ACK 门、10 组数值、重复帧、参数生存期、A capture/F feed/F start 背压、父 RUN 而子 A 尚未 start 的取消、部分 F 帧取消、host prefix 后 abort、DONE 保持及 abort+ready 同拍、reset、子 A 的 N/M 错误、子 F 的 N/M/E/G 错误、部分帧 S helper 错误及恢复、第二行 F 错误保留第一行已消费 prefix。另外显式注入 A 首字 last 错误、F index 错误，检查无错误 payload 捕获/发布并给父错误终态；在未启动 F 与已关闭 A 两阶段分别注入 stale saturation，要求正常无饱和结果不被污染。S 错误是 helper 响应边界注入，不是 native S 错误检测。以上是待执行测试要求，尚不构成 RTL 通过证据。

## 可复现命令与依赖

从仓库根执行（`OUT` 为已有脚本所在目录或空输出目录；`--root` 指正式集成根）：

```text
python work/Melodydt/151/build_af16_vectors.py --root . --directory OUT
python work/Melodydt/151/build_af16_tb.py --directory OUT
python work/Melodydt/151/check_af16_oracle.py --root . --directory OUT
```

脚本同目录需存在 `af16_integer_reference.py`；正式根需包含 `work/Melodydt/151/a16_integer_reference.py`、`f16_integer_reference.py`、`a16-contract-vectors.json` 与冻结 native EXP/G 表。`--directory` 只选择输出，不选择旧参考或 DUT 来源。生成器不改原参考文件；依赖在内存执行，不生成参考源目录的 bytecode。

服务器后续仅编译 `af16-tb-contract.json` 列出的源与 include 路径；每个 `CASE_PASS ID` 必须恰好一次，最终行必须严格为 `PASS_W4_AF16 cases=33`。实际执行日志、源 commit、工具、输入和结果 SHA 由根代理服务器回执绑定，本包当前不能自行宣称 RTL 通过。

这不是完整真实样本模型的形状、精度或供参资格，也不是 L5 通用跨岛 storedACK 网络、外存接口、共同 ROM/路由或物理验收。M2/N2/E2/G1/S2/T2 是本轮实例计数；新增参数208B与 A hidden32B 为明确 FF holding，没有额外 T，也不代表已综合的面积。
