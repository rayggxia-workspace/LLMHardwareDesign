# 分离 min/max 的原生诊断原型

对应 #127 / PR #128，2026-10-27 CST。继 run168/169 来源、PG、完整 timing V 和 OBS 接收后，继续实测时序模型的修正方向。本报告不替换已发布候选，不改变 1 ps 诊断门槛，不签发资格。

## 修改与隔离

固定上游 OpenSTA `bc7af6f02679074eaf43657488ca117c05f98eed` 的原始 `MakeTimingModel.cc` SHA-256 为 `ee117099f485ce17f9fdd24bbaf62569cb3f56107615bf88411aaebd889acde0`。私有变体只把构造器的输出分析选择改为 min，并让 input-to-output 弧使用该选择；没有新增伪造的 `write_timing_model -min` 开关。修改源明确标记为修改版，保留原许可证；补丁见 `min-output-probe.patch`。

构建复制 `libOpenSTA.a`，只替换副本中的该对象，再链接成新的 `sta-min-output-probe`。原 STA、静态库、源码和构建参数 SHA 均保持不变。测量仍使用原始 STA；新工具只参与 min 模型导出。min/max 模型通过受支持的 `read_liberty -min/-max` 分开加载，使用同一 cell 名，不混用分析方向。工具、编译/链接 argv、输入、模型、测量收据及原始输出 SHA 见 JSON。

这是本机私有诊断工具，没有修改主线 exporter、服务器安装、活动作业或统一资源预算。不能把该原型描述成项目已有受支持功能。

## 小控制：24 组实际对照

两个输入驱动（BUF_X1/X2）× 三个输出负载（0/2/10 fF）× 两种模型方案（原单模型/分开 min-max）× 两种长支路（0/8 级 BUF），共 24 个 native pair。单一 typical 库，显式 SPEF；每个场景重新导出，flat/abstract 使用相同 SDC，并从原始 TSV/SPEF 复算测量。

| 2 fF、8 级 BUF | 原单模型 | 分离模型 |
| --- | ---: | ---: |
| 输出 min rise 有符号 slack 差 | +230.138311 ps | -0.001707 ps |
| 输出 min fall 有符号 slack 差 | +208.133455 ps | -0.004524 ps |

正值表示抽象更乐观。全部分离控制的输出 min 绝对差低于 0.009 ps，max 侧保持原结果。但输入 setup/hold 仍有数 ps 差，不能把输出改善当作整对通过。也不从离散的有限负载点外推无界工作域。

## 真实 T6K A/C

原 run168 的封存请求先按原 `candidate_binding` 独立复验。为隔离工具变体影响，max 与 min 都从同一 full timing V/SDC/SPEF 重新导出；输出为独立 probe，原 candidate.lib/LEF 未变。两路 native context accepted=true，没有 missing instance/net 名称告警，pair 收据与原始测量复算通过。

| 最大绝对 slack 差 | A 原候选 | A 分离原型 | C 原候选 | C 分离原型 |
| --- | ---: | ---: | ---: | ---: |
| 输出 min | 107.274412 ps | 5.669021 ps | 60.402183 ps | 4.885758 ps |
| 输出 max | 6.045831 ps | 6.045831 ps | 4.736656 ps | 4.736656 ps |
| 输入 min | 51.864998 ps | 51.768298 ps | 17.720915 ps | 17.622355 ps |
| 输入 max | 51.866067 ps | 51.866067 ps | 17.722712 ps | 17.722712 ps |

输入与输出的 max 聚合 slack 在重导原型与已发布模型之间逐值相同（差 0）。输出 min 的主要长短路径误差得到缓解，剩余输出近似和输入上下文误差没有消失。A/C 总诊断超差仍为 955/897 项，包含端口 slew；**整体诊断仍未通过，未取得宏资格**。

每路输入 max/min 各有 378 项，前者全部超过 1 ps 且悲观，后者全部超过 1 ps 且乐观。这种符号对称是继续定位的线索。固定源码在生成 setup/hold scalar 时使用数据路径 arrival，而 `swapSdcWithBackup` 不移走外部驱动定义；可能包含已经由父层驱动再次计入的部分。尚未用独立扰动实验证明，不能将这一推断写成已修复结论。另需保留输入线阻、驱动 Ceff 和 port slew 的区别。

## 下一步

1. 支线以独立控制核对输入边界 arrival/驱动延迟归属，保留实际输入 RC，不能仅删除 driver 或线阻换取通过。
2. 主线审查是否采用可维护的 min/max 模型方案；私有工具分叉及仅在有限场景下成立的标量模型均需评估维护成本。
3. 继续声明有限有效工作域、完整适用弧/例外/corner 与误差安全预算；C8 合格来源到位后复用接收器。

当前正式宏资格、完整边界等价和冻结标记均为 false；#127 继续执行。实际分工、登记/看板缺项及恢复入口见本目录 README 与 Issue 最新回执。
