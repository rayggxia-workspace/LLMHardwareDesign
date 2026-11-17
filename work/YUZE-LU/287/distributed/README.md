# 646条真实线路的分布RC与双频率STA回放

2026-11-17，YUZE-LU，Issue #287 / PR #288。1292/1292个场景完成，缺项0。原件：`/public/home/yuzelu/project-circuit/issue287-distributed-20261117`。

|真实线路来源|数量|200MHz最差setup ns|300MHz最差setup ns|300MHz负setup数量|源端电容超限数量（每个频率）|
|---|---:|---:|---:|---:|---:|
|A C/U|306|+0.401093|-1.265573|295|305|
|B C/U|306|+0.299329|-1.367338|295|304|
|B G/S|34|+0.037752|-1.628914|34|34|

200MHz全部setup为正，300MHz共624/646条setup为负。全部hold为正，最差+0.426257ns。源端电容超限643/646，slew超限638/646；名义上同时通过本夹具setup/hold及源端电气检查的记录为A1条、B2条。数值接近库限制者仍受提取统计误差影响，不能仅凭名义通过授予更大范围资格。过载点可能含Liberty外推，其slack作为诊断，不可用于可信最高频率或器件验收。

## 方法和范围

每份真实线路RC分别复制到同一合格C V3/U39 v02基准的128位native_tx_data_o→native_rx_data_i接口，取128位路径的最差setup/hold。保留真实门级单元、块内SPEF与原Liberty；沿用前轮理想父层时钟、块内传播时钟、0.1ns uncertainty及相同IO约束。200/300MHz周期为5ns及3.333333333333ns。这里不是A/B当前CTS实现自身的系统STA，也不是G宏到S宏的原生功能路径验收；G/S线路同样只作为C/U基准的负载输入。

先重建实际线路中心线/过孔电阻图，再对两套真实上层几何运行OpenRCX。646条网的两端连通性和电阻总量全部核对通过；采用0.03Ω/□、2μm线宽、0.08Ω过孔的既有研究工艺模型，并计入OpenRCX默认端部延伸。实际节点图细分至最长50μm。模型不是实际激光直写材料的实测工艺角。

电容采用均匀介质εr=3.9的完整上层场景，P金属保留但信号静止。重新对RC节点提取本地静态自电容，并将积分面采样点先投影到最近的真实电阻边，再归入相邻节点，避免折返线路上仅按离散节点距离归属。未使用旧box中心bins直接生成新SPEF，也未按线长均匀分摊C。所有节点C都包含邻线静止时的对地及互容负载；导出的SPEF为该条件下的对地电容网络，不是动态SI所需的完整节点互容矩阵。

逐网比较0.125与0.0625两档积分面距离，共1292行场解；所有节点非负、总量守恒、总C与前轮全量场解在5σ内一致。节点C按前轮整网总C归一化以保持同一负载，未裁掉负电容。归一化电阻加权一阶矩差最大0.000114716ns（0.115ps），通过预设max(0.2ps,1%)检查。另以六条几何代表线做25μm细网格复核，最大一阶矩差约0.001ps。这些是本研究静态模型的数值检查，不代表硅后验证或#222一般物理来源分摊资格。

## STA验证与执行

旧零RC控制复现setup +2.079750ns、hold +0.373600ns；旧P50复现setup +1.573235ns、hold +0.538236ns。串行更换负载再切回零RC后完全恢复，未发现寄生残留。逐位查询与128驱动集合最差路径查询的8个极值完全一致；后续使用等价集合查询加速，并保留起点C、终点U的检查。1292场景全覆盖，646组双频率setup差与周期差一致，hold及电气违例状态一致。

119599初始节点验证；119602边投影验证；119604全量1292节点场解；119606两套OpenRCX；119607 STA控制；119608网格复核；119612最差路径查询等价验证。119609逐位STA保留104个完成场景后停止以切换等价查询；119615和119619各节点8任务、每任务2线程完成余下场景。全量覆盖核验通过后停止119615剩余重复工作；中间未完成目录保留但不纳入结果。每个最终CSV行给出实际报告目录。

## 文件与复现

[1292行CSV](results/sta-all.csv)、[汇总](results/sta-summary.json)、[最终校验与SHA](results/final-validation.json)、[节点验证](results/node-validation.json)、[RCX验证](results/rcx-validation.json)、[网格复核](results/mesh-validation.json)、[STA控制](results/sta-pilot-validation.json)、[查询等价检查](results/fast-pilot-validation.json)。完整SPEF、场行、私有求解器快照/编译输入SHA、逐路径报告和日志留上述远程目录。

复现应复制至新目录并修改脚本绝对路径，保留当前原件。prepare.py生成图和场景；edge_projection.py生成私有求解器；edge_pilot.sh验证后运行all_nodes.sbatch；rcx_prepare.py及rcx.sbatch提取R，check_rcx.py核对；validate_nodes.py、mesh_refine.sbatch及mesh_compare.py验证分布；sta_prepare.py及sta_pilot.sbatch验证夹具；fast_prepare.py、fast_check.py通过后执行分片STA；summarize_sta.py及final_check.py汇总验证。plot_results.py仅在1292行齐备后生成图。

规则rayggxia-project-collab 1.0.0；管理结构检查不替代业务验证。成果待独立审查，不合并、不关闭Issue。登记PR5 pending；缺board配置，看板unverified/同步pending。当前A/B实际版本验收仍需要自身后端闭合、明确G/S旧驱动切断点及完整顶层时钟/功能路径。
