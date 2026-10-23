# Issue56个人辅助资料

Liangruizhi，[Issue56](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/56)/[PR57](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/57)。
正式代码project/experiments/llama_cross，报告docs/experiments/issue-56-llama-cross-model.md。
package.py生成去重小包，保留全部编码整数数组/原始GQA及服务witness；不上传checkpoint或全K浮点线性原始输入。
diagnose.py读取本机完整输入作浮点敏感性诊断，stage-diagnosis.json记录结果，不称硬件实现或可加因果贡献。
manifest.json绑定交付文件但排除自身；原始完整数据位置/大小/SHA在小包local-data-index.json，共享pending。
打包后的仓库index/诊断JSON归一为LF；ZIP内原始记录不改。实际打包脚本快照在包内analysis/package.py。
原始数值负例log以gzip保留字节，避免把Windows CRLF当源代码空白；完整原log仍在D盘。
本机恢复路径D:/Projects/Codex/llama-local-20261023；不重下模型、不覆盖已有run、不启动其他机器任务。
