# Issue16：真实普通 LEF 的几何库存

本工具只读冻结 Issue7 / PR10 的 `parallel-blocks-wave2-06` 三份普通 LEF，输出保留 `PIN → PORT → LAYER → RECT` 层次、PG 与 OBS 的原始几何。它不产生合法接入点，不运行服务器 EDA，不更改其他成员工程。Issue15 的 ACT/MXU 物理对照继续由 YUZE-LU 推进。

## 输入与语义

`inputs.json` 固定服务器目录、三个文件、宏名、单位、字节上限及上游记录 commit/blob。上游提交只有 checksum 审计摘要，没有逐文件 SHA-256、底层 RTL commit、完整工具版本或镜像 SHA；这些缺项保持 null。本次捕获的 SHA 是实测，不是与上游预期哈希核对的结果。

`lef58-single-macro-rect-v1` 是明确限制的单宏 ASCII LEF 5.8 profile：完整保留已支持的声明，遇到未知语法整份拒绝。支持原始总线/转义名字、多 PORT、多 LAYER、多 RECT、POWER/GROUND 和 OBS。缺少 ORIGIN/SYMMETRY 等字段保持未声明；重复及框外矩形保留并诊断。非零 ORIGIN 不作坐标变换或边界判断。这个 profile 不是通用 LEF 解析器。

LEF 数值坐标本来就是微米；`DATABASE MICRONS 2000` 表示每微米 2000 DBU，导出用 Decimal 精确乘法，不四舍五入。数据同时保存原始数值字符串、整数 DBU 和源行号。一个 PIN 的多个 PORT 不合并成免费贯通；`clk` 等名字不代替声明的 USE。语义依据 Cadence [LEF/DEF 5.8 参考手册](https://coriolis.lip6.fr/doc/lefdef/lefdefref/LEFSyntax.html)。

## 运行

从项目根目录执行，Python 3.13 实测；解析、捕获、导出和核验仅用标准库，绘图用 Matplotlib。SSH 使用现有本人专用私钥和已确认 known_hosts，禁止自动接受新主机密钥，不复制或提交凭据。

Windows 示例先将进程临时目录设到 D 盘独立任务目录，不修改系统设置：

```powershell
$env:TEMP='D:/Projects/Codex/lef-endpoint-export-20261022'
$env:TMP=$env:TEMP
$env:TMPDIR=$env:TEMP
$env:PYTHONPYCACHEPREFIX="$env:TEMP/pycache"
$env:MPLCONFIGDIR="$env:TEMP/matplotlib"
python scripts/check_project.py
python scripts/check_research.py
```

先提交源码和配置，保证 `git status --porcelain` 为空。每次捕获和导出都用**全新目录**，禁止覆盖历史运行；下例的密钥路径使用本机实际值代入，不把私钥放进项目。

```powershell
python project/experiments/macro_endpoints/capture.py --identity <本人已有私钥> --known-hosts <已确认主机文件> --out D:/Projects/Codex/lef-endpoint-export-20261022/frozen-inputs-01
python project/experiments/macro_endpoints/export.py --snapshot D:/Projects/Codex/lef-endpoint-export-20261022/frozen-inputs-01 --out project/experiments/macro_endpoints/local_runs/issue-16-run01
python project/experiments/macro_endpoints/verify.py --snapshot D:/Projects/Codex/lef-endpoint-export-20261022/frozen-inputs-01 --run project/experiments/macro_endpoints/local_runs/issue-16-run01 --replay
python project/experiments/macro_endpoints/report.py --run project/experiments/macro_endpoints/local_runs/issue-16-run01 --out D:/Projects/Codex/lef-endpoint-export-20261022/figures-01
python project/experiments/macro_endpoints/archive.py --snapshot D:/Projects/Codex/lef-endpoint-export-20261022/frozen-inputs-01 --run project/experiments/macro_endpoints/local_runs/issue-16-run01 --figures D:/Projects/Codex/lef-endpoint-export-20261022/figures-01 --out project/experiments/macro_endpoints/results/issue-16-run01
python project/experiments/macro_endpoints/archive.py --verify project/experiments/macro_endpoints/results/issue-16-run01
```

`capture.json` 记录实际 SSH 读取的原字节 SHA、读前后 stat、远端身份和 Python、输入配置与捕获源码 commit。`manifest.json` 固定解析/导出源码及配置 SHA，四个业务输出可逐字节重放。`evidence.zip` 无损保存 `inputs/` 和 `outputs/`，外层清单索引 ZIP、表图和两份 manifest。离线恢复时将 ZIP 解压到新的 D 盘任务目录，用其中 `inputs` 和 `outputs` 运行上述 `verify.py --replay`；本地必须保留对应源码 Git 对象。校验哈希用于完整性，不构成第三方签名认证。

## 验收边界与下一步

人工复核和独立审阅应核对全部名字、PORT、RECT、PG/OBS、原始坐标与 DBU，不能只数 SIGNAL。图中点只是信号 RECT 中心，不是 routing track、via 或合法 access point。后续仍须补 DEF 实例方向、RTL/Lib 位匹配、技术层/via/间距/enclosure/OBS 规则、时序与驱动负载、PG 连通和等价性；合格硬宏及物理 H2/PPA 均未在此验收。
