from pathlib import Path
h=Path(__file__).parent
s=(h/'control162-audit553.py').read_text(encoding='utf-8')
s=s.replace('r256-s-local-active-pool-audit-553','r256-zero-pattern-active-pool-audit-593')
s=s.replace("out.mkdir();sha=", "assert all((root/'5890/route'/('trial-'+str(i))/'input.txt').exists()for i in range(16));out.mkdir();sha=")
s=s.replace('for seed in [5450,5451]:','for seed in [5890]:').replace("root/'5400/route'","root/'5640/route'")
s=s.replace("[(95155,5,'dynamic-03/node5',[5450,5451]),(95204,25,'dynamic-04/node25',[5400])]", "[(96297,7,'dynamic-07/node7',[5890])]")
start=s.index("    cmd=row['command'];");end=s.index('\n   queue=',start)
s=s[:start]+"    cmd=row['command'];assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-zero-pattern'in cmd;assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd)"+s[end:]
start=s.index("scope='32 actual");end=s.index("')\nexcept",start)
s=s[:start]+"scope='16 actual trial inputs byte-identical5890 vs5640.16 actual owned single-thread source587 router child commands and CPU masks read from verified node7/job96297; bounded zero-pattern flag is present and ordinary scale/window overrides absent. Actual controller aggregate memory admission readback passed. Full actual589 independent regression completed before candidate release. All original final gates remain required. Execution/comparison evidence only, no speed/convergence/route/PG/RC/300MHz/system qualification."+s[end:]
(h/'control162-audit593.py').write_bytes(s.encode())
