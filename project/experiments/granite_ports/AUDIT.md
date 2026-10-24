# Issue76：Granite有限expert/merge服务独立接收合同

当前状态：设计/实现接收工具，实际服务器结果未执行或未接收。只在本人CPU服务器运行真实输入；本机限源码、小型合成边界和JSON/字节审计。root负责GitHub/SSH/Slurm及共同文档，独立子任务不调用这些接口。

## 同一数值函数与任务边界

起点是Issue74已经发布的Granite layer0/13 R16/evaluation72真实整数norm、top8 ID/Q15 gate及残差cut。原43stage数学PASS、compiled manifest/数组、producer与receiver源码、模型revision和实际row SHA全部闭链。外部Attention/post-attention norm/router不在本轮执行；不能改原数值、精度、profile、scale或输入后还称同函数。

每个token必须按实际ID消费全部8专家的完整gate/up K1536、整数SiLU/乘门、完整512 mid scan及A8重编码、down K512、各down先RQ共同I32Q12、U16Q15乘S64完整8路prefix/final-RNE、0.22 Q20/RNE20、真实残差加法和完整H1536 nextnorm。不能按rank拿其他专家参考、固定旧ID或用原FP中间值作运行桥。Otile128/256×M/V驻留×label2×层2共16条件；分组标签不能改变日历。

## 真正有限库存和生命周期

- 固定M32KiB、V16KiB、R32KiB、S0..S7各32KiB、EXT128MiB和ROM4,260,100B；各银行128bit1RW、单128bit BUS、端点2KiB FIFO、唯一VR8、单SFU/ROM。B1的M256有效16PE，不能按256PE发实际一行。
- 当前层全40专家W8 94,371,840B、static scale614,400B都占有限EXT；其他层不免费驻留。router是已发布外部cut时不计重复运算，但其来源/格式明确，两表payload73,736B和真实ROM对齐/地址仍占库存。
- 每个源、缓存、权重rowpack/transpose、INT32 partial、宽product/prefix、static scale、mid/delta/descriptor和norm临时值有实际对象/偏移/字节/生命周期。复用必须先证明生命周期不交叠，不能只减总和。寄存器和多操作数暂存也要有固定库存。
- V不能容纳完整8×1536×4=49,152B专家返回。该旧策略必须实质容量拒绝；合法路线通过流式merge tile、显式S/backing或者重计算，并计重读、搬运和同步。
- 全512 mid scan屏障先于其新A8/down；全1536 norm统计先于emit。末消费者完成前不得丢弃仍需的residual、merge或scale。K/专家/输出tile、真实ID和版本必须可追踪。

独立接收从每次实际offset推导packet头、16B打包、源/目的leading beat、ROM单口、BUS/FIFO、资源区间与affine loop闭式范围，不直接相信producer totals。

## 可执行微校准的资格

成本表须绑定实际微程序/输入/逐动作trace/SV实现/工具版本与SHA，而非将CPU计时换为芯片周期。至少给op名称、signed/storage/input/output宽度、RNE/guard语义、scratch/operand IO、scalar或同控制SIMD8条件、功能结果和完整动作/周期。

- S8 digit、字节carry、符号、固定/动态shift、sticky/half/even、宽prefix、I32 guard、div/isqrt全部由可执行动作说明；宽结果只在独立oracle中使用Python大整数，不当成免费硬件运算。
- U16 gate可为32768；S32最负码、负tie、进位/溢出、零/最大分母、全宽sticky与LUT边界均须核。I128恢复除法/开方不仅是128/64轮，更要付每轮字节shift/比较/减法/控制。
- SIMD8共享控制的前提须在服务调用中验证。不同输出的RQ shift不能无条件折扣；若动作路径依赖值，必须逐调用匹配或有全域固定上界证明，不能把少量样本最大值当全部调用的保证。
- 每个服务primitive必须有覆盖其确切width/语义/动作路径的校准条目；未知op、缺校准、费用少报、ROM免费多口或哈希改写均拒绝服务排名。软件控制器/寻址仍有限制时，回执保持条件服务，不能称完整RTL/STA/PPA。

## 负例及真实状态

至少对port、capacity、numeric row、width fee和ROM五类实际artifact变更、重新写manifest SHA，再由独立语义检查拒绝。仅hash层失败不算这些测试通过。保留失败产物，不覆盖新输出；未执行的接收或微校准明确记录。

当前未有正式service/微校准接收回执。本文件不是实验通过或物理边界定稿声明。
