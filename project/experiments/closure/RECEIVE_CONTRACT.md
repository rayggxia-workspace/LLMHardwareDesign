# Issue72 独立接收约定

接收代码不导入producer。`integer_oracle.py`用Python int、Fraction、逐bit恢复
除法/开方定义RNE、溢出、饱和、S8 digit宽乘与LUT边界；这些是数学参考，
不是实测硬件实现。tiny边界测试可本机运行，真实模型/采集/数值只在授权服务器。

各producer必须记录模型revision/权重SHA、输入/cal-eval token及来源SHA、
代码commit/实际模块SHA、编译常量/LUT字节SHA、shape/dtype/layout、code和单位
关系、静态/动态尺度及量化粒度。manifest完整列每artifact路径/大小/SHA，
接收前全部核验，输出新目录不覆盖旧结果。

整数runtime输入、状态和输出trace为整数数组，包含每个完整stage及连续状态
必要的初末值。评价浮点参考另存；误差只在独立评价层计算。state事务记录token、
head、attempt、当前/试算单位、epoch、guard、accept、published版本与checksum，
失败代不能污染已提交状态。chunk变化须保持同一串输入与连续checkpoint。

独立接收先校来源和数值边界，再从源整数code完整重算被声称的消费者链，不能
仅抽查已给出的最终值或相信自报operation count。大张量可逐token/head流式，
但4096norm必须完整归约。W8投影若未串入真实整数递推，应明确cut点，不能把
不同轨迹的投影/状态误差相加或拼称完整链。runtime源码需可审查无FP算术桥；
仅整数trace自身不足以证明无隐含浮点运算。

至少执行真正重写SHA的code、LUT/参数、route/epoch等语义篡改负例。每项分别
保留hash层和数学/协议层结果，不把文件哈希通过当数值正确或硬件质量通过。

## Granite显式参考接收

`receive_reference.py`只接收新Granite三种precision参考，不重新运行完整模型。
它核全部router线性前向误差界、每layer/profile最敏感token的独立完整K标量
`math.fsum`、actual-logit top8/严格exact-tie规则及softmax/cast；全32层hidden/
MoE与LM的已发布trace误差和原gate完整重算。模型attention/expert输出自身未在
接收机从权重重新运行，因此不声称全模型算术逐位接收或质量通过。

```text
python -B project/experiments/closure/receive_reference.py --result <granite-ref> --original <Issue70-capture> --producer-source <frozen-granite_reference.py> --binding <JSON> --out <new-receipt>
```

binding为真实commit、`receive_reference_sha256`和`audit_io_sha256`。
默认实际改写NPZ logit/route及JSON资格、重写manifest SHA，再要求语义拒绝；
mutated容器留接收目录供核查。`--skip-negatives`只能得到PARTIAL_NO_NEGATIVES。

## Falcon完整整数R支路接收

`receive_falcon.py`不导入producer；独立负数floor-quotient RNE、完整W8 dot、
U128 restoring sqrt/div、持续conv/LUT/32head state、4096 gatednorm、out_proj、
外部attention/residual join和H2560 nextnorm重算，核每stage整数、每proposal/
state SHA、范围判断、单位/epoch/原子发布/失败不变及连续checkpoint。仅此R支路
闭包；attention与MLP依然cut。编译器生成的浮点LUT/原生cal最大值并未由整数
重放变为无浮点硬件，接收也不声称其模型质量通过。

```text
python -B project/experiments/closure/receive_falcon.py --result <run> --compiled <compiled> --capture <Issue72-capture> --chain-source <frozen-falcon_chain.py> --int-source <frozen-falcon_int.py> --binding <JSON> --out <new-receipt>
```

binding为真实commit、`receive_falcon_sha256`、`audit_io_sha256`和
`integer_oracle_sha256`。默认runtime code、commit epoch、initial unit三个
真实artifact改写并重写SHA的负例；后者更新compiler manifest并同步run的输入
manifest指针，避免仅靠旧hash检测。`--skip-negatives`标PARTIAL_NO_NEGATIVES。

## Granite整数router接收

`receive_numeric.py`独立重算全部768条件、192选择性fallback：精确有理数确定
power2 scale边界、完整K1536 dot/共同unit、真实40选8、Fraction RNE gate、
Decimal70位exp2 LUT编译、严格量化误差证书与逐profile预定S16九份S8完整K
partial。权重/输入FP编码是明确compiler桥；所得整数gate尚未通过expert/down/
merge，此接收不证明完整MoE整数链或模型质量。报告source FAIL资格原样保留。

```text
python -B project/experiments/closure/receive_numeric.py --result <numeric> --reference <typed-reference> --producer-source <frozen-granite_numeric.py> --binding <JSON> --out <new-receipt>
```

binding为真实commit、`receive_numeric_sha256`、`audit_io_sha256`和
`integer_oracle_sha256`。默认code、LUT、gate和fallback四个实际NPZ篡改及SHA
重写负例；`--skip-negatives`标PARTIAL_NO_NEGATIVES。
