from pathlib import Path
h=Path(__file__).parent
s=(h/'control162-refill527-remote.py').read_text(encoding='utf-8')
s=s.replace('sready527-progressive-window-refill','sready590-zero-pattern-refill').replace('sready525-progressive-search-window','sready589-zero-pattern-controlled')
s=s.replace("(3,95098,'dynamic-02/node3',3731,'source-358',4)","(7,96297,'dynamic-07/node7',4050,'source-400',0)")
s=s.replace("and json.loads((b/'r256-ordinary-cost-regression-511/receipt.json').read_text())['passed']", "and json.loads((b/'r256-bidirectional-search-regression-500/receipt.json').read_text())['passed']")
s=s.replace("assert len(attempts)==16 and sum(r['failed_message']is not None for r in attempts)>=minimum_failed", "assert len(attempts)==16;assert all(Path(r['path']).stat().st_size>0 for r in attempts)")
start=s.index("reason='Replace exactly")
end=s.index("')\n (record/",start)
s=s[:start]+"reason='Reassign exactly one verified own older359 source400 fixed16attempt4050 slot to source587 independent full regression then controlled current453 S5380 candidate5890. Actual494 profiles identify2million-pop ordinary fallbacks and repeated long rounds; optional bounded zero-occupancy pattern targets that measured bottleneck, retaining original fallback and final gates. This is task-local resource prioritization, not old search failure or infeasibility. Preserve all16 raw attempts, exact sources/specs/partial physical outputs and independent CUGR3751 comparator. Only exact UID10011/node7/job96297/PID/cmd/out/oldgraph/source guarded step replaced; parent allocations/foreign/R/current453 searches untouched. Candidate5890 uses original16active finite64attempt dynamic refill with actual memory admission after real regression passes. No convergence/speed/final qualification claim."+s[end:]
(h/'control162-refill590-remote.py').write_bytes(s.encode())
