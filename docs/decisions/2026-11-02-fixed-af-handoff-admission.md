# 固定A/F纵向验证与真实模型准入分开

状态：所选合成有界ABI及AF纵向RTL已经验证，外部审查/真实模型/物理未验收。Issue151 / PR152；Melodydt；2026-11-02 Asia/Shanghai。输入cd8dfc9a，真实源a37df8be480d6472627a11419777511042af6a60。

A16/F16的hidden同为S16Fin10，只解决值格式一致；两个输出字与F每行17字参数帧仍不同，参数生存期、源捕获、真实stored/DONE与取消责任需要硬件。故新增固定验证顶层：240B显式holding、父独立终态、逐行帧生成，复用两个未改动的子核，不增加T，不冻结AF新产品岛或替代L5通用母控网络。

值在实际FF捕获后由父持有，A旧T可以正常释放；F启动仍以其真实S存储为门。父RUN先于子start的窗口也有父error终态，防止等待prestart子核不存在的DONE。metadata异常在发布前拒绝，饱和标志按started及阶段归属采样；输出前缀不可回滚。这些holding/解析/控制必须预制，M11/M12不能事后补出。

采用静态ledger+可执行检查器，将role/位宽/Fin/layout/shape/参数规则保留为编译期合同；当前唯一静态ALLOW是合成有界AF16。真实模型身份按锁定来源计算H/I/head等，不能自报H8准入。八模型×三target均GAP，数值/质量/参数供给UNKNOWN独立保留。静态ALLOW、33CASE RTL通过、真实模型推理及共同底座物理不互相代替。

下一实际尺寸优先Qwen3 F H1024/I3072：先接收数值/epsilon/误差，再实施N-long/完整归约和9MiB版本化chunk供参；14912B S布局和36864EXEC/行是未优化候选，不是已映射或性能。外存仍允许存在，本轮不把它当免费供给或强制不存在。细节见[实施报告](../W4_AF16_IMPLEMENTATION.md)、[样本准入路线](../AF16_MODEL_ADMISSION.md)。
