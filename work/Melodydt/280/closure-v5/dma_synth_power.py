"""Read-DMA power from accepted mapped synthesis and real boundary activity.

No placement/route dependency, wire parasitics, or gate-functional claim.
Four mapped variants remain separate; phase includes the shared fabric.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

PLATFORM = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
LIB = PLATFORM/'lib/NangateOpenCellLibrary_typical.lib'
SPECS = {
 'shared': ('physical/physical-38769386','mc_dma_fabric_typed_p','7d7e2016414e8fab542a834be8ef20dde1efc9be95239110a82eb51e0dd03ff5'),
 'shared-noshare': ('read-shared-noshare/physical-38795299','mc_dma_fabric_typed_p','4892fea9e23167c4b0a8b6b1a90ae9d0e00333055758a702684a5813db5d54c1'),
 'phase': ('phase/physical-38769388','c639_dma_phase_ports','dc102ca53c4239fb2607fd6b5c78d8ce28c256739e7863a691cd7083bd7e769e'),
 'phase-noshare': ('read-phase-noshare/physical-38795300','c639_dma_phase_ports','0b058abb9b61e33b03b8e941d8a53283234151dff637c6d3e53980e24a400eb2'),
}

def digest(p):
 h=sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()

def save(p,data):p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')

def ports(path,top):
 result={};modules=[]
 with path.open() as f:
  for line in f:
   m=re.match(r'^module\s+(\S+)\s*\(',line)
   if m:modules.append(m[1])
   m=re.match(r'^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*;',line)
   if m:
    if m[4] in result:raise ValueError('duplicate port')
    result[m[4]]={'width':abs(int(m[2])-int(m[3]))+1 if m[2] else 1,'direction':m[1]}
 if modules!=[top] or not result:raise ValueError('expected one flat mapped top')
 return result

def prepare_wave(source,dest,expected):
 """Normalize all bus declarations and retime 100 to 300 MHz, preserving order."""
 names={};clock=None;start=end=None;edges=[];values={};pending={};counts={};last_clock=None
 def settle(t):
  nonlocal last_clock
  before=values.get(clock);after=pending.get(clock,before)
  if before!=after and before in ('0','1'):
   if last_clock is not None and t-last_clock!=5000:raise ValueError('source clock gap')
   last_clock=t;edges.append(t)
  if before=='0' and after=='1':
   for prefix in ('c','d'):
    for kind in ('req','rsp'):
     valid=prefix+'_'+kind+'_valid';ready=prefix+'_'+kind+'_ready'
     if valid in names and ready in names:
      a=values.get(names[valid][0]);b=values.get(names[ready][0])
      if a is not None and b is not None:
       n=bin(int(a,2)&int(b,2)).count('1');counts[valid]=counts.get(valid,0)+n
  values.update(pending);pending.clear()
 with source.open() as src,dest.open('w') as out:
  for line in src:
   fields=line.split()
   if fields[:1]==['$var']:
    name=fields[4];width=int(fields[2]);names[name]=(fields[3],width)
    if name=='clk':clock=fields[3]
    suffix=' [%d:0]'%(width-1) if width>1 else ''
    line='$var wire %d %s %s%s $end\n'%(width,fields[3],name,suffix)
   out.write(line)
   if fields[:1]==['$enddefinitions']:break
  if {n:v[1] for n,v in names.items()}!={n:v['width'] for n,v in expected.items()}:raise ValueError('boundary port mismatch')
  if not clock:raise ValueError('no clock')
  for line in src:
   if line.startswith('#'):
    if end is not None:settle(end)
    end=int(line[1:]);start=end if start is None else start
    out.write('#%d\n'%((end-start+1)//3))
   else:
    if line[:1] in ('0','1','x','z'):pending[line[1:].strip()]=line[0]
    elif line.startswith('b'):
     val,ident=line.split();pending[ident]=val[1:]
    out.write(line)
  if end is not None:settle(end)
 if start!=0 or end!=81920000 or len(edges) not in (16383,16384):raise ValueError('unexpected window/clock')
 return {'source_start_ps':start,'source_end_ps':end,'window_ps':(end-start+1)//3,
         'clock_mhz':300,'source_clock_mhz':100,'clock_edges':len(edges),'pre_edge_handshakes':counts,
         'boundary_bits':sum(v['width'] for v in expected.values()),'boundary_ports':len(expected)}

def main():
 root,bundle,out=map(Path,sys.argv[1:4]);variant=sys.argv[4];out.mkdir()
 rel,top,expected_sha=SPECS[variant];physical=root/rel;key=Path('nangate45')/top/'base'
 net=physical/'flow/results'/key/'1_2_yosys.v';net_sha=digest(net)
 if net_sha!=expected_sha:raise ValueError('mapped netlist changed')
 check=physical/'flow/reports'/key/'synth_check.txt'
 if 'Found and reported 0 problems.' not in check.read_text():raise ValueError('synthesis check not clean')
 synth_log=physical/'flow/logs'/key/'1_synth.log'
 if 'link_design '+top not in synth_log.read_text():raise ValueError('no prior successful link')
 sdc=physical/'flow/results'/key/'1_2_yosys.sdc'
 if not re.search(r'create_clock .*?-period 3\.333',sdc.read_text()):raise ValueError('wrong clock constraints')
 boundary=ports(net,top);stage=root/'read-port-preflight/stage-38793408'
 accepted=json.loads((stage/'result.json').read_text())['designs'][top]
 def one(source):
  name=source.parent.name;p=out/name;p.mkdir()
  if digest(source)!=accepted[name]['ports_vcd_sha256']:raise ValueError('accepted activity changed')
  wave=p/'ports-300.vcd';timing=prepare_wave(source,wave,boundary)
  tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
   'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
   'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
   'read_verilog {'+str(net)+'}','link_design '+top,'read_sdc {'+str(sdc)+'}',
   'read_vcd -scope dut {'+str(wave)+'}','report_activity_annotation','report_power -digits 9',
   'puts DMA_SYNTH_POWER_COMPLETE'])+'\n'
  assert 'read_spef' not in tcl and 'estimate_parasitics' not in tcl
  (p/'power.tcl').write_text(tcl)
  with (p/'power.log').open('w') as f:subprocess.run(['openroad','-no_init','-threads','6','-exit',str(p/'power.tcl')],stdout=f,stderr=subprocess.STDOUT,check=True)
  text=(p/'power.log').read_text();a=re.findall(r'Annotated (\d+) pin activities\.',text)
  totals=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',text)
  if len(a)!=1 or len(totals)!=1 or int(a[0])<timing['boundary_bits'] or 'DMA_SYNTH_POWER_COMPLETE' not in text or re.search(r'(?m)^(Error:|\[ERROR)',text) or 'problem parsing bus' in text:raise ValueError('power/annotation failed '+name)
  power=dict(zip(('internal','switching','leakage','total'),map(float,totals[0])))
  if min(power.values())<0 or abs(sum(power[k] for k in ('internal','switching','leakage'))-power['total'])>1e-7:raise ValueError('power sum invalid')
  receipt={'timing':timing,'power_w':power,'energy_nj':power['total']*timing['window_ps']/1000,
   'annotated':int(a[0]),'wave_sha256':digest(wave),'source_vcd_sha256':digest(source),'power_log_sha256':digest(p/'power.log')}
  save(p/'receipt.json',receipt);print('DMA_SYNTH_WINDOW_PASS',variant,name,flush=True);return name,receipt
 samples=sorted((stage/top).glob('*/ports.vcd'))
 if len(samples)!=6:raise ValueError('expected six matched activity samples')
 with ThreadPoolExecutor(max_workers=2) as pool:windows=dict(pool.map(one,samples))
 save(out/'calibration.json',{'variant':variant,'top':top,'windows':windows,'clock_mhz':300,
  'wire_parasitics_loaded':False,'activity':'real C639 RTL boundary activity propagated through mapped standard cells; not internal gate replay',
  'timing_signoff':False,'deduplication':'phase wrapper contains shared fabric; never add both totals',
  'input_sha256':{str(p):digest(p) for p in [net,sdc,check,LIB,stage/'result.json',Path(__file__),bundle/'source-commit.txt']},
  'integration_status':'characterization only; require observed active/idle counts and model instance/residency binding before integration'})
 print('DMA_SYNTH_CALIBRATION_PASS',variant,flush=True)

if __name__=='__main__':main()
