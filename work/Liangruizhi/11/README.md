# Issue #11 辅助记录

- 仓库：rayggxia-workspace/LLMHardwareDesign；负责人Liangruizhi，2663955430@qq.com。
- Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/11
- 分支：task/11-frozen-routing-pilot；独立目录：D:/Projects/LLMHardwareDesign-dac。
- 2026-10-22已核对main=1a98e9d、PR4已合并及Issue7/PR8/PR10最新交接。原目录D:/Projects/liangruizhi仍在Issue5分支，未切换或修改。
- 本机实测16核／约31.5GiB可见内存；D盘约351GiB空闲。现有Python3.13.14、NumPy2.5.0、SciPy1.18.0、Matplotlib3.11.0。无已验证的本地OpenROAD/Yosys/iverilog/Docker/WSL环境；没有安装或升级它们。
- 新目录从认证GitHub API按真实commit/tree/blob建立浅层稀疏副本，未获取ref-project/sources内容和更早历史；省略路径保持跟踪，没有删除。CLI作者信息不是认证证据，上传使用已核验Liangruizhi插件。
- 开发尝试local_runs/development-01保留，source_dirty=true，不能作为正式清洁源码结果；其后完善了记录读回与配置预算字段。正式运行另起目录，实际代码commit在manifest中记录。
- 独立审查发现并修复“把SiLU映到矩阵专用Block仍通过”及“NaN位宽绕过检查”，新增映射能力、IO、单射及非法宽度负例。也补齐固定基线设计集选择重建和oracle启发式结果读回。
- 登记默认分支仍无本项目，管理中心PR5为OPEN/未合并；复用已有登记。当前GitHub插件无Projects工具，仓库无board.json，看板unverified／同步pending，管理员待指定；不借用其他身份。

正式代码、数据、报告遵循项目目录；这里仅保存辅助上下文，不承载全部成果。
