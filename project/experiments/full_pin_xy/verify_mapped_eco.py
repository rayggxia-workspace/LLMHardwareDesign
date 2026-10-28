"""Whole mapped terminal-graph identity modulo proven Liberty sizing contracts.

Relative digital proof under identical unchanged hard-memory contracts; this is
not RTL equivalence, analog equivalence, timing or full physical qualification.
"""
from pathlib import Path
import csv,datetime,gzip,json,os,subprocess,sys
from run_exports import ROOT,CFG,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from cell_semantics import check_pair

DRIVER=Path(__file__).resolve().parent


def load(path):
    masters={};terms={};ports={}
    with gzip.open(path,'rt') as f:
        for row in csv.DictReader(f,delimiter='\t'):
            if row['kind']=='CELL':masters[row['instance']]=(row['pin'],row['direction'])
            elif row['kind']=='PORT':
                assert row['pin'] not in ports;ports[row['pin']]=(row['direction'],row['net'])
            else:
                key=(row['instance'],row['pin']);assert key not in terms
                terms[key]=(row['direction'],row['net'])
    return masters,terms,ports


def run(case,revision):
    assert case in ['gemm','mxu']
    view=ROOT/'eco_views/r02'/(case+'-C');proof=json.loads((view/'execution.json').read_text())
    reference=Path(CFG['physical_blocks'][case]['odb']);current=view/'clean.odb'
    assert sha(reference)==CFG['physical_blocks'][case]['expected_sha256']
    assert sha(current)==proof['source_geometry_sha256'] and proof['native_export_returncode']==0
    out=ROOT/'mapped_equivalence'/revision/case;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    inputs={str(p):sha(p) for p in [reference,current,view/'execution.json']};codes=[]
    for label,source in [('reference',reference),('costed_C',current)]:
        target=out/(label+'.tsv');script=out/(label+'.tcl')
        script.write_text('\n'.join(['read_db '+tcl(source),
          'set b [ord::get_db_block];set f [open '+tcl(target)+' w];puts $f "kind\\tinstance\\tpin\\tdirection\\tnet"',
          'foreach i [$b getInsts] {set m [$i getMaster];if {[$m getType] eq "CORE_SPACER"} {continue};puts $f [join [list CELL [$i getName] [$m getName] [$m getType] {}] "\\t"];foreach t [$i getITerms] {if {[$t getSigType] in {POWER GROUND}} {continue};set n [$t getNet];puts $f [join [list ITERM [$i getName] [[$t getMTerm] getName] [$t getIoType] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]] "\\t"]}}',
          'foreach p [$b getBTerms] {if {[$p getSigType] in {POWER GROUND}} {continue};set n [$p getNet];puts $f [join [list PORT {} [$p getName] [$p getIoType] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]] "\\t"]};close $f'])+'\n')
        rc=execute(common,script,out/(label+'.log'),threads=1);codes.append(rc)
        if rc:break
        with target.open('rb') as f,(out/(label+'.tsv.gz')).open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as z:
            for chunk in iter(lambda:f.read(1024*1024),b''):z.write(chunk)
    result={'scope':'WHOLE_MAPPED_DIGITAL_TERMINAL_GRAPH_AND_LIBERTY_LOGIC_STATE_RELATIVE_PROOF',
      'RTL_equivalence':'NOT_EXECUTED','unchanged_memory_semantics':'IDENTICAL_BLACKBOX_INSTANCE_AND_ALL_TERMINALS_CONTRACT_ASSUMED',
      'analog_timing_electrical_equivalence':'NOT_CLAIMED','full_qualification':False,'native_export_codes':codes,
      'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID']}
    passed=False
    if codes==[0,0]:
        a,at,ap=load(out/'reference.tsv.gz');b,bt,bp=load(out/'costed_C.tsv.gz')
        changed=[(n,a[n][0],b[n][0]) for n in sorted(set(a)&set(b)) if a[n]!=b[n]]
        result.update({'reference_nonfiller_cells':len(a),'current_nonfiller_cells':len(b),
          'reference_signal_terminals':len(at),'current_signal_terminals':len(bt),
          'same_all_top_ports_directions_and_networks':ap==bp,'same_nonfiller_instance_set':set(a)==set(b),
          'same_all_signal_clock_reset_constant_terminals_and_networks':at==bt,'changed_masters':changed,
          'changed_terminal_examples':[(list(k),at.get(k),bt.get(k)) for k in set(at)|set(bt) if at.get(k)!=bt.get(k)][:30]})
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        text=subprocess.check_output(common+[IMAGE,'cat',lib]).decode()
        contracts=[];logic_ok=True
        for n,old,new in changed:
            try:contracts.append(check_pair([Path(lib)],old,new,lambda p:text))
            except AssertionError as error:
                logic_ok=False;contracts.append({'instance':n,'old':old,'new':new,'actual_failure':str(error)})
        (out/'changed_master_logic_contracts.json').write_text(json.dumps(contracts,indent=2)+'\n')
        result['changed_masters_exact_Liberty_logic_state_contract']=logic_ok
        expected=3 if case=='gemm' else 1
        passed=logic_ok and ap==bp and set(a)==set(b) and at==bt and len(changed)==expected and all(a[n][1]==b[n][1] for n in a)
    result['all_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    result['relative_mapped_digital_contract_pass']=passed and result['all_sources_unchanged']
    result['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(result,indent=2)+'\n')
    print('MAPPED_RELATIVE_CONTRACT',case,result['relative_mapped_digital_contract_pass'],'NOT_RTL_OR_FULL_QUALIFICATION',flush=True)
    return 0 if result['relative_mapped_digital_contract_pass'] else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
