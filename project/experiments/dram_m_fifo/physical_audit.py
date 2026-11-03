"""Receipt for fresh-process STA; failures stay failures and remain inspectable."""
import json,math,os,re
from pathlib import Path

def verify(root,args,out,run,sha,dump):
 md=Path(args.reuse)/'output'
 p=json.loads((md/'physical.json').read_text());assert p['completed']
 m=json.loads((md/'mapping.json').read_text())
 for f,h in m['source'].items():assert sha(root/f)==h
 files=p['files']
 for f in ('6_final.odb','6_final.spef','6_final.v','6_final.def'):
  assert sha(files[f]['path'])==files[f]['sha256']
 pairs=json.loads((md/'synchronizer-pairs.json').read_text())
 groups=json.loads((md/'cdc-registers.json').read_text())
 # A report per actual synchronizer pair and every source Gray bit.
 text='set f [open synchronizers.tsv w]\n'
 def one(a,b,label,budget):
  return ('set a [get_pins {'+a+'}]\nset b [get_pins {'+b+'}]\n'
   'if {[llength $a]!=1 || [llength $b]!=1} {error "Missing synchronizer pin"}\n'
   'set p [find_timing_paths -from $a -to $b -path_delay max -group_path_count 1 -sort_by_slack]\n'
   'if {[llength $p]!=1} {error "Missing synchronizer timing path"}\n'
   'puts $f "'+label+'\t'+a+'\t'+b+'\t'+str(budget)+'\t[get_property [lindex $p 0] slack]"\n')
 for row in pairs:text+=one(row['from'],row['to'],'stage1-stage2',.30)
 for fifo in ('requests','responses'):
  for bank in ('wg','rg'):
   src=groups[fifo+'.'+bank];first=groups[fifo+'.'+bank+'1']
   for r in first:
    source=[v for v in src if v['Q']==r['D']];assert len(source)==1
    text+=one(source[0]['cell']+'/CK',r['cell']+'/D','gray-first',2.0)
 text+='close $f\n'
 regs=json.loads((md/'registers.json').read_text())
 def matching(prefixes):return[r for r in regs if any(n.startswith(p)for n in r['names']for p in prefixes)]
 def pins(rows,pin):return '[get_pins [list '+' '.join('{'+r['cell']+'/'+pin+'}'for r in rows)+']]'
 text+='set f [open links.tsv w]\n'
 links=[('return-fifo-to-loader',matching(['loader.responses.payload[']),matching(['loader.gather[','loader.a_data[','loader.b_data['])),
  ('loader-A-to-M',matching(['loader.a_data[','loader.a_valid[','loader.a_bank[','loader.a_row[','loader.a_tile[','loader.a_wide[']),matching(['m.aa['])),
  ('loader-B-to-M',matching(['loader.b_data[','loader.b_valid[','loader.b_bank[','loader.b_tile[','loader.b_half[','loader.b_wide[']),matching(['m.bb[']))]
 for label,sources,targets in links:
  assert sources and targets,label
  text+='set a '+pins(sources,'CK')+'\nset b '+pins(targets,'D')+'\n'
  text+='if {[llength $a]!='+str(len(sources))+' || [llength $b]!='+str(len(targets))+'} {error "Missing datapath register"}\n'
  for kind in ('max','min'):
   text+='set paths [find_timing_paths -from $a -to $b -path_delay '+kind+' -group_path_count 1 -sort_by_slack]\n'
   text+='if {![llength $paths]} {error "Missing actual FIFO/M datapath"}\n'
   text+='foreach p $paths {puts $f "'+label+'\t'+kind+'\t[get_property $p slack]\t[get_full_name [get_property $p startpoint]]\t[get_full_name [get_property $p endpoint]]"}\n'
   text+='report_checks -from $a -to $b -path_delay '+kind+' -group_path_count 3 -digits 9 -format full_clock_expanded > '+label+'-'+kind+'.rpt\n'
 text+='close $f\n';(out/'pairs.tcl').write_text(text)
 os.environ.update(DM_ODB=files['6_final.odb']['path'],DM_SPEF=files['6_final.spef']['path'],DM_SDC=str(md/'input.sdc'),DM_PAIRS=str(out/'pairs.tcl'))
 run(['openroad','-exit',Path(__file__).with_name('physical_audit.tcl')],'audit.log')
 raw=[line.split('\t')for line in(out/'summary.tsv').read_text().splitlines()]
 summary={r[0]:r[1:]for r in raw if r[0]!='clock'}
 clocks={r[1]:{'period_ns':float(r[2]),'propagated':r[3]in('1','true')}for r in raw if r[0]=='clock'}
 assert set(clocks)=={'core','mem'}and all(c['propagated']for c in clocks.values())
 assert abs(clocks['core']['period_ns']-10/3)<1e-5 and abs(clocks['mem']['period_ns']-2)<1e-6
 assert abs(float(summary['time_unit_seconds'][0])-1e-9)<1e-15
 assert abs(float(summary['capacitance_unit_farads'][0])-1e-15)<1e-21
 connectivity={r[0]:r for r in(line.split('\t')for line in(out/'connectivity.tsv').read_text().splitlines())}
 for row in pairs:
  a=connectivity[row['first']+'/Q'];b=connectivity[row['second']+'/D']
  assert a[1].startswith('DFF')and b[1].startswith('DFF')and a[3]==b[3]and a[3]!='OPEN',('changed synchronizer',row)
 opens=[r for r in connectivity.values()if r[3]=='OPEN'and r[2]=='INPUT']
 no_driver=[r for r in connectivity.values()if r[3]!='OPEN'and r[2]=='INPUT'and int(r[5])!=1]
 unplaced=[r for r in connectivity.values()if r[3]!='OPEN'and r[7]not in('PLACED','FIRM','LOCKED')]
 endpoints=[];unconstrained=[];waived=[]
 sdc=(md/'input.sdc').read_text()
 # Only explicit raw-reset synchronizer reset pins and actual tie-driven data
 # pins may have both timing sides infinite. Unused outputs must have no loads.
 for line in(out/'endpoints.tsv').read_text().splitlines():
  r=line.split('\t');name,mx,mn,isport,direction=r;endpoints.append(r)
  if mx not in('INF','-INF')and mn not in('INF','-INF'):continue
  c=connectivity.get(name);reason=None
  if c and c[4]and name.endswith('/D'):reason='physical tie-driven D'
  elif c and name.endswith(('/RN','/SN'))and '{'+name+'}'in sdc:reason='explicit raw reset synchronizer pin'
  elif c and c[2]=='OUTPUT'and c[3]!='OPEN'and int(c[6])==0:reason='physically loadless cell output'
  if reason:waived.append({'endpoint':r,'reason':reason})
  else:unconstrained.append(r)
 paths=[r.split('\t')for r in(out/'paths.tsv').read_text().splitlines()]
 categories={(r[0],r[1],r[2])for r in paths}
 sync=[r.split('\t')for r in(out/'synchronizers.tsv').read_text().splitlines()]
 assert len(sync)==40
 violations={k:int(summary[k][0])for k in ('setup_violations','hold_violations','capacitance','slew','fanout')}
 parsed_paths=[{'from':r[0],'to':r[1],'kind':r[2],'slack_ns':float(r[3]),'startpoint':r[4],'endpoint':r[5]}for r in paths]
 syncr=[dict(kind=r[0],source=r[1],destination=r[2],budget_ns=float(r[3]),slack_ns=float(r[4]))for r in sync]
 direct=[r.split('\t')for r in(out/'links.tsv').read_text().splitlines()]
 direct=[dict(link=r[0],kind=r[1],slack_ns=float(r[2]),source=r[3],destination=r[4])for r in direct]
 assert len({(r['link'],r['kind'])for r in direct})==6
 annotations=[r.split('\t')for r in(out/'annotation-connectivity.tsv').read_text().splitlines()]
 active_unannotated=[r for r in annotations if int(r[1])!=0]
 passed=not(opens or no_driver or unplaced or unconstrained or active_unannotated or any(violations.values()))and len(categories)==8 and all(r['slack_ns']>=0 for r in parsed_paths+syncr+direct)
 result={'passed':passed,'clocks':clocks,'violations':violations,'paths':parsed_paths,'synchronizers':syncr,
 'direct_path':direct,'endpoints':len(endpoints),'unconstrained':unconstrained,'explicit_nonfunctional_endpoints':waived,
 'connectivity':{'signal_pins':len(connectivity),'open_inputs':opens,'inputs_without_exactly_one_driver':no_driver,'unplaced':unplaced},
 'parasitics':{'loadless_unannotated':len(annotations)-len(active_unannotated),'active_unannotated':active_unannotated,'partial_unannotated':0},
 'physical_receipt_sha256':sha(md/'physical.json'),'sdc_sha256':sha(md/'input.sdc'),
 'final_files':files,'scope':'Nangate45 typical extracted-RC STA, no silicon PVT/MTBF/DDR PHY qualification'}
 dump(out/'audit.json',result)
 assert passed,('post-route audit did not pass',violations,len(unconstrained),len(opens),len(no_driver),len(unplaced))
