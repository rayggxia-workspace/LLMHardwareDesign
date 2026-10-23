# Issue47 本机辅助记录

任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/47

负责人Liangruizhi；分支task/47-primitive-stream；独立目录D:/Projects/LLMHardwareDesign-primitives。
正式代码project/experiments/primitive_stream，参考映射docs/PRIMITIVE_CAPABILITY_MAP.md。
临时运行和缓存D:/Projects/Codex/primitive-stream-20261023，不新增C盘工作目录。
范围：已有Qwen3-0.6B一层一个完整GQA组，独立校准、整数oracle、因果KV和版本边界。
不接管Issue32/PR36，不下载较大模型，不启动其他机器，不把软件检查写成端口RTL/芯片性能。

2026-10-23（UTC+08:00）恢复时GitHub认证查询HTTP transport失败，尚未重新核验远端任务/PR。
已依据前次Issue47接续；仅推进独立本地范围。远端上传、PR和看板同步须在账号重新认证后补做。
本地源码提交是版本冻结，若尚未上传不称远端已有。开发运行保留development=true，不作为正式验收。

随后通过get_profile核验Liangruizhi/指定邮箱/182389313，远端任务/PR/main及协作资料已重新读取。
源码270568dfcad314f3d16e9bfa68dc378b31bdea9b已用指定连接上传，PR49建立。
原始认证失败为历史记录，非持续权限阻塞。正式小包与完整回执见交接和PR最新状态。
恢复先核[报告](../../../docs/experiments/issue-47-primitive-stream.md)和results索引；
verify_delivery.py只核当前小包，可安全解压到新D盘目录。CPU超算估算已记录，未启动服务器任务。
