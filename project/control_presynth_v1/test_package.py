"""Reject broken frozen handoffs, including internally rehashed bad profiles."""
from pathlib import Path
import argparse, json, shutil, tempfile
import package as pkg

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);pkg.audit(a.package)
    rejected=[]
    for case in ('source_changed','missing_source','control_list_changed','behavioral_bank_in_control','inferred_PM','false_path'):
        with tempfile.TemporaryDirectory(prefix='freeze-audit-',dir=a.out.parent) as temp:
            root=Path(temp)/'package';shutil.copytree(a.package,root)
            m=json.loads((root/'profile.json').read_text())
            if case=='source_changed':
                f=root/m['control_sources'][0];f.write_bytes(f.read_bytes()+b'\n// changed\n')
            elif case=='missing_source':
                (root/m['control_sources'][0]).unlink()
            elif case=='control_list_changed':
                with (root/'control.f').open('a') as f:f.write('"tb_not_delivered.sv"\n')
            elif case=='behavioral_bank_in_control':
                m['control_sources'].append('models/bank.behavioral.v');pkg.dump(root/'profile.json',m)
                (root/'control.f').write_text('\n'.join(json.dumps(x) for x in m['control_sources'])+'\n')
            elif case=='inferred_PM':
                m['parameters']['PM_USE_SRAM']=0;pkg.dump(root/'profile.json',m)
            elif case=='false_path':
                with (root/'constraints.sdc').open('a') as f:f.write('set_false_path -from [get_ports rst_ni]\n')
            if case in ('behavioral_bank_in_control','inferred_PM','false_path'):
                manifest=json.loads((root/'manifest.json').read_text())
                manifest['files']={x:pkg.sha(root/x) for x in manifest['files']}
                pkg.dump(root/'manifest.json',manifest)
            try:pkg.audit(root)
            except (AssertionError,FileNotFoundError,ValueError):rejected.append(case)
            else:raise AssertionError('accepted bad package '+case)
    pkg.dump(a.out,dict(passed=6,total=6,rejected=rejected,scope='Package integrity and semantic boundary guards, not RTL functional tests.'))
    print('PASS package guards 6/6')

if __name__=='__main__':main()
