"""Run maximum-width identity boundaries as a separate immutable campaign."""
from pathlib import Path
import argparse,shlex
H=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 text=(H/'run.sh').read_text();old='repo=$(cd "$(dirname "$0")/../.." && pwd)';assert old in text
 text=text.replace(old,'repo='+shlex.quote(str(H.parents[1])))
 text=text.replace('suites=(matrix legacy)','suites=(matrix)')
 text=text.replace('name=$(basename "$case")','name=$(basename "$case")\n    [[ $name == max_identity ]] || continue')
 (a.out/'identity-run.sh').write_text(text)
 print('PASS prepared maximum-identity boundary replay')
if __name__=='__main__':main()
