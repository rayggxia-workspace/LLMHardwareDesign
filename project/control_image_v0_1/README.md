# 控制镜像与配置装载参考 v0.1

对应 [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) 的第3步，正式合同见 [CONTROL_IMAGE_LOADING_V0_1.md](../../docs/local-blocks/CONTROL_IMAGE_LOADING_V0_1.md)。

- image.py：沿用ISA v0.1的128B头和16B小端指令，装配、解析及有限部署准入。
- bundles.json：3份manifest与7份完整镜像hex，共2080B；镜像与规范化manifest分别有SHA-256。
- loader.py：单bank、全cohort有效互锁、16B顺序写、校验／提交、排空／复位的软件模型。
- config_contract.json：配置动作类型、单位、状态和失败效果；没有新增运行ISA或冻结配置线编码／MMIO地址。
- test_image.py：30组镜像／装载检查，含独立手写字节向量和故障注入。

仓库根执行，只有Python标准库依赖：

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B project/control_image_v0_1/image.py build --output image-bundles-check.json
python -X utf8 -B -m unittest discover -s project/control_image_v0_1 -p test_image.py -v
```

输出临时文件应与bundles.json逐字相同；不纳入交付。同时运行ISA、接口和轨迹三套既有测试，命令见 [ARCHITECTURE](../../docs/ARCHITECTURE.md)。

示例API：begin(manifest, manifest_sha256) → 对每target按offset=0,16,...执行write16 → verify(target) → commit → start。带generation的方法须传begin后读出的generation。typed API使用Python bytes；bundles.json中的hex是文件表示，不代表配置总线使用ASCII。

START返回entry_admitted=true、instructions_executed=false、rtl_tested=false，**不运行PC**。profile 0x17630001支持直线空任务、M op6和RAW16接收先行案例；其支持子集由image.py的SUPPORTED明确列出，其余合法ISA仍拒绝。容量上限不是完整支持所有表项数量的承诺：每局控只允许1任务、最多1对象、单在途服务，路由仅研究fixture 255→0及0→1。

reset保留RAM但清除全部valid；外部cohort复位确认后仍必须重新装载。无tag宏的旧响应不能靠软件generation甄别，实际provider复位／排空证据仍是后续硬件接口门。SHA在主机／参考模型计算，没有假定片上SHA或提供签名认证。软件准入不证明真实金属连通、S写入、无死锁、宏运算、控制时序或物理资格。本轮未实现完整Block或新增服务器仿真。

