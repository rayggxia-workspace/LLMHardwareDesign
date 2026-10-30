# 新V537完成CTS阶段，时序尚未通过

Refs #121 / PR #122。15原始文件、311源Git/远端SHA、实际5234条clock net均NDR none及内部LEC54010/53999、UNSAT/IDENTICAL/all diff0绑定。源cf1fc48e/archive22dd145a，新一轮不继承旧522资格。

CTS阶段setup WS−0.00726574ns/TNS−0.0188773ns/4项，hold WS−0.250592ns/TNS−2.42258ns/20项，cap/slew0、放置合法性0。工具已正常进入global route；以上是阶段估算，不能作为最终RCX验收，也不能豁免负裕量。实际报告首个min/max均从reset到stats_sumsq[1][0/79]；对应input.v SHA与5个实际单元声明见path-source-mapping.json。需继续全部route/final及538独立门、539接口，按最终报告再决定必要修复；无EDA取消/重启或约束放宽。
