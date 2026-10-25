# 保留全行X/Y并流式gamma的RTL候选

关联Issue93/91。采用全H统计后256元素gamma tile、单应答和逐S写ack；整行X/Y驻留，512B V frame和4KiB A缓存保留。理由是H2560 full gamma本身需要20KiB，而tile布局只占15872B；真实RTL已验证原位更新不会影响全行统计，不另加存储端口/乘法器。

该选择收敛容量和功能边界，未冻结M/V物理宏。需为新锁存、控制、接口mux、观测计数付费（generic+180bit，paired logic+4.20291%），当前cfg预装和五拍128bit DMA入口不同，不能做同I/O加速结论。bit精确、量化质量、逻辑面积和物理签核分层记录。

大H继续全行统计；不以每tile归一化替代原算法。general V/SiLU、程序/LUT、A/R更新、宏/STA另立任务。cost01的beat换算错误原样归档，只有独立读取实际桥声明/状态图后的cost02可用于后续成本。
