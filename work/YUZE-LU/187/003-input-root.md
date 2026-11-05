# 003 · 修正容器启动后暴露的输入根

- 采用 `/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu`。脚本 `003-shared-runtime/run_rtl.sh` 的 SHA-256 为 `a2486816addac679ceae0bf93a550af7335c06d7c56d8bcba273567055300360`。
- 作业 97469 在 c96 node17 运行 3 s，两步各 12 核。Verilator 已启动并读到 SRAM wrapper，随后报告找不到 `001-6e11c17eff4d/source/project/...`。实际归档直接解到 `001-6e11c17eff4d/project`。
- P/J 日志 SHA-256 分别为 `b0fbebd8bf93de2d1ea0ab8bf25553a18e517fd4bf1ffb935f22f6cd252025db`、`7c3368213401b661136109c4aa5c34bebf981a048a3b07135e9137df7abe9da4`。无有效内存采样。下一轮只更正脚本参数中的归档解包根。