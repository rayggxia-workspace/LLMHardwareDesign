"""Inspect each immutable final native PG interface in a fresh OpenROAD process.

An inspection pass is not a complete-system PG acceptance gate.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--leaf',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False);row=json.loads(a.manifest.read_text())['leaves'][a.leaf]
    odb=Path(row['final_files']['6_final.odb']['path']);assert sha(odb)==row['final_files']['6_final.odb']['sha256']
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset f [open {'+str(a.out/'pg.tsv')+'} w]\n'
    script+='foreach n [$block getNets] {if {[$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"} {\n'
    script+=' puts $f "NET\t[$n getName]\t[$n getSigType]"\nforeach s [$n getSWires] {foreach b [$s getWires] {if {![$b isVia]} {puts $f "RECT\t[$n getName]\t[[$b getTechLayer] getName]\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]"}}}\n'
    script+=' foreach b [$n getBTerms] {foreach pin [$b getBPins] {foreach box [$pin getBoxes] {puts $f "PIN\t[$n getName]\t[$b getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}}}\n}}\nclose $f\n'
    (a.out/'inspect.tcl').write_text(script)
    with (a.out/'openroad.log').open('w') as log:q=subprocess.run(['openroad','-no_init','-exit',a.out/'inspect.tcl'],stdout=log,stderr=subprocess.STDOUT)
    assert q.returncode==0
    nets={};pins=[]
    for line in (a.out/'pg.tsv').read_text().splitlines():
        fields=line.split('\t')
        if fields[0]=='NET':nets[fields[1]]=dict(type=fields[2],layers={})
        elif fields[0]=='RECT':
            layers=nets[fields[1]]['layers'];layers[fields[2]]=layers.get(fields[2],0)+1
        elif fields[0]=='PIN':pins.append(fields[1:])
        else:raise AssertionError(fields)
    assert {n['type'] for n in nets.values()}=={'POWER','GROUND'}
    result=dict(passed=True,leaf=a.leaf,job=os.environ['SLURM_JOB_ID'],inputs={str(a.manifest):sha(a.manifest),str(odb):sha(odb),str(Path(__file__)):sha(Path(__file__))},
                native_pg=nets,pg_pins=pins,all_rails_have_m10_rectangles=all(n['layers'].get('metal10',0)>0 for n in nets.values()),
                system_pg_qualified=False,scope='Immutable native PG interface inspection only; all cross-block PG access remains a required physical gate.')
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
