# R344 CTS 与内置等价证据

Refs #121 / PR #122。源dda5fd65c494719b840f8439ffcb4a2621817cb4、归档cb5eb96f24fbe75b5d4e403b071683d6ce0f34aea374256db1135f30e055652d。9原始文件SHA、307源Git blobs、所有R RTL及CTS内置LEC UNSAT/IDENTICAL实际核验，见index.json/verification.json。

CTS setup/TNS仅舍入显示0.00ns，不能据此推定最终正余量；hold −0.24ns。max源product[6][11]→failed，min源rsp_ready→rsp_valid，实际网表寄存器与完整路径见path-source-mapping.json。原344已进入route；后续最终RCX、独立时序/电气/连接、完整DRC、三初态最终网表、strictLEC及345/346所有产物仍须真实通过。此处没有授予最终资格或改变R源。
