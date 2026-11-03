from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-audit593.py').read_text(encoding='utf-8').replace('r256-zero-pattern-active-pool-audit-593','r256-pattern-weight-active-pool-audit-622')
s=s.replace("assert all((root/'5890/route'/('trial-'+str(i))/'input.txt').exists()for i in range(16))", "assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [6140,6141]for i in range(16))")
s=s.replace('for seed in [5890]:','for seed in [6140,6141]:').replace("root/'5640/route'","root/'5890/route'")
s=s.replace("assert a.read_bytes()==p.read_bytes();r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),identical_sha256=sha(a)))", "header,body=a.read_text().split('\\n',1);fields=header.split();assert fields[5]=='256';fields[5]=str(64 if seed==6140 else128);assert p.read_text()==' '.join(fields)+'\\n'+body;r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),baseline_sha256=sha(a),candidate_sha256=sha(p),sole_input_difference='initial_heuristic_weight'))")
s=s.replace("[(96297,7,'dynamic-07/node7',[5890])]", "[(95391,4,'dynamic-05/node4',[6140]),(95204,25,'dynamic-04/node25',[6141])]")
s=s.replace("assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd)", "assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd);assert len(row['cpu_affinity'])==16")
start=s.index("scope='16 actual");end=s.index("')\nexcept",start)
s=s[:start]+"scope='Actual6140/6141 on own node4/node25 each16 independent router children, actual CPU masks/CLI and actual memory admissions checked.32 real trial inputs differ5890 only header initial weight256to64or128. Same frozen router source, finite constraints, zero-pattern/bidirectional/RNG/placement/current graph and every final physical gate. Actual nine-case614 preflight passed before routes. Execution/comparison evidence only, no convergence/speed/final acceptance claim."+s[end:]
s=s.replace('else128','else 128').replace('active-pool-audit-622','active-pool-audit-623')
s=s.replace('print(subprocess.check_output',"compile(q,'actual-remote-audit','exec')\nprint(subprocess.check_output")
(h/'control162-audit623.py').write_bytes(s.encode())
