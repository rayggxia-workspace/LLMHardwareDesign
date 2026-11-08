"""Use actual ODB master abstracts, rather than stale accompanying LEFs."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from native_inventory import sha


def extract(configs,out):
    out.mkdir()
    for template,config in sorted(configs.items()):
        native=config['odb'];assert sha(native['path'])==native['sha256']
        raw=out/(template+'-actual-all.lef');tcl=out/(template+'-export.tcl')
        tcl.write_text('read_db {'+native['path']+'}\nwrite_lef {'+str(raw)+'}\n')
        with (out/(template+'-export.log')).open('xb') as log:
            subprocess.run(['openroad','-no_init','-threads','10','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True)
        exported=sorted(out.glob(raw.stem+'*.lef'))
        text='\n'.join(p.read_text() for p in exported)
        macros=re.findall(r'(?ms)^MACRO\s+(\S+).*?^END\s+\1\s*$',text)
        bodies=re.findall(r'(?ms)^(MACRO\s+(\S+).*?^END\s+\2\s*)$',text)
        sites=re.findall(r'(?ms)^(SITE\s+(\S+).*?^END\s+\2\s*)$',text)
        assert macros and len(bodies)==len(macros),'actual ODB LEF export lacks masters'
        lef=out/(template+'-actual-masters.lef')
        unique={}
        for body,name in sites+bodies:
            assert unique.setdefault(name,body.strip())==body.strip(),('conflicting actual ODB LEF definitions',name)
        lef.write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'+
                       '\n'.join(unique.values())+'\nEND LIBRARY\n')
        updated={**config,'lefs':[{'path':str(lef),'sha256':sha(lef)}],
                 'physical_view_source':{'odb':native,'exported_lefs':[{'path':str(p),'sha256':sha(p)} for p in exported],
                    'master_count':len(macros),'method':'OpenROAD write_lef of actual source ODB; master/site sections only'}}
        (out/(template+'-config.json')).write_text(json.dumps(updated,indent=2)+'\n')
        print('ACTUAL_ODB_MASTERS',template,len(macros),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('configs',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();extract(json.loads(a.configs.read_text()),a.output)
