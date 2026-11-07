# 固定 #206 布线的 M11/M12 铜参数提取与对比

[Issue #217](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/217) · 成果 [PR #218](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/218) · 基线 [PR #216](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/216) · 布线 [PR #206](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/206) · 方法 [PR #202](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/202)

**铜主版本将逐网电阻中位数从 20.0000 Ω 降到 7.0112 Ω，最大值从 65.2400 Ω 降到 22.3928 Ω。** 主版本逐网降幅的中位数为 65.01%，所有 2,491 根网均降低。比较对象是原片电阻 0.03 Ω/□ 的未标定研究模型，不能将此结果称为实测铜相对实测铝的提升。

## 固定输入与参数

布线固定为 #206 的 `179ca76ff35673dcb47986e3d873fc2a87dbabbb`，基线结果为 #216 的 `5f055f6cd1349174ecb71ea55bc48e9acd6a618d`；方法依赖 #202 的 `20b945d3cdb73d74778bdccc4952eb4315170cd8`。本次在线核对三项依赖未发生变化。

保留原 ODB/DEF/GDS、M11/M12 宽 2 µm、厚 2 µm、间距 2 µm、层间介质 0.8 µm、2×2 µm 通孔与 M10 落点、相对介电常数 3.9。M1–M10 宏内部保持黑盒，#206 原有 44 个控制、时钟和复位端点的独立边界不变。只在内存中改变电阻参数，不写回源数据库。输入和最终源文件哈希核验通过。

主版本采用接近当前厚度的文献铜膜电阻率 2.04 µΩ·cm，按 2 µm 有效导电厚度换算为 0.0102 Ω/□。通孔主版本保留未标定的 0.08 Ω/个；另外两种电阻率敏感性和零接触电阻的理想铜通孔下限单独记录。20°C 是本次比较的参考温度假设，并非本工艺的标定温度模型。[参数来源、制备条件与边界](../../../project/experiments/m11_m12_rcx/copper/README.md) · [机器可读参数](../../../project/experiments/m11_m12_rcx/copper/parameters.json)

## 服务器结果

| 版本 | 片电阻 Ω/□ | 单孔 R Ω | 网阻中位数 Ω | P95 Ω | 最大 Ω | 逐网降幅中位数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 原研究基线 | 0.03000 | 0.08000 | 20.0000 | 53.2400 | 65.2400 | — |
| 铜主版本 `cu-main` | 0.01020 | 0.08000 | 7.0112 | 18.3128 | 22.3928 | 65.01% |
| 较低电阻率 `cu-low-rho` | 0.00885 | 0.08000 | 6.1256 | 15.9314 | 19.4714 | 69.44% |
| 较高电阻率 `cu-high-rho` | 0.01160 | 0.08000 | 7.9296 | 20.7824 | 25.4224 | 60.41% |
| 理想铜通孔下限 `cu-ideal-via` | 0.01020 | 0.00408 | 6.7075 | 18.0091 | 22.0891 | 66.43% |

所有版本的最大网阻都出现在 `word_1960`。主版本相对原基线的逐网电阻降幅范围为 62.78%–65.79%；固定通孔电阻使总网阻的降幅随线长和通孔数变化，而线段本身统一降为原值的 34%。理想通孔版本进一步将最大网阻从 22.3928 Ω 降为 22.0891 Ω；它只是孔体下限，不能代替实际接触电阻数据。

电容采用原整版场解结果，逐字节保留新 SPEF 的所有非电阻内容。四个版本读回的逐网 Cg/Cc 最大差均为 **0 fF**。逐网最大 Cg+Cc 仍为 `word_1974` 的 **445.8869 fF**（Cg 80.3000 fF、Cc 合计 365.5870 fF）。这符合当前理想导体静电模型：几何和介质不变，金属电阻率不进入电容求解；本次没有再运行一遍相同的场求解，也没有将复用视为独立电容验证。

作业 **99616**，c64/node1，4 核，`COMPLETED 0:0`，耗时 6 分 57 秒，实际时限 `UNLIMITED`。四个版本均通过：

- 每版四个独立 DEF 控制网，共 16 项：原生 M10 线阻、两类上层通孔及默认/零线端延伸。
- 全部 2,491 网、4,982 个实例端点、16,414 条电阻边（7,858 条线段和 8,556 个通孔），逐边按实际坐标解析公式核验。
- 每版完整 SPEF 独立 OpenDB 读回，覆盖 586,172 个非零互容网对、8,234,564 个节点对互容。18,329 个 M11/M12 投影相交网对全部非零。
- 非电阻段统一 SHA-256 `e4039595e18dc7e6e19ce937d7ac93762af8aca58e7163ab0bea7bd30d7c08b5`；所有端点、`*D_NET`、Cg/Cc 记录与原基线字节相同。网对互容读回最大缩放误差仍为 `5.80e-8`。

[完整比较摘要](comparison.json) · [逐网比较 TSV](net-comparison.tsv) · [输入绑定](inputs.json) · [Slurm 终态](slurm.txt) · [执行源码与工具身份](run.json) · [交付校验器](check_delivery.py) · [SHA256SUMS](SHA256SUMS)

## 完整 SPEF 与规则

服务器输出根目录为 `/public/home/yuzelu/PingyangHuang/issue-217-copper-TUcrqCig/job-99616/result/`。下表路径均相对此目录，完整大文件保留在服务器。

| 版本 / SPEF 路径 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `cu-main/assembly/field.spef` | 353,878,655 | `9586929ccee1cd33627657e336538aca8634abcaf6e32e357d6abe271943e532` |
| `cu-low-rho/assembly/field.spef` | 353,887,167 | `a3eeef483f27c68580a7f7a168a739bbe63f4c2bd847776566afa24c9780bf4e` |
| `cu-high-rho/assembly/field.spef` | 353,878,481 | `aa56e063a1b810069e50f03f2514e6a1ed1780479e31fb9a18e8fbd45b47029b` |
| `cu-ideal-via/assembly/field.spef` | 353,904,323 | `7b7caf17f9f9ad9ff30a5e5de32d978d740eb2292139c3942408cbbe14e6a2cd` |

主版本的[生成规则](cu-main/copper.rules)与服务器输出字节一致。它由原规则只改变 M11/M12 的 1,046 行 DC 电阻列；原生层和电容列不变。该规则在本流程中仅用于 R；跨层 C 仍须使用 #202 的场解方法，不能把此文件当作已修复跨层互容的单一 OpenRCX 规则。每个版本的技术配置、控制网与读回回执在同名子目录。

## 复现与校验

服务器执行源码提交为 `b84bf3cc74d41a9fa9929b53ee1091255ba5818e`。输入归档 SHA-256 为 `a7dcef05a2511c3de7af2695f2481c146f65fc73d7b83bc4b293f3f2f5af969b`，归档留在上述提交目录的 `input.tgz`。Git 归档导出使用了 Windows 文本行尾；提交内容与归档经 LF/CRLF 归一核验相同，实际执行字节哈希另列于 `run.json`。证据包 `evidence.tgz` SHA-256 为 `34ed3d6da97addeda87a24645a6a9dec8face2df81e4dd0040c0d1c24bd32f0b`。

容器镜像和 OpenROAD ELF 的实际 SHA-256 见 `run.json`；OpenROAD 自报版本为 `unknown`，没有编造版本号。Python 3.10.12。使用同版源码与 #215 的轻量证据文件，在新的本人服务器工作目录运行：

```bash
root=/public/home/yuzelu/PingyangHuang
sbatch -p c64 -N 1 -c 4 --time=0 --job-name=hpy-cu-pex --output=slurm-%j.log \
  project/experiments/m11_m12_rcx/top_pex.sbatch copper \
  --prep "$root/issue-215-top-pex-zOz2uxIr/job-99157/result" \
  --assembly "$root/issue-215-top-pex-paPJkRpL/job-99183/result" \
  --baseline-readback "$root/issue-215-top-pex-ZU0ApzLR/job-99186/result" \
  --receipt "$root/issue-215-top-pex-zOz2uxIr/route-206.json" \
  --fit "$root/issue-199-rcx-w4JD5wxq/job-98197" \
  --params project/experiments/m11_m12_rcx/copper/parameters.json
```

本地交付检查：

```bash
python scripts/check_project.py
python -B work/huangpingyang04-lgtm/217/check_delivery.py
git diff --check
```

服务器四版本提取与读回、本地管理结构、交付校验器、Python 语法、Git 差分、暂存 SHA 和新文档链接检查均通过。未执行系统 STA，RC 乘积不能当作系统路径延迟。节点局部电容分布仍沿用 #215 的验证边界。本次也不验证铜加工良率、衬层结构和可靠性。

## 协作回执

采用 `rayggxia-project-collab 1.0.0`，项目 `llm-hardware-design`，执行账号/负责人 `huangpingyang04-lgtm`。成果为 PR #218，基于 #216 分支，Issue #217 保持开放 in_review，待独立审查。登记沿用 [management-hub #5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending；缺少 `config/board.json`，看板实际状态 unverified、同步 pending，待维护者指定处理人并补配置。优先级和独立审查人待指定。后续入口为本页及 Issue #217。
