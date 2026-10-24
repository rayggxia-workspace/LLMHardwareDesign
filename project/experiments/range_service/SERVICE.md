# Issue68：有限V/R/S条件服务

这是事件DAG可执行调度，不是测得的硬件周期、RTL或PPA。数值输入绑定Issue66
`state01/evaluation.S32.D31`和成本修订的`norm03/decode.tile16_delta_ACT8`，
二者是独立竞争流；32条norm行不能冒充旧256步R窗的连续完整模型消费者。
本工具不重跑模型、不下载权重、不重放数值内核，数学正确性由独立整数接收证明。

## 固定任务与预算

- R：两head，每head K128/V128，S32/D31，Q/K S16、beta U16、prediction/
  correction/输出受检I64。V按16/32切片，始终保留完整K归约。全部proposal写入
  后备新generation后才检查全group guard；成功再显式第二遍读回完整新state做
  输出，完整Vhead屏障后共同发布state/output/units/epoch/version。
- V：H2560，mixed I64+I16输入25,600B，X16行5120B，gamma S32Q20共10,240B。
  两遍源读与aligned spill写读40,960B互斥；gamma/K128流式。normQ20逐K128
  写回再读出确定新A8，不省略归一化后动态scale的max/编码依赖。
- 相同附加流：每norm行一个16×16×4096的矩阵代理，以及明确有界的FFN RQ/
  attention reduction代理。不能把这些代理称完整FFN/attention/整模型执行时间。
- 总计8个S8 lane、2个活动context和唯一共享sqrt/div SFU；后者按32/64迭代计。
  每个宽乘的S8 digit积后，后续每项合并都另计10个lane slot受检64位shift/add。
  I64 correction×U16使用10×3基础积，不能以观察值小暗中替换成S32。
- V16KiB、R32KiB、M32KiB、S八bank各32KiB，每bank只有1RW128bit端口；
  一条128bit总线，每包32B头/16B打包、最多1984B payload，每端2KiB FIFO。
  这是本服务的显式传输合同，未沿用旧数值工具64B头/64B打包后的数字。
  fresh A8实际payload=2560码+20个I8指数+32B descriptor=2612B，再付分包/总线头。

`shared2_6/shared4_4/shared6_2`和对应`split*`具有逐节点相同的lane分配、两context、
路由、银行和SFU，label-only control必须0差异。`shared8`每operation占整8lane是
单独的发射粒度profile，其结果不能当作纯物理独立R收益。不存在免费第二控制器或SFU。

## 容量、分页和失败恢复

R tile16的old/new分别8192B，另有aux8192B，共24KiB；tile32 old16384B加aux8192B，
new16384B必须放S4并逐不超过1KiB的受检结果fragment付R→S总线成本。
完整两head old/new各128KiB，不能免费驻留S或R；S2/S3仅分页暂存。
EXT有限128MiB，S32全模型状态48MiB、selected proposal128KiB、trial128KiB、真实
输入、descriptor及raw初态各有固定槽位。EXT单端口1/16 cycle每128bit是待校准敏感性。
两个generation在提交后交换角色，不复制整个模型；未访问的模型状态仍占容量。
初态row-major到候选tile-major的分页/布局转换显式收读取、地址/重排及写回成本。

`--range`接收真实`range-results.json`和逐case事务trace，核manifest/文件SHA后只选
`native.evaluation.S32.D31.guard_rescale`或
`legacy.layer0-end8192.S32.D31.guard_rescale`。每个失败attempt计完整decay/pred/
delta/outer/guard，不做未发布output。首次重试先复制完整两head committed state到
trial，然后只给坏head完整K×V RNE右移并写trial，每波写单位和epoch descriptor。
新proposal始终使用另一后备generation；R.aux中的70B提交descriptor读/写也付端口。
宽度失败若无法定价会明确拒绝服务，不给免费失败。原位更新缺相同rollback证明，
明确排除主排名。不同precision或commit/abort合同不并组排名。

## Witness与运行

每case/config各自搜索事先声明的fifo/critical两个顺序，不称全局最优。所有候选保存
完整canonical JSON gzip(mtime=0)，每node都有依赖、start/end、各资源相对区间、
payload和对象、token/head/tile/epoch；固定buffer槽从0到makespan常驻，清楚展示保守
高水位。单个packet包含source read→bus→destination write三个有序区间，同时占用
有限endpoint和FIFO credit；不能同拍将单口写读作两个端口。独立receiver可重算依赖、
resource sweep、容量、公式、source-bound token事件及label control。

```text
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/range_service -p test_service.py -v
python -B project/experiments/range_service/service.py --root <Issue66服务器根> --out <新目录> --binding <JSON>
python -B project/experiments/range_service/service.py --root <Issue66服务器根> --range <range-native01> --task native.evaluation.S32.D31.guard_rescale --out <新目录> --binding <JSON>
python -B project/experiments/range_service/service.py --root <Issue66服务器根> --range <range-legacy01> --task legacy.layer0-end8192.S32.D31.guard_rescale --out <新目录> --binding <JSON>
```

binding必须含真实`commit`与`service_sha256`。`--norm-stage`默认norm03，`--ext-ii`
默认1和16；根目录、输入manifest、单记录fingerprint、原units/epoch/commit和每个结果
SHA均记录。不覆盖已存在out。原state/range饱和、quality_accepted=false和浮点入口桥
不会因服务调度成功变成数值/模型/硬件验收通过。
