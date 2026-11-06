# Issue #55：六个 Block 的内部单元与实际布线图

本页补充上一批接口图未显示的内部内容，关联 [PR #58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58) / [Issue #55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)。

**内部物理数据此前已经存在；本页图片是这次新导出的，不能说这些图片此前已经做完。** 本次只读消费封存的原生导出，不重新布局、综合或布线，不改数据库。

## 先看什么

- 单元布局图：每个小矩形对应实际放置的标准单元；蓝色为其他逻辑单元、橙色为按master名称识别的寄存器／锁存单元、紫色为存储宏。分类是显示辅助，不是新功能分区证明。红框是放大窗口。
- 实际布线总图：读取全部原生金属导体矩形；全层叠加时高层颜色会覆盖低层，不能仅凭总图判断连接。
- M1–M8分层图：逐层分开显示，彩色为信号／时钟金属和via包围，灰色为供电导体。OBS障碍不当作导线绘制。
- 局部放大图：约24×24μm窗口，灰色小格为真实单元边界，彩线为真实金属，部分黑色小框为via cut；窗口从最接近Block中心的真实状态单元确定，并非手画电路。某层显示0条表示该窗口没有该层导体，不表示全块没有。

这些图是LEF/OpenDB层级的单元／存储宏与布线图，**不是晶体管原理图，也没有凭空展开标准单元内部的晶体管连线**。全景有限像素会合并细小形状；放大图和逐层图用于看细节，原始无损数据库仍留服务器。

## 所有六个 Block

| Block | 实际实例数 | 读取原生形状行数 | 图片 |
| --- | ---: | ---: | --- |
| opentpu_auxiliary | 445,524 | 13,603,304 | [单元](opentpu_auxiliary-cells.png) · [总布线](opentpu_auxiliary-routes.png) · [逐层](opentpu_auxiliary-layers.png) · [放大](opentpu_auxiliary-detail.png) |
| opentpu_act | 16,178 | 193,235 | [单元](opentpu_act-cells.png) · [总布线](opentpu_act-routes.png) · [逐层](opentpu_act-layers.png) · [放大](opentpu_act-detail.png) |
| opentpu_mxu | 441,518 | 5,003,770 | [单元](opentpu_mxu-cells.png) · [总布线](opentpu_mxu-routes.png) · [逐层](opentpu_mxu-layers.png) · [放大](opentpu_mxu-detail.png) |
| llaccel_auxiliary | 546,792 | 16,519,607 | [单元](llaccel_auxiliary-cells.png) · [总布线](llaccel_auxiliary-routes.png) · [逐层](llaccel_auxiliary-layers.png) · [放大](llaccel_auxiliary-detail.png) |
| llaccel_gemm | 571,780 | 6,571,452 | [单元](llaccel_gemm-cells.png) · [总布线](llaccel_gemm-routes.png) · [逐层](llaccel_gemm-layers.png) · [放大](llaccel_gemm-detail.png) |
| llaccel_vector | 733,546 | 8,897,011 | [单元](llaccel_vector-cells.png) · [总布线](llaccel_vector-routes.png) · [逐层](llaccel_vector-layers.png) · [放大](llaccel_vector-detail.png) |

## opentpu_auxiliary

实际实例：445,524；显示分类：{"state_cell": 72508, "logic_cell": 372995, "memory_macro": 21}。放大中心依据真实实例 _29822_\\[11\\]$_DFFE_PP_，master=DFF_X1。

### 内部单元布局

![opentpu_auxiliary实际单元布局](opentpu_auxiliary-cells.png)

### 内部实际布线总图

![opentpu_auxiliary实际布线](opentpu_auxiliary-routes.png)

### M1–M8 分层布线

![opentpu_auxiliary分层布线](opentpu_auxiliary-layers.png)

### 实际单元和连线的局部放大

![opentpu_auxiliary内部单元与连线放大](opentpu_auxiliary-detail.png)

## opentpu_act

实际实例：16,178；显示分类：{"logic_cell": 15566, "memory_macro": 6, "state_cell": 606}。放大中心依据真实实例 u_act.wd\\[237\\]$_DFF_P_，master=DFF_X1。

### 内部单元布局

![opentpu_act实际单元布局](opentpu_act-cells.png)

### 内部实际布线总图

![opentpu_act实际布线](opentpu_act-routes.png)

### M1–M8 分层布线

![opentpu_act分层布线](opentpu_act-layers.png)

### 实际单元和连线的局部放大

![opentpu_act内部单元与连线放大](opentpu_act-detail.png)

## opentpu_mxu

实际实例：441,518；显示分类：{"logic_cell": 405095, "state_cell": 36417, "memory_macro": 6}。放大中心依据真实实例 u_mxu.rowi\\[48\\]$_DFF_P_，master=DFF_X1。

### 内部单元布局

![opentpu_mxu实际单元布局](opentpu_mxu-cells.png)

### 内部实际布线总图

![opentpu_mxu实际布线](opentpu_mxu-routes.png)

### M1–M8 分层布线

![opentpu_mxu分层布线](opentpu_mxu-layers.png)

### 实际单元和连线的局部放大

![opentpu_mxu内部单元与连线放大](opentpu_mxu-detail.png)

## llaccel_auxiliary

实际实例：546,792；显示分类：{"logic_cell": 481247, "state_cell": 65545}。放大中心依据真实实例 u_attn.row_asm\\[472\\]$_DFFE_PN0P_，master=DFFR_X1。

### 内部单元布局

![llaccel_auxiliary实际单元布局](llaccel_auxiliary-cells.png)

### 内部实际布线总图

![llaccel_auxiliary实际布线](llaccel_auxiliary-routes.png)

### M1–M8 分层布线

![llaccel_auxiliary分层布线](llaccel_auxiliary-layers.png)

### 实际单元和连线的局部放大

![llaccel_auxiliary内部单元与连线放大](llaccel_auxiliary-detail.png)

## llaccel_gemm

实际实例：571,780；显示分类：{"logic_cell": 550420, "state_cell": 21360}。放大中心依据真实实例 acc\\[9\\]\\[251\\]$_SDFFE_PP0P_，master=DFF_X1。

### 内部单元布局

![llaccel_gemm实际单元布局](llaccel_gemm-cells.png)

### 内部实际布线总图

![llaccel_gemm实际布线](llaccel_gemm-routes.png)

### M1–M8 分层布线

![llaccel_gemm分层布线](llaccel_gemm-layers.png)

### 实际单元和连线的局部放大

![llaccel_gemm内部单元与连线放大](llaccel_gemm-detail.png)

## llaccel_vector

实际实例：733,546；显示分类：{"state_cell": 4117, "logic_cell": 729429}。放大中心依据真实实例 wr_data_r\\[48\\]$_DFFE_PN0P_，master=DFFR_X1。

### 内部单元布局

![llaccel_vector实际单元布局](llaccel_vector-cells.png)

### 内部实际布线总图

![llaccel_vector实际布线](llaccel_vector-routes.png)

### M1–M8 分层布线

![llaccel_vector分层布线](llaccel_vector-layers.png)

### 实际单元和连线的局部放大

![llaccel_vector内部单元与连线放大](llaccel_vector-detail.png)

## 来源、版本和验收边界

- 六块全部来自共同候选图绑定的 runs/union-native-placement-r01-timing-repair-4c-01/expected_placement.json 内的六份child database／native导出。每份数据库和实际使用表的SHA-256见 [manifest.json](manifest.json)，不把旧快照冒充后续修复版。
- 四核可视化作业 92817 已实际完成，最多4个独立worker、每worker的NumPy／BLAS等线程为1；未停止或重复任何仍在运行的主线实验。
- 全部实例行逐项绘制并核对metadata实例总数；全部原生形状行逐项读取，按kind/sig/layer/type核对封存shape_counts，六块均完全一致。输入压缩表SHA-256与原闭合回执一致。PNG解析验证通过。
- 绘图完整性不等于连接、短路、DRC、功能或时序通过；本次未新增这些验证。源快照已有质量限制继续有效，底座未冻结。
- 全景只投影ROUTING导体，CUT用于局部层相邻示意；BLOCK_OBS不当导体，标准单元内未由原生导出提供的几何不补画。所有CUT／OBS仍纳入读取计数核对。
- 图形生成器 [render_internal.py](render_internal.py) 同步保存用于复核，仅为此快照可视化程序，不代表通用映射算法交付。
- 旧[接口／共同候选布局图集](../issue-55-block-diagrams-20261028/README.md)及原[Block布局与接口分布报告](../../../../ref-project/llm-routing/docs/Block布局与接口分布报告.html)继续保留，没有覆盖原图。

规则rayggxia-project-collab 1.0.0；本人huangpingyang04-lgtm；登记沿用管理中心PR5 pending（本次未重核），缺config/board.json，看板unverified／同步pending，待有权限维护者；审查人待指定。Refs #55，PR保持草稿，不合并、不改变主线任务验收状态。

实际资源统计：作业92817 wall=138s，总CPU=412.057s，平均约2.99核（4核容量的74.65%），最大RSS=181108KiB；申请4核不等于每一瞬间使用4核。
