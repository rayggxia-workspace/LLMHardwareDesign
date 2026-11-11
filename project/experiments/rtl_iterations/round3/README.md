# 第三轮：真实四bank供数与有限M控制校准

Issue247 / PR243。入口run.py --root RUN仅接受Slurm1到4核。先核验提交manifest、固定run19基线身份、真实SRAM模型、控制模型绑定的RTL SHA，然后在真实四1RW bank上运行单/双buffer各三seed。

同一vectors.py独立任意精度oracle产生实际16KiB S初始化、完整输出和每个S96累加前缀。输入版本/生成SHA记录；源码及工具版本另锁。没有将leaf的II1作为服务周期。

每次RTL运行留下control.txt：前20项是实际输入，后27项是同边NBA之前的实际控制输出。control_probe使用同输入重放；所有有效命令/读写/完成/提交payload和控制/资源占用比较。只忽略第一条复位边沿之前尚未初始化的寄存器观察，后续所有边沿均比较，无效payload按valid门控。主动翻转一个有效读地址必须被拒绝。

每case工作量与vectors.json独立匹配：命令/有效/非法、真实S请求/ACK、leaf接受/commit、完成数和容量上限。再从control真实握手重新推导这些数量、峰值、首cmd接受至末done消费周期、每个S请求至ACK消费的延迟集合。测量含实际S供数和最终两次128bit写ACK，不删除旧数据搬运。合法未来FIRST的next-ready另由bench实测。

profile仅采纳无人工hold的samectx/multi-ctx、完整K2048/11008、N8、shift16例，单/双buffer三seed周期必须一致。nominal读/写ACK延迟集合如果不是各自单值则停止并要求真实backend状态模型，不取最小值假装固定延迟。延迟压力例与常态分别保留。每一profile行绑定命令、日志SHA、controlSHA及原始事件SHA。

R3候选位于独立实验目录，生产P16和R1/R2不改。128个32×9乘法器属于大面积候选；资源账本、旧版本远端分支和新源码备份单独保留。没有综合面积、300MHz STA、P/DMA全连接或实际LLM生成资格。

后续旧体系模型应替换完整合格本地服务边界，只给每次真实S请求预约一次日历；保留外层DDR、A租约、write combine和非合格操作。新版M工作统计与旧统计定义若不同需明确列账，不能用局部周期或合计S节省直接乘整图速度。

目前本文件说明运行器合同；实际结果以服务器result.json与终态为准。日志可能较大，收集器用--max-result-mib 128保持完整文本证据；对象/二进制仍留服务器并记录SHA。
