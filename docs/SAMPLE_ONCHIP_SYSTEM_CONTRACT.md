# 静态编译下的最小执行合同候选

本稿承接e44c4f5f492b2ef0fef12846dd25c1b1ea637664，原生RTL仍为643c6012。本稿为Issue151 / PR152步骤3正式候选；执行协作Skill1.0.0，未修改叶宏，上传/验证回执见[工作报告](STEPS_1_3_WORK_REPORT.md)。本轮形成步骤3可评审规格，不是新RTL实现、完整程序编译或物理接收。

## 1. 本轮修改的核心

上一轮handle256/task512/event256/lease256以及32KiB控制存储、2MiB ROM是通用候选/比较基线，不能倒推为每颗芯片最低配置。本轮提出一个保守、可进一步实现RTL的静态执行方案：一个预制母顺序器、按资源唯一拥有原生端口的子控、一个全局前台job和一个完成槽；由预制指令/参数表确定每步的真实操作。它优先证明功能可执行，**不宣称吞吐或延迟可接受，也不是存储数学下界**。

| 信息 | 放在哪里 | 为什么 |
|---|---|---|
| role/type/scale/layout、合法性和活跃区间证明 | 离线编译资料 | 生成执行步骤，不在每个数据包上重新识别 |
| 完整程序、层表、地址/尺度引用、合法模板、错误路径 | 永久ROM/表 | 层/head循环仍需查不同参数，不能把所有层scale并为一个常量 |
| PC、真实长度/地址、握手计数、N/R阶段、错误、根版本 | 运行时寄存器/有限状态 | 反压、数据依赖分支和失败不能由静态类型证明消除 |

旧typed账本仍用于编译与审查，不能因去掉运行时role标签就删掉语义检查。它也不要求每宏携带完整通用handle表、task队列或runtime DAG扫描器。

## 2. 同一预制底座与永久产品绑定

所有支持样本的指令、分支/循环译码、子控、数值原语、MUX、holding、仲裁和clock/reset先在M1–M10及有源几何中预制。M11/M12只连接预留常量/入口/参数/路线端点，以被动图形永久选择已有能力，不启动加载程序。

产品A/B不能分别常量化RTL再重新综合FSM、删不用宏或插buffer修时序后仍称同底座。可做的是冻结前编译所有程序进同一ROM、共享子程序，产品只选入口及预制参数。选定产品后运行中的gate/up、N各阶段、R候选往返仍需有源路线选择。**普通push-pull输出即使valid由软件证明互斥也不能短接**；阶段切换的MUX、仲裁和保持寄存必须事先存在。静态role消除不消除route-select和握手计数。

## 3. 具体执行骨架与字段

母控采用阻塞SERVICE指令：校验本步预约与阶段条件→装入命令模板→启动指定子控→等待其完成记录→检查status/error→更新循环/阶段→执行下一步。全局至多1个前台job，不做动态抢占或out-of-order调度。完成记录未被接受前不启动下一job。

唯一owner保持：M cmd/rsp为M_CTRL；S普通口/loader描述符为S_CTRL，M A/B由S内loader提供；N/E/G/R/T各自子控拥有端口。MEM与NUM是待实现服务，不能因分配ID就写成已有硬件。NUM_SERVICE串行承接CONVERT/COEFF/CONV_BIAS32，NUM_WACC另有候选服务；已有native op能完成的转换优先直接使用。

### 指令与命令参数没有隐藏的大task数组

- 微指令64bit：opcode6、service4、flags6、param_record16、immediate16、targetPC16。译码是固定硬件，允许有界循环/CALL/返回、标量读、32bit比较/计数/移位和64bit地址加法；不是新增通用CPU或向量ALU。
- 普通命令模板256bit/32B；显式MEM扩展可用两记录/64B。物理方案明确为**10个服务各预制64B本地模板capture，共640B**；ROM按64bit beat直接送入选中子控的capture，母控没有第二份完整模板fetch bank。即使全局只有1个活跃job，也按10份实体存储计价。该capture是每服务一份当前模板，不是多task队列。
- 通用S流记录包括3个源word地址、1个目的地址、elements、native control及4个stride；R记录包括native_data128模板、S源/目的、index/repeat/op及身份插入模式。详细字段在JSON中逐项给宽度，M与MEM模板也列实际字段。R op0/6/7身份位域不同，不能复用同一未重打包数据。
- 完成记录128bit：status8/error8/service4/op4/index16/flags8/failed_rows8/progress32/PC16/reserved24。由于严格全局串行，母控知道当前PC/服务，不必另带task_id；一条完成仍须区分候选保留、写ACK、局部commit、发布和释放。
- 控制输送用64bit握手字：header后跟4个模板字，MEM可8个；无包交错。header字段由选中服务已预算的32B sequencer状态保持，模板各beat直接写该服务本地64B capture；普通模板只标低4字有效、扩展标8字有效，不能读旧的未使用字。请求beat及完成beat的64bit保持寄存和计数/route锁在32B transport预算内，无额外64B母控完整模板缓存。完成2字；payload数据不经母控。所有valid/payload在ready前保持，子控只在所需模板字完整后执行。更多物理中继/FIFO另计，不能由记录位宽推导pin数。

Native尺度/格式由本步代码和模板确定。M op5已夹S16时可直接抽4个低16bit；若目的只要两个G包，可不先合8；E13等已有转换也可由程序调用。是否合包按目的要求：N支持count=4，可直接接4个S16，无须一律合8；需要紧凑8S16整字写S或完整八lane喂E时才收集/拼包。若E只处理4个有效值，可以补零8lane并由外层保留有效数；S也可用独占整字填零保存半包，但需计padding。未证明的S64重解释、G通用EXP、E16冒充S32加法不会因静态编译自动成立。

## 4. S辅助进展、信用与N/R阶段锁

全局1job不意味着S只能被母控直接命令。R/N/E/G/M等当前job可以向S_CTRL发有限辅助读写，母控等待当前job时S_CTRL继续工作。S同时最多一个普通请求；先take并保存当前响应，再请求下一次依赖S访问，禁止占着S响应等待另一次S读。S helper不占第二前台job，也不等待母控发下一指令才响应。

当前job接受前，预约一个公共完成槽、端点输入/输出空间以及该步骤会写的全部有限目的范围。S/MEM响应有地方捕获后才允许发请求；完成event反压不能阻断已经接受的原生响应排空。普通S请求与loader窗口首版串行；loader接收后必须完成全部A/B义务，不能等待S写spool才允许done。

N/R/M/T各保留一组小阶段寄存器，不建通用lease表：N记录预期/已接收/回放计数，R记录身份/pending/候选有效，M记录bank/scale/结果链，T记录owner/generation/字数和读写进度。一个阶段job结束后释放执行槽，但N/R锁可继续保留；母控调其他宏后RESUME同一context。新context重入才要求关闭旧context。N阶段与R pending guard不因外层静态调度而绕过。

fork/join由静态缓冲分配及执行/分支路径闭合：先保存早到分支，之后收集全部输入。被跳过分支走编译的SKIP/merge，不等不存在的事件。可证明的固定消费顺序可不使用generic refcount；没有证明时保留数据/holding成本。单实例资源冲突用串行重用解决功能，实时/吞吐要求另验。

## 5. 动态MoE不需要下载程序

TopK仍返回运行时8个ID，程序按rank0..7循环，读取S中的ID/概率，检查ID0..39，并查本层40项expert_base64地址表。表中地址不是编译时确定expert选择；选择是运行时的，程序和表结构是永久的。查表避免假定已有通用64bit乘法器。每层不同权重/尺度从层表/模型数据取，不沿用上一expert的B或scale。

如果可证明TopK输入ID恒为唯一0..39且未被覆盖，可以消掉冗余唯一性检查；未证明时32B MoE状态中保留40bit visited mask及rank/ID/地址/标量状态。8个ID与8个Q14权重本身各占一个S字，仍计入当前活跃数据区；NUM_WACC和全模型权重取数不因此成为已实现。

## 6. R根元数据为什么可以固定索引，但不能消失

现有样本中Qwen3.5有24个GDN层，Falcon有32个SSM混合层，其他样本不使用R。只运行一个永久选择的产品、逐层串行，故本候选为**32个layer root×32B=1024B runtime状态**，不是原256×64B通用根目录。root粒度是“一层完整state＋history的版本”，并非一个R tile。超过32层、并发region或新模型都要重新预算，不能偷偷保留原泛化承诺。

每层静态64B ROM项列state0/state1/history0/history1四个64bit基址、两类tile stride/count、L、conv_channels、scale引用与owner base。所有产品合计56项（24＋32），共3584B；模型/层到root的映射固定。实际MEM地址与传输合同仍待研究，四个数值字段不表示存储已存在。

每个运行时32B root逐字段为：published_version32、logical_position32、active_bank_selector8、valid_flags8、dirty_flags8、publish_state8、last_error16、reserved16、old_published_version32、candidate_version32、output_visible_prefix_words32、reserved32。状态至少区分初始化/clean、构建候选、已写齐、根已发布但输出未齐、部分可见、故障。old/next按selector选择，不靠改动静态基址表。

当前region再保留64B的conv/state预期及连续ACK前缀计数、输出/字节ACK进度、失败tile/原生身份。因为全局串行、一个region且按tile顺序处理，不需要1024bit乱序完成bitmap；未来放开乱序必须加回bitmap/日志/队列，不能保留此证明。

完整两遍仍为：conv输出op12保存→local history commit→op14保存ACK；外围处理后从old版本恢复state→state EXEC→op12保存→local state commit→op11保存ACK。每次换OPEN前保存所需payload。它们不会等到全128/4096通道Norm后才做第一次局部R commit。

只有state/history规定范围的写ACK及程序发布条件满足后，才能切换层根selector；输出T批次/MEM发布另有确认。R局部commit接受后不可盲revoke，旧根保留不等于本地active没改变。失败时隔离dirty next bank，排空所有写入后再决定重装；新根/输出已被看见时记partial_completion并停止，不能重放旧状态假装原子回滚。本合同没有自动R/T/MEM联合事务或掉电恢复。

## 7. epoch、取消与失败闭合

执行epoch32及命令序号32只用于当前执行边界和诊断，不在每包附通用role/tag。耗尽前停止新指令，完成原生/loader/S/MEM/消费者排空，再协调重初始化或终止；不允许直接回绕。R native epoch=0xffffffff不能成功commit，开始修改状态前即检查余量。

尚未呈现native valid时可取消待发指令；已呈现则保持到握手，再按合同排空。G已进流水的包必须退休；S loader已接受必须继续A/B接收；M部分行失败保留failed_rows，不重发整条追加。T粘性protocol_error不能由revoke假装清除，R commit与T可见性分别报告。MEM未来可变延迟完成必须有真实接受/完成/错误与drain/reset合同；timeout不是撤销成功。全部排空前不复用上下文或解除数据保留。

## 8. 真实spool成本与外存边界

系统有外存；本轮不研究控制器/PHY/容量/带宽，但保留MEM服务7、64bit外部地址和可变延迟完成扩展。它现在未实现；P0禁用请求只限制片上验证profile，P0容量失败不能写成模型不支持。最终M1–M10冻结前仍必须落实所选MEM控制、接口和I/O，不能冻结后靠M11/M12新增有源控制器。

S保守预留loader快照1024B及T整批spool6144B，剩计算区9216B；另有新loader capture1024B，避免loader活动时只能等同S写的等待环。已有S内192B队列不能重复冒称完整capture。互斥复用只有给出具体路线、活跃区间及排空证明后才扣除，本次不扣。外存、片上状态/KV/activation/weights、gamma/taps/bias/A_log及逐组量化数据独立出账，不能藏入控制ROM或4KiB控制状态。

## 9. 逻辑存储预算与容量未证明

JSON逐项列所有状态与端点holding。母控/GPR/loop/call、10×64B模板capture/当前job/完成/错误、10个局部sequencer、N/R/M/T/S阶段、MoE、32根状态、当前region、预约标志和控制传输共计到端点数据staging后，逻辑subtotal为**3448B**。候选预算点4096B，裕量648B；独立loader capture再1024B。本次明确远端模板capture后相较旧稿增加576B（640−64），没有因全局单活跃而漏计实体bank。E三输入/输出64B，G两输入向量/输出48B，M32B、N48B、R32B、S16B、T32B、MEM placeholder32B、NUM128B、WACC96B均显式计入，不把native反压当无限缓存。

此预算不包括完整MEM控制/PHY、NUM运算/LUT额外状态、模型payload、ROM以及MUX/仲裁/时钟/复位和物理布线。共享S前台job的pointer/counter存64B当前job状态；局部32B sequencer保持header/执行状态，本地64B模板capture另行逐服务计入。ROM直达capture，没有另一份母控完整模板缓存；实现时若增加预取整记录、流水中继或队列必须增加预算。本数字不是下界，也不能从它推导总芯片更小。

永久存储的一个估计点为：8样本×1024条64bit指令=64KiB，共享/错误程序1024条=8KiB；16384×32B模板=512KiB；242层×128B层表=30976B；Granite32层×40专家×8B地址表=10240B；56×64B R根表=3584B；8×256B模型header=2048B；128×32B地址/布局辅助表=4096B。总**648960B**，候选包络1MiB，裕量399616B。9216条指令与16384个模板索引均能由16bit字段表示。

没有完整编译八样本程序，不能声称每样本1024条足够、参数表已闭合或比旧2MiB节省了多少。native算术误差、超65535归约计划、完整layer/head参数和失败路径可能扩大代码/表/硬件，故capacity_unproven=true。按层/head循环索引查参数不是“所有参数变成一个常量”；训练权重、gamma、taps、每通道因子与逐组scale若由模型数据提供，也仍需真实数据存储和标量取数动作。

## 10. 变更与后续验证门

从通用动态图执行记录改为“离线证明＋固定程序＋必要运行状态”，动机是避免为固定产品实现不必要的runtime类型系统；从多task队列改为全局单前台job，动机是先闭合端口归属与排空，代价是尚未接受性能；从通用根表改固定层索引，动机是八样本范围及逐层串行可证明，state/history版本本身仍保留。

下一阶段需：真正编译全部程序/模板/层参数；实现并验证母/子控与独立S helper；随机背压/错误/取消/epoch耗尽及R阶段回访；MoE动态地址与尺度；完整MEM服务和NUM原语；模型数值oracle及质量；端点负载、MUX/仲裁、时钟/复位、ROM和M11/M12路线的同源综合/物理接收。独立R最终资格继续跟踪原任务，不接管其作业。任何通过前都不称为现有系统硬件或支持所有完整模型运行。

## 11. 与动作规划器的路线边界

全局单前台job是本次控制功能基线，S辅助事务可独立进展。步骤2中的M源holding直送G等方案是可选的动作规划；它还必须绑定源/目标唯一_CTRL、跨端点握手和实际MUX，不能因probe通过就写成这套执行器已经支持所有直连。先实现S物化基线可避免跨job持有未归属响应；若增加直通原语，须在共同底座冻结前明确其协同子事务及保持/排空成本，未实现时保留route/control gap。
