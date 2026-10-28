# V提前诊断脚本失败，保留原始结果

实际UTC见index（21:50:03.318354），目录名不作为时间。290直接读Yosys signed网表被OpenSTA拒绝；293已过逐位结构转换、round-trip及单bit负例，但link_design缺少technology LEF。均自然FAILED，原目录保持，没有V时序资格。294补齐原生tech/macro LEF后另行运行。

14原始文件、293/297源Git blobs及6稳定输出绑定核验。两个node-queue-child.log异常traceback在worker finally封存receipt后追加；捕获全文由index单独SHA绑定，verification列出差异。业务输出不允许此例外。
