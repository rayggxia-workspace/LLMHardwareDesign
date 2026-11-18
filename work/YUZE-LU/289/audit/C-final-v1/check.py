from pathlib import Path
import sys,re,json,hashlib
p=Path(sys.argv[1]).resolve();run=Path(sys.argv[2]).resolve();res=next((run/'flow/results/nangate45').glob('*/*'))
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def lines(q):return [s.strip() for s in q.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
a,b=p/'expected-normalized.sdc',p/'final-normalized.sdc';assert lines(a)==lines(b),'Actual SDC differs from unchanged independent engineering contract'
assert not any(re.match(r'set_(false_path|multicycle_path|disable_timing)\b',s) for s in lines(b))
counts={a:int(b) for a,b in (s.split() for s in (p/'counts.tsv').read_text().splitlines())};assert set(counts)=={'setup','hold','capacitance','slew','fanout'} and not any(counts.values()),counts
slacks={k:float(re.search(r'worst slack (?:max|min)\s+([-+0-9.eE]+)',(p/(k+'.rpt')).read_text())[1]) for k in ('setup','hold')};assert min(slacks.values())>=0
for n in ('async.rpt','electrical.rpt'):assert 'VIOLATED' not in (p/n).read_text().upper()
pg=dict(s.split('\t') for s in (p/'pg.tsv').read_text().splitlines());assert pg=={'VDD':'1','VSS':'1'}
selected=set(Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/C-outputs.txt').read_text().splitlines());drivers=[s.split('\t') for s in (p/'drivers.tsv').read_text().splitlines()]
assert len(drivers)==153 and {s[0] for s in drivers}==selected and all(s[3]=='BUF_X8' for s in drivers)
def geometry(q):
 rows=set(q.read_text().splitlines());power={s for s in rows if s.startswith(('PIN\tVDD\t','PIN\tVSS\t'))};return rows-power,power
orig,opg=geometry(p/'original-geometry.tsv');final,fpg=geometry(p/'final-geometry.tsv');assert orig==final,'Signal/die/macro geometry differs'
# The fresh exported netlist is the final formal-proof source; retain raw saved netlist identity separately.
result=dict(passed=True,scope='Independent physical/timing/IO/driver gates only; no functional or full-GDS acceptance implied',run=str(run),period_ns=4,frequency_MHz=250,uncertainty_ns=.1,selected_load_fF=50,other_output_load_fF=2,selected_drivers=153,driver_master='BUF_X8',counts=counts,slacks_ns=slacks,async_clear=True,pg=pg,signal_die_macro_geometry_exact=True,requires_pg_boundary_review=opg!=fpg,power_bpin_removed=sorted(opg-fpg),power_bpin_added=sorted(fpg-opg),final_netlist_byte_equal_saved=sha(res/'6_final.v')==sha(p/'final-from-odb.v'),source_sha256={str(q):sha(q) for q in [a,b,res/'6_final.odb',res/'6_final.sdc',res/'6_final.spef',res/'6_final.v',p/'final-from-odb.v',p/'drivers.tsv',p/'original-geometry.tsv',p/'final-geometry.tsv']})
(p/'independent-gates.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','power_bpin_removed','power_bpin_added')},indent=2))
