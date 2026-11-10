# 原生共享A入口16→32B/P/拍：独立验证

Issue247 / PR243，负责人Melodydt。此目录是新测试入口，旧`shared32_native`实验保持历史冻结；旧runner直接运行应使用其固定原源码a7a36cbb，不能拿它在pair默认已改2的当前源上冒称兼容通过。

测试仅在本人服务器目录的Slurm分配内执行。`job.sh`使用`mdt-a32-native`、c64/c96、4核、2小时上限；每个编译/运行还有独立超时。实际SRAM行为模型和宏库用既有SHA锁定，无行为假宏。默认`A32_COMPONENTS=all A32_AREA=1`；可按`units`、`compat`、`pair`分阶段诊断，局部通过不能写成完整suite通过。

## 功能与默认兼容

- Pool 1/2词对照：完整保留旧真实宏、两描述符、4槽FIFO、同址双P分别收费、背压稳定、非法描述符、RELEASE及reset检查；新增rows1/3/7/8 × tiles1..4 × base offset0..3的64组双P随机ready检查。逐lane核对地址、payload、row/tile/bank/format，覆盖单词尾与跨row/tile。
- M普通/8context × 1/2词：64形状，S8/S16与B8/B16，含S16极值，用独立标量有符号整数点积核对每run2432输出；mask10和重复tag观察无部分写，恢复后再作数值核对；busy bank、reset失效与context释放检查。
- M双词控制定向：clear-all、clear同bank、clear其他bank、start同拍、busy另一bank、01尾高lane垃圾、reset清空；普通/8context均执行。
- 历史pair完整bench分四种share/rw配置，旧五个生产模块从`shared_a32_baseline/source.json`锁定的2fc03de5快照替换。候选显式A_WORDS_PER_BEAT=1与旧快照逐个MEASURE/PASS（数值、周期和生命周期）完全相等；两边追加完全相同只读observer，逐拍核对全部ready/valid状态及有效A/B、命令、IO载荷，事件仅按实际cycle及observer名称规范排序。候选A2另跑四配置全部原断言，仅监视器按有效lane计数，不删除检查。
- 所有build使用三组初始化模式/种子(1,247)、(2,247)、(2,248)。新pool/M单元严格编译；pair闭包保留旧width警告，但任何PINMISSING/PINNOTFOUND和新bench警告都失败。失败日志和已完成结果逐步保存。

## 等工作性能口径

`pair_body.sv.inc`生成独立双P微基准。1/2词、普通/8context分别运行完全相同的64场景：四种A/B格式 × 四种rows × 四种tile数，offset0..3与lastK尾部覆盖。两P相同A对象，各有确定性B，初始化、wide_write/LOAD、计算命令、输出校验数量与校验和逐场景相同；此处没有真实DDR DMA桥。

记录初始化+处理周期（不含测量后的对象RELEASE）、处理周期、两P LOAD周期合计、M计算命令周期合计、实际A供数跨度、词数及beat数。比较前逐字段核对工作量与结果，并要求初始化/M计算周期不变；报告只给同工作处理周期比。两P合计阶段周期不是墙钟分解；不得把重叠等待相加。旧bench的负例/不等负载只作功能与兼容性，禁止从其shared/local配置间计算性能增益。

此微基准不是完整LLM吞吐，不能将周期比乘旧SystemC token/s或声称新原生整模型token/s。

## 面积

功能门通过才调用独立`area.py`：同Nangate45库比较pool1/2词、普通M1/2词、8context M1/2词，共六项。共享池始终8颗4KiB宏。SRAM黑盒面积单列，标准单元面积不含宏；只汇总pool差值加两颗同类型M差值，不将两种M实现重复计入，也不宣称包含P/pair外围、布线、时序或芯片面积。该实验不改本地存储ECHO_WRITE_DATA=0生产配置。

## 可复现执行与证据

根会话将完整源码上传真实commit，包装`inputs.json`、`source-files.sha256`和固定baseline后，在新run目录执行`sbatch --parsable job.sh`。不覆盖既有run。服务器入口为：

```text
python3 -B source/project/experiments/shared_a32_native/run.py --repo source --out results --manifest inputs.json --workers 4 --components all --area
```

该入口拒绝没有真实Slurm分配的本地/登录节点EDA执行。结果在`results/result.json`，含源码commit与SHA、工具/真实宏身份、命令及退出码、每次PASS/MEASURE、默认精确比较、等工作比值及独立面积回执。终态后在run根目录执行`python3 source/project/experiments/shared_a32_native/collect_server.py JOB_ID`，回收非obj日志、结果/stat JSON、综合脚本及生成bench。较大的`mapped.json`、`mapped.v`留服务器；完整输出SHA索引仍覆盖这些网表，不删除原始文件或略过原面积检查。

当前本地只进行Python语法、纯文本派生和静态接口审查。RTL编译、仿真、综合结果以之后的实际Slurm回执为准。管理结构核验由根会话在完整正式快照运行；开发子集工作树不补管理模板。
