from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-watch660.py').read_text(encoding='utf-8').replace('control162-watch660','control162-watch662').replace('known={};prior=None','known={};prior=None;failure_floor=None')
s=s.replace("  if any(r['failures']or r['receipts']for r in d['rows']):", "  failures={r['root']:sum(r['failures'].values())for r in d['rows']};new_failure=failure_floor is not None and any(n>failure_floor.get(root,0)for root,n in failures.items());failure_floor=failures\n  if new_failure or any(r['receipts']for r in d['rows']):")
(h/'control162-watch662.py').write_bytes(s.encode())
