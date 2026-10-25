# Issue102：先固定整数函数，再接共享服务

采取三遍score的完整GQA8头/d128有限切片，与64整数参考逐位保持；实际cached独立从61编译。理由是先把S8分解、宽score/PV、SFU、LUT和单16KiB真实协议闭合，避免同时改online算法造成数值/电路变化无法归因。已通过证据和限制见[报告](../experiments/issue-102-attention-rtl.md)。

一个owner硬复位生命周期、version正数单调不回卷；新version显式取代旧版，同版scale/base固定且length不退。理由是只记last pair允许A→B→A绕过旧scale保护。调用者负责已提交KV前缀；RTL没有append完成证明。

下一条最小整合是M/A/R串行共享一个S/8S8/S32/SFU/link银行，逐个owner lease/drain、R原子提交和S覆盖生命周期验收。102的8S8目前内嵌控制器，抽离mux/仲裁须新增实际逻辑费用；不得把三个独立核心相加后声称共享。在线softmax、硬件append、宏与时序/产品定制另外验，不从当前raw gate外推。
