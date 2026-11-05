from pathlib import Path
import sys,json,hashlib
h=Path(__file__).parent;repo=h/'LLMHardwareDesign-worktrees/issue-162-control';sys.path.insert(0,str(repo/'project/experiments/control_v1'))
from tree_router_cpp import route
from pin_release_regression import parse
root=h/'control162-wrapper970';root.mkdir();original=h/'control162-release-fixture946/input-971.txt';prefix=h/'control162-release-fixture946/before-971.txt.native-prefix-paths.txt';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();manifest=root/'seed.json';manifest.write_text(json.dumps(dict(prefix=str(prefix),prefix_sha256=sha(prefix),input=str(original),input_sha256=sha(original))))
_,tm,lm=parse(original.read_text());out=root/'route';out.mkdir()
_,proof=route(tm,24,24,977,80,out,heuristic_weight=256,locked_names=list(tm)[:8],wire_limits=lm,negotiated_priority=True,defer_access_vias=True,congestion_scale=1,bidirectional_two_terminal=True,weighted_bidirectional=True,ordinary_zero_pattern=True,pareto_wire_budget=True,critical_first=True,native_prefix_first=True,native_prefix_flexible=True,native_prefix_input=manifest)
(root/'receipt.json').write_text(json.dumps(proof,indent=2));print(json.dumps(dict(zero=proof['final_conflicts'],changed=proof['native_prefix_proof']['final_native_paths_changed'])))
