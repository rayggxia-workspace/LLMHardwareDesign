# 当前 V507 的 GRT 阶段证据

Refs #121 / PR #122。507/93623已进入实际详细布线。5份原始小文件、1份完整GRT JSON的大文件SHA索引、311份源Git blob及四份RTL/505映射与功能/515 CTS来源绑定通过；源3e5a4c25838bb6d6e1bf2ead63ae69d0dcf2c2ab，归档bfc785a25e0a55c675d97bbee5205ac55b7c59fa1a95ebed893b46ee20ff021c。

GRT setup WS为−0.00631628ns、TNS−0.0102154ns、5违例；hold WS为+0.0784364ns、TNS0、0违例。maxcap28/maxslew1，全部保留，不豁免。它们是阶段结果，详细布线、fresh RCX和全部最终门仍须完成，不能据此授予或否决最终资格。

首次就绪检查发现最终日志/JSON尚未生成，在写入采集目录前停止；随后文件齐全才执行本次采集，没有重跑EDA。实际时间、路径、大小、SHA及完整标量指标见[index.json](index.json)。完整JSON保留授权服务器。
