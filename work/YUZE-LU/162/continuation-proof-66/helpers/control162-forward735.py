from pathlib import Path
p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control/project/experiments/control_v1/system_upper.py');s=p.read_text(encoding='utf-8');a='trace_routing_phases=a.route_trace_phases)';assert a in s;s=s.replace(a,'trace_routing_phases=a.route_trace_phases,weighted_pair_margin=a.route_weighted_pair_margin)',1);p.write_bytes(s.encode())
