# 固定校准的GQA共享与因果KV：本机实验

2026-10-23（UTC+08:00），Liangruizhi。[Issue47](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/47)，
[PR49](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/49)，base PR44。未合并、未验收done。

## 问题与范围

Issue39的同张量离线平衡只用于定位，不能证明独立校准或连续cache成立。本次先补最小缺口：
已有Qwen3-0.6B，layer0，KV0及其全部关联Q0/Q1，d128；32token独立校准，两个不同的40token文本，
各含32token prefill及8步teacher-forced decode。不存在自由生成或语言质量benchmark。
原模型FP32 CPU执行，捕获post norm/RoPE的Q/K/V和pre-o_proj注意力输出；不修改模型算术。

源码commit `270568dfcad314f3d16e9bfa68dc378b31bdea9b`；模型revision
`c1899de289a04d12100db370d81485cdf75e47ca`。现有8个模型/分词器文件逐一核对大小/SHA，
torch2.10.0+cpu、transformers4.57.6、NumPy2.5.4，以及安装的Qwen/cache实现SHA均绑定。
捕获器4线程。权重沿用D盘既有环境，无新增下载、GPU或远程作业。

## 冻结数值合同

- 两组候选：direct_static_KV，以及calibrated_shared_QK_static_KV。
- 只用校准文本计算每通道g，g=RNE(0.5log2(Kmax/Qmax))并限制[-8,8]；Qmax覆盖同一KV组全部query头。
  Q*=2^g，K*=2^-g，变换在norm/RoPE之后；对两头保持实数QK不变。评价不重新拟合。
- K/V各使用一个校准冻结的dyadic exponent；Q exponent只观察当前行，M/r按当前行离线浮点编译。
  Q/K/V存i8；QK累加i32；score RNE/sat到i16.f8；4097项exp LUT；P15/32767；V8；输出i16.f12。
  其宽RQ、P15×V8的三次8位部分乘、i64对齐和恢复除法继承C1显式整数参考。
- norm/RoPE、浮点到代码、校准/动态scale和M/r编译仍有浮点辅助。没有在线整数scale前端，
  不声称全整数模型、实际INT8内核速度或参考项目RTL逐位复现。

## 实际结果

下表是局部pre-o_proj注意力输出相对原始FP32输出的相对RMSE，**不是准确率下降**。
没有事后把误差阈值设为“通过”，也没有完整模型接受结论。

| 独立评价文本 | direct固定KV scale | 校准冻结/全组共享QK变换 |
| --- | ---: | ---: |
| systems，40token | 0.6455952016 | 0.0179797327 |
| arithmetic，40token | 0.4928941513 | 0.0190307204 |

4例Q/K/V输入裁剪均0；捕获full与cached的FP32差异均满足事前atol=rtol=1e-4，
但并非浮点逐位一致（例如systems K最大绝对差约1.068e-4，仍满足相对项）。
这4例量化后的full/cached Q/K/V代码及整数输出差异均0，不能推广到其他层/头/长度。

校准direct的K exponent=2，变换后=-4；V均=-7；实际共享g范围[-2,7]。
QK最大绝对INT32累加值依次为504/394和61,180/67,201；所有checked边界通过。
对本合同对称[-127,127]、K128，最坏绝对和上界2,064,512，小于INT32上限；不推广到更长归约。
本次score/输出无饱和计数，输入无裁剪，不表示其他层/长度不会溢出或裁剪。
counts是当前标量参考的完整矩形遍历（含被mask位置的QK/PV计算），不是最优因果内核的操作下界或cycle。

- 生产运行：79,360个独立oracle整数值；40,960个batch/token输出值；98,304个前缀/未来扰动输出值，均一致。
- 8项边界测试：共享变换、未来离群点不重拟合、当前行Q无未来依赖、顺序/容量/dtype、过期epoch、
  profile变更拒绝且不修改已发布缓存、分块追加一致。
- 独立读回审计不导入目标run/core/fixed/quantize/cache：Fraction重新量化81,920个输入代码，
  80位Decimal重新编译640个M/r值；独立oracle重新计算79,360整数值；检查160条缓存发布事件。
- 两次运行的frozen-calibration.json、integers.npz、numeric.json、summary.json逐字节一致。
- 3个审计负例在**更新文件SHA后**修改输入代码、M或cache epoch，均仍被独立约束拒绝，避免只测哈希。
- 小证据ZIP安全读回31个文件，通过路径/重复成员/长度/SHA验证；管理结构检查通过。

## 对Block的影响与未闭合成本

这支持保留“完整GQA共享组＋KV格式/scale profile＋发布版本”的接口约束；按query头各自选变换会破坏
同一KV的兼容性。cache追加应先完成数据和格式一致性检查再发布有效长度/epoch。
软件检查没有证明异步硬件内存序、广播、命令队列、死锁自由或端口时序。

40token、d128的一份K8/V8逻辑payload为10,240B；按两query头重复存储将是20,480B。
本参考分配48token即12,288B，单份能容纳40token，双份同容量最多24token；这是容量反例，
不是速度或物理广播收益。共享/重复方案若改变buffer或端口需另做同资源比较。

当前文件合同每profile存128个i8 g及两个KV exponent，即130B；80个当前行Q exponent共80B；
若缓存每行u32 M/u8 r则400B。它们是**字段payload**，未包含Python对象、profile ID/descriptor、
地址、epoch、对齐、报文header、scale生成的临时值与硬件RAM开销，不能当完整物理存储。
平衡方案每评价另有15,360个Q/K分量的dyadic变换；g作用在norm/RoPE之后，不能直接无证明地折入前面的投影权重。
动态Q max/reduction、参数生成和转换会占用V/端口，未赠送零周期硬件。完整操作分解见numeric.json counts。

因此D1保留“独立校准且全GQA共享”的候选，D2/D3/D5仍需带回压和宽算术服务的配对实验；
没有因为局部误差降低就定案M/A/V边界。P1–P15能力图的实现/候选/缺口见[映射表](../PRIMITIVE_CAPABILITY_MAP.md)。

## 版本、复现与交付

正式运行在D:/Projects/Codex/primitive-stream-20261023：capture02、numeric03、numeric04；
开发capture-dev01/numeric-dev01不作正式证据。本地先冻结1cfdc8c，随后用已认证账号发布完全相同源码树
407cc590fd2dbc8c3266577229aa26e5b7387e04为270568df，并按线上commit重新运行正式组；没有修改旧结果的producer。
旧capture01/numeric01/02及audit01保留为前置本地版本验证，不冒充线上commit产生的结果。

[证据索引](../../project/experiments/primitive_stream/results/issue-47-run01/index.json)；
evidence.zip=1,026,550B，SHA256 `e03719d3e21171c380958a2dcbea99e5f3e773babba0ab19bea4d1852c36ff9b`。
其中有原FP32少量张量、整数代码及M/r、原manifest、两次结果、审计和源码快照，不含权重。
完整命令在[实验README](../../project/experiments/primitive_stream/README.md)及manifest；正式组路径使用capture02/numeric03/04。

```powershell
python -B work/Liangruizhi/47/verify_delivery.py project/experiments/primitive_stream/results/issue-47-run01/index.json --extract D:/Projects/Codex/primitive-stream-20261023/review-new
python -B project/experiments/primitive_stream/audit.py --capture D:/Projects/Codex/primitive-stream-20261023/review-new/capture02 --numeric D:/Projects/Codex/primitive-stream-20261023/review-new/numeric03 --repeat D:/Projects/Codex/primitive-stream-20261023/review-new/numeric04 --output D:/Projects/Codex/primitive-stream-20261023/review-audit-new.json
```

恢复先核最新Issue/PR及SHA。用户未通知师兄批次完成，因此本次只读其任务范围/交接，未整合数值包。
Issue48资源估算器由另一成员推进，本次不接管或重复开发。CPU超算仅给出条件估算，未登录或启动任务。
审查/合并、项目登记PR5、Projects同步仍待处理，见[交接](../handoffs/2026-10-23-issue-47-primitive-stream.md)。
