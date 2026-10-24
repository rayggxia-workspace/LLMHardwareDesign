# Issue74 同函数分组RQ的M/V驻留服务

每个g0/K512/K256分别比较near_m/shared_v；每项两个无功能差异label，总12配置。不同g是不同量化数值函数，不能把其差异称placement收益。全部实际数据/服务只在服务器，源和tiny测试可在本机。初始scope只有当前72token真实轨迹，Attention/MLP切口保留。

输入为已独立PASS的Issue72三g数值产物/receipt、fullS32 guard_rescale基准/compiled，以及已独立PASS的S32 r32_d8/wide1完整服务。原完整输入→R→4096norm前段和RQ之后MuP/join/nextnorm/发布逐event继承，stage/meta/body/原duration做canonical SHA。仅删除out.A8_absmax/minimal_shift/encode和out.matrix_fullK_RQ四stage/token；新产物绑定各g所有部分和/完整I64对齐/I128 product/out/join/nextnorm码的row SHA。原R状态/unit/epoch/事务和字节地址不变。

## 资源与合法差异

保留M256 16×16阵列、B1有效16PE；唯一VR8（8条S8/字节ALU lane）、单SFU、单ROM端口、旧全部RAM容量/128bit1RW、单BUS、端点2KiB FIFO及EXT128MiB。不新增近M ALU。VR8是已有共享bank-select服务端，新wide操作数和临时结果每次读/写明确付owner bank1RW和BUS包；没有无偿M本地wide路径。bank-MUX/物理线长仍待实现，此实验测试驻留/搬运策略，不直接证明宏布局locality。

两配置都真实预留M和V的相同scratch：partial64、sum128、product256、shifted256、product16=32、digits224、meta256、out64、control64B，各1344B；V另留64B groupdelta。near_m在M保留sum/product及参数，shared_v在V保留。共享V每完整group将M的64B INT32 partial转V；近M直接保留M的partial，只最终输出写共同EXT消费者。M/V同一个VR8、相同wide操作和shared BUS服务，差异是明确packet/1RW/驻留，不是label。

固定output tile16、物理Ktile256（对三个g全部相同），从完整K4096 A8输入加载M一次，逐row权重包/transpose/有效16PE/INT32累加均计。G0全K完成才RQ；G8/G16各完整Kgroup完成INT32 partial，按真实delta-d0对齐至I64，完整K后才一次final RQ，禁止分组提前舍入。每output静态W scale Q31+I16仅一份，在最终RQ tile加载，动态delta按G×I16逐token缓存一次；d0为同一整数向量最小值，参数不按G复制。

## 显式wide配方

32×32用5×5 signed-high radix128，64×32用9×5；低digit[0,127]、最高signed8，完整重构。核心分别25积+24×(8byteADD+2control)=265、45积+44×(16byteADD+2control)=837 lane操作。

服务还计：digit提取18/26 byteops；每term常数shift64/128构造14/22 byteops（包括byte填充/符号、交界SHL/SHR/OR和固定控制上界），以及所有digit/16bit积/宽partial/累计product真实bank/BUS流。首term直接初始化product，无额外add；其后24/44次完整carry相加。32/64累加digit/Q31的实际功能由独立wide probe和三g数学接收约束，费用为明确候选微实现，不宣称RTL速度。

最终RNE64/128另106/170 byteops：abs、byte shift、sticky/half/tie、increment、sign restore、I32 guard和控制各项在RQ_RECIPES内；随后bias add/guard另计。packet/BUS不是这些lane操作的替代。VR8工作输入最大bundle320/576B，借既有2KiB FIFO；未赠另一套宽寄存器。新scratch和所有宽临时都已占bank容量。

## CLI/证据

~~~text
python -B project/experiments/moe_grouped/grouped_service.py --base-service OLD_S32_R8_W1 --base-receipt OLD_SERVICE_RECEIPT --grouped GROUP_RESULT --grouped-receipt GROUP_RECEIPT --baseline FULL32_GUARD --compiled COMPILED --placement near_m --label shared --binding BIND --out NEW
~~~

binding需commit、grouped_service_sha256、closure_service_sha256（只读helper依赖）。manifest/summary/splice/witness冻结源码、所有源产物/receipt SHA、实际分组函数、完整库存和费用。witness沿用旧压缩loop/affine地址schema，新增engine_access叶含单operand/bytes/offset、BANK/BUS资源、FIFO和读写计数；独立接收从bytes重新推导。splice记录旧event身份/canonical SHA和唯一删除cut，不准拿旧whole-row suffix数值冒充新g数值。

所有事件保守串行，prefill也无batch；不称优化调度、真实时钟或PPA。新wide数据准备更详细，绝不能直接将新whole-row绝对slots与旧简化kernel当硬件进步比较；有效比较只在本批同g、同配方、同资源、同数值轨迹的两个驻留政策之间。label应逐byte零差。
