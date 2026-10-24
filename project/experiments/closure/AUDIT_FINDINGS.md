# Issue72 独立审计记录

2026-10-24；本文件为审计范围和限制，不替代root的实际服务器作业/SHA总索引。
接收实现不导入生产模型或数值producer。合成边界可本机；真实张量数学及服务
只由root在授权CPU服务器执行，子代理不启动SSH、下载、GitHub或他人作业。

## 已记录的独立接收

root中转回的`audit-granite-numeric01/receipt.json`为PASS：768路由候选、192
选择性路由、2,211,840个完整K输出、412,560个实际完整K S8 lowering partial，
四类实际改写artifact并重写SHA的负例均被数学/协议层拒绝。来源model64新参考
PASS；原Issue70 FAIL不更改。该证据只到router input→top8/Q15 gate，不到
expert/down/merge，不能称完整MoE整数执行或质量验收。

选择性fallback有13,824行，等于192×72全部行；当前保守严格量化界没有留住
W8-only快路。`certified_rows=22,893`是所有四候选总计，不能当作W8成功数。
不能宣传选择性宽路由重算很少；tightening bound或换格式若要再做，需另冻协议。

root中转回的`audit-falcon-full32-guard02/receipt.json`为PASS：完整32head
数值、31个整数stage、72个连续commit、51个head重定标、epoch25；三类实际
SHA重写负例拒绝。新post-run误差接收与完整conv+branch连续性有各自独立
源码/作业回执，不能从早期receipt推断已经执行；以root最终索引为准。

## 关键审计修正

- 初版接收把B1 tokens的`(1,16)/(1,72)`当作一维长度，导致90201接收报错。
  9446123只规范明确B1形状并保留校准/评价分离，原失败日志不覆盖。
- S8宽乘采用低7bit非负digit和最高signed S8 digit；8/16/32/64位分别需
  1/3/5/9个digit。每partial的宽重组/位移/进位另计，不能把U8数字直接叫S8。
  Granite的S16见证使用另一套明确的符号×绝对值三digit，九partial同样合法。
- Falcon alpha为UQ31，可能等于2^31；必须显式U32格式，不能当S32窄乘。
  公共数据/中间dtB等S32独立检查符号界，避免I64安全掩盖声称格式越界。
- 两阶段dt×B和×x有两次RNE，不等价于一次三乘积后舍入；精确顺序进spec。
- 全4096维gate后RMSNorm、完整N256 readout和全hidden nextnorm不可删。
  所有div/isqrt、ROM单端口查表及宽算术都是候选能力，非已实现硬件。

## 范围和失败语义

Falcon旧批量链先因果预计算72行coefficients。`static_guard`拒绝后只有短前缀
state/output发布，但`conv_history_final_q12`仍是预处理全72历史；旧数值接收
仅认证算子/前缀数学，不能认证完整branch checkpoint。新的逐token接续把conv、
R state、units、epoch/version/position留私有，直到完整消费者成功才共同发布。
其late-consumer失败/恢复合成测试由producer额外记录；独立接收核全部实体
checkpoint与已独立数学重放的baseline，不把SHA一致当RTL原子性证明。

静态饱和/静态guard/guard_rescale不同失败合同分列。零发布sat而仅commit1
token是停止，不是成功。full S16/S32 guard均完成72、相同51重标和算术量；
其nextnorm局部L2约3.03%，不是全模型质量阈值。S16只是存储变窄，不能自动
把算术/吞吐翻倍。原生attention/residual为固定编码外部cut，MLP不在整数闭包。

## 同资源服务审计边界

由独立service producer按真实固定数值任务生成；接收应从source-bound任务
复建次数、分页、全消费者屏障、每物理beat、容量/银行/FIFO/总线与重试事务。
相同任务、单位/epoch轨迹、算术/ROM/RAM/端口库存下，标签变换应为零差。
未RTL校准的有界串行服务不能称最优、整模型端到端或PPA收益。

完整I64 proposal代在EXT占空间，不能把局部tile当全token提前发布；W8权重、
RQ参数、当前整数动态scale选择、完整norm/gamma双扫、conv history、state
clone/trial/shadow/readback、descriptor和所有spill/重读均计价。矩阵若按每token
重新加载是保守调度，不是prefill64必需权重下界。旧32层S32 state128MiB自身
填满EXT128MiB的拒绝保留；本轮单layer服务不得包装成全模型可部署。
