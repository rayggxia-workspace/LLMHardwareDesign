# Issue #265 运行输入冻结与服务器预检

- 2026-11-13（Asia/Shanghai），负责人 Melodydt。项目 `llm-hardware-design`，协作规则 rayggxia-project-collab 1.0.0。
- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 为 #234 提供独立评估证据。评估分支 `task/265-qwen3b-system-evaluation` 继承 PR #260 的 `05225f51ee5367f8ca19793c45485dc5a90cc81c`。本地项目根目录是管理参考副本，文件整理在独立任务路径。远端版本与审查状态以 Issue 和评估 PR 回执为准。
- [清单与预检](../../work/Melodydt/265/README.md)固定 Qwen/Qwen2.5-3B revision `5defd2796acd3cb2051bb4c787eddc7f8f35e113` 的 9 个运行文件，6 份历史 `tokens.json` 和配套参考回执，以及旧 S16 的校准与 434 份权重索引。P512 主场景为 case-2、case-3，均从空 KV 连续生成 128 token。历史参考程序的额外一步 warm-through 只用于数值检查。
- 旧基线固定 PR #220 `1d284bdcb38bc9625c74d6ffeabae151094520b7` 和九组、3 个 M。两通道／四 bank／16 字节是编译资源描述。物理 DDR 容量、带宽和控制器参数仍待绑定。#250 的 TT300 MHz、51.2 GB/s、16 KiB 私有 S 和 W8A16 是独立候选，其已发布目标数值与运行值分开登记。#235 的 S16 参考与 #257 的短输入证据各自保留原范围。

## 恢复服务器核验

1. 通过已核对的 ED25519 主机指纹严格校验 `yuzelu@10.129.166.172`。指纹及本轮连接结果见清单。新工作站首次连接时，先依据可信渠道提供的指纹核对主机公钥。
2. 在 `/public/home/yuzelu/Melodydt/runs/issue-265/<attempt>/` 建独立运行目录。校验共同项目目录中的 `reference-002`、`algorithm-fix-43-calibration` 和 `frontend-full-002`。由项目成员提供经授权的共享 checkpoint 和 Python 运行环境，或通过允许的来源物化同一发布版本。历史脚本所用 checkpoint 和 Python 位于其他成员个人目录。可检查 #149 使用过的共享 SIF，按实物散列与工具版本登记 #265。提交脚本使用 `zny-*`、c64/c96 和本人路径，原 #234 脚本仅作参数与输入溯源。
3. 按清单校验四份 ONNX 实物及参考回执。历史图的散列和外部数据检查已完成，W8 候选的实际量化部署输入仍需单独绑定。
4. 按实际部署填入所选 profile 的运行字段和文件散列。记录真实编译器、RTL、DDR 配置、SRAM 端口／仲裁、时钟和跨域配置、工具链、SIF、启动入口以及代码和运行依赖的 `build-inputs.sha256`。用 #257 的产品交接检查核对 IR、硬件、计划散列与 `control-images.json` 中的镜像归属和 ABI。对于未形成联合时序证据的配置，保留时钟假设及来源。

预检所用目录布局如下。共享输入可以在可信来源取得后分开复制到这些位置。索引中的文件路径相对于相应目录。

```text
<assets>/checkpoint/              固定 revision 的 9 个文件
<assets>/reference/case-0..5/     各含 tokens.json 和 receipt.json
<assets>/legacy-weights/          output.sha256、generated/calibration.json、generated/weights/
<assets>/legacy-resource.json     旧编译器的九组资源描述
<assets>/graphs/                  export-0..2/cached.onnx、template-full/template.onnx 及外部数据
<deployment>/                     清单 runtime_artifact_names 所列文件、控制二进制及索引成员
```

```bash
sacct -n -P -X -j 101602,103217,103220 --format=JobIDRaw,JobName,State,ExitCode
python3 -B work/Melodydt/265/preflight.py --profile legacy --assets /path/to/assets --deployment /path/to/deployment
```

## 交付与阻塞

管理结构与清单已在本地检查。完整服务器预检待获授权的共享 checkpoint、完整 Python 环境和实际平台绑定后执行。#265 仍在执行。项目登记沿用管理中心 PR #5 待合并。仓库缺 `config/board.json`，当前工具无 Projects 条目操作，看板待核验，待具权限维护者同步。

## 2026-11-13 服务器只读核验

以管理员提供的 ED25519 指纹校验服务器后，使用本机获授权的登录密钥连到 `mgt01`。主机指纹记录在清单。本机任务专用的主机密钥记录留在本地。实际 `sacct` 返回：

| 作业 | 终态 | 耗时 | 分区／核数／节点 |
| --- | --- | --- | --- |
| 101602 `yzl-sc234-chain` | FAILED 1:0 | 02:16:37 | c96／60／node13 |
| 103217 `yzl-strict-kv` | COMPLETED 0:0 | 00:01:23 | c64／10／node5 |
| 103220 `yzl-strict-dram` | COMPLETED 0:0 | 00:00:07 | c64／2／node1 |

- 两份 KV 定位与 DDR 组件回执和 #260 记载的 SHA-256 一致。六个 token 文件和六个参考回执全部匹配。旧 S16 校准、索引、434 份实际权重与九组资源描述均通过实物散列核对。
- 四份 ONNX 的 SHA-256 均与已校验归档中的回执一致。按 ONNX protobuf 模式遍历张量，四份图均无外部数据引用。宿主 Python 导入共享 ONNX 依赖时报语法错误，共享 SIF 的 Python 3.10.12 导入完整 ONNX 包时仍有本地扩展不匹配。最终以该容器内的 protobuf 解析完成图引用核对。完整 ONNX 运行环境仍需绑定。
- #149 的共享 SIF 实物散列与历史回执一致。在已核对的共同项目路径内未找到匹配的公开模型副本，待用获授权的共享 checkpoint 和完整 Python 环境。整机部署的 RTL、硬件时钟、DDR 配置、镜像和启动入口仍待提供。未执行完整预检或提交仿真。
