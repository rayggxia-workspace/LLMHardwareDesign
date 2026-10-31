# V 128bit 分组进位：函数证明与完整设计语法失败

304/93055自然FAILED/1:0；实际22文件捕获UTC22:55:30.772207，11稳定输出SHA匹配，三个node-queue-child.log在finally回执后追加traceback，明确另记，不豁免业务输出。

实际RTL提取add128_grouped/rne函数的264输入位（两个128bit字、1carry、7shift）全域SAT加法/减法/RNE全128bit等价通过，实际bit18翻转负例拒绝。该证明只涵盖函数。

完整数值/映射/端口编译在RTL145行失败：批量替换误把1bit carry参数加进$ signed选择cast。三项失败原样保留；未产生物理资格。305源3a3e1d6仅纠正这处cast，函数逐字节相同，function-reuse-305.json记录两源/归档/函数SHA和304 SAT回执；不重复已过数学证明，不转移失败完整设计检查。

305/93057已实际提交，新的完整三初态数值、映射、公共端口benchmark各16CPU独立并行；source305 archive eb0a9d88df0ed2a53ded60e1a8be85be0547dffd0098d52b66fb5761352a2c07。最终新P&R/所有门仍未通过。原291 CTS严格LEC、236 GRT及281旧V DRC继续，不因慢或日志静默取消。
