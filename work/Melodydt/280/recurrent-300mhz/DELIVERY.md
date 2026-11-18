# 最新300 MHz递推状态候选交付

负责人Melodydt；Issue #280 / PR #295；规则rayggxia-project-collab 1.0.0。更新时间：2026-11-18T23:15:17.877035+08:00

用户要求按此前200 MHz方法，收窄最新300 MHz Qwen3.5/Falcon能耗范围。本轮固定父线v5 e29d72a585dd1fb0cde6c9a6976ef0fe78f98f96及P512第3版01141df70d358c4a4225e36f153b695ced1d05b1，采用一个共享8-lane R替换状态代理。表内包含一个读DMA的四方案包络，单位mJ/token，均为Decode2。

| 模型 | 原片上 | 新片上 | 新片上＋DDR | 区间宽度缩小 |
|---|---:|---:|---:|---:|
| Qwen3.5-4B | 846.651–1567.051 | 831.164–1009.028 | 2080.251–2258.114 | 75.31% |
| Falcon-H1-3B | 837.730–2057.398 | 622.070–767.853 | 1526.504–1672.287 | 88.05% |

删除匹配状态代理后，加入完整LOAD/EXEC/读回动态增量、整窗R静默驻留以及仍保留的Falcon注入代理。四DMA互斥，不叠加phase和shared；其他特殊候选组合单列。吞吐和DDR不变，未宣称候选已接入完整系统时序。

## 方法与实际验证

300 MHz标定源码提交9783bddb6dc65b2c81759905121b771db431859e，分支task/280-recurrent-first-round。既有Nangate45典型库综合网表、输入向量和零延迟门级事件不变；严格把2500 ps半周期映射为1667 ps，检查事件顺序/值/全引脚声明与SHA，然后用3.334 ns时钟重新运行配对OpenROAD功耗分析。没有重新综合、新门级功能仿真、SDF或布线寄生，不等于300 MHz物理时序验收。

120432/120433均COMPLETED 0:0；node12/c64，各12核、UNLIMITED。源码/输入/输出SHA、48个功耗窗全引脚覆盖及8个模型窗口的代理去重、单位守恒、DDR保持和服务预算检查通过。具体数值检查见verification.json；PDF全页检查见pdf-validation.json。管理结构检查通过，只验证管理文件。

本轮仍有边界：两个早期通道块，不是独立层；Prefill是冷状态样本外推；P512没有完整实跑/误差验证；候选定点相对浮点TLM有差异，完整模型精度/格式转换/provider/加载与门控/真实调度未验收；Falcon外部注入仍用代理。全局时钟/跨块互连、PHY/封装/板级及物理时序未补齐。

## 运行与复用

服务器yuzelu@10.129.166.172；目录/public/home/yuzelu/Melodydt/runs/issue-280/recurrent-300mhz-9783bddb/{qwen35,falcon-wide}。实际提交命令：各目录下 `sbatch --parsable --time=0 --job-name=mdt-r300-<模型> run_calibration.sbatch`。原标定目录只读。日志slurm-120432.log/slurm-120433.log，结果calibration.json；详细启动和核验回执jobs.json/status.json/collection.json。

```bash
sacct -X -j 120432,120433 --format=JobID,State,Elapsed,ExitCode,Timelimit
tail -n 20 /public/home/yuzelu/Melodydt/runs/issue-280/recurrent-300mhz-9783bddb/qwen35/slurm-120432.log
tail -n 20 /public/home/yuzelu/Melodydt/runs/issue-280/recurrent-300mhz-9783bddb/falcon-wide/slurm-120433.log
```

在仓库根目录或完整包解压根目录，用Python 3.10+运行：

```text
python -B work/Melodydt/280/recurrent-300mhz/integrate.py
python -B work/Melodydt/280/recurrent-300mhz/verify_integration.py
python -B work/Melodydt/280/recurrent-300mhz/build_report.py
```

PDF需要ReportLab/pypdf与Deng字体；不重新运行freeze_inputs覆盖既有快照。包保存冻结输入、数值、OpenROAD轻量回执和脚本，不含大波形/网表/权重。服务器重标定仍依赖上述原工件及工具，不能仅靠本包从头重跑物理流程。完整本地目录无.git；本轮只操作独立recurrent-300mhz与指定报告路径，不修改主线源账本、200 MHz结果或共享本地STATUS文件。

## 状态与后续

本地已完成；远端上传/最终commit以publication.json为准。独立分支已在706a6e9a6ecc4b5626702332ff4c56bf80f38744吸收父线e29d72a5，保留父线共享文档与此前200 MHz交付；未合并PR。整体Issue280保持in_progress，独立审查人待指定；登记PR5 pending；看板缺配置及Projects工具，条目unverified、同步pending，具权限维护者接续。未配置聊天结束后的自动监测。

剩余步骤：扩展独立层/非零Prefill/真实长序列活动；模型数值及转换/注入验证；确定R实例和加载/状态路径，接入调度并重算时间；按需要补物理时序、寄生及其余覆盖；独立审查与合并。恢复第一步：读source.json、publication.json及status.json，核对输入SHA，再运行积分和独立校验。技术接续负责人Melodydt，审查/看板处理人待指定。
