from pathlib import Path
p=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control/project/experiments/control_v1/tree_router.cpp');s=p.read_text(encoding='utf-8');a='<<weighted_checks<<"}"<<endl;return 0;';z=r'<<weighted_checks<<",\"independent_weighted_heap_order_checks\":"<<heap_checks<<"}"<<endl;return 0;';assert a in s;s=s.replace(a,z,1);p.write_bytes(s.encode())
