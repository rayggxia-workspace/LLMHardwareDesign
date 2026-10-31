# V 归约叶节点与乘法操作数对齐

Refs #121 / PR #122。仍保留一个基础V，实现修正不增加裕量版本。

实际证据：旧350最终RCX setup −0.11ns/TNS −11.47ns，offset[0]→stat_block_min[6]；当前357 CTS setup −0.05ns/TNS −0.63ns、hold −0.17ns，offset[0]→stat_block_sq[65]，CTS内置LEC已UNSAT/IDENTICAL。原始报告及网表源映射见work/YUZE-LU/121/review-20261028/v-350-finish-diagnosis和v-357-cts-diagnosis。CTS不是独立最终资格；原357继续自然收尾，不按耗时取消EDA。

原归约在S_REDUCE读取a、在C_REDUCE重新寻址input_mem[offset+l]，并把offset+l<length尾块比较直接送入平方和/极值树。操作数已经在S_MUL/C_MUL进入operand_a，后经M_EXEC得到product；归约阶段重新读取原始回放数据和地址掩码没有必要。

选定修改：归约叶值直接使用已有八个S32 operand_a，不新建数据副本；在S_MUL/C_MUL同时记录八位operand_reduce_mask，分别采用l<stats_n及offset+l<length，复位清零。S_MUL→M_EXEC→S_REDUCE及C_MUL→M_EXEC→C_REDUCE次序和周期不变，使用mask前必经捕获。忙时命令不能改写A/回放，offset在C_ADD才推进，原有效叶值和有效范围保持。

保持S64求和、U80平方和、S32极值、索引稳定选择、统计上下文/计数/异常、完整S128归一化/RNE/饱和及所有事务定义；只增加8bit本地valid寄存器，复用已有八乘法器和操作数寄存器。未增加false-path/多周期例外，未放宽数值域、时钟或物理检查。

尚待361新源三初态/公共/扩展/组合/逐命令延迟/映射验证；362新占用/有限工作空间及预算重新绑定；之后363全新六阶段原生、364独立全部最终门/六文件/完整几何、365全部端口引出。未授予新源物理资格，不复用357最终结果。

后续实际：361七项全部通过，三初态566999检查/414906拍、公共42/扩展36测量均保持；映射445432单元，较355多2656，组合重映射成本不能忽略。362七项通过、135有限场景和78公共占用测量保持，80预算按新源重绑。363/93294于16:23:02 CST实际启动；全部新源最终资格仍待物理及独立门。


## 2026-10-29 17:48:49 CST阶段证据

2026-10-29 17:48:49 CST：V363 CTS内置LEC实际UNSAT/IDENTICAL（51142公共输入/51131公共输出、diff均0）；CTS setup/hold约−0.12/−0.08ns，rsp_ready→stats_sumsq[0][79]/rsp_valid；GRT setup−0.10/hold+0.02ns，rsp_ready→stats_sumsq[1][79]及cmd_data[117]→a[3][21]，仍详细布线。旧357六原生阶段自然COMPLETED/0，最终RCX setup−0.15ns、offset[2]→stat_block_max[16]，hold仅舍入0，不接收也不转移资格。三诊断目录共29原始文件SHA/字节与各308源绑定核验。R344仍全局布线拥塞修复；364/365及345/346按真实前置。M/S/T接收保持、V/R最终未齐，Issue121=in_progress/PR122=draft、目标active；登记pending、看板unverified/同步pending、独立审查待指定。

原始证据：`work/YUZE-LU/121/review-20261028/v-363-cts-diagnosis/`、`v-363-grt-diagnosis/`、`v-357-finish-diagnosis/`。全局布线后的新关键路径已经转为rsp_ready到统计上下文；等待当前原生最终RCX，保持数值合同与300MHz预算，不以中间报告提前授予资格。
