from pathlib import Path
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-r-fullguard')
s=(p/'access.tcl').read_text().replace('pin_access -bottom_routing_layer metal1 -top_routing_layer metal10','set_routing_layers -signal metal2-metal10 -clock metal4-metal10\npin_access').replace(' -min_access_points 1','').replace('r-access-ripped.tsv','r-access-v2-ripped.tsv');(p/'access-v2.tcl').write_text(s)
s=(p/'access.sbatch').read_text().replace('access.tcl > access.log','access-v2.tcl > access-v2.log');(p/'access-v2.sbatch').write_text(s)
