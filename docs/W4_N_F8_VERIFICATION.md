# W4独立数值及RTL证据读回

状态：所列N与preNorm F8有界合同内，独立数学预期、真实RTL及故障生命周期测试已有证据；整个L4/W4全组合/W5、完整模型和物理未验收。Issue151/PR152的外部审查、上传、合并和项目状态由根任务分别记录。本代理只写独立draft，不修改正式包/状态，不执行ModelSim/服务器。

## 1. 实际执行与版本

根任务在Windows本地使用ModelSim SE-64 2020.4，分别执行n-r01与f8-r01；本报告根据实际receipt/log/source读回。研究parent0101cc7、native7078786固定；新文件在执行时尚未commit，以精确输入SHA绑定，最终交付commit由根另记。没有将14叶编译通过解释成14叶功能/物理资格。

| suite | 实际结果 | 运行回执SHA256 | 仿真日志SHA256 |
|---|---|---|---|
| n-r01 | compile0/sim0，29唯一CASE_PASS，20336cycle | e2abfd4d095d135f0ee3270f4c81504b9c06cc7f19aa42ad1057983c67cb7bc2 | fc67d7061843a530dc97a579b12227bd72819c17d04732bc73772b05de6cf162 |
| f8-r01 | compile0/sim0，25唯一CASE_PASS，16323cycle | 39cf9fd1a263749ada7450c71a7924e029aa26966ca2523d2f5a86e38c6a29fb | 0dad4670616f90fb596bffef0eb06df996c3f9a410c6832e407539552f2c03b0 |

位置在包根 `runs/n-r01` 与 `runs/f8-r01`。`review_w4_evidence.py`核对CASE顺序/唯一数、退出码、日志SHA；新RTL/TB的draft=integrated formal=run/source=receipt。冻结vectors/参考脚本的draft=formal=receipt；期望常量已自包含在实际编译的SV TB，无运行时SVH依赖。它只读现有仿真文件，不重新执行RTL。

Nctrl SHA `02e6e8f0538c8423481c2f30a3d0a2d392bae583551cbf7ffcc7cd947674cd01`；F8top `54905280f8b9dbfcd7440981fd4f4244c509ea8de5e1a8912a050c457ad75a8e`；N TB `75964257de4b6d979fb35c36a74a35527590201bc898ad73f2c77676ea07b868`；F8 TB `996e53d0a9501339ed6db0f2e22a1c11686e1676048d91a228472820192e252a`。两TB已冻结，不为报告扩测。generator曾将协议marker数误写为9，现终端摘要纠正为10；已测SV marker及数值没有改变。

## 2. N29场景的实际边界

11数值组逐字对照数学预期；8准入错误分别count0/258、mode3、epsilon0、范围越界、src-dst/gamma-dst/src-EXP重叠。10其余marker含native命令与应答保持、Softmax257最终写ACK门、helper请求/应答保持、准入错误后复用、真实native非法op15的poison/reset恢复、helper读响应error、第二目的写ACKerror保留已存前缀、EXP写ACK待回reset、held BEGIN response reset。部分marker包含恢复成功服务，29不是服务总数，也不是所有guard笛卡尔积全覆盖。

TB实际实例化S16k、原Shelper、N及新controller。host初始化也走同一helper；源/gamma尾部故意放非零垃圾，再核native有效count和tailmask；scoreboard检查每次S地址/读写顺序和结果、native阶段、raw/EXP/gamma血缘、成功结果实际ACK后完成、完成flag保持与一次消费。错误响应注入位置与原生N非法命令分开记录，不用mock数组替代真实ACK。

总量：S读715、写288、ACK1002；Ncmd624/rsp623；服务completion32。21个成功服务合R642/W285/ACK927/N547。其余贡献为：native错误R1/ACK1/N2；读响应错误R1/ACK1/N1；第二目的ACK错误R37/W2/ACK39/N37；reset待回EXP写R34/W1/ACK34/N36；reset held BEGIN N1/rsp0。故S请求1003比ACK多1，正是reset取消EXP300写ACK；N响应少1正是reset取消held BEGIN响应。32完成=21成功+8准入错+3poison错；另两取消服务不凭空生成完成。不作全suite无条件请求/响应守恒声明。

## 3. F8 25场景的实际边界

六组完整有界输入逐阶段检查S464..475以及S448窄化覆盖、原残差、T最终字。正常帧逐次39/39 S、N1服务/4native、M15/15与3loader、E2/G1/T1/release计数；保持16输入全部ACK后才RUN、早start不排队/heldstart只接受一次、实际padding零、S唯一owner、EXEC状态不作tensor、M结果保存后才复用。

继承W3有限生命周期场景，并新增N服务响应在474 ACK后保持、真实N非法op导致无投影/无T输出且协调复位恢复、held N服务响应reset、N474目的ACK待回abort。还包括M/E/G真实非法命令错误，G所有已接受pair退休后报错；两类协议错误与done_saturated分离。已有DONE遇abort和ready仍只消费一次；已被take的T输出前缀不能回滚。

日志汇总input564、Sreq1224/Sack1221、M413/413、Ttake25。S差3分别来自prestart输入写ACK、RUN原X466写ACK、N输出474写ACK的协调abort；正常成功帧单独断言39/39。reset取消生命周期不表示RAM清零，也不能保证尚未重新填满的新frame可启动。

## 4. Python与剩余门

本代理实际执行 `python scripts/check_project.py`：PASS，只是管理结构。`check_w4_oracle.py`先取得201103项Python断言PASS，包括全65536个S16值RNE3/clip与Fraction参考、整数Newton与独立二分root、RNE30负数ties、N11/F8六组逐边一致、EXP1025/G2564源表一致、UTF8/LF。后续加入报告后UTF8/LF断言数量随文件数增加，以最终`w4-oracle-checks.json`为准。Python生成、检查、证据读回均不冒充RTL执行。

执行中发生过的Python准备失败（初版W3 fixture回退路径层级错误、checker中not表达式语法错误）均已修正。独立review另发现旧生成器依赖本机旧W3 draft、fresh输出目录未预置参考脚本时无法复算：现已改为只读`--root/work/Melodydt/151/w3-contract-vectors.json`正式输入，参考脚本SHA从`__file__`同目录读取，输出目录自动建立；`--directory`仅输出。旧运行使用的生成器原字节保存在`prior-inputs/build_w4_vectors.py`，SHA `660a578ec24c74a6c11e49e66ed8fdb53c5d9fe5990468938b6d29c870ee9423`，与原n/f8回执相同，原回执不重写。N TB generator同时补可指定`--directory`，默认生成逻辑不变。

已实际在空`repro-output`目录重建两份vectors及两TB，四个文件SHA均与已跑版本完全相同，见`w4-generator-reproduction.json`；当前生成器与旧运行元数据输入明确分开。该路径修复没有改变任何数学预期、已编译RTL/TB字节或已执行场景，不以此虚造第二次RTL仿真。这些Python准备失败不是RTL attempt，不覆盖任何原仿真回执；是否有额外旧回归以根的独立回执为准。

剩余：完整A和模型特定完整F前后Norm/布局、不同gamma/epsilon与产品scale误差/质量、超过257的controller扩展与全部guard组合、TopK服务、跨服务phase保留/回访、一般拓扑/同S/T/forkjoin、MEM真实接口/容量、完整有限产品ROM、跨产品同M1–M10以及综合/物理。现有P2/W1一般门继续开放，本报告不替代外部设计/PR审查。
