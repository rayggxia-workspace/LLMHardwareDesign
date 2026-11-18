from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-main-clock4-physical-v1'
s=(r/'audit/C-final-v1/antenna-map.sbatch').read_text();i=s.index('export C_ANT_RUN=');s=s[:i]+'''python3 "$r/bind-c-antenna-report.py" "$r/audit/C-main-clock4-physical-v1/focused"
set -- "$r/cu/runs/C-v20-native-clock4" "$r/audit/C-main-clock4-physical-v1/focused/antenna.lyrdb" "$r/audit/C-main-clock4-physical-v1/focused/antenna-binding.json"
'''+s[i:];(p/'map-after.sbatch').write_text(s)
