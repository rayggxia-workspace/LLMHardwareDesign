"""Independent tiny schedules and unknown-energy handling; synthetic inputs only."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys

CASES=[
 ('serial',[('a',5,'-', 'M',2),('b',7,'a','M',3)],12,5,True),
 ('parallel',[('a',5,'-','M0',2),('b',7,'-','M1',3)],7,5,True),
 ('port_contention',[('a',5,'-','M0,S',2),('b',7,'-','M1,S',3)],12,5,True),
 ('ack_dependency',[('load',4,'-','DDR,S',2),('compute',7,'load','M,S',3),('store_ack',6,'compute','DDR,S',4)],17,9,True),
 ('unknown_energy',[('a',5,'-','M','?'),('b',7,'a','M',3)],12,3,False),
 ('fork_join',[('a',3,'-','S',1),('b',4,'a','M0',2),('c',8,'a','M1',3),('join',2,'b,c','E',4)],13,10,True)]

def run(case):
    name,rows,time,energy,complete=case
    file=Path(name+'.tsv');file.write_text(''.join('\t'.join(map(str,r))+'\n' for r in rows))
    result=subprocess.run(['./timed-resources',str(file)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    record=next(line[7:] for line in result.stdout.splitlines() if line.startswith('RESULT '))
    report=json.loads(record)
    assert report['makespan_ps']==time,(name,report)
    assert report['known_dynamic_nJ']==energy and report['energy_complete']==complete
    return {'name':name,'passed':True,'actual':report,'boundary':'synthetic scheduler/unit test; not Qwen performance or calibrated energy'}

if __name__=='__main__':
    os.environ.update(OMP_NUM_THREADS='10',OPENBLAS_NUM_THREADS='10',MKL_NUM_THREADS='10')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(run,CASES))
    Path('probe.json').write_text(json.dumps({'passed':True,'cases':rows},indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(rows),'systemc_kernel':True,'qualified_hardware_energy':False}))
