# Issue53个人辅助资料

负责人Liangruizhi；[Issue53](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/53)/[PR54](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/54)。
正式代码project/experiments/cpu_pilot，报告docs/experiments/issue-53-cpu-migration.md。
package.py只封装白名单小记录，不遍历权重、wheel或venv。交付manifest排除自身，绑定本任务全部文件。
临时目录D:/Projects/Codex/cpu-pilot-20261023；恢复时先核交付/原始回传SHA，不能覆盖已有run目录。
实验数值门通过与作业退出码分开；BF16失败不是安装失败，也不修改旧FP32/BF16证据精度。
