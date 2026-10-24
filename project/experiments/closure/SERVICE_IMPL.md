# Issue72 完整R链条件服务实现

只在授权服务器运行真实任务。service.py不导入数值producer，读取compiled/numeric全部artifact SHA、transactions和runtime的A8 shift，强制独立full guard_rescale PASS且72token全部提交/0发布饱和；质量误差仍保留，不设应用质量PASS。S16/S32分别接受/比较，不跨精度称placement收益。

库存固定M256 S8 PE(16×16)、V/R共8个S8 lane、单SFU、4,260,100B单128bit端口LUT ROM、M32KiB/V16KiB/R32KiB/S8×32KiB/EXT128MiB、各bank128bit1RW、单128bit BUS、32B header/16B beat/payload1984/FIFO2048。ROM4B对齐，每随机4B查表单独1拍，请求/响应各48B经过BUS并和SFU串行，不能4值拼成免费一拍。常量和外部整数cut入场已在分配位置持有；state/history清零和初始units加载另有setup账。

B1逐token串行完整链，prefill前64与decode8标注但不跨token合并batch。M每次Otile16/Ktile512，始终16有效PE，完整K累加后才RQ。权重rowpack、256B寄存器片转置、单A16B保留后16次weight16B→16 MAC均显式，占M双8192B tile、A4096B、累加64B、metadata和512B工作寄存器预算；不把总MAC除256。

R32-D8(old8192+wide16384+aux8192=32768)、V16-D2(2048+4096+8192=14336)、R32-D16-Sspill(old16384+aux8192在R、wide32768在S0)。old按S32保守预留，实际IO按所选state_bits；S16不凭空获新资源。提案整数微程序每步8元素，完整decay/injection/proposal/readout-product四组I64数组均有EXT位置，每组8MiB。代价刻意保守、不是优化服务下界。Sspill每次真的分片跨BUS进aux，不允许把32KiB塞进8KiBaux。

状态全层先生成完整decay/injection→全量I64 guard扫描→完整proposal/range guard→所有head通过→完整readout product/I64 maxproduct×N guard→完整N归约/skip→完整4096 gate后RMSNorm→完整outproj/三输入join/nextnorm。RNE/scale/guard/clone/retry/recode/单位/epoch/owner描述符及完整权重/系数/输入输出均计。observer SHA/软件hash遍历不收费为目标必须算术；目标range/max/commit扫描收费。

state、conv history、units、owner descriptor均私有两代，旧代直到nextnorm结束前保留；最终用16B descriptor pointer/epoch/version单bank拍发布，指向96B私有描述符及state/history/units位置。两次old/trial复制、宽proposal/中间EXT backing、失败代、重标和chunk实际state保存重载均显式。只有成功完整任务作placement比较，观察者/校验的native浮点数组不进入运行时资源。

compute成本：M16有效PE计S8 MAC；VR8每32×32为25个signed-high radix128 S8产品+24个宽重组，每64bit shift/add/RNE/比较/abs为10个byte-lane slot，128bit add18slot。除法128次、isqrt64次单SFU，LUT每元素单独request/read/reply，非RTL时序。wide_factor=1/2/4统一乘VR byte-lane成本(包括copy/control)，M/SFU/port不缩放，库存不变。逐记录只称条件时隙，未校准PPA或E2E。

JSONL.gz每行macro有id/stage/token/phase/meta/start/end/deps/body。body叶start/end及resource区间相对父body原点；loop count/period/end=start+count×period，iteration原点=loop.start+i×period。access.index_strides按当前loop索引右对齐(缺省前补0)，对象offset+Σidx×stride+repeat×stride决定真实地址；连续/逐包的leading-byte偏移均重新ceil至128bit。所有macro及body叶严格串行；接收可用重复微程序闭式校counts、affine范围、mod16拍数恒等，无需展开过亿leaf。只按声明访问和16B/LUT alignment证明不变的循环可闭式；未知情况必须枚举余数/拒绝。

局部流式向量compute允许等时重排证书：输入/输出窗口已在aux8KiB内，按8元素读→VR8字节算术→输出写回，最多512B临时寄存器；重排不跨外部transfer、完整归约barrier、guard或发布边界。银行串行拍、VR操作slot、所有字节和结束时间与记录相同。RMSNorm的U128 tile partial、完整group合并、epsilon/variance、denominator与broadcast都有实际对象/访问。全局无并行收益主张。

~~~sh
python -B project/experiments/closure/service.py --numeric FULL_GUARD_RESULT --compiled COMPILED --receipt INDEPENDENT_PASS.json --binding PHASE_BINDING.json --out NEW --placement r32_d8 --label split --wide-factor 1
~~~

对r32_d8/v16_d2/r32_d16_spill、label split/shared和factor1/2/4分独立Slurm/输出。label不传入builder，仅summary描述，witness科学SHA应完全相同；同配置双轮也应同SHA。binding要求commit和service_sha256。7个本机小合成测试检查offset逐包、实际容量、矩阵完整K、ROM对齐、FIFO padding、stream tail、宽算术和SFU；本机未构建真实模型service。
