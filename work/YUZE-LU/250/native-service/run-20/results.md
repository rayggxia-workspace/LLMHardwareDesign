#102209 有界G下游与下一投影并行

同一完整trace与总线读取/逻辑读写、3,028,352 M记录；严格服务自检、
全图容量/ACK资源审计通过。仍是有明确未绑定服务的条件模型。

| 条件 | token/s |FFN周期|
|---|---:|---:|
|新3stage scale/RF参考|8.228485|17490597|
|G/quant/retention与下192列投影重叠|8.348983|16964401|
|重叠但保留三P前置广播barrier|8.348906|16964732|
|重叠但4ticket|8.327808|17034687|
|重叠但关闭两A预取|8.197929|17626545|
|128列重叠|7.967604|18684355|
|旧pipeline参考，非最新硬件资格|8.510610|17394331|
|旧pipeline重叠|8.641356|16860987|

新profile下纯重叠调度收益约1.46%。保留两个256项S32 gate/up环，总容量
2KiB；每个N8最终写前按global_col/epoch领取对应槽，旧128值在G最后真ACK后
释放。峰值恰256值，未扩大环。G输出512B和A16临时256B只有原一份，
G→quant→retention仍串行；最多两个group编号控制任务，单copy route全局仲裁。
新scoreboard与两项metadata队列是控制寄存器候选，必须RTL/面积计账；不添SRAM。

当下core EXEC最早previous RF EOP+1仍只是预解析候选。W agent102213真实
guard fixture在head CONTINUE→FINAL观察II35，不能把理想II31冒充已有端到端资格。
root已启动独立RF II1硬件修订，收益和此处纯调度分列，实际完整产品周期等真leaf后替换。
E/N/dynamicQKAV、metadata、完整MC/LC/outer均仍需资格，物理系统未验收。
