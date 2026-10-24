# Issue76：保留完整merge候选，先校准宽frame再定宏边界

2026-10-24 UTC+08；Liangruizhi；[Issue76/PR77](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/77)。依据[实验报告](../experiments/issue-76-granite-ports.md)的24完整03配置、6 M/V配对和12标签对照，非最终物理实现验收。

决定保留M/V/A/R/S/D六逻辑模板，fullH1536 merge也保留为合法候选。front/down/norm互斥、mid在S0和O16输出流式写回，使V14,224B<=16KiB，修正静态acc+完整输出相加的排除理由。全8路S32 49,152B返回驻V仍拒绝。不能为证明小tile更好而强制无必要共驻，也不能为fullmerge赠端口或RAM。

决定不固化M/V物理融合。相同原整数函数与库存下，近M仅减少55,296次64B partial复制，即774,144条件slots/5,308,416wire B，完整cut占比约0.0008405%。当前byteframe公共费用约占99.75% wire、micro整体约占99.46% slots，绝对值是保守BUS-attached实现，不等真实LLM通信/最优目标周期。必须先有同库存局部frame/完整controller的可执行校准和物理时序，不能免费去掉这部分成本后宣称新收益。

决定把scale译码守卫列入接口义务。真实L0有32处移位130/131，旧0..128域失败不删；统一03付cmp/sub/max/sub、flags IO与controller测试后以S64 RNE证明保持原Q12。全部配置同费版，原43stage不变；负shift需新左移/溢出合同，不免费clamp。

制造前候选固定局部INT32 fullK反馈、有限宽临时与ROM仲裁、owner/phase/信用/完成协议；expert动态路由、M↔V宽旁路、merge窗口/owner与S/backing端点保留产品定制。逻辑完整归约不推出同一制造宏。8byte lane/512B存储与端口预算下的局部frame、wide FSM/RF及STA/PPA是下一必要分叉，不继续盲扫窗口/品牌；R/A/整模型质量沿用独立任务，不把本batch冒充其验收。

此决策可由真实局部frame/控制器校准、共享资源并发及布局/STA证据修订。PR待审查合并，未done；失败、先前费用版和原输入条件保留。
