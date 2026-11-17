import pathlib,json,re
P=pathlib.Path;p=P(__file__).resolve().parent;old=P('/public/home/yuzelu/project-circuit/issue287-cu-realwire-20261117/v4')
validation=json.loads((p/'node-validation.json').read_text());assert validation['passed'] and validation['count']==646
graphs=json.loads((p/'graphs-rcx.json').read_text());caps=json.loads((p/'node-capacitances.json').read_text());out=p/'sta';out.mkdir(exist_ok=True)
head=(old/'p50.spef').read_text().split('*D_NET')[0]
spefs=p/'spef';spefs.mkdir(exist_ok=True)
for key,g in graphs.items():
 cap=caps[key];lines=[head]
 for bit in range(128):
  net='link_data[%d]'%bit
  def name(n):
   if n==g['source']:return 'C:native_tx_data_o[%d]'%bit
   if n==g['sink']:return 'U:native_rx_data_i[%d]'%bit
   return net+':'+str(n+1)
  lines+=['*D_NET %s %.15g'%(net,sum(cap)/1000),'*CONN','*I C:native_tx_data_o[%d] O'%bit,'*I U:native_rx_data_i[%d] I'%bit,'*CAP']
  lines += ['%d %s %.15g'%(i+1,name(i),v/1000) for i,v in enumerate(cap)]
  lines+=['*RES']+['%d %s %s %.15g'%(i+1,name(a),name(b),r) for i,(a,b,r) in enumerate(g['resistors'])]+['*END']
 (spefs/(key+'.spef')).write_text('\n'.join(lines)+'\n')
base=(old/'p50-200/run.tcl').read_text();prefix=base.split('create_clock')[0]
constraints=base[base.index('set_clock_uncertainty'):base.index('read_spef')]
internal='\n'.join(line for line in base.splitlines() if line.startswith('read_spef -path'))+'\n'
report=base[base.index('report_worst_slack'):].replace('puts REPLAY_COMPLETE','puts CASE_COMPLETE')
# Load the accepted hierarchy once per worker; each case re-reads all three SPEFs.
def runner(path,jobs):
 text=prefix+'\n';previous_spef=None
 for key,freq,spef in jobs:
  case=out/(key+'-'+str(freq));case.mkdir(exist_ok=True)
  text+='cd {'+str(case)+'}\ncreate_clock -name core -period %.12f [get_ports clk]\n'%(1000/freq)+constraints
  if spef!=previous_spef:text+='read_spef {'+str(spef)+'}\n'+internal
  text+=report+'\nputs {FINISHED '+key+' '+str(freq)+'}\n';previous_spef=spef
 text+='puts WORKER_COMPLETE\n';path.write_text(text)
pilot=[('control-zero-before',200,old/'ideal.spef'),('control-p50',200,old/'p50.spef'),('A-n14653',200,spefs/'A-n14653.spef'),('control-zero-after',200,old/'ideal.spef'),('A-n14653',300,spefs/'A-n14653.spef')]
runner(out/'pilot.tcl',pilot)
jobs=[(key,freq,spefs/(key+'.spef')) for key in graphs for freq in [200,300]]
for i in range(8):runner(out/('worker-%d.tcl'%i),[(key,freq,spefs/(key+'.spef')) for key in list(graphs)[i::8] for freq in [200,300]])
(p/'sta-jobs.json').write_text(json.dumps([{'net':k,'MHz':f,'spef':str(s)} for k,f,s in jobs],indent=2))
print('Prepared 646 distributed SPEFs, 1292 STA cases; pilot required before full run')
