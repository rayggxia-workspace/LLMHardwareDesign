# V供电报告条件定位

Refs #121 / PR #122。用537既有allocation只读同一ORFS镜像脚本，未运行EDA或分配新节点。522/537工作器已记录的镜像SHA均49eae8b5，见image-bindings.json。原始文本、SHA/捕获时间见index.json及details/index.json。

平台默认VDD1.1/VSS0；PDN默认标准单元M1/M4/M7、顶层pin在M7。final_outputs.tcl在实际RCX之后设置网络电压并调用analyze_power_grid，未显式传-vsrc；脚本中也未见该位置载入活动文件。这些是镜像默认，不证明最终522不存在其他运行时覆盖，也不证明实际pad/bump或M10/未来M11-M12供电边界。

522原始报告总功率1.66W、VDD/VSS最差压降24.16%/31.19%仍保留，见533；不可把PG连接通过等同供电充分，也不能仅因默认边界未核实而豁免压降。后续须核对实际供电接入和活动/电流来源、必要时修正宏内PDN后重新验收。此处不引入整芯片或制造签核范围。
