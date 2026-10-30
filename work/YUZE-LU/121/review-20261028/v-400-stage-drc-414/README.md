# V400 原生全芯片 DRC 阶段定位

Refs #121 / PR #122。2026-10-30 03:19 CST 归档 9 份原始文件，index.json 保存逐份 SHA/字节。

两个只读诊断在 R404/93555/node21 已有 allocation 内并行执行，指定 16–31、32–47 两个互不重叠的 16CPU mask，保留父流程 0–15。启动前检查父队列仅运行 R、无同父 cohost、固定 SIF SHA；节点内 MemAvailable 必须大于两项 12GiB 预测乘 1.2 加 16GiB。没有新增 allocation 或取消任何 EDA。

源 b32cfb7bd0c001a6fdf33e258a8855c93c4fc4c5；脚本、源 ODB SHA 和 V400 回执绑定记录于 launch.json。route/fill 两项均正常 COMPLETED/0；输入 ODB SHA 前后一致。对 5_2_route.odb、5_3_fillcell.odb 得到的原生报告，与 401 检查最终 6_final.odb 得到的报告**逐字节相同**，均 433 项违规。

结论仅为阶段定位：违规已存在于 route 数据库，后续 fill/final 阶段没有改变这份违规报告。还不能据此断言路由器缺陷或具体几何根因，不能作为修复或物理接收。旧 V400 的负时序和 DRC 拒收保持；新 V410 继续正常执行，其结果单独验收。
