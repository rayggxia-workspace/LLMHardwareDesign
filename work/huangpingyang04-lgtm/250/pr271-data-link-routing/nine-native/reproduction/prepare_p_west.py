from pathlib import Path
import csv,json,shutil,sys
root=Path(sys.argv[1]).resolve();out=root/'P-west';out.mkdir();(out/'tmp').mkdir()
for name in ('mapped.v','mapped.json'):shutil.copyfile(root/'P'/name,out/name)
plan={}
for r in csv.reader((root/'export-P/ports.tsv').open(),delimiter='\t'):
 if r[0]=='pin' and r[1] not in ('VDD','VSS'):
  b=list(map(int,r[3:]));b[0]+=432000;b[2]+=432000
  plan.setdefault(r[1],[]).append([r[2],*b])
base=root.parent/'hpy-four-compact.uwoxpDJq/compact'
routes=json.loads((base/'check/route.json').read_text())['routes']
for r in routes.values():
 for v in r['via10']:
  if not v['pin'].startswith('P2_down_reader.peer_'):continue
  name=v['pin'].replace('P2_down_reader.peer_','down_s_');x,y=v['at'];x-=6032000;y-=64000
  plan[name]=[['metal10',x-2000,y-2000,x+2000,y+2000]]
with (out/'native-pins.tcl').open('w') as f:
 f.write('set b [ord::get_db_block]\nset t [ord::get_db_tech]\n')
 for name,shapes in plan.items():
  f.write('set term [$b findBTerm {'+name+'}]\nif {$term eq "NULL"} {error {Missing '+name+'}}\n')
  f.write('foreach pin [$term getBPins] {odb::dbBPin_destroy $pin}\nset pin [odb::dbBPin_create $term]\n$pin setPlacementStatus FIRM\n')
  for layer,*box in shapes:f.write('odb::dbBox_create $pin [$t findLayer '+layer+'] '+' '.join(map(str,box))+'\n')
(out/'native-pin-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
s=(root/'P/prepare_native_place.py').read_text()
s=s.replace('die_um=[1470,2245], m_xy_um=[24,831], s_xy_um=[24,24], reserved_g_bbox_um=[928,24,1168,264]',
            'die_um=[1686,2245], m_xy_um=[240,831], s_xy_um=[240,24], reserved_g_bbox_um=[1144,24,1384,264]')
(out/'prepare_place.py').write_text(s)
(out/'run.sh').write_text('''#!/bin/bash
#SBATCH --job-name=hpy-P2-native-west
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=16
#SBATCH --time=00:15:00
set -euo pipefail
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/tmp" PYTHONDONTWRITEBYTECODE=1
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" python3 -B prepare_place.py
bash "$tool" bash -c 'cd place250; openroad -no_init -exit place.tcl > place.log 2>&1'
''')
print('P2 west collar: same 3 native leaf macros, same RTL, no new reader instance.')
