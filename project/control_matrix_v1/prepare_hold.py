"""Create a separate state-observation campaign; preserve the full-matrix runner."""
from pathlib import Path
import argparse,shlex
H=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--patch',type=Path);a=p.parse_args()
 if a.patch:
  text=a.patch.read_text();needle='if(deployment_ready_o)$fatal(1,"poisoned cohort still deployment-ready");continue;'
  assert text.count(needle)==1
  a.patch.write_text(text.replace(needle,'if(deployment_ready_o)$fatal(1,"poisoned cohort still deployment-ready");repeat(4)tick();continue;'))
 else:
  a.out.mkdir(parents=True,exist_ok=True);text=(H/'run.sh').read_text()
  old='repo=$(cd "$(dirname "$0")/../.." && pwd)';assert old in text
  text=text.replace(old,'repo='+shlex.quote(str(H.parents[1])))
  text=text.replace('backends=(0 1);seeds=(1:143 2:143 2:144);suites=(matrix legacy)','backends=(0 1);seeds=(1:143);suites=(matrix)')
  text=text.replace('> "$out/instrument.log"','> "$out/instrument.log"\npython3 -B "$matrix/prepare_hold.py" --patch "$out/bench/tb_matrix.sv"')
  text=text.replace('name=$(basename "$case")','name=$(basename "$case")\n    [[ $name == pm_lost* ]] || continue')
  (a.out/'hold-run.sh').write_text(text)
 print('PASS prepared explicit four-cycle POISON observation hold')
if __name__=='__main__':main()
