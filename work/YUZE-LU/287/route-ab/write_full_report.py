import pathlib,json,csv,collections
p=pathlib.Path(__file__).resolve().parent
s=json.loads((p/'all-summary.json').read_text());q=json.loads((p/'validation-all.json').read_text())
assert s['completed']==s['expected']==646 and not s['missing']
rows=list(csv.DictReader((p/'all-nets.csv').open()));assert len(rows)==646
out=['# A/B 全量非P真实连线评估','',
'2026-11-17，YUZE-LU，Issue #287 / PR #288。本轮覆盖646/646个方案—线网条目，替代上一轮六条探针作为总体统计依据。A 306根C/U；B 306根C/U及34根G/S。每根线实际求解，不按抽样线长或单位长度电容外推。P相关网不评驱动，其真实上层金属保留为电极。',
'','## 全量结果','',
'|方案/通路|网数|超限|已知负载未超限|长度中位/最大 mm|线路C中位/最大 fF|已知总负载中位/最大 fF|',
'|---|---:|---:|---:|---:|---:|---:|']
for k,g in s['groups'].items():
 a=g['length_um'];b=g['wire_self_fF'];c=g['known_total_fF'];status=g['cap_status']
 out.append('|%s|%d|%d|%d|%.3f / %.3f|%.2f / %.2f|%.2f / %.2f|'%(k,g['count'],status.get('exceeds',0),status.get('not_exceeded_known_load',0),a['median']/1000,a['max']/1000,b['median'],b['max'],c['median'],c['max']))
out += ['', '超限按每根线的真实输出单元Liberty上限计算。已知总负载包括线路Cg+Cc、接收输入引脚，以及已识别的源侧本地输入引脚；不包含块内连线C。未超限不能视为完整电气/时序通过。3σ统计判定：`'+json.dumps(s['cap_status_3sigma'],ensure_ascii=False)+'`；σ只覆盖场求解统计误差，不覆盖介质、几何或模型系统误差。',
'','## 全量数据入口','',
'- [646行可筛选排序表](all-nets.html)：按方案、通路、超限状态筛选，搜索线网/引脚/驱动，点击表头排序。',
'- [646行逐网CSV](all-nets.csv)：全部网名、驱动口、接收口、实际长度、过孔数、真实驱动与接收单元、Cg/Cc、自电容、已知总负载、库上限、负载倍数、统计误差、旧接收驱动、时序状态。',
'- [306行A/B同名C/U对照](CU-A-vs-B.csv)、[总体统计](all-summary.json)、[完整端点绑定](endpoint-binding.json)、[646条输入索引](inventory.json)、[数值检查](validation-all.json)。',
'','## 真实端点与负载定义','',
'680个唯一端点全部绑定实际ODB单元或冻结ITerm目录，所有端点模型可解析。646条记录的驱动分布：`'+json.dumps(s['driver_masters'])+'`。C/U按交接的4_cts.odb读取实际BUF；G按实际C最终ODB的block_v2_g宏，S按实际F最终ODB的local_s_base宏。Liberty原始单位逐文件识别并统一为fF；不是假设输出电阻，也不是统一给所有线设置一个上限。',
'',
'G/S接收端原有父层驱动被逐网保留在existing_sink_driver_terms字段。接入新连线需要明确切断原驱动；本轮负载统计不将测试网表切断当作实际版图改动。源侧原有本地输入引脚负载计入known_total_fF，原有块内布线寄生未计入。',
'','## 场模型、R估计与200/300MHz范围','',
'场景使用真实A映射后及B最终route.json的全部上层导体，线宽2μm、介电常数3.9、M10/M11/M12及via高度沿用前轮#199/#215研究模型。每条非P网解一行Maxwell电容；非目标网静止。保留各行全部耦合系数做数值检查，不将有噪声的小互容截断后偷偷重分配。原始节点bins只归档，不用于制作分布SPEF。',
'',
'CSV中的series_R_estimate_ohm为中心线长度×0.03Ω/□÷2μm，加每个via 0.08Ω；这些参数沿用#215 coupon.py的研究参数。它是线段电阻之和的几何估计，不是本轮OpenRCX提取或多分支等效电阻，不包含块内连接与接触。不得将它与总C简单相乘当作已验收路径延迟。',
'',
'本轮完整覆盖的是所有非P真实连线的静态负载/端点统计，完整下层金属、块内RC去重、动态串扰、电感及跨块STA仍未执行。C/U实际基底的回执为“mapped placed CTS; native detailed routing not accepted”，此前已取消的后端未恢复。因此200/300MHz setup/hold/slew均未验收；降频不消除已发现的库电容超限。',
'','## 计算、检查与复现','',
'远程目录 `/public/home/yuzelu/project-circuit/issue287-route-ab-all-20261117`。Slurm119532在c96/node13分配64核，8个任务各8线程，646条逐一完成。每条min_walks=262144、最多4194304 walks，沿用已记录SHA的field_row二进制和前轮冻结场景；原始输出逐网gzip归档并记录未压缩SHA。119540导出实际C G宏原生网络。bind_all.py首次遇到SRAM库pF单位时停止，随后修正为逐库单位转换，未绕过检查。',
'',
'`full_field.py`生成全量索引并完成所有场行；`bind_all.py`绑定实际单元/库和宏原有网络；`summarize_all.py`生成逐网表和对照；`validate_all.py`验证覆盖、行守恒、误差和非P互易性。`build_table.py`只生成离线全量表，不替代计算。复现需复制到新的任务目录并修改绝对根路径，不覆盖当前证据。',
'',
'覆盖与质量：`'+json.dumps(s['quality'])+'`。非P强互容对（任一方向≥5fF）共%d对，双向差超过3σ的%d对，最大标准化差%.3f。随机检查不能替代整个包含P的矩阵资格或分布RC验收；详细异常保留validation-all.json，不隐去。'%(q['reciprocity_nonP_pairs_over_5fF'],q['reciprocity_over_3sigma'],q['reciprocity_max_z']),
'',
'规则rayggxia-project-collab 1.0.0；管理结构检查另行记录。PR待审查、不自行合并；登记PR5 pending、缺board配置，Projects unverified/同步pending。完整联合时序仍需确定合格基底、重绑定引脚/切断点、补齐RC后继续。']
(p/'FULL-REPORT.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
print('646-row full report written')
