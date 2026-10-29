# Issue #55：完整案例集成阶段记录

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，负责人huangpingyang04-lgtm；分支task/55-full-block-integration；[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)仅阶段一已上传，远端head09f1876dd8eaaf0cb77005a4c094527d9ed5d9b0，未合并。当前没有冻结底座；主要布局候选1/3。

唯一服务器根目录（以下相对证据从此开始）：
/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

## 范围、输入和阶段判定

完整openTPU small目标为otpu_asic_top，保留全部33个原内部SRAM；完整llaccel_core锁定EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，16个外部SRAM bank、DRAM和主机参与功能测试但不计core物理面积。采用ACT/MXU/GEMM/VECTOR及两个完整案例辅助资源的并集；闲置不意味着面积节省、免费门控或断电。ACT+MXU合并版仅为对照，不重复计入。

主方案M1–M8固定、M9/M10及实际via8_0（M8↔M9）、via9（M9↔M10）定制。M11/M12后备未启动。原始设计、工艺、其他成员工作树和历史结果均只读。原RTL版本f237dab2f196855a59a083b1454786df8f01291f、f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5；按实际使用文件SHA绑定，不宣称整仓库干净。ACT/MXU采用团队Issue15更新版本，GEMM/VECTOR沿Issue7来源，未混用HTML旧快照。

| 阶段 | 当前实际状态 | 未完成事项 |
| --- | --- | --- |
| 一：清单/原始基准 | pass_with_inherited_issues，已交付 | 保留原VECTOR时序/电容和研究模型限制 |
| 二：完整分区/集成 | 未验收；有限物理网表回归、状态锥及辅助视图通过 | 最终物理回装、辅助新时序问题；组合/极值和适用复位边界仍有限 |
| 三：迁线/共同底座 | fail；共同宏布局和供电原型已实际通过各自几何检查 | 新增/恶化违例、6/6新时钟slew违例、复位时序、预连线/活动加闲置、冻结 |
| 四：两完整案例定制 | 未执行 | 同冻结底座的最终M9/M10布线、回装、寄生/STA与独立终检 |

未执行不能记为通过；工具测量完成不等于时序满足。新引入或恶化问题不能归为继承。两态零延迟有限测试不等于源RTL全输入形式证明、SDF、多corner或制造签核。

## 阶段一：完整清单与原始基准

两完整顶层、实际参数/文件表、21项源码归属前沿、全部叶/状态/内存归属及四核心原生库存/端点一致性核查已完成。证据为inputs/rtl_inventory.json、inputs/baseline_evidence.json、deliverables/coverage_map.csv、runs/catalog-01/{input_manifest,block_catalog}.json和hierarchy-*/partition-*收据；原始大型数据只保留服务器索引。

原完整open观察器20例及87160行trace、全部256KiB输出核对通过；含DMA/VPU、QUANT/MXU/VPU、rinit与预期WAIT超时。原llaccel补seed0/2各30次连续任务并复用seed1有效证据。open前端临时反馈清理的删除/保留状态有限归因89968保留：442项原图无输出路径、1项受限二态常量化后无路径、6项保留状态表达式一致；不当作源RTL完整形式等价。

| 核心 | 原边长μm | 原实例 | 信号位 | 原高层占用 |
| --- | ---: | ---: | ---: | --- |
| ACT | 326.205 | 16178 | 860 | M9：69网 |
| MXU | 1100.455 | 441518 | 2172 | M9：11网 |
| GEMM | 1157.32 | 571780 | 3753 | M9：47网，M10：3网，存在同网不直接相加 |
| VECTOR | 1148.52 | 733546 | 2246 | M9：40网 |

输入ACT/MXU/GEMM已有预算内setup/hold；VECTOR输入setup WNS=-4.16659ns、电容59项违例。它们不豁免迁线/新集成产生的问题。位宽不当作有效吞吐。

## 阶段二：完整分区与实际物理DUT回归

完整分区保持全部原叶/状态/存储/parent连接，原mem对象只允许唯一自包含MEMID随层次改名。resource-union-01覆盖六资源及全部逐位映射。open辅助含21个原SRAM、全目标共33个；LL辅助14个逻辑存储映射为逻辑单元，物理SRAM宏0，外部16bank仍在测试环境。

最新已资格的完整布线辅助为open91774与LL91823：fresh DRC0/PG/布局通过，必要信号网分别536661（91835）、624010（91869）全连通。当前几何与模型版本对应两新辅助M8引出91889/91890，不使用旧来源的证明冒充当前版本。

| 实际完整物理DUT测试 | 结果与范围 | 证据 |
| --- | --- | --- |
| open原20例 | 87160行/2317514字段及全部256KiB输出一致 | physical-opentpu-timing-repair-route-replay-4c-01，91848 |
| LL六组180连续任务 | 243883行/17769493字段/540份完整1MiB镜像一致；独立1256文件闭合 | paired91904、独立91919 |
| open真正连续两次host任务 | seed0/1/2，系统reset不重拉、存储不重载，前次halt/drain后正常重启sequencer；50535行/1348307字段，3份最终完整内存一致 | 原91947/物理91949 |
| open补充ISA/VPU/QST | 54个程序×seed0/1/2=162例，原版/位精确模型/完整物理DUT全部一致；29876行/713277字段、162份完整内存共42467328字节 | oracle91973、原91976、物理91980 |
| 补充用例独立复核 | 重验全部协议/逐周期掩码比较与完整内存，1797文件；真实ready位破坏和内存末字节破坏检出；未重跑仿真 | 独立91985 |
| MM/QACT新增定向模式 | 40程序×3seed=120例，原RTL/校准ISA/完整物理DUT一致；36858行/899277字段、120份256KiB内存共31457280字节 | 输入92033、原92035、物理92040 |
| MM/QACT独立复核 | 1382文件与完整协议/逐周期/内存重验，ready位与末字节破坏检出，不重跑仿真 | 独立92042 |

91940对旧20例实际trace审计确认每例只一次启动、仅7类opcode及VOP函数0/3。补充suite已加入旧缺失的NOP/LI/ADDI/LOOP/BAR/RLD/QST/GATHER，覆盖全部20个VPU函数、适用四种广播、OUTER三种decay、QST四种模式/步长和3列对4lane尾块。S=1 collective只按实际单slice目标测试。DSTEP/STREAM按原HAS_DSTEP=0禁用，未缩硬件或伪称运行。静态指令存在/定向执行不等于每种flag、数值边界或所有输入均已证明；新MM/QACT suite已定向测试全部四WF、UNIT/ACC/RMAX/ASCALE、合法三WF的RSC、三种4bit格式PAIR偶/奇KB、k0非零/ACT尾端及QACT ROW/CSCALE/RSCALE/两scale/DUP/全零/符号零和次正规混合。每项保持完整原硬件；不宣称穷尽组合、数值极值或中途复位。

参考模型使用原项目isa/isasim/fp32/quant五份必要只读源码副本及既有Python3.12.7/NumPy2.3.3，无安装。先对三个既有原RTL完整256KiB结果逐字节校准，再生成新输入/期望；输入按$fread大端word、输出按原模型小端word处理。协议时序参考来自真实原RTL，不从功能ISA预测延迟。新用例公共请求/响应、有效字节、停顿保持及计数逐周期比较，不只比最终值。

状态资格：原严格图对照失败保留，不据此断言逻辑错误；整体布尔miter91852超时。实际库完整真值/合法pin对称资格91867后，两辅助所有72529/65545状态、149067/168074锥经完整规范化91884/91885零差异；实际状态D反相/时钟模型破坏检出。该证书依赖同名状态/初值及原存储模型，不是源RTL完整形式证明。

### 新辅助时序/电气问题及另一实现候选

原约束下实际布线基准测量：open 2.5ns setup WNS=-0.043080873ns/19、hold=-0.025135839ns/3、cap947；LL 3ns setup=-1.516328883ns/5597、hold=-0.238355009ns/30、cap1044；slew均0。完整有效SPEF覆盖分别467175网/1476167端点（91856）、558724/1772965（91897）；孤立单端点/原未连接输出逐项分类；fanout无有限限制不记为检查通过。这些是本任务新辅助的失败，不是原输入继承。

LL最坏是ATTN时钟数据路径og[0]→wdata_acc[998]，cell约4.047ns/net约0.448ns，长FA_X1链占主要延迟；另一条reset recovery满足，不能误称最坏为复位。91911只关闭可选强制adder单元映射、保留原RTL/3ns/容量/位宽/流水，完整综合和接口通过，565287单元，相比旧442863；不能从首个空blackbox模块统计FA/DFF或声称提速。91959 floorplan、91964完整布局/PG几何通过；92008 CTS已完成，布局/PG检查通过，耗时15:02/CPU21:33.566，平均1.43核。实际完整布线92018已闭合：独立fresh DRC0、完整原生placement/PG/结构通过，耗时3:02:38/CPU9:37:10，平均3.16核。92108全信号端点及导体连通通过；92109直接规范化65545状态/168074锥零差异，实际破坏负例检出，无需借旧源状态证明。92112原3ns实际RC测量却失败：setup WNS−2.151527017ns/9662端点，hold−0.547692518ns/8704端点，slew98、cap2548，不能称重映射改善。92119已独立证明725253个active网/2325528个端点精确SPEF覆盖；65080孤立单端点、8175原未连接输出逐项分类，不当缺寄生或功能通过。最坏clk组从u_attn.D_r[6]到bit_4175输出，arrival4.551527ns/required2.4ns；前列异步recovery路径为正裕量，不误作全局最坏。未完成本候选完整原case回放/M8/model资格，不替换当前底座源。92121已绑定该真实失败与RC覆盖，从同一完整CTS前驱启用现有native setup/hold/electrical修复；新run4CPU，原3ns/规模/接口不变，正在运行，不宣称改善或替换。两源core die均0,0,4200010,4200000 DBU，不表示可直接移用内部几何/PG/clock证明；原始失败均保留。

## 阶段三：迁线、完整M8接入与当前源视图

四核心必要高层连接在派生副本迁到M1–M8，逻辑/内部位置/非目标导体/PG/原障碍保持、M9/M10固定占用清零、fresh DRC0；原失败保留。四核心全部9031信号真实M8引出、同时via8_0接入/新接触/规则/完整RC锚点资格通过；核心全网/PG分别ACT5593、MXU229998、GEMM290149、VECTOR380381网。原生DRC与增量接触检查边界分开；PG是几何/拓扑，不含IR/EM。

两新版辅助2229/13507信号+各2PG的实际M8引出91889/91890通过。91920/91921独立复核全部M8锚点及2213/13507个正电阻图；有效SPEF分别467259网/1476251端点、558748/1772989。测量仍不接受时序，未作公平同提取边界比较的差值不全部归因M8。

两新视图各发现一处M8固定wire抽象漏盖（open91956检查19513338个routing矩形；LL91958检查23843388个），失败保留。91981/91982复用闭合导出，只在派生LEF增加对应保守OBS并扣除PIN；原DB/全部PIN不变，新进程R0全端口读回通过。91992/91993独立证明旧原生OBS 15433576/19081988个矩形完整保留且各只增加1个声明矩形，全部原缺口由新OBS/PIN覆盖；这是完整旧扫描+精确单调扩展的组合证明，不是重跑全部扫描。91999/92000复用同版本原生模型并实际重新链接，2229/13507端口通过；宏视图合格不等于时序满足。

92004已对两个新辅助及四核心重新绑定全部资源端口，92005已在该版本重新证明常量输出别名并规范父层图。旧端口别名/布局/PG版本不静默沿用到新源。

### VECTOR：继承与新增/恶化分开

die/track-only控制保留全部原导体/实例，能重现部分先前差值，故必须固定提取范围。相同范围：原/迁线/后M8 setup WNS为-4.172909247/-4.173307151/-4.173307595ns；三版同名287个setup违例端点。91786逐cap引脚：迁线新增2、消除3，56项持续中22项恶化；M8相对迁线无新cap项/无持续cap恶化。91812用未舍入native slack逐端点对照：迁线最差单点恶化28.510528ps，M8最差3.676171ps；不能以全局WNS微小或总数减少代替无新增。4项差异负例通过。新增/恶化尚未解决；接近浮点精度的量只作数值定位，不作工艺结论。

### 共同宏布局和固定供电原型：实际通过的范围

第1轮真实pad/通信图驱动规划91853使用7851跨资源逐位连接/572站点。6000μm方形规划边界、500μm网格、200μm间距是研究参数，不是可布线保证。91888对真实六宏ODB/DEF独立读回通过：24779端口（24767信号+12PG）、位置/朝向/FIRM/全部PIN与OBS源几何、无重叠；真实移动宏的负例检出。数据库为runs/union-native-placement-r01-provisional-4c-03/common_placement.odb，统一200μm外halo，die6400μm。

91954在同位置上实际构建M7/M8共同PG并重新读回，12个真实PG端点、全部受保护实例/源几何保持；91960独立检查真实导体和via：VDD/VSS各6资源锚点与外部源连通，分别561/507导体节点、各1连通分量，金属/切孔间距及短接检查通过，源stub对实际子块M8检查无新接触。断网/反供电短接/删通孔负例检出；新进程check_power_grid两网均catch0/return1。真实数据库为runs/union-fixed-pg-r01-prototype-4c-03/common_pg_prototype.odb。

旧PG原型不能当新版证明。92011核对新版尺寸/ID/R0相同后保留第1轮坐标/7851连接，主要候选仍1/3。92015新六宏/24779端口完整原生读回、无重叠和真实移位负例通过。92025新源实际PG构建/读回通过；92026独立证明VDD/VSS各6锚点、561/507节点、各1分量，金属/cut间距、删线/反供电短接/删via负例和新进程双网check_power_grid通过。没有IR/EM、完整DRC、RC/STA或冻结。新源ODB：runs/union-fixed-pg-r01-timing-repair-4c-01/common_pg_prototype.odb。

91971四向M8直线局部引出12项中4项失败，保留证据。新92020采用有界单层A*折线、真实子块/父PG/其他宏障碍和原child die禁入，联合预留全部已选路径，12项全部找到合法局部路径；真实障碍穿线、source-pad异网短接负例检出。此处仍是旧源几何探测，约30秒/CPU28.610，未写导体。92028新目录实际写出含12个独立控制代理输入的ODB/DEF，新进程完整读回通过：44个新增真实形状、12源/代理锚点全部连通、实例/源PIN/OBS/PG严格保持、真实删线和异网导体短接负例检出；局部控制接口引出不等于完整clock/reset分发，不改变active reset拓扑，也不能当新源最终证明。

92041确认1共同clock+4不同reset；MXU rst真实源为open辅助bit_23659输出，不能替成外部reset。12sink+该source共13接入。92044联合几何通过，但构建因变量覆盖把方向写成top而失败，原证据保留。86e48b2只按原生ITerm/规范角色恢复已知坏源码的方向元数据，几何不改、未知方向冲突不豁免。92064复用精确同源闭合路径，重新实际构建/读回13端点/51新增形状，保护实例/几何/PG，删线与短接负例通过；不是完整分发或CTS。

完整控制网络复用PG-aware A*，保留全部原资源/PG/局部路径。92065/92071规划失败：同网两via中心距1600DBU，cut边距800小于实际880要求；无合格ODB。保守4x2点集虽满足cut，却使M7横/M8纵图分成奇偶X两组，92078不可达，属于算法限制，不是容量或后备层理由。9bb5826加入带桥接行的connected_staggered，92085重现旧图断开并通过新图跨组/间距/默认PG几何回归。92087全5网/13锚点规划及实际ODB/DEF重新读回通过，2614新增形状、4外部根、全部单驱动/连通和受保护源geometry/PG保持；删实际源导体、异网短接、删via和端点错网4负例检出。没有新增器件、移动Block或放宽规则。数据库为runs/union-fixed-control-networks-r01-connected-native-4c-01/common_fixed_controls.odb。

92092按精确92087 submission/job/source/结果SHA自动续接，只读加载同一ODB和全部6个已资格宏模型，实际提取5网并核对全部13资源端点+4外部根、实际原生pin bbox及正电阻连通图。共同clock为200电阻图节点/199正电阻、线电容4.57556pF；LL reset为97节点/96正电阻、2.18601pF；其余3reset各15节点/14正电阻，0.284179/0.319355/0.310359pF。删除实际提取电阻网络与移除端点负例检出，源ODB不写回。6个实际宏模型全链接；135个未实例化标准库master未载LEF警告和旧提取选项弃用警告保留，不作为完整无警告或STA通过。寄生提取/覆盖不是源驱动、clock slew/skew、reset recovery/removal、全案例STA或制造签核。

旧raw控制全静默强性质91834失败，不代表有效非法写；未定义MXU t_wen及ACT写控制归因91844保留。92061因两个完整物理源重复标准单元定义编译失败，保留。17399a4仅按逐字节相同body共享93重复库定义，120唯一定义及全部实例/连接保持；不同body/游离指令负例拒绝。92063实际同时实例化完整两父层/6资源/33原RAM，保持reset、无start/valid、共享clock，seed0/1/2各16预热+256检查周期/5120公共请求检查，全33 RAM无有效we&&wmask写；实际强制请求负例检出。无清内存/门控/缩规模。仅二态零延迟有限held-reset证明，不是active+idle完整任务、物理tie/隔离或全输入证明；依赖闲置父层原内部连接保留，不适用于任意各Block独立tie。

### 共同钟线的实际传播测量：新互连质量失败

92101读取同一真实ODB/SPEF/6宏模型，按原2.5ns/3ns默认时钟源测量各6入口、rise/fall×min/max共24记录/例。全部实际native模型max_transition=0.199ns；LL辅助/GEMM/VECTOR分别1.129704/1.438422/1.577455ns，open ACT/辅助/MXU分别0.588570/1.746217/0.342831ns，6/6违例。最大入口传播延迟约1.290465ns，入口到达跨度约1.010006ns，不等于完整寄存器间skew或内部叶时钟签核。这是当前长距离wire-only分发产生的新失败，不能归原输入继承；全例STA/reset recovery/removal仍未执行。

早期92096原生API多传scene导致结构化输出失败；92097/92098证明即便时钟标成ideal，底层raw vertex仍会报告实际物理arrival/slew，因此不能用非零值判断已传播。92101显式global_auto=0、原生is_propagated=1，负例真实unset后state=0被拒；native ns校准1.0000000282819324采用1e-6相对单位容差，不改变任何slew/时序判据。92099的单位精确相等失败与其他旧失败保留。测量收据PASS只表示测量/检查器闭合，其字段macro_input_slew_check=FAIL、clock_quality_accepted=false才是质量结论。

原SDC没有clock source driver/transition规范；保留原默认边界，不虚构真实外部驱动。92103只读核查同已资格auxiliary route的macro.mod.lef/SHA与既有标准库：CLKBUF_X1/X2/X3有实际M1信号/PG脚，site为FreePDK45_38x28_10R_NP_162NW_34O（380×2800DBU=0.19×1.4μm），native CTS/make_rows/repair_clock_nets可用。92100 CLI参数错误和92102三LEF选择歧义失败保留，未视为软件缺失。没有添加buffer/row/PG或保存派生ODB；修复须在冻结前作为共同主动资源加入，并实际验证供电、布线、寄生、两频率入口质量和完整功能。

### 共同缓冲树：实际生成/放置通过，真实PG和钟线尚未完成

92107在新派生ODB中仅替换被拒绝的task-owned父层clock导体，新增75个真值已验证的无状态正向buffer（CLKBUF_X3×35、CLKBUF_X1×8、BUF_X32×21、BUF_X16×8、BUF_X8×3）和合法row。原placement候选仍1/3，资源版本r01-common-clock-CTS-prototype-v1-unfrozen。实际CTS报告只计43个tree buffer，另32个由clock-wire repair加入；以保存数据库的实际75实例为准，不拿工具局部计数当总资源数。

新进程完整native读回/合法放置通过：原6宏master/身份/位置/朝向/FIRM不变，全部58,972,634行原PIN/OBS逐行hash相同（ccd690fd30c27608d8e49ea2f4cc255c7bce310379e2de827e943de78e95f239），PG/reset/外部pin几何保持，新cell无重叠/越界；实际native placement catch0/空return/0marker。原有状态/存储和data端口未改。75buffer构成76逻辑clock网，全6原clock入口可达/单驱动/无环/无unused分支，实际记录的buffer输入断网负例检出。没有证明clock已实际布通或质量已改善。

92116从同一真实保存ODB只读导出75实例/5种master的实际pin矩形，原生origin/朝向变换后逐端口bbox与native ITerm吻合；150个M1 PG端点均在实际pin矩形与制造网格上。真实origin偏移负例和一个VDD bbox中心空洞反例被拒，不能用bbox中心伪造电源接触。尚无M1–M8电源逃逸/导体/通孔，也未把新增buffer真实接入既有PG。新PG、clock详细布线、DRC/寄生/slew/skew及两case完整功能均是下一道门槛。原wire-only source的供电/clock结果不作为新75资源证明。

future续接复用verify_closed_producer：92108/92109在92018准确闭合后绑定submission/job/source/结果SHA调用原全网与状态检查；92112在92108/92109合格后生成实际源配置再调用原RC工具。92111用另一真实旧PASS路由与新submission错配，两个入口均拒绝且没有启动后续工作；92110旧解释器fixture失败原样保留，不称旧失败为业务错误。

## 资源、恢复入口与交付

所有新任务4CPU，线程上限与申请匹配；92107用14:56/CPU15:10.141（平均1.02核），92116用0:10/CPU0:08.244；92101用0:35/CPU0:41.573，平均1.19核；未停止/在线改造任何旧任务。92087用14:06/CPU14:14.796，平均1.01核；92092用0:17/CPU0:20.620，平均1.21核。91954供电构建13:44/CPU13:50.230，平均1.01核；91960独立PG25:03/CPU25:07.181，平均1.00核。新162例物理回放91980用2:00/CPU1:40.817，主要单线程；独立1797文件91985用0:07/CPU0:12.204，最多4个哈希worker。LL新辅助布局91964用47:48/CPU1:07:11，平均1.41核。新版布局92015用31:25/CPU31:38.039；局部实际接入92028用13:21/CPU13:28.390，均平均约1.01核。新120例物理回放92040用1:22/CPU1:07.852，独立92042用0:08/CPU0:12.797。申请4核不等于四倍加速；全部实际账单见最新索引。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

大ODB/DEF/SPEF/trace/模型全在服务器，路径/大小/SHA由各execution收据及本页索引串联。没有对原始参考目录全量审计，没有软件安装或大文件下载。GitHub仅阶段一；阶段二/三未验收，不上传“阶段通过”；登记pending、看板unverified/同步pending、审查人待指定。

<!-- current-buffer-PG-status -->

当前检查点2026-10-29T01:03:14.503334+00:00，以本段及最新索引为准。完整目标不变，阶段一pass_with_inherited_issues；阶段二/三未验收、四NOTRUN；候选1/3 **UNFROZEN**。

**同一底座边界。** 两完整硬件案例采用计算/状态/存储/控制资源并集；冻结后资源、位置/朝向、内部实现、固定预连线、PG/clock和真实M8接点完全相同。M1–M8固定，只定制M9/M10及真实via8/via9；M11/M12未启用。open=otpu_asic_top及33内部SRAM；LL=EPILOGUE_FUSION0/DMA_MAX_OUTSTANDING16，外16SRAM bank/DRAM/主机参加完整功能、不计core面积。不缩硬件、不加流水、不放宽原3ns。

**固定预连线：实际失败，不是已完成导线。** 92548自然FAILED1:0/4，wall24335s/CPU24357s，约1.001核（四核利用率约25%）。原生先报GRT-0116全局拥堵，未进入详细布线；后续DRC计数查询再报DRT-0002，是次生记录错误。保存2,502,723,609字节ODB仅失败快照，SHA47e51b052c508d4988c89a20aade663892468cbd847bcd2fd9c124227076d793；回执SHA694354b64878322d74b67e6853a4374ef5401fcee6b8eab2c80ac66a3b93f4b8。93104新进程只读完整保存GCell、没有重跑6小时GRT：7层各5,040,025格，总35,280,175层格；M5/M6/M7/M8超容量格分别63,626/236,171/372,529/190,028，总862,354。wall120s/CPU119.319s≈0.994核；回执SHAf91ddbb7e49b87097b7ff191e152c8ba08d97317808b5bb12fbd03c768a22f40。

93107对全部862354行按真实六宏矩形作空间归属：633205格中心位于宏外（约73.43%），5595个宏外中心格仍与边界相交，热点在M7底边、M6左边的64×64网格区域。**完整14059目标中，14059有数据库guides，实际有wire的目标为0**。guides不是导线，统计不是完整物理连通。wall6s/CPU4.877s；回执SHAa729ea6d1ff978201c6a93589e11353db859d63556fdc3bfad8aa72ff0bf6b9d。该归属不等于逐PIN/OBS碰撞或排他根因，不能据此删几何；应反馈公共IO/通道与预连线策略。93103首次读回把DRT的15566信号/clock网数误作native全网数而失败；原生库存实际另含2PG共15568，修复为绑定真实191实例/15568全网后才运行93104，未去掉身份守卫，原失败保留。

**接入点：完整实测部分改善，仍未通过。** 93086完整native PA/GRT实际完成、两诊断DB已保存，但独立读回脚本缺need而Slurm FAILED；93093新目录逐SHA及真实独立读回恢复了完整观察证据，没有重跑PA。13507端口、27014盒、47262AP行一致；5066个M8盒无AP，其中53在选中网。93093回执SHAf9187747c0b938a88569d1a8e80a5a774e4c6c4f0b24728500627d9bf7ba5f65。所有端口有原低层AP不等于全部新M8接口可用。

93095小对照、93100原生helper资格后，**93101完整设计观察COMPLETED0/4**：只按真实pitch/offset补充相邻M9轨道元数据，原52模式保留；不增加M9导线或器件、不移动引脚/内部cell、不删PIN/OBS/导体、不软件补AP，实际布线上限仍M8。完整546459实例/124targets/62splits/15489424保护不减。缺M8 AP从5066降至**1642**，剩余在负X左侧，其中1口在选中网；43862个AP均在自有真实盒内。PA后/GRT后与实际新进程ODB读回一致。**这只是native接入机制部分改善，没有执行详细布线或完整接入/布线验收。** wall961s/CPU3404.059s≈3.542核（四核利用率约88.6%）；源码cedf97f7f1f65a5570da3d2c0cac080f315a0083；回执SHA85f5d98c466134abb8eb041a2e1f3e847419bba7f317446685b4266880940685。GRT后UNACCEPTED诊断DB1,484,948,574字节，SHA74b0b27c315c1d8a80041dcaa2a94a405737bf8bb6473c6140a7739024839e4e。旧93099 Rect对象误作列表在PA前失败保留；新代码按实际阶段闭合才标actual，不沿用旧预设布尔值。

**检查器与后续实际动作。** 93105只在独立小夹具验证所需M8接口守卫：真实native正例、禁用实际AP方向负例、恢复正例、删除实际M8 AP负例均检出；回执SHA6b0ca82e34402cb23884eb2ae523d573e4d32ab1c727fefa8a8e96d72716f8c4。旧“每个金属盒都有AP”守卫不修改/不放行；新M8接口检查器尚未接入成功全设计源，完整检查程序已写但未执行，因1642真实缺口未解。它不代替原低层物理连接、全DRC/PG、RC或功能。93109实际在native PA启动前失败：旧夹具适配器只接受M6/M8双形状，而剩余左侧实际为M5/M8。故min_access_points=1/2/4三项原生调用均NOTRUN，不能把配置编写当实测。错误回执SHA094c4986134c93dc2f3226e187eea38057f73eb580db95bf9892790f6f4ec098。下一步先按实际低层形状参数修复此案例适配，再测native设置；不据此重复完整PA。

**仍有效的限定通过。** 93016新增62BUF_X2真实合法放置、原546397实例/原导体阻挡保持及off-site负例；93022实际新旧65545状态/168074状态输入输出锥一致及真实状态破坏检出；93058新UNROUTED源placement0/VDD1/VSS1；93056闭合prepare+15来源破坏拒绝；93069完整13507口读取器+8数据破坏拒绝。均不能当新完整整机、四态/SDF/所有输入形式等价、实际线路或电气验收。旧LL六组180任务/243883行/17769493字段/540份1MiB镜像、旧open20例及active+idle只适用各自源版，不能转移为新增driver/当前191/最终底座通过。

**失败、未执行与缺项。** 93067在bit118真实M8盒无AP失败，没handoff/没fresh-detail；93018原DRT1231失败保留。93024/26/29/34/36 child_launched=false，五项实际RC/覆盖/完整LL准备/编译/回归NOTRUN。93053记录器失败与93065只读复核不变更原终态；49旧口AP点相同不覆盖全部13507口或方向/worker可达性。93081拆PORT两项真实DRT0302失败未采用。旧未加62buffer M8 AUX原3ns setup5691/WNS−1.5718422563995755ns、hold36/WNS−0.24845087801435276ns、cap1104/slew0质量拒绝；不是新driver测量。VECTOR新增4cap及e238相对原版200setup/26cap恶化未解，不设epsilon/复位例外/放宽时钟。外clock rise/fall、open37常量输出负载用户未确定/null，不填0。每例841模式相关闲置扇出、当前191统一PG/clock/固定线/完整功能仍未闭合。

下一步最小动作：依据93109及1642端口的真实轨道/层/坐标选择可验证接入处理；依据93104/93107的保存拥堵反馈公共IO/通道/固定连接安排，不缩设计、不把guides当wire。实际线路完成后独立全连接/接触/fresh DRC/PG、同frame RC/完整负端点与电气、新完整功能；统一同源全部条件通过再冻结，再做两完整case最终M9/M10定制。

唯一根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/；93101在runs/auxiliary-driver-adjacent-track-complete-PA-capture-r01-4c-02/；93104在runs/closed-fixed-parent-route-native-grid-r01-4c-02/；93107在runs/closed-fixed-parent-grid-macro-attribution-r01-4c-01/。
最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-native-access-partial-improvement-and-actual-congestion-20261029T010314Z/milestone.json
SHA-256：**b8962b17db48829974621da22f9ba70c1fb5c6b8f7ba0ecfcc4ae3f02a448f02**。
review源码481d2af73c43c06f756ece9740d2eb552051c93b；所有job spec/source_revision/submission及关键输入/工具/输出SHA按源绑定。OpenROAD版本unknown、binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。父索引和上一版六记录完整先封存，不改失败/封存结果。

同一Issue55/task/55-full-block-integration/草稿PR58；前次精选远端b6be911b647331ea24dbf60d7b2864b04391166e已核验，本次发布另有独立delivery receipt。大ODB/DEF/SPEF/完整日志/trace/工艺留服务器，远端仅精选小记录，不冒称完整后阶段源码已交付。所有新job4CPU/native≤4/BLAS1，单线程明确单列，无独占，不超分配，不停/重复活跃作业，不改四个受保护dirty路径、原资料或其他任务。rayggxia-project-collab1.0.0；登记PR5 pending复用未重核，board.json缺失/Projects unverified/同步pending，审查人待指定，Issue继续in_progress。
