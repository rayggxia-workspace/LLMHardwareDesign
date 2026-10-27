# 两导体科学几何与真实OpenDB布线绑定

关联Issue121 / PR122，2026-10-27 CST。承接180已实际通过的科学节点电容组装和原生读回，补上其锚点ODB没有wire/via的来源缺口。完整Block、生产via、一般分布提取及原生/新增层拼接仍是单独必需门。

## 接收合同

1. 只读绑定180两路receipt、measured-joint-rc.json及原始科学helper SHA。坐标和node ID逐项一致后才创建明确编码的branch/via资格布线，不宣称自动详细路由器生成。
2. 使用原009封存十二层技术overlay，真实LEF/DEF导入后写ODB/DEF，再以现有odb_geometry.tcl只读导出wire、via金属/切孔和全部实例pin。OBS不当作导体，绝不只核对主线。
3. 以2000单位/um将xyz坐标变成整数，按两份几何全部边界压缩为三维体元，逐net核对每个体元的导体占用。不同矩形分区但同一实体可接受；相同bbox或总体积不能替代逐体元比较。算法显式上限200000体元，超出范围拒绝。
4. 几何实体和物理node坐标完全相同后，才复用已独立科学接收的场测量。六种SPEF分别原生导入真实routed ODB，逐节点ground、R边及耦合节点对精确读回；导入前后所有导体TSV必须逐字相同。保留received.odb及全部源SHA。
5. via科学小例是命名CAPTURE_via10的0.8um cut、0.5ohm显式假设，无生产enclosure。它并非BV1_via10的0.6um cut/0.1um enclosure/0.888889ohm候选，禁止作为生产via DRC或RC资格。

本地纯几何控制实际通过：两份重新分区正例，以及位移、额外金属、缺金属、net交换和缺via共九个破坏控制。182实际OpenDB资格测试准备，尚未执行；不存在从纯控制推断原生通过。

资源沿用96CPU节点队列、默认16CPU/项，两个真实独立科学fixture各六个单线程原生变体按就绪并行。只有两份已合格科学输入时，不为填核新增无研究目的场景；结束立即释放节点。4GiB/项是暂定预算，180短采样不作为精确峰值或上界。本任务现有七allocation，计划182是第八个，其他成员不计入且未操作。

可复查输入/配置：work/YUZE-LU/121/node-queue-182.json、joint-routed-controls-182.json。代码joint_routed.py与joint_routed_geometry.py。原生LEF/DEF/ODB工具参考：https://openroad.readthedocs.io/en/latest/main/src/odb/README.html 。实际安装版本仍以执行receipt与命令日志为准。
