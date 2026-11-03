# W3独立数学预期、TB与根执行证据核对

Issue151 / PR152；parent `99d6df2e094febe4ea8fc9896301adbbfdc803ed`，native7078786。本子任务是oracle/TB作者，独立于RTL实现；**不是外部独立PR审查人，也没有亲自执行ModelSim或服务器作业**。实际仿真由根任务运行，本报告读取其原始日志、receipt、源快照并与当前draft/formal SHA比对。没有修改冻结RTL/TB以取得结果。

## 已实际执行与复核

| 根执行批次 | 结果 | 有限范围 |
|---|---|---|
| regression-r01 | 47个历史CASE，compile/sim exit0 | 原P2 helper6＋MST13及W1 28；不是W3新覆盖 |
| ffn-r01 | 19 CASE、6609周期，exit0 | 首版FFN TB；保留旧快照，不冒充后续强化版 |
| ffn-r02 | 21 CASE、7524周期，exit0 | 新增真实E非法op与G一拍非法fn、全accepted drain及恢复；最终FFN版本 |
| adapters-r01 | 46 CASE、2231周期，exit0 | 22E＋14G数值/guard基础case和10握手/ACK/reset label |

已核对每批原始CASE集合与receipt相同、无重复，PASS token存在且无FAIL/Fatal；最终ffn-r02/adapters-r01使用的源码与当前draft、formal、run source快照逐文件SHA相等，所编译G table SHA与数学重建验证版本一致。所有工具退码0。CASE是单TB进程中的检查标签，不是独立进程数或全域覆盖率。

Python参考另完成48099条整数RNE（对照精确Fraction round ties-even）、冻结向量/packing、表版本及UTF8/LF断言；数学函数重建2564节点与固定707 G LUT逐项相同。该结果不等于RTL，RTL有限通过也不等于激活近似误差或整模型质量接收。

## 数值和关键错误门

FFN六向量覆盖不同权重/非均匀列、零、正负极值和稀疏输入；逐次S464..473实际写/读都与独立冻结预期对照。TB由自己输入字重新计算M与residual公式交叉检查，不以DUT中间寄存器或最终值生成预期。正负极值输出分别all7fff/all8000，done_saturated为stage OR，distinct from done_error。

每个正常帧独立断言32普通S请求/ACK（26写6读）、15M命令/应答、3loader完成与各3个A/B beat、2E服务/原生事务、1G服务/4pair接受退休、T1字及实际RELEASE。入口16拍和16个真实写ACK后才能start；padding真实覆盖旧RAM；输出/DONE背压、完成sat保持、重复/早start、reset/abort/prestart/RUN/prefix/DONE同拍及恢复均按列明case检查。

ffn-r02新增的E测试在首次native handshake强制op14一拍：实际native error上报，residual467无写且无T发布，随后新帧成功。G测试仅首native beat强制fn4，其余正常：4个accepted pair全部retired后service error，无mid468写、无T发布，随后新帧恢复。没有强制正确结果/ACK/完成标志，不把TB fault字段当产品运行配置入口。

Adapter测试真实实例化S16k、原S helper及nativeE/G；A/B/C按op需要的读数、顺序、捕获与inactive mask独立检查，E12/13 compact格式、FMA C单位、RNE/ASR、sat及非法/count/tail有定向样例。G测试fn0..3的gated0/1，odd5/single、invalid4/7和count0/9；**未明确跑unsupported5/6或全部count/shift/数值组合**。同源协议门对两端一致施加停顿；成功必须destination真正写ACK后才rsp，native错误不写结果。reset同时作用adapter/leaf/helper，不外推单边reset或无reset取消。

## 总轨迹差额解释

ffn-r02总计input452、Sreq823/Sack821、Mcmd353/Mrsp353、Ttake21。两笔S ACK差额是显式场景：输入native写已接受而ACK被permit_s_rsp阻塞时prestart abort；RUN最初x-unpack466写已接受而ACK阻塞时abort。源S写不会回滚，但响应被协调复位丢弃。其余正常帧逐帧32/32；不能把总差额称静默丢ACK或隐藏为全局无条件守恒。捕获输入但尚未发native请求的取消不增加Sreq。

Adapter总计E接受24、Gissued65/Gretired61、Sread72/Swrite36/Sack108。G差4是唯一的G在途reset场景：count8四pair均已接受、native输出门关闭后协调reset，四个旧pair不再退休；之后新服务重新计数。所有完成的正常或native-error G服务都逐次断言issued=retired=ceil(count/2)，不能用总差额掩盖正常丢退休。E reset也丢弃其已接受未输出事务，报告不宣称全局E输入/输出无条件守恒。

Adapter的S计数仅service_active事务，排除host初始化。基础case共46读/26写；四个E停顿服务加10读4写；四个G停顿服务加6读4写；E reset前与恢复共6读1写；G reset前与恢复共4读1写，合72读36写108ACK。两reset都在native输出被hold时，前置读已ACK、结果写尚未发出，所以没有丢S ACK。对G4差额与FFN2差额的解释适用各自TB场景，不能泛化成任意reset原子性。

## 最终绑定与未完成项

- E_CTRL：`e0325cb2a833a6609c3c7996f1bf9a89b0fe02fab32e7a9a108921711e7dd621`。
- G_CTRL：`9174cb97a0dd9e969f7d6fce49dc32eda4ab29c50c43f3a3d47503d34fba3c30`。
- FFN top：`704c3f41a4265517cf768250e9256b59f420c88c8068a066e63e54dd280159e8`。
- FFN final TB：`61e5427bc13f4ae24afbfd59645d4cfcfecd4ba3b628082ea691404e27ff2582`。
- Adapter TB：`7eabf9949d4d056e79efaff35f840dabdc94e31412c9d0b1bd748f674496e0f6`。

源/expected/generator/table/checker完整SHA、各轮receipt/log SHA与CASE名单在`w3-run-review.json`。可用`review_w3_evidence.py --package <本包> --output <新回执路径>`只读复算，脚本不调用仿真器。根任务负责在线交付和要求的审查；本作者不批准自己PR，也不称本地PASS代表合并。

本次是明确Fin、固定shape/地址/程序、可变tensor的FFN8与有限E/G adapter切片。完整F仍缺N/pre/post Norm、真实H/I/工作集/MEM和模型scale接收；一般shape/tile、所有alias/count/fault、无reset drain、cross-island/NUM/版本、形式活性、综合/PPA/同底座产品均未接收。P2剩余门、W1完整岛壳和后续P4–P7义务不被这些CASE自动关闭。
