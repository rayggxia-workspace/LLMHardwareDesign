"""Source-grounded supplementary records; values are transcriptions, not new experiments."""
def build():
    papers=[]
    def paper(id,title,kind,url,locator,hardware,boundary,notes,rows=None):
        p=dict(id=id,title=title,kind=kind,url=url,locator=locator,hardware=hardware,boundary=boundary,notes=notes,rows=rows or [])
        papers.append(p)
        return p
    def row(model,precision,stage,tps=None,tpj=None,power=None,conditions='',method='原文',**kw):
        return dict(model=model,precision=precision,stage=stage,tps=tps,tpj=tpj,power=power,conditions=conditions,method=method,**kw)
    p=paper('R01','ProQuant: Progressive Quantization-aware Training for Edge MLLMs','ASIC + DDR4','https://arxiv.org/html/2611.08216v1#A5','2026，arXiv v1；附录 E，表 A7-A12',
      'TSMC 22 nm 流片；8 GB DDR4，38.4 GB/s；权重和 token SRAM 各 4 MB；INT8 峰值 2.46 TOPS。具体工作频率、电压和裸片面积未核实。',
      '芯片计算延迟/功耗实测，DRAMPower 估计 DDR4 能耗，周期模型组合整模型；不含控制 FPGA、主机和测量设备。',
      '统一取视觉 V=256、文本 T=256 的工况，不是“256 输入/256 输出”。视觉骨干通常保持 BF16。原文prefill速率为整次请求/s；本报告按512个视觉+文本token另算等效输入吞吐，包含视觉编码开销，不能视为纯文本吞吐。')
    raw=[('Qwen2-VL-2B',[(124.55,493.04),(62.71,246.94),(31.79,124.33),(31.40,123.95)],[(877.02,2400.87),(863.03,1519.00),(530.80,1020.90),(350.51,779.96)]),
         ('Qwen2.5-VL-3B',[(248.69,984.06),(125.07,492.73),(63.25,247.63),(62.45,246.85)],[(1663.57,4802.11),(1582.40,2690.07),(882.53,1580.31),(507.40,1030.43)]),
         ('Qwen3-VL-2B',[(140.46,556.20),(70.35,278.22),(35.89,141.56),(35.89,141.56)],[(869.62,2227.72),(857.16,1375.00),(498.60,860.56),(300.42,569.67)])]
    for model,dec,pre in raw:
        for stage,vals,n in [('decode',dec,1),('prefill',pre,512)]:
            for prec,(t,e) in zip(['BF16','W8A8','W4A8','W4A4'],vals):
                p['rows'].append(row(model,prec,stage,n*1000/t,n*1000/e,e/t,'V256 + T256；batch 未明；生成总长度未明','换算：N×1000/ms；N×1000/mJ',latency_ms=t,energy_mj=e,numerator_tokens=n))
    paper('R02','VitaLLM: A Versatile and Tiny Accelerator for Mixed-Precision LLM Inference on Edge Devices','ASIC','https://arxiv.org/html/2605.00320v1#S4','2026，arXiv v1；表 I、§IV',
      '16 nm；1 GHz / 0.8 V；0.214 mm²；120 KB SRAM；权重与 KV 位于片外 DDR。',
      '作者称硅原型，但未充分说明整板测量方法。59.12 mW 为所列设计功耗，是否包含片外 DDR 未明；以下能效只按此边界换算。',
      '与下一篇是同一设计系列的不同论文，不能混用速度与功耗；量化为三值权重/INT8 激活，不是 W8A8。',
      [row('BitNet b1.58 3B','三值 W / INT8 A','decode',72.46,72.46/.05912,.05912,'解码上下文、batch 未明','换算；DDR 边界待核实'),row('BitNet b1.58 3B','三值 W / INT8 A','prefill',64/.88,None,None,'64 输入；0.88 s；不配对 decode 功耗','换算输入吞吐')])
    paper('R03','VitaLLM: A Versatile, Ultra-Compact Ternary LLM Accelerator with Dependency-Aware Scheduling','ASIC','https://arxiv.org/html/2604.27396v1#S4','2026，arXiv v1（作者声明期刊接收）；表 V-VI、§IV',
      '16 nm；1 GHz / 0.8 V；0.223 mm²；130.5 KB SRAM；LPDDR5T 峰值 76.8 GB/s，读峰值 63 GB/s。',
      '性能模型与布局后门级仿真交叉核对；65.97 mW 对应 3B 设计，DDR 能耗未单列。2B 不复用该功耗。',
      'Top-32 KV 筛选减少注意力访存；预填充 3B/2B 分别为 0.88/0.65 s。原表能效1098.38 tokens/J与70.70/0.06597=1071.70不一致；此处保留明确算式的后者。',
      [row('BitNet b1.58 3B','三值 W / INT8 A','decode',70.70,70.70/.06597,.06597,'上下文、batch 未明','换算；DDR 边界待核实'),row('BitNet b1.58 2B','三值 W / INT8 A','decode',99.21,None,None,'2B 专属功耗未报告'),row('BitNet b1.58 3B','三值 W / INT8 A','prefill',64/.88,None,None,'64 输入；0.88 s','换算输入吞吐'),row('BitNet b1.58 2B','三值 W / INT8 A','prefill',64/.65,None,None,'64 输入；0.65 s','换算输入吞吐')])
    paper('R04','TOM: A Ternary Read-only Memory Accelerator for LLM-powered Edge Intelligence','ROM ASIC','https://arxiv.org/html/2602.20662v1#S5','2026，arXiv v1；表 I/IV，图 11-12，§V',
      '7 nm；500 MHz；56.9 mm²；ROM 498.54 MB + SRAM 37.5 MB；200 TB/s 片上汇总带宽；最大片上上下文 1024。',
      'Verilator 周期仿真、综合及 PowerArtist；ROM 子模块做布局布线。5.33 W 为门控后的芯片估算，不含主机。',
      '基座权重固定在 ROM；302.4 μs/token 是单步峰值，精确上下文未绑定。用论文总体功耗换算的 620 tokens/J 是条件估算，不是同时间窗实测。',
      [row('BitNet b1.58 2B','三值 W / FP8 A,KV','decode 峰值',1e6/302.4,(1e6/302.4)/5.33,5.33,'B1；评估输入/输出各含64-512；峰值的具体长度未明','条件换算',latency_us=302.4)])
    paper('R05','ROMA: a Read-Only-Memory-based Accelerator for QLoRA-based On-Device LLM','ROM ASIC','https://arxiv.org/html/2503.12988v1#S4','2025，arXiv v1；表 I、图 7/9、§IV',
      'TSMC 7 nm；500 MHz；503.7 mm²；1.86 GB ROM + 304 MB SRAM；表 I 功耗 33.1 W。',
      'RTL 综合、PrimeTime PX 估算；权重与 KV 片上。未给逐阶段积分能量，表内 tokens/J 统一以 33.1 W 作条件换算。',
      'LoRA rank 16、FP8；激活/KV FP16。空 KV 峰值不能代替长文本持续生成。FP16 KV 和固定 ROM 属于此设计的关键条件。',
      [row('Llama3.2-3B','W4 / FP16 A,KV','decode 峰值',31800,31800/33.1,33.1,'空 KV；rank16','条件换算'),row('Llama3-8B','W2 / FP16 A,KV','decode 峰值',24100,24100/33.1,33.1,'空 KV；rank16','条件换算'),row('Llama3.2-3B','W4 / FP16 A,KV','端到端',20078,20078/33.1,33.1,'256 输入 / 4096 输出','条件换算'),row('Llama3.2-3B','W4 / FP16 A,KV','端到端',8533,8533/33.1,33.1,'2048 输入 / 4096 输出','条件换算')])
    paper('R06','PALUTE: Processing-In-Memory Acceleration via Lookup Table for Edge LLM Inference','M3D DRAM PIM','https://arxiv.org/html/2606.08891v1#S4','2026，arXiv v1；表 1-2、§4',
      '7 nm 逻辑 / 200 MHz；假设 35 nm、768 层、24 GB M3D DRAM；112.4 mm² 为存储/逻辑中较大裸片面积。',
      '周期仿真 + 逻辑综合；端到端模型含 DRAM LUT 查询、累加和生成器。0.16 W 是四舍五入值，保留原报 7738 tokens/J。',
      '摘要将 headline 绑定 Qwen3-4B；另评估0.6/1.7/8B。表 2 未清楚绑定 batch 与输入/输出长度。正文对 FIGLUT 的能效倍数与表内数字不一致；只保留原始绝对值并标待核实。',
      [row('Qwen3-4B','W4A4','作者称端到端 decode',1264,7738,.16,'摘要绑定4B；表2 headline；长度/batch 未明','原文；条件不完整')])
    paper('R07','NVLLM: A 3D NAND-Centric Architecture Enabling Edge on-Device LLM Inference','NAND + NPU','https://arxiv.org/html/2604.25699v2#S4','2026，arXiv v2；表 2-3，图 6(a)',
      'TSMC 28 nm；NPU 500 MHz / NAND CMOS 350 MHz；NPU 0.459 mm²、240.15 mW；新增 NAND 逻辑 2.692 mm²、895.68 mW。',
      '模块综合 + 存储周期模型；所列功耗不是各容量配置的完整系统功耗，不能相加后直接算 tokens/J。',
      'FFN 权重在 NAND，attention 权重与 KV 经 LPDDR5X。',
      [row('OPT-2.7B','INT8','decode',t,None,None,f'上下文64；{n} NAND planes；{v}') for t,n,v in [(23.2,32,'基础'),(29.9,48,'12C'),(35.4,64,'16C')]])
    paper('R08','P³-LLM: An Integrated NPU-PIM Accelerator for Edge LLM Inference Using Hybrid Numerical Formats','HBM-PIM','https://arxiv.org/html/2511.06838v4#S6','arXiv v4；表 VII-VIII、图 13',
      '28 nm PCU 综合后缩放到 20 nm；4 个 1 GHz NPU；16 个 HBM 伪通道；PCU 500 MHz。PCU 计算8.4 mm² + 缓冲6.2 mm²。',
      '周期仿真；0.18 pJ/MAC 是 PE 级指标，缺少完整模型能量，不能换算 tokens/J。',
      '总吞吐为同批所有序列之和，不能作为每用户速度。图估读，保留两位有效数。A8为FP8-E4M3、P8为FP8-S0E4M4，不能称全INT8。',
      [row('Llama3.2-3B','W4A8KV4P8','decode',v,None,None,f'上下文4096；batch={b}；总吞吐','图估读') for b,v in [(1,360),(2,670),(4,670),(8,890)]])
    # Prior works retained with explicit missing-data status. None is promoted to an absolute throughput result.
    missing=[
      ('M01','Slim-Llama','ASIC 流片','https://doi.org/10.1109/ISSCC49661.2025.10904761','ISSCC 2025，23.9；官方项目页及原论文','Llama-3B；二值/三值 W','Samsung28 nm；20.25 mm²；500 KB；25-200 MHz；0.58-1.0 V','4.69 mW @25 MHz 与82.07 mW @200 MHz是不同点。28.3-41.3 μJ/token 的阶段与token定义未充分核实，不转换为输出tokens/J。连续decode绝对速度未核实。'),
      ('M02','TENET','稀疏三值 ASIC','https://arxiv.org/html/2509.13765#S5','2025；§V，表IV','Sparse BitNet-3B；三值','28 nm；500 MHz；91 mm²；1.375 MB缓冲；HBM2 512 GB/s','5.7 W为加速器合计。3B端到端相对优化A100为1.33倍；缺绝对tokens/s及同窗HBM能量。'),
      ('M03','MARCA','SSM ASIC','https://dai.sjtu.edu.cn/my_file/pdf/010527f5-f0b2-4859-8c27-9052bd14da49.pdf','ICCAD 2024；表4、图9、§7','Mamba-2.8B；32位定点','28 nm；1 GHz；221.88 mm²；24 MB SRAM；HBM1 256 GB/s','10.44 W为表内模块合计；长度1与64-8192分decode/prefill，结果以相对加速呈现，缺绝对tokens/J。'),
      ('M04','MARCA-v2','SSM ASIC','https://doi.org/10.1109/TCAD.2025.3624278','TCAD；表III、图13、§VII','Mamba-2.8B；32位定点','28 nm；1 GHz；296.37 mm²；24 MB+16 KB；HBM1 256 GB/s','113.24 W是峰值估算，不与MARCA的10.44 W直接相比。缺逐模型绝对速度与能量。'),
      ('M05','Platinum: Path-Adaptable LUT-Based Accelerator Tailored for Low-Bit Weight Matrix Multiplication','算子 ASIC','https://arxiv.org/html/2511.21910#S5','2025；§V','BitNet b1.58 3B提取的BitLinear；三值','28 nm；500 MHz；0.955 mm²；324 KB；DDR4 64 GB/s','3.2 W对应预填充矩阵负载，DRAM占53.5%。N=1024/N=8是矩阵列/批维，不代表完整自回归推理；不推算tokens/J。'),
      ('M06','HB-PIM: Unifying Two Operators with One PIM','3D DRAM PIM','https://doi.org/10.1007/978-981-95-1021-4_16','表2、图8','OPT-2.7B等','32 nm；1 GHz；每DuoPU 1.24 mm²、807.81 mW；16GB','4.06倍为跨模型平均吞吐加速；单DuoPU功耗不等于16核系统功耗；缺逐模型绝对tokens/J。'),
      ('M07','Titanus: Enabling KV Cache Pruning and Quantization On-the-Fly for LLM Acceleration','CIM','https://arxiv.org/html/2505.17787#S5','2025；§5','OPT-2.7B/6.7B等；W8A8、KV INT3','14 nm；200 MHz；CIM宏由22 nm缩放','2.7B质量实验不等于该模型吞吐；headline为6.7B。31.95 W对应125M单核，不配对6.7B或2.7B算tokens/J。'),
      ('M08','TriGen','混合精度 ASIC','https://arxiv.org/html/2602.12962v1#S7','2026；表IV-V、图9','Llama3.2-3B/OPT-2.7B；MXINT8 A/UINT4 W','14 nm；1 GHz；1 MiB/NPU；DRAM32 GB/s','序列2048，相对基线延迟约0.36/0.39；绝对速度与完整功耗未核实。'),
      ('M09','FlexPosit','Posit ASIC','https://arxiv.org/html/2609.04724v1#S6','2026；表II/VIII、图11','Phi-2 2.7B/OPT-2.7B；平均4.5/4.1 bit W，FP16 A','16 nm；1 GHz；两类缓冲各512 KB；DDR4','B1/输入256，相对FP16延迟0.247/0.225。0.109761 mm²、65.537 mW只对应32×16阵列；不算系统tokens/J。'),
      ('M10','Pimba','GPU + SSM PIM','https://arxiv.org/html/2507.10178v3#S6','MICRO 2025；表3、图12','RetNet/GLA/HGRN2/Mamba-2 2.7B；MX8状态','45 nm综合缩放10 nm；SPU378 MHz；HBM2E1512 MHz','输入/输出各2048；Mamba B32/64/128相对A100约1.4/1.8/2.4倍。单元0.092 mm²、计算8.2908 mW不是整GPU+PIM功耗。'),
      ('M11','MX-like Tensor Core','算子 ASIC','https://arxiv.org/html/2610.26083v1#S4','2026预印本，标称ASPDAC2027；§4、图5(d)','Qwen2.5-3B层数据；MX浮点','28 nm；400 MHz；0.8 V；0.646 mm²；51.6 mW','204.8 GOPS对应4×16 PE和重量化；32×1024为数据块，不是端到端tokens/s。')]
    for id,title,kind,url,loc,model,hw,note in missing:
        p=paper(id,title,kind,url,loc,hw,'缺少可配对的整模型绝对速度/能量；保留证据缺项。',note)
        p['models']=model;p['missing']=True
    return papers
