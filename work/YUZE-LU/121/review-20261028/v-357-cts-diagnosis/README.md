# V357 CTS 时序与内置等价证据

Refs #121 / PR #122。源f23119383a731625acbf173834d69420fb1b44bd/归档9ac7d1d484cd6a369ce1eaf3ae77541e6c27256fb56aab6b3cc9ed2f4ef85a3d；11份原始文件SHA、308源Git blobs和所有V RTL绑定核验，见index.json/verification.json。

CTS内置LEC于2026-10-29 16:02:56 CST实际UNSAT/IDENTICAL。实际CTS最终报告setup −0.05ns/TNS −0.63ns、hold −0.17ns；最差max为offset[0]→stat_block_sq[65]，min为rsp_ready→rsp_valid。完整路径及input.v实际源寄存器映射见path-source-mapping.json。此结果不等于提取后最终STA或独立strictLEC。

原357正常继续route/finish。结合350最终RCX offset→stat_block_min路径，下一次同一基础V选定归约叶值/尾块valid预取修正；新源必须重新通过所有数值、映射、物理及最终门，不转移旧资格。
