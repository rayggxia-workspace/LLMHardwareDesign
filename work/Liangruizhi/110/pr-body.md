本次解决注意力limb动态宽移位的可证明缩窄问题。原106与STYLE0先全域等价，再以真实FF reset/归纳不变量证明limb域；STYLE1显式常量移位、STYLE2 QK34/PV45保持原INT32 guard及所有消费者行为。

同库、同唯一16KiB/8S8/S32/SFU/link、同观测和寄存库存，三变体24套完整102/106回归全部逐字段、逐周期、协议及实际端口事务一致；独立原整数oracle、34项负例/反例、六路实际mapped gate均通过。逻辑面积126029.470→125300.098→125009.626µm²，STYLE2仅省0.80921%；无周期加速，不把旧106历史125966.694当本批baseline，无STA/宏/物理或整库完成声明。

实际验证全部本人服务器；106作业104完成/2次调度失败保留，双包/PC精选/5phase320原Git源字节PASS。报告、paired receipt、proof、gate、index及交接齐全；不改106/109，候选整合需独立接续。

Refs #110

规则版本：rayggxia-project-collab 1.0.0
项目/任务：https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue110；负责人Liangruizhi
成果：本PR；源码fe9ee178 / 运行f066925 / 最终验收3b974e1；后续文档commit不替换真实运行SHA
验证：check_project、源码AST、累计diff、真实SAT/全整数/端口/恢复/34负例/六raw gate/唯一库存/逐周期配对与字节接收；实际命令与SHA见work110/execution.json
登记：pending，management-hub登记PR5未合并
看板：unverified（缺配置/read:project）；同步pending，管理员待指定
审查与状态：待指定审查人；应置in_review，未合并/done
下一步：独立审查后在后续共享top整合STYLE2并重新核库存/功能；宏、STA、online/append、真实下游事务缓冲和制造后定制另验
