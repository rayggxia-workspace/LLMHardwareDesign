# Issue72 同精度、同资源比较冻结前提

本轮只比较可审计的有界数值任务和条件服务时隙，不声称RTL、PPA、整图模型
质量或端到端硬件收益。旧Issue70的Granite参考失败与Falcon四次饱和保留。
未得到新的独立数值接收前，不把旧W8投影和旧浮点递推拼成完整整数链。

## 数值先决条件

每个 placement pair 使用同一producer源SHA、输入/配置/编译常量/LUT SHA，
相同精度、逐token code/unit/epoch、guard/retry、完整head/group归约和原子发布
轨迹。compiler/LUT生成的浮点参考须与runtime整数路径分开。评价误差或未来
原生状态不得选择在线单位；校准和评价输入互斥。完整Falcon范围须保留32head、
4096维共同gated RMSNorm，不得每head归一化后拼接。

Granite route-sensitive oracle/native诊断和部署W8路由不是同一精度，分别报告；
fixed-ID反事实不替代原生路由。原FAIL仅由新证据追加解释，不覆盖或改阈值。

## 守恒库存

split/shared仅改变声明的服务归属、合法部署与调度，不能增加总S8 lane、控制
context、宽算术、SFU、ROM或RAM、bank的1RW端口、总线、FIFO与backing容量。
逐数值节点的总算术和权重/常量存储必须一致。纯label变换应为零差对照；不同
发射粒度或bank分配属于独立搜索变量，不能偷换成物理宏边界的收益。

沿用工作预算V16KiB/R32KiB/M32KiB/S8×32KiB，每bank1RW128bit；单条128bit
总线、32B header/16B beat、1984B最大payload、端点2KiB FIFO。若新的完整
整数链不能在该预算下合法部署，明确拒绝，不赠缓存或隐式端口；backing的
实际数据/双generation/metadata/weight/LUT各占有限槽位。

## 完整服务义务

必须计入W8矩阵完整K、投影输出RQ、scale编译结果及metadata/epoch更新；
宽乘的S8 digit积与每步宽shift/add、RNE/饱和、topk与dispatch、LUT单端口读取、
多周期除法/开方、完整归约和消费者屏障、所有weight及activation流。
Falcon包括MuP、持续conv history、softplus/exp/SiLU、二维state更新/输出，
4096维gate/RMSNorm、重新编码及必要的next projection。若attention分支以捕获
输入接入，必须标为cut边界并付其输入IO，不称完整hybrid或整模型W8执行。

状态guard重试包括未发布shadow代、读改写、clone/recode、每head单位与owner/
epoch/version/position descriptor、全group原子commit；失败代不作消费者输入。
副本、广播、打包重排、spill、重读、stride、packets和同步都付端口/链路成本。
旧Issue70 COPY日历只能作为搬运参考，不能替代这些算术服务。

## Witness和独立接收

每个事件给出数值stage/shape/位宽与lowering计数、输入输出对象/offset/bytes、
依赖、资源相对区间、start/end、token/head/group/attempt/unit/epoch。独立接收
从冻结数值任务重建次数、按物理beat核端口、扫资源区间、检查容量/生命周期
和完整生产消费依赖。除SHA损坏外，负例实际改事件或数值并重写artifact SHA，
证明接收能发现语义错误。两轮同科学payload或独立数学重放才可作为执行证据。

服务时隙的基础算术/端口时延尚无RTL校准时逐项写明假设并做敏感性，不给
伪精确硬件周期。若数值链失败，允许保存成本诊断，禁止排名为已验证划分收益。

## 本轮实际有限服务的独立接收

`receive_service.py`不导入service producer。递归校每template串行日历、loop
次数/period、闭式计数及affine对象地址范围；用最多16个模16地址余数证明逐
packet的leading-offset拍数，既不过度要求所有stride为16倍，也不漏算真实
跨拍。源码数值回链、每head/attempt/unit/epoch、全group/I64 guard、完整N
readout、完整4096norm及末消费者后16B发布均独立核验。默认port/head/norm/
RAM四个实际artifact/SHA重写负例。

```text
python -B project/experiments/closure/receive_service.py --result <service> --numeric <full-guard-run> --compiled <compiled> --math-receipt <independent-PASS.json> --producer-source <frozen-service.py> --binding <JSON> --out <new-receipt>
```

binding含真实commit、`receive_service_sha256`、`audit_io_sha256`。
`--skip-negatives`只得PARTIAL_NO_NEGATIVES。新服务库存明确包含M256的16×16
S8 PE及VR8的8个S8 lane，单row只用16个matrix PE，不能与旧只有matrix代理
的COPY/Issue68服务数字直接比收益。SFU只有一份，48B固定128bit操作数状态
从已有aux8KiB中预留；U128 numerator shift和division RNE finalize也另收费。

完整proposal/decay/injection/readout-products的EXT暂存、私有history/units/
descriptor代和所有clone都占容量并付IO。初态物化在setup；已发布代在每token
内不可写，新state/history/unit只在nextnorm完成后以单128bit描述符发布。
模板层数超过一亿实际leaf时采用归纳接收，不能把压缩文件大小当物理缓冲量。

本工具将已独立重算的值轨迹与合法有界服务结构关联，没有做RTL或内存字节级
功能模拟。所有宏及叶均采用保守串行政策，未搜索prefill batching或最优互锁；
因此只能报告该合同下的服务差异、容量拒绝及零差对照，不能宣布独立R物理宏
胜出或将条件时隙换算成真实LLM速度。
