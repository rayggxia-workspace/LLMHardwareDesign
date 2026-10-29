# M/S/T真实生产者—消费者互联有限实验

已完成48项真实宏测量：MT通过0/24项，TS通过19/24项。这里的通过仅限声明的电气与时序条件，新增缓冲/中继尚无放置布线资格。生产M/S/T未改动，主线Issue121仍需按其自身验收推进。

关键结果：

- M→T在568µm/base直连时，电容、slew、hold均无违规，但`right_write_index[6]→T.write_ready→M.rsp_ready→left_cmd_ready`的setup为−0.159452ns。负载合格不能替代跨宏组合时序验收。
- 按实际接点距离，M→T在high直连有98项电容/17项slew违规；8→2端口缓冲清零这些违规，setup仍为−0.243808ns。section下加入8→8→2中继后电气违规清零，setup仍为−0.313493ns。M→T在本轮声明I/O预算下没有整体通过方案。
- T→S最长连接1688µm，high直连有78项电容/64项slew违规，8→2缓冲后全部通过，链路setup+0.377193ns。section下8→2仍有65项电容违规，8→8→2则全部通过，链路setup+0.308616ns。存在可行的电气候选，但有源器件必须预制，尚需实际放置与布线。

## 实验回答什么

固定M1–M10的积木能否仅通过M11/M12连接，取决于原生输出驱动、双方内部寄生、线的RC及跨宏组合时序。对两个真实接口各130根数据/valid/反向ready线，同时载入两份完整原生门级宏及寄生，比较直连、端口缓冲和端口缓冲加一级中继。

MT：M.rsp_data/valid→T.write_data/valid，T.write_ready→M.rsp_ready；TS：T.read_data/valid→S.din/req，S.ready→T.read_take。T的lease/index及S的写模式/地址由外部控制输入承担。本实验不声称完整协议控制器、系统吞吐或MoE调度已实现。

Nangate45 typical Liberty，300MHz，0.1ns不确定度；未连接外部口保持0.8/0.2ns、BUF_X2和50fF条件。相连接口使用实际生产者和接收者，不再使用虚拟BUF_X2，也不额外叠加2fF接收假负载。共同理想clock根保留双方原CTS图，不授予组合CTS资格。

## 原生图与工具控制

M/T/S交付功能Verilog省略ODB中原有输入保护器件。实验按已验收physical回执与原清单恢复M142/T190/S143个ANTENNA_X1到实验副本，验证精确字节逆变换和原文件SHA不变；不是删器件或屏蔽警告。真实总线使用向量端口。原生连接、全部ground/coupling C和R的计数及SHA256记录指纹在拼接后反查。

保留的原生记录：MT `{'conn': 1190934, 'cap': 9570614, 'res': 1533116}`；TS `{'conn': 2281215, 'cap': 19305014, 'res': 3152360}`。新增线用π模型；未做新层串扰资格。原生警告、连接着的未标注驱动、错误单位、无约束路径、缺失真实源/接收pin均为硬失败。

run901–905的路径/工具接口/单位前置失败保留。run906小电路工具控制与完整RC准备通过，但真实宏拼接存在省略保护器件与端口命名问题，结果全部拒收；只在核验精确作业身份后取消本侧线93214，主线和他人任务未动。后续只复用已通过RC准备，逐文件SHA及图准备函数AST一致性检查，不复用失败STA。

run907实际四DFF、两个保护器件、向量端口、分离SPEF控制通过；大R/大C实际工具负例产生违规。run908再验证混合BUF_X8/BUF_X2及非等长线控制。弱DFF直连自身的电容/slew违规如实保留，“图消费正例”不等于电路通过。

## 固定长度扫描（36项）

direct保留原生驱动；endpoints在原驱动之后增加BUF_X4发送、在原接收之前增加BUF_X4接收；relay再加一个BUF_X4中继。局部两段线各8µm，主线中继等分。每段含0.24Ω声明via预算。新增门均是电气候选，没有临时改动生产宏底层。

base：C′0.155390996fF/µm、R′0.015Ω/µm；high：R/C同时1.5×。high是敏感性条件，不是制造工艺角。

下表违规数量覆盖两宏全局，余量栏为130根连接上的最差路径；已逐项与原始全局worst slack交叉检查。48项全局最小hold为0.007987778ns，不能把链路的较大hold余量当作整宏余量。

|接口|方案|长度µm|RC条件|C/slew违规|setup/hold违规|链路setup ns|链路hold ns|声明条件通过|
|---|---|---:|---|---:|---:|---:|---:|---|
|MT|direct|1200|base|0/0|11/0|-0.231132|0.610309|否|
|MT|direct|1200|high|130/0|141/0|-0.296847|0.669187|否|
|MT|direct|250|base|0/0|2/0|-0.121519|0.511358|否|
|MT|direct|250|high|0/0|2/0|-0.136459|0.525639|否|
|MT|direct|568|base|0/0|2/0|-0.159452|0.546064|否|
|MT|direct|568|high|0/0|2/0|-0.191538|0.575685|否|
|MT|endpoints|1200|base|0/0|12/0|-0.251027|0.644390|否|
|MT|endpoints|1200|high|130/0|293/0|-0.310125|0.703400|否|
|MT|endpoints|250|base|0/0|2/0|-0.153966|0.547657|否|
|MT|endpoints|250|high|0/0|2/0|-0.168811|0.562537|否|
|MT|endpoints|568|base|0/0|2/0|-0.187895|0.581508|否|
|MT|endpoints|568|high|0/0|10/0|-0.218081|0.611652|否|
|MT|relay|1200|base|0/0|30/0|-0.274933|0.668532|否|
|MT|relay|1200|high|0/0|715/0|-0.336624|0.730177|否|
|MT|relay|250|base|0/0|2/0|-0.173069|0.566713|否|
|MT|relay|250|high|0/0|2/0|-0.188416|0.582147|否|
|MT|relay|568|base|0/0|2/0|-0.208559|0.602249|否|
|MT|relay|568|high|0/0|11/0|-0.240650|0.634368|否|
|TS|direct|1200|base|0/0|0/0|0.397221|0.609500|是|
|TS|direct|1200|high|130/0|0/0|0.337735|0.668373|否|
|TS|direct|250|base|0/0|0/0|0.497308|0.510646|是|
|TS|direct|250|high|0/0|0/0|0.482878|0.524936|是|
|TS|direct|568|base|0/0|0/0|0.462290|0.545254|是|
|TS|direct|568|high|0/0|0/0|0.432342|0.574878|是|
|TS|endpoints|1200|base|0/0|0/0|0.365191|0.642892|是|
|TS|endpoints|1200|high|130/0|0/0|0.306453|0.701565|否|
|TS|endpoints|250|base|0/0|0/0|0.461382|0.546810|是|
|TS|endpoints|250|high|0/0|0/0|0.446524|0.561651|是|
|TS|endpoints|568|base|0/0|0/0|0.427670|0.580494|是|
|TS|endpoints|568|high|0/0|0/0|0.397719|0.610394|是|
|TS|relay|1200|base|0/0|0/0|0.340669|0.667490|是|
|TS|relay|1200|high|0/0|0/0|0.279224|0.728884|是|
|TS|relay|250|base|0/0|0/0|0.442295|0.565895|是|
|TS|relay|250|high|0/0|0/0|0.426869|0.581313|是|
|TS|relay|568|base|0/0|0/0|0.406798|0.601392|是|
|TS|relay|568|high|0/0|0/0|0.374705|0.633467|是|

## 实际接点距离及较强缓冲（12项）

用已接收M10内部接点的逐bit坐标，在R0相邻、80µm间隔的四方位中选最小最大Manhattan距离：MT向东916/1348/1548µm，TS向北880/1468/1688µm（最小/中位/最大）。线可以从内部M10接点沿Z上到新增层后跨块走线，没有强制先退到宏边缘。这是距离下界，不证明130根线同时可布通。

endpoints为新增BUF_X8发送、BUF_X2接收；relay再加一个BUF_X8中继。high使用C′0.233086494、R′0.0225；section使用独立理想截面C′0.336771929、相同R′。两者都不是标定工艺或实际三维布线提取。

|接口|方案|长度µm|RC条件|C/slew违规|setup/hold违规|链路setup ns|链路hold ns|声明条件通过|
|---|---|---:|---|---:|---:|---:|---:|---|
|MT|direct|916–1548|high|98/17|373/0|-0.317282|0.633307|否|
|MT|direct|916–1548|section|130/84|3090/0|-0.413064|0.691797|否|
|MT|endpoints|916–1548|high|0/0|11/0|-0.243808|0.606884|否|
|MT|endpoints|916–1548|section|9/0|101/0|-0.290248|0.640209|否|
|MT|relay|916–1548|high|0/0|17/0|-0.266090|0.628278|否|
|MT|relay|916–1548|section|0/0|324/0|-0.313493|0.663086|否|
|TS|direct|880–1688|high|78/64|0/0|0.324762|0.621483|否|
|TS|direct|880–1688|section|130/72|0/0|0.243035|0.678007|否|
|TS|endpoints|880–1688|high|0/0|0/0|0.377193|0.598236|是|
|TS|endpoints|880–1688|section|65/0|0/0|0.332254|0.630489|否|
|TS|relay|880–1688|high|0/0|0/0|0.354789|0.619459|是|
|TS|relay|880–1688|section|0/0|0/0|0.308616|0.653258|是|

## 电容模型的独立核对

二维有限体积、2µm宽/厚、0.8µm下间隔、εr3.9，单下连续接地平面/再加两根接地邻线/再加上连续接地平面的C′分别为0.219417/0.249961/0.336772fF/µm。0.2/0.1/0.05µm三档网格，最后两档相差<0.37%；加远外边界相差<0.71%；能量、电荷、残差、平行板解析控制和错误面距负例通过。

真实M10/M12是图案而非连续平面，三维交叉线、介质标定、开关相关耦合未建模。因此不能用这些数值宣称真实工艺电容或上界；它们说明原high不能被当作普遍保守上界。

## 给主线的边界建议

1. 保留混合内部接点。按输出驱动—原生寄生—允许线负载—接收电容定义接口契约，分别规定最大线长/RC、扇出、输入到达预算、输出延迟预算和setup/hold，而不是仅写“有M10 pin”。
2. 长线的负载可以用预制较强发送缓冲、必要的接收隔离和中继分段处理；这些有源器件必须在固定M1–M10底座内预先放置供电、布线验收，或成为固定中继小宏。M11/M12本身不能提供驱动，不能待定制时临时增加FEOL器件。实际位置、接点接入和本地8µm假设仍需验证。
3. M→T的ready跨宏组合路径需要单独处理。在已测0.8ns输入/0.8ns输出预算下，短线也可能不满足300MHz，单纯加缓冲不能保证解决。先用真实外部控制器的寄存器与连线时序分配预算；若不够，再采用能正确处理在途数据的弹性缓冲/信用或局部寄存控制，并验证协议与延迟。不得直接插一只ready寄存器、添加false path或随意放宽约束来宣称通过。
4. 不把全部接口统一堆满缓冲。原生短线已经满足时，加门会增加延迟/功耗；从具体接口结果选择资源。当前仅覆盖单下游、声明环境和代表性链路，不外推广播、多跳、所有宏或完整模型。

BUF_X8/BUF_X2的Liberty单元面积分别为3.458/1.064µm²。130根线的8→2端口候选共260门、587.86µm²；8→8→2含中继共390门、1037.40µm²。这只计标准单元面积，不是放置留白、供电、pin接入或routing面积。

## 来源、资源与复现

run907源commit `7383a79be199987af204abf3249891aadf68e4ac`；run908源commit `b591fd8fd38a087237ca139a29e0d127f8266361`。完整源/工具/输入/输出SHA在每任务receipt及本地捕获index。

93222与93236均自然COMPLETED/0:0，分别34:05和14:07。实验后重新核验M/T/S原始Verilog/SPEF/SDC九文件及三个原physical回执SHA不变，见`work/YUZE-LU/121/interconnect-study-20261029/production-source-readback.json`。

run907资源：`{'max_parallel_tasks': 6, 'default_cpus': 16, 'largest_sampled_tree_rss_gib': 6.097774505615234}`；run908：`{'max_parallel_tasks': 6, 'default_cpus': 16, 'largest_sampled_tree_rss_gib': 6.09674072265625}`。实际峰值并发不超过6个独立16CPU任务，任务即完补位。Issue121共享最多8allocation、pending/unknown计入；run908初次准入无空位时没有提交或挤占其他作业。

服务器原始目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-{901..908}`。大Verilog/SPEF/ODB及完整全零扇出字典留在授权服务器。派生结果摘要只把该字典替换成计数/字典SHA，原始报告SHA绑定原receipt，其余字段不改。

```powershell
python -m unittest discover -s project/experiments/block_v1 -p test_interconnect_spef.py -v
python scripts/check_project.py
python project/experiments/block_v1/interconnect_pin_profiles.py . NEW_PIN_PROFILE.json
python project/experiments/block_v1/interconnect_cross_section.py NEW_SECTION.json
python project/experiments/block_v1/interconnect_collect.py block-v1-20261029-907 NEW_RUN907_CAPTURE
python project/experiments/block_v1/interconnect_collect.py block-v1-20261029-908 NEW_RUN908_CAPTURE
python project/experiments/block_v1/interconnect_report.py . NEW_RUN907_CAPTURE NEW_RUN908_CAPTURE NEW_REPORT.md
```

重新测量必须生成新run ID、重新bundle精确Git对象，经原共享dispatch提交。不能修改旧源或重复提交已有关联job的任务。此报告不更新主线Issue完成状态、不授予制造/完整P&R/共同CTS资格。
