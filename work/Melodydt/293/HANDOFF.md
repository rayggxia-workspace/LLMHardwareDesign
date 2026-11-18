# 任务293进行中

任务 Issue293 / PR294，身份 Melodydt，分支 task/293-seven-model-200mhz，基线5464d279，当前脚本05cc76fe1c083995e07d405091b5f70c59793d02。

本地根目录无.git，任务目录独立work/Melodydt/293；远程~/LLMHardware/zenanyan/issue-293-200mhz-01。

作业38832271：28x1核，m3ca0208，UNLIMITED；其他五模型进行中，Qwen3缺被覆盖挂载资产、Gemma共同runner不含专用provider而失败。作业38832294：8x1核，m3ca0401，UNLIMITED；Gemma采用原已验收runner进行中，Qwen3旧Bash空数组失败。失败样本不得进入结果。第三次仅补Qwen3，见后续作业回执。

sample_frequency.py执行原冻结计划中代表完整层，恢复上层冻结残差并比对当前层输出，连续执行两位置以保留该层真实KV/递推更新；分别实测300/200MHz，DDR固定630ps。数值比对失败必须修正采样恢复，不得豁免。入口、boot、head也测。TLM组件统计和DDR实际能耗逐segment快照差分，原stage窗口observer设全局窗口仅用于收集计数。

待完成：七模型抽查；300MHz代表层与原page时间对账；按每层类别和频率比率重建全窗；512估计使用同一原有公式；网表动态/漏电与事件增量重新积分；PDF+JSON/CSV+Word与可视QA；上传PR并写持久交接。不要停止或触碰父会话#280作业。没有自动后台监控。
