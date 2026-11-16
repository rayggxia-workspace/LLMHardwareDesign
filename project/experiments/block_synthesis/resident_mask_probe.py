"""Qualify untouched native RTL with uninitialized/nonzero inactive words.

The only changes from the row probe are testbench initialization and removal
of testbench padding writes. Functional macros, feeder and S are byte-identical.
"""
import hashlib,json
from pathlib import Path
import shutil


def prepare(origin,bank,output,formats):
    from resident_row_probe import prepare as row_prepare
    output=Path(output);m=row_prepare(origin,bank,output,formats)
    tb=output/'tb_resident_row_probe.sv';text=tb.read_text(encoding='utf-8')
    padding='for(integer j=0;j<8;j=j+1)begin access(1,abase+j,0,got);access(1,bbase+j,0,got);end'
    if text.count(padding)!=1:raise ValueError('unknown row padding initialization')
    text=text.replace(padding,'// Deliberately leave every inactive word untouched.')
    text=text.replace('if(pattern<0 || pattern>2)','if(pattern<0 || pattern>3)')
    text=text.replace('if($value$plusargs("sinit=%d",pattern))begin',
        'if($value$plusargs("sinit=%d",pattern))begin\n    $display("MASK_INIT bank=%0d pattern=%0d",bank,pattern);')
    target='dut.store.storage.banks[bank].memory.mem[wi]=seed;'
    if text.count(target)!=1:raise ValueError('unknown SRAM initial-state probe')
    text=text.replace(target,"if(pattern==3)seed='x;\n     "+target)
    tb.write_text(text,encoding='utf-8',newline='\n')
    here=Path(__file__);shutil.copyfile(here,output/here.name)
    for name in (tb.name,here.name):m['sha256'][name]=hashlib.sha256((output/name).read_bytes()).hexdigest()
    m['inactive_word_probe']={'kind':'native-M-active-prefix-v1','initializations':['zero','ones','mixed','unknown'],
        'padding_writes':False,'rows':[1,8],'k':[1,2],'columns':1,
        'contract':'A words [0,rows) and B word 0 are required; other wide-read words do not affect active results'}
    (output/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8');return m


def qualification(directory,logs):
    from resident_row_probe import analyse
    directory=Path(directory);m=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if (len(logs)!=4 or len({Path(p).resolve() for p in logs})!=4 or
        m.get('inactive_word_probe',{}).get('kind')!='native-M-active-prefix-v1' or
        m['inactive_word_probe']['padding_writes'] is not False):raise ValueError('four-state inactive-word proof required')
    reports=[analyse(directory,p) for p in logs]
    for state,log in enumerate(logs):
        actual=[line for line in Path(log).read_bytes().splitlines() if line.startswith(b'MASK_INIT ')]
        expected=[f'MASK_INIT bank={bank} pattern={state}'.encode() for bank in range(4)]
        if sorted(actual)!=expected:raise ValueError('actual SRAM initialization mode not recorded')
    if any(r['profile']!=reports[0]['profile'] for r in reports[1:]):raise ValueError('inactive SRAM words affect service timing')
    return {'kind':'native-resident-services-active-prefix-v1','profile':reports[0]['profile'],'formats':m['formats'],
        'rtl_sha256':{k:v for k,v in m['sha256'].items() if k.startswith('rtl/')},
        'proof':{'manifest_sha256':reports[0]['manifest_sha256'],'logs_sha256':[r['log_sha256'] for r in reports],
                 'cases_per_initialization':[r['cases'] for r in reports]},
        'operand_mask':m['inactive_word_probe'],
        'scope':'unchanged native P/M/feeder/S active-prefix read contract; not free layout movement or system qualification'}
