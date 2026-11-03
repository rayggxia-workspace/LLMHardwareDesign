# W3 FFN8独立数值合同、参考与测试边界

Issue151 / PR152；parent `99d6df2e094febe4ea8fc9896301adbbfdc803ed`，native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本目录负责独立Python整数参考、冻结向量及SV TB。ModelSim实际执行由根任务负责，本子任务不自行使用服务器或修改RTL/正式包。下列Fin是**这个有界小核主动选择的完整数值profile**，不是等待整模型scale才能定义，也不授予完整F/模型量化质量资格。N未集成，FFN8不含完整F的pre/post Norm。

## 固定算术

`rne(v,s)`为数学整数除以2^s的nearest ties-even；负数也按floor商＋非负余数作最近偶数。clipS16为[-32768,32767]，饱和独立于协议error。所有中间和/乘在Python无限精度整数求值，按已声明阶段舍入/clip，不在每个乘法或每个K项提前舍入。

| 阶段 | 固定数值合同 | S位置 |
|---|---|---|
| x/Wgate/Wup/Wdown | signed S8，Fin7；每矩阵64元素n-major `8*n+k` | 输入448..463 |
| gate/up M | raw dot Fin14；op5 widthS16、RNE右4（0x104）→S16 Fin10。每响应四S32 carrier，取各low16，跨两响应合8元素 | 464/465 |
| x展开/残差 | sign-extend x到8S16 Fin7；E7左移3后S16 Fin10 | 466/467 |
| G mid | fn0 SiLU(gate)，LUT Q10、RNE插值；乘up后RNE右10、clipS16 Fin10 | 468；469..471真写零 |
| down M | A16 Fin10、B8 Fin7，raw Fin17；op5 widthS16、RNE右7（0x107）→S16 Fin10 | 472 |
| final | E0对down＋residual做S16饱和加，输出Fin10 | 473及T一字 |

done_saturated是实际观察到的M格式读出、G和E各阶段saturation OR；正常成功向量与独立oracle逐项一致。发生error/abort时保存已经观察的sat直至error完成，不能把sat等同error；已有DONE遇abort两个flag必须保持到唯一一次take。协议error不允许发布正常final，不能使用截位伪装合法数值转换。

入口16×128bit共256B，x8B＋三矩阵192B为有效200B，56B x组padding实际写零。S448..473预留416B，T最终一字16B；系统有外存但此小核不使用MEM。固定程序/地址/shape/op/shift只允许数据变化，无bootload或运行时配置新程序。

正常帧S32事务（26写6读）逐一ACK；M15命令/应答、3loader且A/B各3拍、E2服务/native事务、G1服务及4个pair issued/retired、T BEGIN1/WRITE1/COMMIT1/TAKE1/RELEASE1。S普通口只有一个helper owner，loader wide读不算普通S请求。

## 独立G参考与表版本

`w3_integer_reference.py`从数学函数构建节点，未从DUT表或DUT结果取得期望：SiLU x/(1+exp(-x))、Sigmoid、tanh近似GELU `0.5*x*(1+tanh(sqrt(2/pi)*(x+0.044715*x^3)))`、Softplus log1p(exp(x))。fn0/1/2在[-8,8]，fn3在[-16,16]，间距1/32，节点Python round ties-even，Sigmoid乘16384，其余乘1024。与根提供的原生成script Git blob `b75c058284c95191a9b0449addf79f2a44b39de0`公式一致。

数学重建的513＋513＋513＋1025=2564节点已逐项与707固定`block_v2_g_tables.svh`核对完全相同；table SHA和oracle脚本SHA写入`w3-contract-vectors.json`。读表仅用于版本一致性验证，不作oracle输入。运行时按native合同取相邻节点、`RNE(delta*frac,5)`后相加；区间外采用原生端点规则，不能用连续高精度函数直接替代原生LUT行为。G.fn1 ungated输出Q14，gated先乘Q10 gate再RNE14→Q10；其余gated为RNE10→Q10。

## 数据与SV测试

- `w3-contract-vectors.json`：六个FFN输入normal/zero/positive_extreme/negative_extreme/mixed_weights/sparse_distinct，16入口字、S464..473逐阶段、raw dot/量化结果/各阶段sat及final/sat。正、负极值final分别八7fff和八8000，done_sat=true；这些clip是本合同的定义。
- `block_w3_ffn8_tb.sv`：自包含冻结常量，并在TB中用自己的入口字重新算M与residual公式交叉；不读取DUT计算结果生成oracle。逐次S访问检查stage及唯一owner、32S/15M/3loader、G4pair退休；覆盖六向量、padding、部分ACK/早start、重复、背压、reset/abort/prefix/DONE同拍与M/E/G真实native错误恢复。
- `w3-adapter-vectors.json`与`block_w3_adapters_tb.sv`：22个E基础case、14个G基础case及10个握手/写ACK/复位label。真实S16k＋block_p2_s_ctrl＋nativeE/G，不用mock内存替代写ACK。E各operand mask、E12/13 compact输出、RNE/ASR差别、sat、invalid/tail；G四fn/gated、odd/single、unsupported fn、invalid count、多个在途及冻结；成功必须实际destination ACK后才rsp。所测读/原生/本地guard错误在结果写前终止；目的写ACK报错不能回滚已经接受的RAM写。

入口/mem/nativeE/G停顿均对握手两端一致门控；请求/响应字段在未接受时保持。TB会刻意在请求被捕获后改上游字段，检查adapter快照；native S写已可见但ACK尚未被take时，service不得提前done。reset需同时复位adapter/leaf/helper，不能把单边reset或无reset取消视为已验证。

生成器均只写本目录UTF8/LF文本。根运行结果须以其各轮receipt和实际源/TB SHA记录，失败轮不覆盖、旧TB通过不冒充强化TB通过。Python数学/表检查不等于RTL通过，RTL有界通过也不等于完整模型质量、全部格式范围、形式活性或PPA。
