# R操作数预取：真实功能、端口和流水占用

实际捕获UTC23:25:44.406924，58原始小文件、32稳定输出绑定；309映射仍在运行。
309源f32c4ff/archive7130f86c；310源93a250c/archivef958e3ce。
309三初态回归、24公共情形×两初态、9卷积情形×两初态全部通过；
各初态回归379979检查/178456周期，240递推/100卷积案例。
独立参考未改，只更新显式延迟断言：GDN4N+15、SSM3N+11、卷积14。

310/93068 node22两项16CPU真实内部采样也通过，自然COMPLETED/0:0；
全部公共结果/流量/周期与309逐项相同。取数用fetch_done、乘积用operand_valid、
退休用row_valid精确计数，不把新增填充拍当有效乘法。
例如GDN256：每个row循环phase257拍（256行+1填充），乘积8200 lane-slot、
shadow写4096、dot写4096；SSM256乘积6152 slot；卷积单组32 slot。
这些是逻辑写使能，不是门级翻转、功耗或有用MAC率。

公共连续情形：GDN128冷单块1094拍，GDN256为2150；SSM256为2403；
卷积冷单组46拍，连续256组6421。所有装载、控制、响应和完整导出均计入。
对应成本已更新当前RECURRENT-RESOURCE-BUDGET和RESOURCE-BUDGET，原预算
previous-recurrent-budget.json保留；没有修改并行实例候选或扩大系统实现。

311原生/312最终七项/313接口六项已远程validate暂存，dispatch.tasks为空，
都未分配；source14b4746/archivefb5b506d。五份归档全部Git blobs及309/310输入核验。
仍待309映射真实通过才启动311；312待311native，313待312完整几何。
新源不复用236旧物理资格。旧236/291继续，旧281已终态；其未claim R分支
以及292/297旧R分支已不作为新源主线，不应误恢复。

补录旧V281完整DRC：原生2项，metal2 spacing及NS Metal，同网
$abc$1198970$new_n220011；完整未修改FreePDK45 GDS deck0不能覆盖原生失败。
精确bbox和deck/GDS SHA在实际five-macro-drc.json；未豁免、未修旧数据库。
