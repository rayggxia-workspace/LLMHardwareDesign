# ACT/MXU 冻结三视图接口合同（Issue19）

目标：复用 Issue7 已有 8 组、685 bit ACT/MXU 连接合同，把 wave2-06 的 Yosys 端口、Liberty 与 Issue16 原字节 LEF 逐 bit 关联。父层包含40个外部端口、1662 bit；computing 同时反馈 ACT.r_use 和导出父层，clk 同时进入两宏。

检查证明所选版本名字、位宽、方向和合同边界一致性，不证明完整 RTL 等价、时序弧覆盖、合法 via/access、PG 连通、新 matched 宏资格、PPA 或 H2。具体结果以 results/ 下实际归档为准；源码存在不等于实验通过。

## 数据和解析边界

- inputs.json 固定十个服务器文件、只读路径和9 MB总量上限，四个elab/experiment SHA来自PR17固定提交。读取比较前后stat和SHA，严格验证SSH已知主机，不在服务器写文件或启动EDA。
- 两份LEF和旧capture来自Issue16固定ZIP；捕获的生产索引同时验证 boundary、elab、experiment、Liberty、LEF共十项SHA。生产索引属于同一生产过程，非第三方签名。
- top-contract-completion.json保留PR10固定提交原字节；既有685位相等性证明来自此记录。本次将合同应用于冻结视图，不重新宣称父层RTL仿真。
- Yosys bit ID仅模块内有效，输出别名和0/1/x/z常量单独保留；物理边界pin不因逻辑ID相同而合并。
- ANSI header支持input/output logic/wire、字面packed范围与同声明继承；多维只接受零起始降序Yosys展平。cmd_t类型定义未捕获，宽度明确取自Yosys，未重新解析完整RTL类型。
- Liberty解析器完整解析带行号的语法树；归档保存原始Liberty及bus/type、direction继承、pin名称和属性。时序原文保留，不导出完整AST、不验证弧覆盖或正确性；缺失电容/约束不补值。
- LEF按精确名字关联，保留PORT/RECT、方向、USE、行号、微米和DBU。PG以LEF USE分离；clk合同角色与原始USE分开，不把SIGNAL改为CLOCK。

## 复现

Python 3.11+，本工具仅标准库。根目录执行：

~~~powershell
$env:TEMP='D:/Projects/Codex/interface-contract-20261022'
$env:TMP=$env:TEMP
$env:TMPDIR=$env:TEMP
$env:PYTHONPYCACHEPREFIX="$env:TEMP/pycache"
$env:MPLCONFIGDIR="$env:TEMP/matplotlib"
.venv/Scripts/python.exe scripts/check_project.py
.venv/Scripts/python.exe scripts/check_research.py
~~~

正式捕获及运行要求已提交且工作区清洁。路径参数用已有专用密钥/known_hosts，私钥不入仓库；输出目录须全新：

~~~powershell
.venv/Scripts/python.exe project/experiments/interface_contract/capture.py --identity <已有专用私钥路径> --known-hosts <已有known_hosts路径> --out D:/Projects/Codex/interface-contract-20261022/frozen-inputs-01
.venv/Scripts/python.exe project/experiments/interface_contract/run.py --inputs D:/Projects/Codex/interface-contract-20261022/frozen-inputs-01 --out project/experiments/interface_contract/local_runs/issue-19-run01
.venv/Scripts/python.exe project/experiments/interface_contract/verify.py project/experiments/interface_contract/local_runs/issue-19-run01
.venv/Scripts/python.exe project/experiments/interface_contract/archive.py project/experiments/interface_contract/local_runs/issue-19-run01 --out project/experiments/interface_contract/results/issue-19-run01
~~~

capture与run manifest各记录实际clean commit及源码SHA；所有输入与派生文件记录SHA/大小。verify默认验证Git blob、完整文件集合与逐字节重放。它复用生产算法，不能替代独立审计。

离线恢复：先核对archive-manifest.json里的ZIP SHA，把evidence.zip解压到D盘新任务临时目录，verify.py指向包含inputs/及manifest.json的解压根目录。仅实际归档结果可作证据。

格式参考：[Yosys write_json](https://yosyshq.readthedocs.io/projects/yosys/en/0.43/cmd/write_json.html)、[Synopsys Liberty 2017.06手册](https://media.c3d2.de/mgoblin_media/media_entries/659/Liberty_User_Guides_and_Reference_Manual_Suite_Version_2017.06.pdf)。文档仅参考语义，非生产工具版本；实际Yosys creator原样保存，UNKNOWN Git版本保持未知。
