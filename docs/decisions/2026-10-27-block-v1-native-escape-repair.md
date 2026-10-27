# 原生预制接入线的有限修复

135完整接收失败、148定位通过后，实际133封存DEF显示部分M10端口接入线存在U形折返，A的read_data[43]在M9还有无其他锚点的树枝。C的begin_words[0]折返线与[1]仅0.07µm间距，原生规则要求0.8µm。原生TRACKS、077锁定pin与via9网格读回一致，当前证据不支持以网格失配解释这些标记。

固定上游OpenROAD提交[6556255的接入点实现](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/drt/src/pa/FlexPA_acc_point.cpp#L336)（文件Git blob `3448bacfa619416880c959b827624c7264817d8f`）中，VIAINPIN/VIA_ACCESS关闭平面接入的逻辑受`isStdCellTerm`条件约束。这是对端口仍可能有平面接入的源码解释；未证明安装二进制与该提交完全相同，也不以此代替实际路由证据。133已经完整使用这些参数，135仍检出间距，不能仅以参数已设置宣称via-only有效。

## 唯一确定性候选

`native_escape.py`只处理148实际命中的网络：一条固定BPin到一个现有via9的简单M10链。没有新增有源资源、改pin坐标、时序约束或搜索不同seed/偏移。

- 若M9已在BPin中心有现有树节点，将同一个via9移至该节点；保留到所有via8锚点的树路径，只去掉不再连接锚点的M9树枝与M10折返。
- 否则仅把M10链改为从pin横向、再到现有via9的确定性至多两段路径。M9/M10中心线总长均不得增加。
- M1–M8全部路径和via1–8、逻辑连接、实例、位置、PG、CTS、所有端口及其他网络必须保持。只支持明确的Manhattan路径语法；分支、多via9、额外延伸、环、未知矩形和上层cell锚点均拒绝。

这是**预制冻结之前**在独立副本上的修复。已封存133和135原始输出不改；未来两个定制产品仍只能改变M11/M12/via10/via11，不能在产品之间移动M9/M10或有源实例。

## 有限探针及资格边界

`native-escape-probe-group`在一个c96 allocation内并跑A/C，各2CPU，合计4CPU。原149填写16GiB申请，在提交前被既有`RealMemory=1`集群保护拒绝，没有dispatch-state/tasks/job；原部署不改，索引`run149-not-submitted`保留。150恢复既有`memory=0`整节点内存申请，未放宽dispatcher。运行时可用内存不足12GiB则顺序执行；独立失败不取消另一分支。本任务仍受6基础/8上限统一dispatcher限制，排队及未知提交计槽。

两路各绑定133完整源文件/回执、135失败全门结果、148零遗漏定位和077固定pin的SHA。OpenROAD先导出源DEF/Verilog/实际形状，副本仅替换计划中的wire，再严格读回全部网络及NETS之外字节、完整逻辑网表、未改网络实际形状和M1–M8形状。检查选中网络全部wire/库terminal的矩形连通，及对所有其他网（含PG）的M9/M10/via9重叠、接触和基础间距。真实去via9 cut、插入异网短路控制须被拒。

实际上下层mask另写独立GDS，读回XOR必须为零。原安装完整deck SHA为`4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`。探针建立明确标注的M9/via9/M10诊断子集，保留这些原生规则正文；先在源实际mask复现135同样18/2个分类标记，再要求修改后的上层诊断为零。它不替换、不修改正式完整接收器或完整规则。

语法、树锚点、DEF范围、missing-cut、异网短路/边接触的声明合成控制可本地运行：

```powershell
python project/experiments/block_v1/native_escape_control.py NEW_CONTROL.json
```

输出必须不存在。`escape-controls-149.json`保留早期控制，含边接触新增控制的复跑另写`escape-controls-149b.json`。这些是合成控制，不能证明实际OpenROAD编辑成功。

## 150实际失败与151修正

150/92236实际A/C两路均失败，1:14、TotalCPU2:09.030、MaxRSS1326488KiB；严格读回发现修改网没有ROUTED记录，未进入几何/DRC门槛。原OpenROAD命令虽然返回0，不能以退出码充当编辑成功。失败组/两子及原输出哈希保留于`run150-group-terminal`、`run150a-terminal`和`run150c-terminal`，不覆盖。

固定上游[definReader.cpp 1967行](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/odb/src/defin/definReader.cpp#L1967)（Git blob `a8044b54be76e89052244c5f94d58492122dbca6`）仅在DEFAULT/FLOORPLAN等模式注册NETS回调，INCREMENTAL没有NETS回调；这与150实际忽略patch路由一致。[definNet.cpp](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6556255d82c707820dd400e9b8cf331b378b735e/src/odb/src/defin/definNet.cpp#L54)（blob `22fb6bc7d134431f30aec144b0eb3f1d8d2bbcde`）会在读取既有网络时替换该网wire。

151只修正导入方式为`read_def -floorplan_initialize`，patch仍只列既有命中网络，没有COMPONENTS/PINS/PG/DIE/TRACKS等段；不再预先删除wire。所有原网络/范围/实际几何读回门槛保留；必须实际验证该安装版行为，不能仅凭上游源码宣称成功。151本源码提交时尚未部署/执行；同一4CPU/整节点内存allocation内A/C各2CPU，仍作12GiB内存预检。

即使149探针通过，仍须从修改后的真实ODB重新生成完整原生GDS、寄生、SDC与网表，并重跑完整DRC、全部端点STA/电气、PG/连接/LEC和实际最终功能；不能复用133旧SPEF充当新路由寄生。正式同源宏视图、flat/abstract边界、父层glue、完整恢复/epoch、一般多网分布十二层RC与原生/新层拼接、共同冻结父层、两产品和敏感性仍是独立门槛。探针的四个完整资格标志保持false。
