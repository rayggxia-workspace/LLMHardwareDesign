# PR17 已配对物理结果的补充审计（2026-10-23）

固定提交：`ce5896de47921fcdc422c4ac9c05cefcb6666bff`。本次刷新 PR17 head 正是该提交，PR open、draft=false，Issue15 open、status:in_review；评论接口返回0条。本补充更新2026-10-22旧审计中“尚无合格配对”的时点结论，旧报告原样保留。**目前已有通过记录中全部工程门槛的正式配对，但仍待独立审查/合并，不能写项目done。**

已按统一Skill只读工作，唯一认证身份 Liangruizhi / 182389313 / 2663955430@qq.com。没有修改远端、他人文件或ref-project，没有重跑/接管物理实现。

## 主要结论与一个交付缺项

**数字与配对来源一致；Git中三个已核验文本产物的原始字节SHA与报告manifest不一致。** 三者转成CRLF后分别精确匹配声明SHA，符合生成工作树与Git文本换行表示不同的情况。这是可复现性/交付字节边界问题，不是发现了PPA数字计算错误。CRLF重构只作诊断，不把原始Git字节检查记成通过。

独立脚本 `audit_paired.py` 直接读取固定Git快照，不导入/调用生产compare，完成407项字段、算术和来源一致性断言，覆盖11个选定来源、33条封存输入绑定。15个下载源的Git blob SHA逐一核对一致。报告manifest的HTML、comparison.json、comparison-inputs.json三文件原字节SHA均不匹配；六个图像产物未在本补充重新下载/哈希或目视核验。

机器结果：`audit-results.json`，状态 `NUMERIC_CONSISTENT_WITH_GIT_ARTIFACT_SHA_MISMATCH`。它不是物理重跑或制造签核。

| 文本产物 | Git LF 原字节 SHA-256 | manifest 声明（恰为 CRLF 重构 SHA） |
| --- | --- | --- |
| comparison-inputs.json | a2b3220f32d45f01ec635a2ce2892271210e0ecff90ab6a16f0621d2adbbce5d | f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d |
| comparison.json | dd25eabd548f4f036e854a4e030cde1b395dbf72efbf4c632c06ef03985611d6 | 2051d26f19da9895b05315d2e57962668a8a166476d2f8661f3ee791a29e2c2d |
| issue-15-opentpu-results.html | caeaee2d3ddbab65855d8ce01027e295e955b9cfe09d015ab81605a50075d48b | 2b67168409aae8ff31f09400d2917f64db8b404782a5a5dd2cc17e5f8ab507bc |

建议由本任务负责人后续补充Git交付字节清单并说明原生成CRLF快照身份；新生成流程固定编码/换行，保留旧执行来源和旧manifest。不要仅在检查器里无说明地忽略换行，也不要把新SHA倒填为旧物理运行输入。此次只读补充没有代其修改。

## 正式配对及独立复算

[固定选择文件](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ce5896de47921fcdc422c4ac9c05cefcb6666bff/project/experiments/opentpu_compare/selection-reuse20-merged13.json)：
块内ACT89671、MXU89677、merged89678；拆分 `top-split-reuse-20-01 / 89829`，合并 `top-merged-13 / 89772`。

| 指标（块内加父层） | 拆分 | 合并 | 拆分相对合并 |
| --- | ---: | ---: | ---: |
| 叶单元面积 µm² | 484240.4 | 482252.4 | +0.4122322668% |
| 信号线 µm | 6647739 | 6204600 | +7.1421042452% |
| 信号通孔 | 1322289 | 1284106 | +2.9735084175% |
| 完整setup WNS ns | +0.102306 | +0.065642 | 不是频率提升证明 |
| 完整hold WNS ns | +0.036146 | +0.013027 | 两组通过当前约束 |

分解复算：
- 叶面积：拆分468605.5+15634.9=484240.4；合并465542+16710.4=482252.4，差1988.0µm²。硬宏占地与共同die另列，未加回自身叶面积。
- 信号线：拆分3286032+3361707=6647739；合并3535985+2668615=6204600。拆分块内少249953µm，但父层多693092µm，净多443139µm。
- 通孔：拆分1248336+73953=1322289；合并1226927+57179=1284106，差38183。
- 父层包含外部IO、时钟和块间连接，不能把所有差额归给685bit ACT/MXU边界；当前setup最差路径也不是直接测量边界本身。

所用原生实现runner：拆分 `edc6479bbf993669aba7eae405ede1610baa538a`，合并 `182898cca91c3b403985b6d2278b143ef2dd9852`。报告生成runner `8a646d80b08845079da4e1b7a544233d6a94ffbf`；它们与交付head是不同身份，未互相替代。

六类证明分别为三块功能89687、父层功能89831、非支持库存89733、双子块RC89798、RC覆盖89832、五个完整ODB成本89833。封存记录内五个实现的DRC/天线/电气计数及有符号余量、setup/hold/TNS、两父层最终PG与完整STA均通过。父层逻辑锥拆分2348/合并1662、差异0；证明对象为共同映射逻辑经物理支持变换后的结构，不等价于上游RTL通用形式证明。

## 对线路复用及补充对照的核对

主拆分从源20仅将place13151 BUF_X4升至X8；记录显示合法化后1实例变化、2条关联信号线路清除、11952条线路保留到DRT输入。完整最终ODB有11954条有线路信号网。这里不能推断“最终11952条线均冻结”，因为DRT仍可改变任何网络。

主拆分原生完整ODB线长3361438.35µm，DRT主口径3361707µm，差268.65µm，约0.008%；五个实现的对应输入ODB/SHA、主DRT口径及检查记录均已匹配。1%阈值用于识别明显成本漏计，不是放宽DRC、电气或时序门槛。主表使用统一DRT口径，未只统计新布两条线。

补充 `results/alternates/full-clear21/comparison.json` 的拆分89826同样从源20做同一驱动升级，清线后全量布线。相对主拆分：面积相同、总线长+42µm、通孔−2、setup WNS+0.000008ns、hold相同；这些差值已独立按两个comparison JSON计算。没有重取补充539KB输入快照及其全部证明，所以本补充对其限定为**交付摘要的数值交叉核对**，不冒称独立重审全部15个唯一来源。

## 当前证据允许说什么

- 可以说：在此small配置、Nangate45 typical、固定宏位置/外部引脚/共同die和相同时序预算下，两种同起始计算/状态/SRAM资源的H1实现均通过工程检查；拆分在最终统一口径下叶面积、线长和通孔略高。不是普遍最优Block划分。
- 初始169109映射单元、37023DFF、12 synthetic SRAM相同；新增/升级的BUF、INV、CTS等有源支持资源可以不同且计入成本。不能把“同起始资源”说成“所有终态硬件完全相同”，更不能视为固定有源层之后只换少量金属。
- 本轮允许完整父层信号布线与新增有源缓冲；父层M10以下信号线占比拆分99.391558%、合并99.256017%。**H1成立不等于H2少量掩模定制已经实现。**
- 统一40外部端口/1662bit，2.5ns clock、0.5ns数据IO预算、BUF_X4/Z输入、5fF输出、50ps时钟转换。完整时序取真实父/子网表与SPEF，不相加各块WNS。
- 最终只读接口检查记录的最薄宏接口slew余量约+1.549039ps；单typical的薄余量不能推广到多角点鲁棒性。ORD-0011层次STA开发功能、STA-0441对clk的input-delay被忽略、synthetic SRAM无真实GDS、上游RTL等价与制造签核未完成等限制仍保留。
- **它不是Issue27/29 attention端口/队列模型的校准。** openTPU ACT/MXU的真实几何和时序结果可启发“驱动/电容/缓冲/时钟/接入层预算必须显式化”，但不能把本对照的面积或WNS直接转换为本attention DAG的cycle、功耗或端到端吞吐。

## 固定来源与审查范围

主来源：`docs/experiments/issue-15-opentpu-comparison.md`、HTML、selection、results/comparison.json、comparison-inputs.json、report-manifest.json、delivery-validation.json、最终接口检查、交接/状态，均固定于ce5896d。所有15份文本的Git blob/SHA-256清单见 `evidence-manifest.json`，API状态见 `github-status.json`。

源文件副本只在本独立审计目录。未运行生产compare、未访问原始服务器ODB/SPEF、未重算物理流程、未重验六个图像文件、未宣称已替代PR独立批准。工程结果与远端验收状态分别记录：已形成并上传，PR待审查/合并；登记与看板既有pending未由本任务改变。
