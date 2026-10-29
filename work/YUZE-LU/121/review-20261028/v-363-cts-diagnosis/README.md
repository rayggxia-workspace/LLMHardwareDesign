# V363 CTS阶段诊断

这是当前V修订的中间阶段证据，不是最终300 MHz接收。

2026-10-29 17:15:51 CST捕获11份服务器原始文件，逐份核验SHA/字节数；308个源文件的服务器SHA与归档/Git blob均已核验，源423c006、RTL2c166771，input.v绑定见source-verification.json。

CTS内置等价检查于17:12:49 CST得出UNSAT/IDENTICAL，51142公共输入/51131公共输出、diff0/diff1均0。阶段setup报告约−0.12 ns（critical path slack −0.1174 ns）、hold约−0.08 ns；两条路径均由rsp_ready输入出发，分别到stats_sumsq[0][79]和rsp_valid。实际单元映射见path-source-mapping.json。

原生流程继续布线，最终RCX/独立四门、六文件、完整几何与365接口尚待真实前置；不根据CTS中间负裕量提前转移资格，也不取消活跃作业。
