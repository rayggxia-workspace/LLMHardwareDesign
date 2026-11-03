# 参考一致性、F整数回归与模型质量分开接收

Issue151/PR152，Melodydt；b18e8a5f/95979。官方Transformers层0参考必须实际调用并锁源码，容差在结果前固定；旧eval已被观察，只作回归，不倒推产品阈值。W8固定S16Fin10/S8Fin8/READ8/epsilon1，用原qnum静态-G验证，既有54RTL/TB不改，AF1024父控不自动切换。28框架stage和8F行×7Case/8流SHA分别接收；完整trained整数A→F、代表性新holdout、模型误差限及其它变体仍需独立门。每步同名覆盖现有本地交流PDF属于持续交付要求。
