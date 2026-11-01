from pathlib import Path
import json,csv
from final_report import table,csvwrite
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended'
def arch(r):return'A0'if r['architecture']==0 else'B'+str(r['capacity'])if r['architecture']==1 else'C-M'if r['architecture']==2 else'C-E'
def main():
 raw=json.loads((E/'attempt053/results/RESULTS.json').read_text());rows=[]
 for r in sorted(raw,key=lambda r:(r['workload'],r['architecture'],r['capacity'],r.get('latency',0),r.get('bandwidth',0),r['policy'])):
  rows.append(dict(candidate=arch(r),workload=r['workload'],status=r['status'],latency=r.get('latency',''),bandwidth=r.get('bandwidth',''),policy=r['policy'],cycles=r.get('cycles',''),S_conflicts=r.get('S_conflicts',''),S_port_wait=r.get('stages',{}).get('S_port_wait',0),competing_wide_cycles=r.get('stages',{}).get('S_background_wide',0)))
 csvwrite('BANDWIDTH_SENSITIVITY.csv',rows)
 selected=[]
 for w in ['W1-m0-l24-t16.bin','W2-m0-n8192-t1.bin']:
  for a in ['A0','B256','B1024','B2048','C-E']:
   rs=[r for r in rows if r['workload']==w and r['candidate']==a and r['latency']==40 and r['policy']=='cache']
   selected.append([w.removesuffix('.bin'),a]+[next((r['cycles']for r in rs if r['bandwidth']==b),'不支持')for b in [1,4,16,64]])
 shared=[]
 for a in ['A0','B1024','B2048','C-E']:
  rs=[r for r in rows if r['workload']=='W1-m0-l24-t16.bin'and r['candidate']==a and r['latency']==40 and r['bandwidth']==16]
  clean=next(r for r in rs if r['policy']=='cache');s=next(r for r in rs if r['policy']=='cache_shared');shared.append([a,clean['cycles'],s['cycles'],s['S_conflicts'],f"{100*(s['cycles']/clean['cycles']-1):.2f}%"])
 major=[];ports=[]
 for n in [15,38]:
  rr=json.loads((E/f'attempt{n:03d}/results/RESULTS.json').read_text())
  for r in rr:
   if r['status']!='PASS':continue
   a=arch(r)
   if r['policy']=='cache'and r['workload']=='W1-m0-l24-t128.bin'and a in ['B1024','C-M','C-E']:
    for k,v in sorted(r['stages'].items(),key=lambda x:-x[1])[:8]:major.append([a,k,v,f'{v/r["cycles"]*100:.2f}%'])
   for k,v in r['ports'].items():ports.append(dict(attempt=n,candidate=a,workload=r['workload'],policy=r['policy'],port=k,payload_bytes=v,average_payload_bytes_per_simcycle=v/r['cycles'],scope='native interface payload or modeled command container; metadata/ready/valid not complete packet-network wire traffic'))
 csvwrite('PORT_PAYLOAD_RESULTS.csv',ports)
 report='''# 带宽、延迟、S争用和利用率敏感性

新增attempt053：336个实际联合仿真配置，324PASS，12原R超容量不支持。固定同一批整数输入/期望状态及实际可执行文件SHA；外存带宽1/4/16/64B每模拟cycle（latency40），独立latency0/40/100（带宽16），每点cache与cache_shared。不是把不同latency和带宽的变化混为一个因素。

'''+table(['任务','候选','BW1周期','BW4周期','BW16周期','BW64周期'],selected)+'''
外部BW从16增到64后完全没有收益：模型的片内DMA staging/窄S口均128bit，每次搬运最多16B，并且单个DMA服务串行。额外DRAM带宽没有变成额外S端口。不能把这个平台直接称为DRAM带宽饱和；瓶颈已转到128bit片内端口、S服务/握手和计算，需按真实系统重新决定是否并行DMA/扩大内链路。

'''+table(['W1-l24-t16','独占S周期','竞争宽口周期','实际仲裁冲突','周期增加'],shared)+'''
cache_shared为每次窄S访问之前明确发起一个真实受模型仲裁的64B宽请求，而不是声称真实模型一定存在这种精确竞争强度。S对照RTL校准已经验证该优先级/背压规则。

'''+table(['W1-l24-t128','阶段','周期','占任务周期'],major)+'''
B1024：R功能乘法slot利用率15.18%；S访问约33.59%、DRAM数据16.78%、外存等待15.39%、R执行15.57%。这解释了缩小单次计算时延不能等比例降低整任务时延。C-E：E_wide约91.84%，八路物理乘法slot利用率7.03%，实际执行的数位积全部有效，但归并/握手占去许多周期。C-M：64物理slot利用率约3.01%，其中仅12.5%乘积被使用，不能用“八路结果都算对”掩盖阵列浪费。

PORT_PAYLOAD_RESULTS.csv保留每个原生数据端口/模型命令容器的payload字节和平均占用；原JSON有每阶段周期和每类状态/中间值/系数DDR字节。有效/就绪、地址/op/epoch等sideband不包含在payload字节里，不能将其称为完整packet网络on-wire流量。完整多源packet化网络、统一header、集成DMA控制器及所有线路的物理成本尚未测；不假造额外空闲端口、FIFO容量或最终功耗。当前串行调度下一个DMA staging packet、最多一个未完成写；通用多流FIFO峰值与仲裁冲突不能从这个串行模型推广。

所有周期为递推工作负载边界内的实际联合模型周期，缺少完整集成RTL/统一真实时钟时，不把这些数转换成最终芯片ns或tokens/s。
'''
 (D/'BANDWIDTH_SENSITIVITY.md').write_text(report,encoding='utf-8')
if __name__=='__main__':main()
