# 有界RF流水，Refs#250 / PR251

从root `e582220f57229effdfb45d6a02ef405f4b3bc3fe`独立分支。
正对照为保守3stage scale/RF `c50bbc21a`、`0c00c9ac8`及102201/102202。
目标是保持mul/RNE/prefix+bias三段300MHz候选结构，同时使同context的
head连续STEP可II1；不是回退到5.98ns组合路径，也不是减少8次独立RNE。

scale增加显式ROUND_ONLY参数；默认三段独立API保持，RF内部只用前两段。
RF第3段从真实已提交state读取prefix，并从同拍retire的注册响应旁路。
two metadata465bit owners + one registered response最多3个packet；控制命令
仅在arith pipeline空时接受，不越过STEP，原控制1拍保持。STEP验证延迟到
第3段，所以先前数值或身份失败时，后续包必须针对实际RF cursor重验，
不能沿错误的推测cursor提交。无新SRAM，930bit metadata是真实寄存器，
原scale中previous/bias携带可能被消去，实际面积需综合确认。

独立Fraction/state oracle沿用全部CREATE/RESTORE/STEP/SPILL/DROP、错误原子、
上下文/owner/K检查；新增同owner8 STEP连续接受、最多3在途、每级reset取消、
三初态、逐接受/retire CSV。unit通过后才交W agent做真实完整产品联测，
再使用同源进入mapping/P&R。不能只凭unit把II1称为完整产品或300MHz合格。

代码独占：两个scale/context RTL及context/scale单测。生产M/serial guard、
原生S、G、MC/LC与整体合同仍由root和相应agent负责。主任务在线状态由root维护。
