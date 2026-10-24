# Issue72关键闭环实验（进行中）

负责人Liangruizhi，Issue72；task/72-numeric-closure，base PR71@f4d2c46。协议在project/experiments/closure/PROTOCOL.md，实际源码逐phase/sourceSHA、命令见work/Liangruizhi/72。服务器新issue72-numeric-closure-20261024，无新模型下载；只有模型/数值/服务在服务器，本机小合成检查。

首轮Granite native32和router64均已实际完成且独立接收，参考条件仍FAIL：native32原chunk16 .005823/1.183复现；router64 chunk过而cached失败，不能只提升router算术就称解决。原grouped_mm不支持Double的90182失败保留，后续model64显式eager及native32_eager控制已跑，新model64两文本full/cached/chunk原门及路由集合自洽（完整独立接收进行中），仍含框架内部FP32 norm/RoPE/softmax cast，不是全FP64/部署精度。基于新参考的768整数router诊断已提交，不先写通过。

Falcon补采和编译、S16/S32×3政策×state/full两模式共12条件已在服务器完成。初步full guard_rescale各72step/零状态sat、51个按head重标事件，full32后继norm相对误差约3.0289%。它是明确cut的整数R分支：输入/外部A编码→完整R消费者→后继norm，不覆盖A/MLP或整模型质量。独立接收首轮遇calibration.tokens原shape(1,16)与接收len断言不匹配，保留失败并修正schema，不能先写独立通过。真实conv+R共同checkpoint/prefill64decode1/chunk正在补验，旧仅R恢复不当完整链。

同精度资源比较必须等math/轨迹明确，尚未执行。共有8lane/单SFU、V16KiB/R32KiB/M32KiB/S8×32KiB、EXT128MiB单层有界任务、各128bit1RW/BUS/FIFO守恒；完整算术/LUT/宽proposal/clone/重试/权重/元数据均计价，非COPY或RTL/PPA。

原70失败/FP桥/4sat不改写，Phi封存、成员55/63工程不接管。当前47项新边界小测试通过，后续源码更新后记录实际检查。登记PR5 pending，无board.json/Projects能力，看板unverified/同步pending待管理员；审查待指定。Task进行中，不done。
