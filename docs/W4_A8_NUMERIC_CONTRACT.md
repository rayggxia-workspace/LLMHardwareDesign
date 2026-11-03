# L4 A8独立整数参考与有限测试合同

Issue151 / PR152；parent `1d722477564e14f7dc93e39ce8e28b8e2d150cb0`，native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本包仅准备一个query、八key/token、D8、八输出通道的QK→Softmax→PV计算切片；属于继续主线四，不代表进入或完成主线五，也不代表完整Attention。

## 数值与布局

Q/K/V都是signed S8 Fin7。QK每个token的点积raw Fin14，M op4的有符号S16 factor=11585、leftshift0。11585是`RNE(2^15/sqrt(8))`，以独立80位精度Decimal重算验证。该乘积Fin29经M op5 widthS16、RNE右19→score S16 Fin10，op5参数0x113。factor不是右移量，负score须signed RNE ties-even，不能用向零截断或普通ASR代替。

K布局为`K[token][dimension]`，M B中byte offset=`8*token+dimension`；V布局为`V[channel][token]`，byte offset=`8*channel+token`。两者物理都是n-major B512，但逻辑轴不同；非对称V向量与错误转置计算交叉，保证本测试能区分该布局错误。

Softmax复用nativeN整数合同：先全score统计max，再全部原score重读生成EXP。EXP数学节点独立生成`round(exp(-16+i/64)*32768), i=0..1024`；score差Fin10按16raw步长做RNE插值。精确EXP是U16码[0,32768]，不能按signed负数解释。EXP全部写S/ACK后，`factor=floor(2^44/sumEXP)`，回放同一码，`RNE30(EXP*factor)`夹至[0,16384]，概率是非负S16 Fin14。概率整数和不强制16384；末key极值例得到7×59+15968=16381，这是本合同定义的整数结果。

PV用M A16概率Fin14×B8 VFin7，raw Fin21，scale1/left0；op5 widthS16、RNE右11→输出Fin10，参数0x10b。两投影原生CLEAR是opcode6，MC_CLEAR=0只是局控阶段编号，不能发原生opcode0。

M op5每应答四个signed S32容器，最终取各low16跨两half合成8×S16。本参考另保存完整S32容器字面值；TB同时核对容器、score/EXP/prob/output存储字。当前S8输入/D8范围不会触及S16输出夹限，8组向量的done_saturated均false；有限极值测试不被表述为“饱和路径已覆盖”或所有M格式合格。

## 地址、计数与生命周期

入口12×128bit=192B：Q8+K64+V64=136有效字节，56B Q padding实际写零。S448..451存Q，452..455存K，456..459存V；460 score，461 EXP；462..463不读写；464概率，465..467实际零padding，468输出。概率M A起点464满足4字对齐；不能用462作wide A基址。

正常帧23个普通S请求/ACK=19写+4读：12入口写、score写、N的EXP/prob两写和三读、三padding写、output写和最终读。M每投影CLEAR6/SCALE4/EXEC10/READ5half0/READ5half1，合10命令/应答和2loader；N一服务6命令0/1/2/3/4/6；T一字被take并RELEASE后才DONE。EXEC response是状态，不作为score/PV tensor；原生结果必须通过op5读取。

所有入口实际ACK后才start_ready；partial、末字已接收但ACK未回均不能RUN。局部S owner只能LOCAL或N，N lease持至结果存储ACK和service响应消费；再padding/复用M做PV。输出/完成保持至握手。abort/reset协调参与叶、Nctrl与Shelper；已接受RAM写和已消费T前缀不能回滚；已有DONE遇abort保持状态并只消费一次。

## 参考与验收边界

`a8_integer_reference.py`只用标准库、数学式、Python无限精度整数。EXP1025节点与冻结native源逐节点一致，另用Decimal高精度重建；源表只作验证，不作expected输入。`a8-contract-vectors.json`含8组Q/K/V和所有raw/scaled score、EXP/factor/prob、PVraw、输出、容器与S字。`a8_expected_vectors.svh`是可单独审阅的literal函数，生成的TB已将同样函数嵌入，无运行时include依赖。

8组为非恒定/非对称、相等score不同V、zeroQ非zeroV、末key极值新max、交替符号极值、稀疏identity布局、负Q混合K、常值V通道。`a8-tb-contract.json`独立列26个必要CASE及PASS_W4_A8，预期集合不是从待测日志动态提取。故障保留真实N非法opcode15、QK/PV EXEC保留位错误；另测S/M/N/loader/output背压、ACK门、重复输入、abort/reset恢复和DONE精确消费。

Python检查通过不替代RTL。按照当前用户约束，所有新增RTL仿真和旧回归只能在服务器Verilator执行，工作/日志/结果位于`/public/home/yuzelu/Melodydt/`，作业名前缀zenanyan。当前本代理没有执行本地或远端RTL仿真；SV timing/force/hierarchy兼容及真实场景结果待根任务实际回执。

未覆盖QKV/output投影、preNorm、RoPE、GQA、多head、多组、mask、KV cache、原模型维度/容量/数值质量、MEM、完整有限产品程序、M11/M12永久绑定或物理资格。旧N/F8 ModelSim结果保留历史，不自动转为本次Verilator通过。
