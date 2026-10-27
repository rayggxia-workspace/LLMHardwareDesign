# 原生预制接入线的有限修复

135完整接收失败、148定位通过后，实际133封存DEF显示部分M10端口接入线存在U形折返，A的read_data[43]在M9还有无其他锚点的树枝。C的begin_words[0]折返线与[1]仅0.07µm间距，原生规则要求0.8µm。原生TRACKS、077锁定pin与via9网格读回一致，当前证据不支持以网格失配解释这些标记。

固定上游OpenROAD提交[6556255的接入点实现](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/drt/src/pa/FlexPA_acc_point.cpp#L336)（文件Git blob `3448bacfa619416880c959b827624c7264817d8f`）中，VIAINPIN/VIA_ACCESS关闭平面接入的逻辑受`isStdCellTerm`条件约束。这是对端口仍可能有平面接入的源码解释；未证明安装二进制与该提交完全相同，也不以此代替实际路由证据。133已经完整使用这些参数，135仍检出间距，不能仅以参数已设置宣称via-only有效。

## 唯一确定性候选

`native_escape.py`只处理148实际命中的网络：一条固定BPin到一个现有via9的简单M10链。没有新增有源资源、改pin坐标、时序约束或搜索不同seed/偏移。

- 若M9已在BPin中心有现有树节点，将同一个via9移至该节点；保留到所有via8锚点的树路径，只去掉不再连接锚点的M9树枝与M10折返。
- 否则仅把M10链改为从pin横向、再到现有via9的确定性至多两段路径。M9/M10中心线总长均不得增加。
- M1–M8全部路径和via1–8、逻辑连接、实例、位置、PG、CTS、所有端口及其他网络必须保持。只支持明确的Manhattan路径语法；分支、多via9、额外延伸、环、未知矩形和上层cell锚点均拒绝。

这是**预制冻结之前**在独立副本上的修复。已封存133和135原始输出不改；未来两个定制产品仍只能改变M11/M12/via10/via11，不能在产品之间移动M9/M10或有源实例。

## 有限探针及资格边界

`native-escape-probe-group`在一个c96 allocation内并跑A/C，各2CPU，合计4CPU。原149填写16GiB申请，在提交前被既有`RealMemory=1`集群保护拒绝，没有dispatch-state/tasks/job；原部署不改，索引`run149-not-submitted`保留。150恢复既有`memory=0`整节点内存申请，未放宽dispatcher。运行时可用内存不足12GiB则顺序执行；独立失败不取消另一分支。本任务仍受6基础/8上限统一dispatcher限制，排队及未知提交计槽。

两路各绑定133完整源文件/回执、135失败全门结果、148零遗漏定位和077固定pin的SHA。OpenROAD先导出源DEF/Verilog/实际形状，副本仅替换计划中的wire，再严格读回全部网络及NETS之外字节、完整逻辑网表、未改网络实际形状和M1–M8形状。检查选中网络全部wire/库terminal的矩形连通，及对所有其他网（含PG）的M9/M10/via9重叠、接触和基础间距。真实去via9 cut、插入异网短路控制须被拒。

实际上下层mask另写独立GDS，读回XOR必须为零。原安装完整deck SHA为`4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`。探针建立明确标注的M9/via9/M10诊断子集，保留这些原生规则正文；先在源实际mask复现135同样18/2个分类标记，再要求修改后的上层诊断为零。它不替换、不修改正式完整接收器或完整规则。

语法、树锚点、DEF范围、missing-cut、异网短路/边接触的声明合成控制可本地运行：

```powershell
python project/experiments/block_v1/native_escape_control.py NEW_CONTROL.json
```

输出必须不存在。`escape-controls-149.json`保留早期控制，含边接触新增控制的复跑另写`escape-controls-149b.json`。这些是合成控制，不能证明实际OpenROAD编辑成功。

## 150实际失败与151修正

150/92236实际A/C两路均失败，1:14、TotalCPU2:09.030、MaxRSS1326488KiB；严格读回发现修改网没有ROUTED记录，未进入几何/DRC门槛。原OpenROAD命令虽然返回0，不能以退出码充当编辑成功。失败组/两子及原输出哈希保留于`run150-group-terminal`、`run150a-terminal`和`run150c-terminal`，不覆盖。

固定上游[definReader.cpp 1967行](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/odb/src/defin/definReader.cpp#L1967)（Git blob `a8044b54be76e89052244c5f94d58492122dbca6`）仅在DEFAULT/FLOORPLAN等模式注册NETS回调，INCREMENTAL没有NETS回调；这与150实际忽略patch路由一致。[definNet.cpp](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/odb/src/defin/definNet.cpp#L54)（blob `22fb6bc7d134431f30aec144b0eb3f1d8d2bbcde`）会在读取既有网络时替换该网wire。

151只修正导入方式为`read_def -floorplan_initialize`，patch仍只列既有命中网络，没有COMPONENTS/PINS/PG/DIE/TRACKS等段；不再预先删除wire。所有原网络/范围/实际几何读回门槛保留；必须实际验证该安装版行为，不能仅凭上游源码宣称成功。151本源码提交时尚未部署/执行；同一4CPU/整节点内存allocation内A/C各2CPU，仍作12GiB内存预检。

151/92237实际1:14、TotalCPU2:09.700、MaxRSS1322996KiB，两路已导入10/1个网络，但严格header字节顺序检查失败。实际DEF显示`revoke_valid`、`begin_words[0]`等网络的hold与diode端点顺序交换，网络/端点名字一致；没有据此跳过连接证明，原失败保留于`run151-group-terminal`及A/C子索引。

152将header检查改为严格解析网络名、完整无重复端点集合和USE种类，唯一忽略端点序列化顺序；额外属性与未知语法仍拒绝，其他所有DEF范围/路径检查及完整Verilog字节相等保持。`escape-controls-152.json`实际本地通过端点换序正例，以及错cell/错pin/缺端点/多端点/改USE/额外属性六类新增反例。该修正只处理序列化等价，不改变物理候选、pin、规则或资源；152在本源码提交时尚未部署/执行。

## 152实际失败与153固定via候选

152/92239实际FAILED/1:19、TotalCPU2:19.502、MaxRSS1324944KiB。A/C均通过严格网络/路径/NETS外范围、完整Verilog字节、其他网络及M1–M8实际形状读回；进入诊断DRC后，源合并mask仅报A6/C1条，而135完整GDS报18/2，原计数一致检查拒绝。A修改后的诊断仍有3条VIA9.2（880nm spacing），对应把via9移到pin中心；C修改后的诊断为0，但不能据此接收任何完整资格。绑定回执/报告/网表/plan的实际失败诊断见`native-escape-152-diagnosis.json`，完整失败索引保留。

153有两项明确修正，均需实际验证：

1. **所有via的身份和原坐标完全保持**。M9若有pin根，只保留根至所有via8的树，再从保留树中离原via9最近的投影点接一条确定性至多两段M9线；M10仍是固定pin到同一个原via9的确定性L。没有移动cut、参数或偏移试探。13条真实源记录的本地dry-run为A改8/不改3、C改1/不改1；长度不增，via逐项身份/坐标断言通过。新声明合成控制保存于`escape-controls-153.json`。
2. 用135原完整GDS的M9/via9/M10 union与实际ODB导出的before mask做精确XOR，要求零差异、DBU可精确整数换算；源标记复现则直接在135**原完整未合并GDS**上运行相同上层规则正文，仍要求18/2及原分类完全一致。报告条数受分离/合并影响，不能仅用合并mask的计数替代这一门槛。after继续要求实际修改mask诊断0，异网短路/边接触由逐网实际几何检查补充。

153本源码提交时尚未部署/执行。probe会在完整诊断JSON中保存源标记复现是否通过，再统一断言所有门槛；失败报告不会因最先的计数断言而缺少其他诊断。完整GDS/全规则、重新提取寄生/STA及功能仍必需。

153/92241实际FAILED/1:20、TotalCPU2:21.279、MaxRSS1322944KiB：原生GDS的DBU为0.0001µm，探针为0.0005µm，单向整数放大检查拒绝0.2比例，未进入XOR/DRC。实际原GDS UNITS二进制记录也读回0.0001µm（1e-10m）；这不是物理候选通过或失败的结论，失败索引保留。154仅把两份mask均整数放大到共同细网格，本例原GDS×1、探针×5，在0.0001µm做XOR，禁止坐标舍入或非整数缩放；物理候选和所有门槛不变，实际154尚未运行。

## 154实际通过与155/156完整后继

154/92243实际COMPLETED/1:43、TotalCPU3:01.781、MaxRSS1897412KiB，一个c96 node22/4CPU allocation内A/C各2CPU并行。两路各10项检查均通过：完整原GDS18/2及分类准确复现，ODB/原GDS上层mask精确XOR为0，修改后原生上层诊断0，全部连接/范围/低层/网表一致性、missing-cut及异网短路控制通过。A只修改8网、C只修改1网；全部via原坐标/身份不变。源e1beb5821428bf57e8cbe02e06a6260f161cb22c、归档4c2b48a868c38970690e16322ee4f490611e6b51966a09c8e21a6e0cd92dc4d9（162成员/1095680字节），组与两子终态索引保留。**这只是有限几何探针通过，完整物理/新寄生/功能/宏资格均未通过。**

155的`native-escape-finish-group`将在同一32CPU allocation内A/C各16CPU，从154实际accepted edited.odb运行安装原生`do-6_report`，重新写最终ODB/DEF/Verilog/SDC、LEC与SPEF；不再次插fill、placement/CTS/route或优化。原生最终输出脚本SHA `b56f8584f32520191869a7f6da061843b27d1cf574176902c281c7f11a159168`内含真实RCX命令，不复制133旧SPEF。全部实际flow脚本/Makefile SHA、原输入/保护、原工具/预算继续绑定。

固定上游[原生check_drc入口](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/drt/src/TritonRoute.tcl#L494)和[全片实现](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/drt/src/TritonRoute.cpp#L1248)说明零面积默认box检查整个Block。155必须在实际安装版读回该命令body/默认box、调用新最终ODB的全片检查并要求报告0；检查前后DEF字节相同。再次要求最终全部NETS/NETS外与154接受副本完全一致，全部物理Verilog及原约束SDC字节不变。不复制旧DRT报告，不以旧源DRT0冒充修改后检查。

156的`native-escape-qualification-group`仅在155完整成功后启动；同一32CPU allocation内A/C独立物理与A/C实际最终功能四路各8CPU。物理接收器仍运行原完整GDS/deck、全部端点STA/电气、PG/连接/LEC/RC覆盖/面积/pin/驱动与原生DRC门；功能仍是最终全部实际信号单元/真实RAM的三初态242事务接收。每路32GiB估计加20%余量，按实际可用内存选4/2/1路；producer选2/1路。失败不取消独立peer，所有门槛保留。新pipeline为`native_pipeline_escape.json`，正式宏视图还需后继绑定，不复用147失败来源。

155/156在本源码提交时**尚未部署/执行**。宏边界、C8完整组合/恢复epoch、父层物理、一般多网节点分布十二层RC/拼接/窗口、共同冻结与两产品/敏感性/参数库仍需继续完成。

即使149探针通过，仍须从修改后的真实ODB重新生成完整原生GDS、寄生、SDC与网表，并重跑完整DRC、全部端点STA/电气、PG/连接/LEC和实际最终功能；不能复用133旧SPEF充当新路由寄生。正式同源宏视图、flat/abstract边界、父层glue、完整恢复/epoch、一般多网分布十二层RC与原生/新层拼接、共同冻结父层、两产品和敏感性仍是独立门槛。探针的四个完整资格标志保持false。

## 155实际API失败与157/158后继

155/92248实际FAILED，8:05、TotalCPU19:39.463、MaxRSS41807612KiB。A/C原生do-6_report完成，但新OpenROAD进程发现安装版没有公开`check_drc` Tcl命令；原native-final-check.log及全部失败索引保留，不能把新最终文件或RCX产生视为完整接收成功。156已读回空dispatch-state/tasks、没有Slurm作业，依赖155失败停用，不修改原不可变部署。

实际容器二进制`/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad`的只读字符串检查确认存在编译命令`drt::check_drc_cmd drc_file x1 y1 x2 y2 marker_name`及其SWIG包装；镜像没有对应源文件。上游零box全片语义仍只是固定源码依据，实际安装入口必须由运行证据验证。157在昂贵do-6_report前先检查实际命令存在，并以无参数调用保留运行时完整六参数usage；新最终ODB调用`drt::check_drc_cmd native-router-drc.rpt 0 0 0 0 native_escape_drc`，使用与上游公开wrapper相同的编译入口和全片box，报告必须零，检查前后完整DEF字节相同，所有原几何/网表/约束/新RC/独立接收门保持。不会把缺失命令当作空报告，不复制旧DRT报告。

157生产者仍32CPU allocation内两路16CPU，158资格仍32CPU内四路8CPU并行，按实际内存限制并发。158依赖157完整成功；本源码提交时157/158均尚未部署/执行。实际运行若入口、签名或任何资格失败均保留失败并继续处理，不放宽检查。

## 157实际全片短接与159有限预制修复

157/92253实际FAILED/8:50、TotalCPU34:56.338、MaxRSS41813472KiB。安装版运行时命令表实际包含`::drt::check_drc`及`::drt::check_drc_cmd`，全局`check_drc`缺失；底层六参数调用实际执行整个2240000×2240000 DBU Block。新最终DEF全部NETS/NETS外、完整物理Verilog、原SDC和检查前后DEF均相同，随后零DRC门拒绝A4/C1条。A为write_data[54]/[55]的M9/M10 Short及via9 Cut Short，还有read_data[77]/[78]的M10 Short；C为word_count[1]/[2]的M10 Short。这些网络在154未修改，其几何本来就存在于133，不以旧route阶段报告0覆盖新全片发现。158无job、空state，因157失败停用。原报告/日志/回执SHA和完整DEF命中网/pin分别在157-diagnosis、157-routes及组/两子terminal索引保留；初次诊断的空routes字段由另一个明确按缩进解析的routes文件补充，未覆盖原文件。

原独立GDS间距检查不能识别合并mask内部不同网络的短接。159继续使用133不可变源及135原完整GDS18/2复现、全mask精确XOR、全部原几何/连接/DRC门，并额外绑定157真实失败回执/报告的全部短接网络。read_data/word_count命中折返沿用固定via的最短L；A的write_data[54]/[55]不能保持重叠via9，故只对这两网使用显式新函数，其他全部via及所有M1–M8路径严格逐项相同。

唯一预定落点：write_data[54]的via9到(3390,1961900) DBU，即其原pin上方160 DBU；write_data[55]的via9到其原pin(3390,1968140)。前者与实际write_data[53]原via9中心1958540相隔3360 DBU，等于原1600 DBU cut宽+1760 DBU间距；后者使原write_data[54]未移动via8在M9上的包围与新via9保持1600 DBU金属间距。两网原via8身份/坐标与所有下层保持，新增M9回接、M10接原pin，M9+M10总中心线长度不增。没有扫描种子/偏移或移动pin；这些推导只是候选，所有实际规则、全片检查、重新RC/STA及功能仍需通过。

新增`upper_shorts`按x方向活动集合检查**所有**实际M9/M10/via9导体含PG、端口和未修改网；不仅检查选中网。原完整上层短接pair必须准确复现157三对/A2+C1，after必须全为零。逐网完整连接、原全部GDS复现、实际修改scope、原子网表字节、missing-cut/跨网短接反例及原生规则保持。控制以实际失败DEF验证两有限重定位和低层保持，并实际拒绝缺via8/额外via9；全局审计的边接触/跨层cut及隔层无cut正例通过。这些声明控制不能替代159实际EDA。

159仍一个c96 allocation内两路2CPU；后继160原生新最终输出两路16CPU及161四路8CPU完整资格必须依次以实际成功为依赖。本源码提交时159/160/161均未部署/执行。全部共同冻结、宏边界、父层物理、一般多网分布十二层RC/拼接/窗口和两产品/敏感性/参数库目标保持。

## 159实际通过与C8全片原生门补充

159/92258实际COMPLETED/1:49、TotalCPU3:09.295、MaxRSS1350256KiB。A/C各12检查全部通过：原18/2间距/分类与完整upper mask XOR保持，原实际A两对/C一对跨网短接准确复现，修改后全部上层3087/2919形状和386/389网络的跨网短接0，上层原生规则诊断0。A改11网/C改3网，只有A的write_data[54]/[55] via9按预定落点调整，全部其他via/所有M1–M8/固定pin/完整逻辑网表保持。源8b62c2cf21f4d1b44e9a1f18e44713e0a73bec4d、归档1c867426a518e0016d9fcfb85850acf55e062539564c33b04b80404af9fd0720（166成员/1126400字节）。组和A/C终态索引保留；四项完整资格标志仍false。

160/92259两路16CPU已启动；161完整物理/最终功能四8CPU组已不可变部署，空state无job，等待160完整实际成功。不能把159的12门扩展为完整物理/宏资格。

128 C8 A/C原生全流程虽成功，旧route阶段的native DRT报告仍不能替代对最终ODB的新全片检查，157已给出反例。因此新增162独立只读C8最终全片DRC门，直接绑定128 A/C成功回执与最终ODB SHA，同一16CPU allocation内两路各8CPU调用实际编译入口的零box全片检查；检查前后DEF必须字节相同，源SHA必须不变，新报告必须空。失败先写分类/完整报告与proof再断言，独立peer继续。它补充134完整物理与141完整组合，不能替代任何一门。按128实际最大约177GiB，预算每路200GiB+20%余量，可用内存不足480GiB时串行，峰值用核不超16。162在本源码提交时尚未部署/运行；下一次冻结与宏视图必须显式包含此新门。
