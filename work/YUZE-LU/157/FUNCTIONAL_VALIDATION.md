# 功能与逐拍等价

当前待执行。原始RTL基准bench三初态（all-ones、seed157、seed158），含GDN/SSM、完整动态读、连续递推、四抽头卷积、溢出回滚、无效命令、背压、reset和提交失败。A0/A1/A2均使用同一冻结bench。

小规模选择网络正例+错误银行极性反例仅验证工具及代数，不替代完整证明。完整设计经proc/memory_map进行通用证明降级，equiv_make/equiv_simple/equiv_induct后equiv_status -assert全通过才准综合；保留所有状态、输出、时钟/复位和错误分支。不以bounded、局部或黑盒证明代替完整。

SystemC数值模型尚未通过逐位RTL对照，任何早期性能结果都不能视为合格架构。大于2048状态的参考扩展须独立明确64位跨块累加、最终一次RNE和全局事务。
