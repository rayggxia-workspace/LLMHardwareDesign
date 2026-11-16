#102238 RF II1与真实guard交接收费

新profile为102228/source637c51787：18份实际产品CSV已冻结并独立审核。
ordinary/head INPUT均11；CONTINUE RF EOP16、FINAL18。head保留8次独立RNE，
新RF三段流水在同context可II1；m_native另用4×37bit元数据FIFO，均属硬件修订。
实际guard fixture的head CONTINUE→下一core EXEC为21，即RF EOP后5拍。

| 条件 | token/s |
|---|---:|
|新RF+已测guard gap5|8.136179|
|gap5，取消G重叠|8.017249|
|gap5，但4ticket|8.091893|
|gap5，关闭A预取|7.945371|
|快速guard gap3，仅控制实现候选|8.507534|
|最早EXEC预解析gap1，仅候选|8.605452|
|gap1但不做G重叠，仅候选|8.477494|
|旧RF II3配旧理想gap1参考|8.348983|

八任务各12CPU，服务微时间线、完整固定trace/总线/记录及有限owner审计通过。
analyzer只用当前已测gap5行判断部分时间门，结果仍不达9.215647。不能用
gap1/3候选或旧参考满足门，也不能把gap5和旧gap1直接比较后判定RF负收益。
同gap1时新RF把Dot从11.410921M降到10.340020M周期，但该变化属于硬件收益。

bounded_service_guard实际N_WAIT→N_IDLE→N_ISSUE会阻止早预解析；如需gap1/3
必须实现/验证真实控制改动及ticket匹配，不能仅调模型数字。MC/LC outer、
metadata、E/N/dynamic services仍有显式未绑定，所有token/s为条件模型结果。
