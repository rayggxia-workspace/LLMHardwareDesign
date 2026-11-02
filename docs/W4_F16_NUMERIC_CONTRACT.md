# F16：H8/I8 RMSNorm—SwiGLU—原S16残差整数合同

Issue151/PR152；研究输入febc042，native7078786。新`block_w4_f16_top`、独立参考与TB不改变旧F8/A8/叶宏。这里只定义明确的H8/I8整数profile，不授予完整F、全部模型量化质量、L4整体或物理资格。所有RTL仿真由根任务在服务器Verilator执行；本子包没有执行本地或远端RTL仿真。

## 输入与实际数值

17×128bit：beat0是完整8S16 Fin10 X；beat1..3实际canonical零；4..15为gate/up/down三份8×8 signedS8 Fin7权重，n-major8*n+k；beat16为可变8S16 Fin10 gamma，写S475。传输272B，有效X16+weights192+gamma16=224B，加48B padding。不能沿用旧F8的8S8 X或仅保留低64bit。

N固定RMS mode1/count8/epsilon_code1，src466/gamma475/dst474。独立参考精确计算：`sumsq=sum(x*x)`，`radicand=floor(sumsq*65536/8)+65536`，`root=floor(sqrt(radicand))`，`factor=floor(2^38/root)`；输出为`clipS16(RNE30(x*factor*gamma))`，Fin10。gamma可正、负、零或非unity，epsilon以raw平方码单位表达，不冒充未经换算的模型浮点epsilon。

N结果从S474读回，**完整S16**写S448作wide A，449..451仍为零。没有N→S8的RNE3、clip、低64打包或其他有损窄化。原X在S466独立保留，E7 shift0只做保真复制到467；最终E0为`clipS16(down+originalX)`，Fin10。

gate/up/down三投影均M A16 Fin10×B8 Fin7，scale_factor1/left0，op5参数0x107：rawFin17经RNE右7夹S16→Fin10；EXEC0x9885。M两个op5应答的四S32容器各取低16，跨half拼8元素。G使用fn0、gated1，数学SiLU(gate)及nativeRNE插值，乘up后RNE10、夹S16。done_saturated为N/M/G/E所有已观察阶段clip的OR，独立于done_error。

S464/465=gate/up，466=原X，467=残差，468=mid，469..471=实际零padding，472=down，473=final，474=norm，475=gamma。正常帧39普通S请求/ACK=29写+10读（17入口、运行12写/10读），M15cmd/rsp、3loader（全部Awide1）、N1服务/4native命令0,1,2,5、E2服务（identity+final）、G1服务/4pair accepted-retired、T1word并release后完成。

## 独立预期与覆盖

`f16_integer_reference.py`保留前轮独立数学N/G/E基础函数，新`f16()`直接构造本轮链，未读取新RTL输出作expected。G2564/EXP1025节点从math重建，只用native表逐节点检查版本一致。`check_f16_oracle.py`以Fraction独立核对RNE7/10/30，以二分root交叉Newton，并核对原X、可变gamma、raw M、存储字及明示30CASE合同。

10向量包括：非8倍S16 X、zero X配可变gamma、正负极值饱和、正负/零/非unity gamma、zero gamma保原始完整S16、稀疏布局、两组固定LCG随机、zero gamma保非8倍小残差。zero-gamma时down=0，输出必须逐位等于原X；例如`[11,19,-27,35,-43,51,-59,67]`输出`0043ffc50033ffd50023ffe50013000b`。这种路径不能被S8量化替代。当前全部向量均为本合同主动选择的可表示输入，不是浮点模型精度结论。

`block_w4_f16_tb.sv`自包含冻结literal functions，没有TB SVH include。它针对F16检查每阶段S448/464..475、17输入实际ACK、wide M输入、原X残差、39S/15M/3load/4N及T release；覆盖padding、早start/heldstart、重复、输入/输出背压、held DONE与abort同拍、prestart/running abort/reset及S/M/N/E/G故障恢复。S故障通过helper已定义响应error边界受控注入，原生S本身无error输出，不能声称新增S错误检测器。已接受的RAM写或已消费T前缀不能回滚。

CASE集合在`f16-tb-contract.json`独立预声明，marker严格为单行`PASS_W4_F16 cases=30`；额外计数在`F16_STATS`行。仅有限向量/故障场景，不写成所有数值/错误全覆盖。server runner还须结合源码/工具/输入SHA、退出码、完整CASE集合及无fatal/watchdog判断，不借旧F8/A8通过替代新F16执行。

## 复现与执行边界

从正式项目根运行脚本时，参考及生成器放`work/Melodydt/151/`，`build_f16_vectors.py --root <项目根> --directory <输出目录>`只读冻结native表、从脚本同目录取参考SHA，输出vectors；`build_f16_tb.py --directory <同输出目录>`从该vectors生成自包含TB/机器合同。无需读取旧task draft，也不要求预先复制参考脚本到输出目录。native include仍需`project/rtl/block_v2`，机器合同列全部compile_sources。

实际Python检查和管理检查已PASS；它们不是RTL仿真。根任务负责source commit、服务器Verilator运行/回执以及最终上传审查。原有源码与历史证据保持原范围，外存/MEM、跨岛接口、完整产品程序及物理接收均未由这个小切片完成。
