# Block V2 请求中的 Gather 母控派发

远端作业 `110415` 把 512 个 prefill Gather 页和 127 个 decode Gather 页逐一绑定到请求 `9fc35ec5fb682adce14f20458c9d5b22aef84c4722bd74823b39f241e760968e`。链接器复核每页原始母控程序、CALL 目标、原描述符和编译来源，校验新局控镜像中的表地址、索引格式、目的地及完成语义。请求总计 184927 页、8273243 次 CALL。本次生成了其中 639 次 Gather CALL 的替换映射，交接状态为 `partial`，其余 8272604 次仍沿用原包的待移植记录。

替换的母控 PM 是 160 B，程序为 `CALL U0, token=9`、`WAIT 1<<9`、`END`。各页的 U0 局控 PM 由各自 sidecar 指定。decode 页要先有上一步词表退出产生的 token，才能启动母控。局控再执行 `LINK_RESERVE`、`LINK_RECEIVE` 和 `GATHER`，每条命令都等待对应完成。启动前置条件和索引 SRAM 写确认分别落在请求调度和局控程序中。

作业 `110423` 取原请求中第 127 个 decode 步的第 0 页，使用真实母控的程序 SRAM、四拍控制帧、九路交换机的 U0 分支、U0 局控、现用 DDR fabric 和 U0 SRAM。词表输入使用归档的 151936 个 logits，由硬件 argmax 在验证中实时产生 token 81917。测试检查回读全部 512 个嵌入 SRAM 字，并在正常与人为延迟索引确认两种情况下检查母控终态。

| 项目 | 正常 | 索引确认延迟 |
| --- | ---: | ---: |
| 母控送出 CALL 首拍 | 38738 | 38738 |
| U0 索引提交确认 | 38802 | 38811 |
| U0 嵌入行最后一次确认 | 41287 | 41287 |
| 母控收到完成回包末拍 | 41305 | 41305 |

两种情况下均读取 128 个 DDR beat，嵌入输出为 8192 B。母控共确认读写各 8208 B，其中另有 16 B 索引访问。表中周期由此夹具读取 PM、链路和 SRAM 的握手得到。

词表投影和 C0 退休发送端仍需接入同一 Block V2 请求。夹具以归档 logits 驱动 argmax，并将索引写入器接到 U0 现有的存储链路对端。其余 CALL 的原生服务、同计划 Algo2 全量交接以及 P512/D128 完整退休仍待验证。

`request-link.json` SHA-256 为 `6434921731a215bf028dd5ab6ccb42855376c706568d67a7a778f57f02b322c0`。母控镜像 SHA-256 为 `92bc1b7e90d3cf4ea4a993339112a51bfb98a7d50000c18f2ecd1a1746a1c027`。

远端工作目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/ingress-route-iN0LbH/resident-gather-HefhYQ/prompt-ddr-6T8eOJ/decode-feedback-xts0x7/mother-ingress-sNMsK9`。作业入口为 `link-gather.sbatch` 和 `run-mother.sbatch`。
