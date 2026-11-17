import pathlib,re,json
P=pathlib.Path;p=P(__file__).resolve().parent;old=P('/public/home/yuzelu/project-circuit/issue287-cu-realwire-20261117/v4')
base=(old/'p50-200/run.tcl').read_text();prefix=base.split('create_clock')[0]
constraints=base[base.index('set_clock_uncertainty'):base.index('read_spef')]
internal='\n'.join(line for line in base.splitlines() if line.startswith('read_spef -path'))+'\n'
drivers=re.findall(r'set driver \[get_pins \{([^}]+)\}\]',base);assert len(set(drivers))==128
report=base[base.index('report_worst_slack'):base.index('set f [open crossing.tsv w]')]
report+='set drivers [get_pins {'+' '.join(drivers)+'}]\nif {[llength $drivers]!=128} {error "missing replay drivers"}\n'
report+='''set f [open crossing.tsv w]
puts $f "bit\tmode\tslack\tstartpoint\tendpoint"
foreach mode {max min} {
 set paths [find_timing_paths -through $drivers -path_delay $mode -group_path_count 1 -sort_by_slack]
 if {[llength $paths]!=1} {error "missing worst crossing path"}
 set path [lindex $paths 0]
 puts $f "all\t$mode\t[get_property $path slack]\t[get_full_name [get_property $path startpoint]]\t[get_full_name [get_property $path endpoint]]"
}
close $f
report_checks -through $drivers -path_delay min_max -format full_clock_expanded -fields {slew capacitance input_pin net} -digits 9 > worst-paths.rpt
'''
def runner(file,jobs,root):
 text=prefix;previous=None
 for key,mhz,spef in jobs:
  d=root/(key+'-'+str(mhz));d.mkdir(parents=True,exist_ok=True)
  text+='cd {'+str(d)+'}\ncreate_clock -name core -period %.12f [get_ports clk]\n'%(1000/mhz)+constraints
  if spef!=previous:text+='read_spef {'+str(spef)+'}\n'+internal
  previous=spef;text+=report+'puts {FINISHED '+key+' '+str(mhz)+'}\n'
 text+='puts WORKER_COMPLETE\n';file.write_text(text)
runner(p/'fast-pilot.tcl',[('control-zero-before',200,old/'ideal.spef'),('control-p50',200,old/'p50.spef'),('A-n14653',200,p/'spef/A-n14653.spef'),('A-n14653',300,p/'spef/A-n14653.spef')],p/'fast-pilot')
if (p/'fast-pilot-validation.json').exists():
 assert json.loads((p/'fast-pilot-validation.json').read_text())['passed']
 graphs=json.loads((p/'graphs-rcx.json').read_text());finished=set()
 for log in (p/'sta').glob('worker-*.log'):finished.update((k,int(f)) for k,f in re.findall(r'^FINISHED (\S+) (\d+)$',log.read_text(),re.M))
 jobs=[(key,mhz,p/'spef'/(key+'.spef')) for key in graphs for mhz in [200,300] if (key,mhz) not in finished]
 for i in range(8):runner(p/('fast-worker-%d.tcl'%i),[j for j in jobs if list(graphs).index(j[0])%8==i],p/'sta-fast')
 (p/'fast-job-index.json').write_text(json.dumps({'reused_old_completed':sorted(finished),'new_cases':[(k,f) for k,f,_ in jobs]},indent=2));print(len(finished),'retained;',len(jobs),'remaining')
