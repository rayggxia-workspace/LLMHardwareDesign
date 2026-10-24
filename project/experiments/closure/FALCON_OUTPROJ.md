# Issue72 Falcon output projection单一受控分叉

触发证据是服务器首轮完整整数链S32 guard_rescale72：input norm误差0.0181%、in_proj后2.4868%、scan1.5086%、完整4096 gatednorm3.125%、out_proj6.7257%、nextnorm3.0289%。S16/S32的nextnorm误差均约3.03%，而绕过in_proj的statecut out_proj仍约5.99%，因此继续增加状态位宽不是当前最直接的误差修复。以上是原局部诊断，未定义应用质量PASS。

本实验预先固定唯一三个条件：whole-row A8、K512 A8、K256 A8。只读同一已整数闭合的fullS32 guard_rescale72轨迹，冻结gated_norm_q12、residual、外部A、原W8 codes/逐output Wscale及原cal16 compiler。不会重调R、gatednorm、W8或用eval误差拟合scale；每group仅从当前整数输入选择最小RNE右移得到[-127,127]。

## 完整K与数值合同

每group完整dot按最坏Kgroup×127²和实际值核INT32。A8各group的exponent delta不同，禁止直接把不同单位INT32 partial相加：每row取d0=min(delta)，计算partial_g左移(delta_g-d0)后完整K累加为checked I64。W8逐output scale跨K组共享，因此因式分解到完整和之后，只做一次Q31重标：weighted_sum64×mantissa32，checked I128，RNE(31-Wexp-d0)，输出I32Q12。逐group先RQ再相加是另一种舍入函数，本实验不混用。

I128产品用signed hi64和unsigned lo64两数组保存，重构(hi<<64)|lo；不存object NPZ、不转float。whole-row保持原INT32累加/checked I64 RQ合同，必须逐码复现原A8/delta/dot/out/MuP/join/nextnorm。完整K4096、原矩阵和scale不变，各group partial/full标记明确。

固定I32输入时minimal A8 delta≤25，K4096的aligned sum保守界小于2^51，I64可容；再乘Q31通用界小于2^82，不能保证I64。G>1候选用64×32→128，按radix128 S8 digit分解计45个积及44次宽shift/add；whole32×32用25个积/24次shiftadd。实际产品位宽、I64是否足够另报，不把观察到的小值变成无条件硬件能力。

然后完整执行ssm_out MuP、外部A MuP、residual+A+R三输入join和H2560 pre_ff norm，全程整数；float只在执行结束后报告native及frozen integer baseline误差。报告whole72、prefill64、decode8三种误差口径，不将改后局部误差称模型质量通过。

## 接口和容量义务

static W8scale可因式分解：每output Q31+I16共6B，out_proj共15360B；无需复制G份。dynamic A8 exponent是每row、每group I16，共T×G×2B；d0可本地导出，witness不是必然增加传输。group dots是T×G×O×4B，本协议按每group output row连续stream、32B header/16B拍/payload1984/FIFO2KiB计wire，不赠跨Block hop或参数cache。

K256的G16完整partial/token=163840B，远超V16KiB；必须按output tile流式消费或显式S/backing，不能免费整物化。比如每次partial O256=1KiB、S64acc2KiB、I128prod4KiB、输出1KiB、scale1.5KiB，再加group metadata/descriptor可在16KiB候选内；其bank/端口/缓冲仍须真正调度。M32KiB也不能驻完整W8矩阵，权重tile和prefill复用另计。对比三精度方案的资源/误差不是placement收益；固定每一个数值合同后才可配对M/V位置。

## CLI和产物

~~~text
python -B project/experiments/closure/falcon_outproj.py --compiled COMPILED --baseline FULL_S32_GUARD_RESCALE72 --group 0 --binding BIND --out NEW
# 另两独立job使用--group 512和256，不能复写同out。
python -B -m unittest discover -s project/experiments/closure -p test_falcon_outproj.py -v
~~~

binding需commit、falcon_chain_sha256、falcon_int_sha256、falcon_outproj_sha256。outproj.npz保留全部整数A8/delta/partial/完整aligned sum/I128产品字/重标以及每个后续stage；alignment.json保留逐row/group prefix hash；report/manifest保留源索引、实际位宽、元数据/partial wire/算术成本和SHA。真实计算只在服务器，tiny测试仅3row/K16/O5标量Fraction独立期望及边界，不在本机读实际tensor。
