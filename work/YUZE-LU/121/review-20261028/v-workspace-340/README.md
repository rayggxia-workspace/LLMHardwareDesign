# V340 当前源占用与有限工作空间

Refs #121 / PR #122。93177自然COMPLETED/0:0，七项全部通过：两项实际占用、有限S16KiB/V工作区及四组模型长度。六个16CPU槽、任务结束立即补位，1.2内存预留与16GiB guard/liveRSS保持；源3c54ff4、307源Git blobs，47原始小文件/35稳定输出及receipt绑定核验。

135有限场景均由独立整数参考检查通过；90个RMS/L2场景周期与333相同。连续供给Softmax每256元素回放EXP命令增加1拍；带供数/消费停顿的场景保留实际相位变化，不强行按固定公式计价。3072元素连续RMS/L2仍10503拍，Softmax16707→16719拍；工作区与S载荷访问字节保持。全部逐场景实际差异见schedule-comparison-to-333.json。

真实函数入口valid计数已加入采样，并要求数值/周期/流量与336公共测量一致，不授予功耗或有效MAC结论。旧333预算原字节封存在historical-333-RESOURCE-BUDGET.json/md；新80候选预算已使用340实际源重新生成，源SHA/生成器Git及80项成本差异核验见budget-verification.json。有限测量不是完整系统10token/s或模型整数质量验收。
