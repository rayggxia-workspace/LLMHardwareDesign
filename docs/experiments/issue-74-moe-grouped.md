# Issue74完整MoE与分组边界（进行中）

负责人Liangruizhi；[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)/[PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75)，task/74-moe-grouped，base PR73@88e9c4b。全部真实模型/张量/数值/服务本人服务器新issue74-moe-grouped-20261024、Slurm lrz-i74-*；PC只源码/微合成/metadata和字节接收。协议project/experiments/moe_grouped/PROTOCOL.md在执行前冻结；源commit/SHA及实际command在work74。

## 已执行与已核结果

Granite层0/13新真实post-A residual、norm、全部40专家weights/选中8expert中间值及后继norm采集90284完成；两文本与72model64原参考LM/router/norm/MoE/hidden/真实残差join均逐码0差，IDs一致。仍是部分框架算子FP32 cast的model64条件参考，不是全FP64、原生INT8或整模型质量。旧native32 FAIL原样保留。

实际完整整数链已执行8条件（2层×R8/R16×cal/eval72），并90297–90304全量独立数学/边界/真实SHA重写负例接收PASS。起点真实residual I32Q12→完整RMSNorm→实际router/top8/Q15→全部8expert完整gate/up/SiLU/门乘/down→共同Q12宽weightedmerge/RNE→0.22 Q20残差→后继完整norm。Attention/更后层边界外，编译/最终诊断FP与整数runtime分开。评价层0 R8/R16 native route改变15/0，层13为3/0；R16同当前integer-norm FP64 router层13仍1差，不能把与原native吻合说成所有router算术精确。

R16评价MoE局部L2层0约7.712%/层13约7.731%，nextnorm约8.629%/1.020%。不同层残差/归一化会放大或衰减误差，不跨层直接比较质量；没有整模型质量门。路由改善没有消除专家路径误差。下一步只用原8产物做matched-ID mid/量化/舍入分解，不先调格式或追加样本。

实际三种group各184,320个RQ产品，以S8 signed-high digit和显式8/16字节carry重组全量逐码通过，共552,960产品。证明core32×32为25 S8积+24次8字节加法/控制，64×32为45积+44次16字节加法/控制；operand抽取、shift构造/RNE/传输另计，不把software时间当target速度或声称RTL。

## 进行中的匹配服务

已冻结新版服务源码phase6，90306完成K256/near_M首例，仅待独立资源/单位/完整消费者接收；旧90305费用较粗版本保留调试，不入正式排名。三函数分别同精度比较M/V驻留，守恒M256/VR8/全部SRAM/ROM/1RW/BUS/FIFO，不新增M私有宽ALU。所有宽乘提取/构造/重组/RNE、I64对齐、元数据、packets/缓冲均计价；engine_wire是total_wire子类，不能相加。M22720/V9600/R32768、EXT85293632/ROM4260100首例合法，不等于全模型同时部署。

本批改变了RQ微费用、Ktile与BUS显式接口，不能把较旧whole-row日历多出的slots全部归因分组，必须与本批同g的配对及共同g0控制比较。完整input/R/gatednorm前缀和MuP/join/nextnorm后缀逐段canonical继承并源绑定，suffix数值改用对应新g已验代码，不引用旧whole输出值。

## 真实状态与未完成

新代码23项小检查及管理结构曾通过；更多接收/服务源码更新后最终记录检查。8条件数学通过不等于hardware/modelquality。全12服务、事后归因、完整/精选归档/索引、最终报告/划分方案/决策/交接正在推进，尚未写完成。

本人身份/最新Issue/PR与成员55/63已核，无重复工作/新模型/其他机器/Phi解封。登记PR5 pending，无board.json/Projects能力，看板unverified/同步pending，管理员/审查人待指定；当前in_progress/draft，不合并/done。
