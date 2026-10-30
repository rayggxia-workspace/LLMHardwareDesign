# V350 CTS 原始报告与内置等价证明

Refs #121 / PR #122。源 `845bf03cd935066bf209acf8bd21c789bac89b4d`，原生任务 `93210/node17`；2026-10-29 14:20:53 CST 采集。此处只封存阶段证据，V 尚未最终接收。

CTS 内置 LEC 于 14:17:59 CST 完成，51126 输入和 51115 输出匹配，diff0/diff1 均为0，求解为 UNSAT/IDENTICAL。报告最差 setup −0.04 ns（cmd_valid → stats_sumsq[0][79]），hold −0.23 ns（reset → rsp_data[86]）；保留完整路径及源网表单元/输入端口映射。TNS max −0.28 ns。二者均为 CTS 中间寄生估计，不代替最终 fresh-RCX STA。

11 份原始文件按 SHA 核验；源归档全部 308 Git blobs 和全部 V RTL SHA 绑定核验，见 [verification.json](verification.json)、[index.json](index.json) 和 [path-source-mapping.json](path-source-mapping.json)。124087263 字节 input.v 留服务器，SHA `72cb9f933efa832c4dd9cde27efc324a39a65683feea142090457d72ca8775e2`。原始日志空白、换行不改写。

当前350继续原生route/finish；351四独立门、最终六文件、完整几何及352完整端口引出/负载/πRC仍依赖真实前置。未取消或重启任何 EDA，不把旧337或内置阶段LEC的资格转移为最终独立LEC。
