# Issue145：七宏SystemC事务模型交付

- 任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/145
- 分支：`task/145-systemc-seven-blocks`；PR待创建后补回执。
- 当前执行账号：YUZE-LU。独立任务；未操作Issue143/121/130的服务器、作业或实现分支。
- 模型：[project/systemc](../../../project/systemc/README.md)。M/N/E/G/R/S/T七个有限状态功能引擎及真实SystemC模块。
- 设计合同来源：本地 `9cc23ff32cf7a57c5eadbfccc8bfb37438f3643d`；公开PR144起始 `d739fc46992ecb95cfab1a0f58ba1467f172cbb0`。Softmax采用本地最新Q1.14，而非公开旧头的UQ0.16。来源规范化SHA见 `project/systemc/source_manifest.json`。

## 实际检查（2026-10-31，Asia/Shanghai）

环境：Windows本地WSL Ubuntu18.04，GCC10.3.0，CMake3.27.0，Python3.6.9（WSL）/3.12（Windows），Accellera SystemC3.0.1/C++17。依赖仅写本任务`.systemc-deps/`；归档SHA `d07765d0d2ffd6c01767880d0c6aaf53cd9487975f898c593ffffd713258fcbb`。

```bash
bash project/systemc/tools/build_systemc.sh
cmake -S project/systemc -B project/systemc/build -DCMAKE_PREFIX_PATH="$PWD/.systemc-deps/install" -DCMAKE_BUILD_TYPE=Debug -DBLOCK_SANITIZE=ON
cmake --build project/systemc/build -j 4
ctest --test-dir project/systemc/build --output-on-failure
project/systemc/build/softmax_trace
python scripts/check_project.py
git diff --check
```

- 本地依赖脚本含下载SHA复核和真实编译/安装，已执行；未安装全局依赖。
- 编译使用 `-Wall -Wextra -Werror`、UBSan；通过。3/3 CTest通过。
- `block_tests` 524425断言通过，包含七引擎、七个SC_MODULE实际调度、深度1 FIFO背压；详见[test-output.txt](test-output.txt)。
- 257元素例子由S保存原向量和EXP，N仅保留统计/系数，T交接最终输出；详见[softmax-trace.txt](softmax-trace.txt)。第256元素处理后max2048，第257元素到达后max4096，EXP和473536，factor37150683。Q1.14逐项舍入导致输出和16366/16384，并不保证量化后恰好求和为1。
- 表系数一致检查通过；共享系数不是独立oracle。管理检查和diff空白检查通过，不替代业务验证。
- [模型代码SHA](model-file-sha256.json)按UTF-8/LF计；非Git commit哈希。

## 边界及下一步

无时钟、无RTL流水时延，Reset为顺序事务；S供数按事务串行化，未复现A/B重叠吞吐或端口仲裁。R按完整行装载合并物理半行端口。主机宽容器不是新物理位宽或额外片上容量。非法未ready尝试在本模型返回错误。未进行RTL协同仿真/形式等价、完整LLM质量或物理验证。详细差异已写模型README。

下一步：指定审查人审核事务抽象与冻结合同，特别是尚未发布到旧PR头的Q1.14接口；需要后续RTL协同仿真时另加适配器。PR待审查，Issue不关闭。

## 协作回执

规则：rayggxia-project-collab1.0.0；project_id=`llm-hardware-design`。
登记：management-hub PR5此前pending，提交时读回记录在PR回执；不另建登记。
看板：仓库无config/board.json，当前工具无Projects字段查询/同步能力；在线状态unverified，同步pending，处理人待指定。
审查：待指定审查人；成果提交后保持in_review，未合并、未验收。
