# 当前七宏原生接口与连接审计

固定研究基线faabeda68b3b098ba562d68517319e02725f5bc3，七宏导入源643c6012a11cbf461146ac40fbf61485223fe946。来源14份核心RTL/include未改动，完整指纹见[rtl-baseline.json](../work/Melodydt/151/rtl-baseline.json)。这些是代码观察，不是系统仿真结果。

| 附录 | 覆盖内容 |
| --- | --- |
| [M/S/T](rtl-contracts/MST_NATIVE.md) | 真实端口、M七种操作码与位域、S普通写ACK/loader布局与完成、T状态与合法握手 |
| [N/E/G](rtl-contracts/NEG_NATIVE.md) | N十二种操作/归约回放与raw公式、E十四种操作与特殊pack、G函数/门乘尺度/流水反压 |
| [R](rtl-contracts/R_NATIVE.md) | 全16个操作码、owner/epoch/position、pending合法矩阵、mode数值单位、两遍版本服务与提交边界 |

N内部group/EXP、G表、S loader均有源实现，但不因此成为外部通用数值宏或系统调度器。统一外侧任务/handle、局部控制、S访问与NUM服务仍待实现，见[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)。

关键更正：M op4不是旧feed_m merge；CLEAR_ALL不重置scale；op3 S64不能当E13的四S32；N没有目标总长/mask；E/G没有count；G gated Sigmoid输出Q10；R只有skip固定Q16.16；SSM仍要求param_valid；R先保存输出再局部提交、再按有效范围导出；T只有首读启动等待，后续take可每拍refill，末字仍需release。S/T reset不清payload，逻辑有效性和恢复由外层管理。

附录中行号来自冻结字节；完整产品、新增wrapper与数值oracle尚未验证。R仍是未获最终资格的跟踪候选，不转用原R4032数据库。本轮可执行静态核验见[验证脚本](../work/Melodydt/151/verify_rtl_design.py)及[回执](../work/Melodydt/151/rtl-redesign-verification.json)。
