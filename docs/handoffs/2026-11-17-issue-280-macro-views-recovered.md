# Qwen3 SRAM 与母控 PM 工件恢复

2026-11-17 10:52（Asia/Shanghai），Melodydt。工作起点 `23789fd77c3671c4c0fa77c6f7f793e29eb0a41b`，任务分支 `task/280-seven-model-energy`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [原件路径与来源](2026-11-17-issue-280-bscc-t6-covered-power-and-bindings.md#sram母控-pm-工件)

旧服务器 `10.129.166.172` 的主机已按原登记指纹核对。显式指定用户名下已授权的本机 SSH 身份后，登录和项目共享归档读取成功。仅取回 #155 S128 bank 的 TT Liberty 和 LEF、#200 S_P 与 S_base 两组 `6_final.{v,odb,sdc,spef}`、#223 母控验收包，共 11 个原件。源端散列、接收前归档成员散列和 BSCC 解包结果均与原验收清单相符。

BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com` 上的工作目录为 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01/incoming/macro-views/`。迁移包 `issue-280-macro-views.tar.gz` 共 96,310,575 字节，SHA-256 为 `fe4fdc1a594d2a54aafefa362eb38f79260a4ea7926eb83bc35fcb97e655ebfb`。`source/` 按旧机项目根的相对路径保留 11 个原件。`mother128/` 已提取母控 `physical/6_final.{v,odb,sdc,spef}` 及 `native-audit/mother_control_64.{lib,lef}`，六件与 #223 验收散列一致。Windows 本地备份在 `tmp/issue280-bscc-t6/macro-views-20261117/`，大体积工件保存在任务目录与本地备份中。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/incoming/macro-views
sha256sum -c archive.sha256
(cd source && sha256sum -c ../source-files.sha256)
(cd mother128 && sha256sum -c ../mother-subset.sha256)
```

`source-files.sha256` 的 SHA-256 为 `a14470817a2e159d2b2ef24211af1f24a3e3f20a4b4a16c29af358b08f75a9f3`，`mother-subset.sha256` 为 `f15123630564ffbda9db5d4f59bf906911f5c3bd145af669a1bb5378558cb888`。恢复后的三个网表直接核对到：`local_s_p` 和 `local_s_base` 各实例化四个 `s_sram_256x128_freepdk45`；`mother_control_64` 的 `program_store.sram.storage` 下有四个同名宏。

下一步由 Melodydt 将实际读写宽度、bank 选通、母控 PM 载入与读回活动绑定到这批 OpenSTA 工件，先测空闲和读写配对，再按三窗实际驻留与事件计数积分。旧版 M 和读 DMA 仍以各自作业及结果回执为准。本次仅恢复工件并核对网表实例，SRAM 和母控 PM 的新功耗标定未执行。项目管理结构检查通过，任务进行中、PR #281 草稿。登记 PR #5 待合并，Projects 待有权限维护者核验。
