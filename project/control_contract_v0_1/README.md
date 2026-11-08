# 控制接口合同参考 v0.1

对应 Issue179 / PR180 的第1步：固定资源、原生端口、接受／完成及 native 字布局。只研究母控／局控，不实现完整 Block。机器 ISA 仍为 sibling 目录 control_isa_v0_1 的 v0.1。

- native_interfaces.json：6 个来源模块的 149 个实际端口声明和握手／复位／上下文边界。
- control_links.json：母控／局控任务与事件、局控／适配器元数据合同；这些为控制接口建议，不是已有原生端口。
- services.json：12 个 P 范围服务注册项及 proposed native_abi_id=65537（0x00010001），不作为已部署硬件 ABI。
- profiles.json：P16_M_ONLY 与 P16_VIA_S，两者控制归属／资源 mask 相同，数据路线要求不同；均为研究需求，不是已连接版图。
- contract.py：复用已有 codec 的 execution／object 编码规则，静态检查已注册服务、native 位、容量／窗口、对象引用和路线要求，给出拟议端口映射。
- examples.json / test_contract.py：5 个字段示例和 15 组独立向量／拒绝检查。

```powershell
python -X utf8 -B -m unittest discover -s project/control_contract_v0_1 -p test_contract.py -v
python -X utf8 -B project/control_contract_v0_1/contract.py examples
```

static_fields_valid=true 仅表示本工具已覆盖的静态字段合法；deployable 始终 false。工具不执行指令／数值计算、不生成完整镜像或验证 RTL／真实连线。对象初始有效字节为0不等于数据就绪；本工具要求固定地址／静态无重叠分配，动态字段、未登记服务、32KiB 或 M→G 直通 profile 均拒绝。

M 读出 op5 可保存 RAW_BYTES 或 S32 容器；G 参考适配接口按四个 S32 容器中的 S16 有效值拆成两个原生包，再将结果符号扩展回一个128bit S写。转换／holding／S helper 是待实现接口需求，核心 G 仍为两路S16。Q格式、数值范围、上下文、数据就绪和真实ACK由后续编译／执行模型核对；单独检查描述符不能证明完整链合法。

来源／Git blob／SHA见 [来源索引](../../work/Melodydt/179/control-interface-sources.json)，研究结论见 [接口合同](../../docs/local-blocks/CONTROL_INTERFACE_CONTRACT_V0_1.md)。每次接续研究和上传前必须读 PR176 最新 head／说明／评论／review，按 [同步回执](../../work/Melodydt/179/pr176-sync.json)记录差异；这不是后台自动监测。
