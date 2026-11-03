from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-audit593.py').read_text(encoding='utf-8').replace('r256-zero-pattern-active-pool-audit-593','r256-eighth-node-active-pool-audit-621')
s=s.replace("root/'5890/route'","root/'5495/route'")
start=s.index(' for seed in [5890]:');end=s.index(' for job,node,folder,seeds',start)
s=s[:start]+s[end:]
s=s.replace("[(96297,7,'dynamic-07/node7',[5890])]", "[(96222,24,'dynamic-06/node26',list(range(5490,5496)))]")
start=s.index("    cmd=row['command'];");end=s.index('\n   queue=',start)
s=s[:start]+"    cmd=row['command'];assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-search-margin=64'in cmd;assert '--ordinary-congestion-scale='+str([16,64,256][(seed-5490)%3])in cmd;assert '--ordinary-zero-pattern'not in cmd;assert len(row['cpu_affinity'])==16"+s[end:]
s=s.replace(" r.update(passed=True,scope=", " masks=[set(next(x for x in pool['actual_processes']if x['seed']==seed)['cpu_affinity'])for pool in r['pools']for seed in range(5490,5496)];assert len(set.union(*masks))==96 and sum(len(x)for x in masks)==96\n r.update(passed=True,scope=")
start=s.index("scope='16 actual");end=s.index("')\nexcept",start)
s=s[:start]+"scope='Actual eighth own job96222/node24 running96CPUs. Six independent16CPU steps5490..5495 and96 actual owned single-thread router children read from OS; six actual16CPU affinity masks disjoint and union96CPUs. Actual source537 ordinary scale16/64/256 with window64 verified in commands, plus finite8m/critical flags. Six actual cumulative memory admissions pass. Queue directory node26 is a label, actual Slurm host is node24. No parameter/control/route speed or final physical qualification implied.'".rstrip("'")+s[end:]
(h/'control162-audit621.py').write_bytes(s.encode())
