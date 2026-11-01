# W4 源码与根执行证据交叉审阅

以下是另一作者源码及真实日志的交叉核验，不是外部PR批准。

# W4 F8 独立源码检查与真实运行证据读回

研究输入 `0101cc7e1e6d5718455fb45b61c7428439efc09a`，native `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本审阅者实现了N控制器，因此不把对自身N源码的核对描述为外部独立批准；另一作者的 `block_w4_f8_top.sv` 已做独立静态交叉检查。随后只读核对root实际执行的 `runs/n-r01`、`runs/f8-r01`。本审阅者没有执行这些仿真，没有修改FFN顶层/TB/native，也没有批准PR。

结论：所读源码及本次有限真实测试证据未发现阻断性问题。N控制器和F8顶层当前草稿与两次运行快照字节一致；回执/log SHA、compile/simulation退出码及CASE_PASS数量已核对，详情见配套JSON。

## F8接口、数值与生存期

| 检查对象 | 结论与源码锚点（本次F8快照） |
| --- | --- |
| N调用 | L172–186连接独立真实N与controller，固定RMS8/mode1/epsilon1，src466、gamma475、dst474，exp0未用；三个一字used区域不相交 |
| 原始X与gamma | L303–304：先保存原x S16到466并消费写ACK，再实际写gamma475={8×1024}并消费ACK，才把owner交给N。N全服务保持owner3，源/gamma无其它写入或交错N命令 |
| N结果完成门 | L320–323只在N服务rsp消费后切回LOCAL；Nctrl最后dst474写ACK已被消费，helper此时已空闲，再发本地474读，未提前换owner |
| 数值窄化 | L121–137是真实新增的8lane S16→S8 RNE3/clip逻辑：floor算术移位、余数与保留位奇偶形成正负tie-even，clip到[-128,127]。低64打包，上64清零；不是E12别名或裸截位 |
| 投影输入 | L305–309读474后生成规范化Fin7窄字，实际写448并收ACK，才进入后续计算。449..451仍来自本帧实际canonical-zero写，M loader不依赖reset清RAM |
| 残差 | E7仍按原W3固定接口读取466原始x Fin7并左移3到467 Fin10；投影使用已经覆盖448的Norm结果，残差没有误用Norm输出 |
| M/G/E后续 | gate/up仍M S8×S8→op5 S16/RNE4，G SiLU gated，down A16/B8→op5 RNE7，最终E0+原残差；M的compact槽位提取与单M复用沿已验收W3固定路径 |
| 普通S owner | L142–160给LOCAL/E/G/N真实MUX与对称ready/valid门控；lease保持到各服务rsp消费，最后helper应答已先消费，无两个普通native驱动者 |
| 错误poison恢复 | Nctrl发生runtime mem/native error时poison；F8 L320–322消费error后调用fail_job，L264–268顺序置internal_reset，下一沿协调reset N/Nctrl/helper/其它leaf，未在未清poison上下文上偷偷发新BEGIN |
| abort/DONE/组合环 | leaf_reset L90仅来自reset/abort/寄存internal_reset；没有rsp_error-ready组合反馈。已有DONE遇abort保留结果且ready可同拍消费；hard reset取消valid不造completion，源/输出已写部分不回滚 |

正常完整帧普通S事务为39=29写+10读：原W3 32=26写6读，新增gamma475写1、N服务4（3读1写）、本地读474一次、写规范化A448一次，总增7。含入口16写后，RUN为23笔=13写10读。15个M命令/应答、3个loader与原W3相同，另有1个N服务/4个native N命令与应答。最终S473→T一字→实际TAKE→RELEASE后才成功DONE。

## 真实回执与TB可支撑的结论

root使用本地ModelSim SE-64 2020.4；两个suite的compile/simulation exit均0，实际log的SHA全部匹配receipt。N log为 `PASS_W4_N cases=29 cycles=20336`，F8为 `PASS_W4_F8_FFN8 cases=25 cycles=16323`；CASE_PASS逐项/顺序与receipt一致。命令argv/cwd、工具版本与SHA、输入来源/快照/SHA、时间、原始stdout和log SHA均保留在run-receipt。新W4源运行时未提交，以逐文件字节SHA绑定；707仅表示原生叶源，最终交付commit应另记。

N suite包含11个独立数值向量：RMS count1/8/257，L2 count8/257，Softmax count1/8/9/257。包括正负gamma/饱和、零输入、尾部脏lane mask、257最后一项新max、EXP code32768无符号回放、截断区域与舍入。TB逐命令检查BEGIN/STATS/finalize/replay顺序、count/tail和raw-vs-EXP/gamma载荷，逐S请求检查读取/写入顺序及独立期望，成功逐字检查目标和EXP存储。

N另有4个命令/响应/ACK/helper背压例、8个准入拒绝例、一次本地拒绝后成功复用，以及native非法op、mem读错误、第二个dst写ACK错误后的poison/reset和两个中途reset例。第二个写ACK错误测试核对两个已接受目标字仍可见、第三字保持poison，明确支持部分写不可回滚；该mem_error是TB注入，当前真实S helper普通口固定error0，不能称新增存储故障检测。runtime error rsp被消费后req_ready0/busy1，协调reset恢复由N suite直接检查。

F8 suite含6个冻结整数参考输入及W3式流程/恢复，成功帧逐阶段核对S464..475、规范化A448和最终字；检查39/39普通S、29写10读、4/4 N命令/应答、1个N服务，以及15/15 M、3loader、T释放。N相关新增case在TB L487–500：

- 保留N服务response时，474 ACK已经完成，但A窄化/首条M命令尚未发生。
- 强制真实native N非法op15后，无474结果、无A窄化、无M投影/T写；顶层协调reset后新帧成功。
- hard reset丢弃保留N service response后新帧恢复。
- 暂停N destination474真实ACK，确认没有提前投影，再abort并恢复新帧。

两组suite累计req/ACK及cmd/rsp差额包含明确reset/abort取消，不能把全suite计数当无条件守恒。29/25是有限检查标记，不是完整模型任务或参数空间覆盖率。

## 未证明及审查边界

N服务支持本次1..257和disjoint存储profile；测试只覆盖上述指定count/输入/epsilon/gamma，不是任意count×数据×地址的穷举、随机或形式活性证明。overlap/in-place/更长group仍为实现能力缺口，不改算法语义合法性。

F8只集成RMS8前归一化，未在F8内测试L2/Softmax，也没有完整Attention、后归一化、样本H/I规模或所有完整F变体。RNE3/clipS8是此小核明确的新数值选择，Norm值可能因S8 Fin7范围发生clip，done_saturated需要累计；有限参考一致不证明模型质量。原始残差与Norm投影输入分离是本次已实现边界，不能省略。

没有外存/MEM/NUM通用服务、CDC、完整多岛调度、物理P&R或M11/M12永久产品绑定资格。N本轮增加的是所列真实功能路径，R/legacy等编译纳入不转移功能/物理资格。作者交叉检查、root仿真、文件上传、外部PR批准、合并及整体任务验收必须分别报告。


---

# Ncontroller独立静态交叉审阅

审阅另一作者`drafts/nctrl/block_w4_n_ctrl.sv`，SHA`02e6e8f0538c8423481c2f30a3d0a2d392bae583551cbf7ffcc7cd947674cd01`，研究父提交`0101cc7e1e6d5718455fb45b61c7428439efc09a`。没有修改该文件或自行运行仿真。当前源码在W4的1..257项有限group合同内未发现静态阻断；以下是源码推导，不是RTL执行证明。

- 行42–68用17bit扩展做ceil(count/8)、末地址及区域相离检查；有效group最大33字，6bit words/index足够。norm仅检查src/gamma/dst，Softmax检查src/EXP/dst，未使用地址不错误加入限制。非法mode/count/epsilon/range/overlap在BEGIN前返回错误，不改变N且不poison；这是当前服务profile限制，不能当作算法永久禁止in-place。
- 行125–132仅在请求接受时锁存mode/count/epsilon/各基址。行87–100的native/mem输出来自锁存字段，状态停顿期间payload保持。每次S响应在MEM_RSP接受后才转入下一次读；并未持有S响应同时发第二读。
- 行135–171先BEGIN、全部原始STATS并消费ACK、FINALIZE；norm按原值重读和gamma读形成op5，输出mask后写回。最后chunk_count为真实1..8，source/gamma及结果尾部均清零。F8的一字RMS路径恰为4个N命令/应答、3次S读和1次S写ACK。
- 行145–175的Softmax按raw重读→op3→EXP写ACK推进；所有EXP落存后才op4，之后重读EXP原样送op6。EXP的32768保留为U16位模式，mask函数不作S16算术转换；不能将原始score直接重放到op6。
- 行176–183只在最后目的写ACK接受后给完成response；此前的部分EXP/dst写可能已经发生。response保持error/sat直到rsp_ready，caller必须持续保有整个S owner及source/gamma版本，不能把每个native ACK当group完成。
- 行81–86、111–112、135–160中，native或mem运行错误置poison，response消费后req_ready仍低、busy仍高，必须协调controller/native/helper复位。单独BEGIN无法绕过poison。BEGIN前local拒绝不poison；成功group的下一次请求可用新BEGIN清Ngroup。F8 top的internal_reset同时清三者，符合这个合同。
- saturation只OR已退休的N响应；错误不提供回滚。特别是WRITE_EXP/WRITE_DST应答报错前写请求已接受，已写数据可能保留。真实Shelper的error恒0，但通用mem接口仍不能把所有error解释为未写入。reset也不回滚数据，输出group只能在成功完成后发布。

## 实际执行证据读回

根任务已实际执行本地ModelSim SE-64 2020.4：`runs/n-r01`编译/仿真exit0，29个唯一CASE、20336周期；`runs/f8-r01`编译/仿真exit0，25个唯一CASE、16323周期。本审阅者读取原始receipt/log/TB快照、核对CASE及输入SHA，没有自行启动这些仿真。Ncontroller上述SHA和F8 top SHA`54905280f8b9dbfcd7440981fd4f4244c509ea8de5e1a8912a050c457ad75a8e`在draft、正式checkout和两次run source快照全部相同。F8是本审阅者所写，其证据读回只核对版本和范围，不作为独立批准自己的RTL；独立源码审阅对象仍为另一作者的Ncontroller。机器记录含54个CASE与11项审阅结论的对应关系，非外部PR批准。

N suite实际检查RMS/L2/Softmax共11个数值场景，含1/8/9/257项及tail、raw epsilon/gamma、signed gamma与clip、最后新最大score、相等score输出EXP32768、截断边界；原值/EXP/gamma和命令/存储阶段顺序逐次比对独立literal。成功group检查全部EXP存ACK后才factor、重放精确U16 EXP、最后目的写ACK后才response，且正常group命令/应答/读写数目守恒。29项还包括参数接受后变更、native/mem/response背压、八类guard无BEGIN/S副作用、本地拒绝后复用、运行error poison后无法复用及协调reset恢复。

晚到写应答错误用例实际先接受并保存两个目的字，然后在第二个逻辑写应答注入error：TB确认400/401为已计算结果、402仍为poison，service error、req_ready低/busy高保持到协调reset。该错误是逻辑mem应答的合成注入，真实Shelper的error仍恒0；它证明代码不能回滚已接受prefix，而不是声称native S产生错误。pending EXP写ACK及held native response的协调reset后都实际完成新group。

F8 suite另外确认39笔S/29写10读、N4/M15/loader3/E2/G1/T1、N474真实ACK后才service response、原x残差与norm窄化分离、窄化clip累计、N错误禁止进入M投影及协调恢复。两套suite全程累计差额包含显式reset/abort，不能用作全局守恒；正常group/frame各有独立守恒断言。

N回执SHA`e2abfd4d095d135f0ee3270f4c81504b9c06cc7f19aa42ad1057983c67cb7bc2`，N仿真log SHA`fc67d7061843a530dc97a579b12227bd72819c17d04732bc73772b05de6cf162`；F8回执SHA`39cf9fd1a263749ada7450c71a7924e029aa26966ca2523d2f5a86e38c6a29fb`，F8仿真log SHA`0dad4670616f90fb596bffef0eb06df996c3f9a410c6832e407539552f2c03b0`。全部编译/日志SHA在JSON保存。

当前未发现该有界合同内的开放RTL阻断。范围仍是实际mode/count/value与有限stall/error场景，不宣称全部N opcode、统计诊断/TopK、所有位模式或所有时序交错；14native文件全量语法编译不等于14份功能通过。完整F/A、真实模型量化质量、大shape、MEM、整片母控/M11/M12和物理验收均不由这54项自动闭合。
