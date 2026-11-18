from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-main-clock4-physical-v1';p.mkdir(exist_ok=False)
s=(r/'c-focused.sh').read_text().replace('out=$root/c-physical/focused-$(basename "$run")','out=$root/audit/C-main-clock4-physical-v1/focused')
(p/'focused.sh').write_text(s)
s=(r/'audit/u-full.sh').read_text();start=s.index('case "$run"');end=s.index('\nout=',start);s=s[:start]+'case "$run" in "$root"/cu/runs/C-v20-native-clock4) ;; *) exit 2;; esac'+s[end:];s=s.replace('out=$root/audit/full-$(basename "$run")','out=$root/audit/C-main-clock4-physical-v1/full').replace(' "$res/6_final.spef"','')
(p/'full.sh').write_text(s)
base=(r/'c-focused.sbatch').read_text();base=base.replace('yzl-289-C-diag','yzl-C-mainphysical').replace('--time=04:00:00','--time=12:00:00').replace('issue289-ab-x8-20261117/c-focused-%j.log','issue289-ab-x8-20261117/audit/C-mainphysical-%j.log').replace('bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/c-focused.sh "$1"','bash /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-main-clock4-physical-v1/"$1".sh /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4')
(p/'run.sbatch').write_text(base)
