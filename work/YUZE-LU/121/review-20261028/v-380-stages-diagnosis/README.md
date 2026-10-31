# V380 CTS/GRT阶段诊断

Refs #121 / PR #122。源5a6e0be84d3aedbb139a29268317761b74e4fbee，归档b6854770bc030eb47b74c8ff920ddd83b29165c92a83d1ea0a24d8c60ac4416c。13原始文件SHA/长度、308源Git blobs及远端实际源SHA核验，input.v摘要和实际端点映射见index.json/path-source-mapping.json。

CTS setup−0.07 ns/TNS−0.16 ns、hold−0.25 ns；最大cmd_index[2]→stats_sumsq[1][40]，最小reset→stats_valid[1]。CTS修复内置LEC UNSAT/IDENTICAL，51206公共输入/51195公共输出，diff均0。

GRT setup报告为−0.00 ns（仍为负、不得解释为通过），TNS−0.01 ns，hold+0.02 ns；最大low_product[0][0]→output_mem[93][7]，最小reset→rsp_data[0]。CTS/GRT均不代替最终RCX，也不授予独立最终验收资格。

93441/node17继续原finish，流程内最终LEC正在求解。R344/93237/node21继续GRT extra26/30，不取消或重投。381/382及345/346等待实际前置；M/S/T既有接收保持。
