"""Propose repeaters from a sealed native path report; never launch or accept PPA."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('inspection')
p.add_argument('attempt')
p.add_argument('--path-reserve-ns', type=float, default=.12)
p.add_argument('--wire-delay-ns', type=float, default=.09)
a = p.parse_args()
assert all(name.replace('-', '').isalnum() for name in [a.inspection, a.attempt])
assert 0 < a.path_reserve_ns <= .3 and .05 <= a.wire_delay_ns <= .3
target = HERE / (a.attempt + '.json')
assert not target.exists(), 'Preserve existing attempt specifications'
probe = r'''
from pathlib import Path
import hashlib,json,re,sys
name,reserve,wire=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
root=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15')/name
assert (root/'exit-code.txt').read_text().strip()=='0'
manifest={name[2:]:h for h,name in (line.split(None,1) for line in (root/'output.sha256').read_text().splitlines())}
def sealed(name):
 f=root/name;assert hashlib.sha256(f.read_bytes()).hexdigest()==manifest[name];return f.read_text()
assert json.loads(sealed('extracted-source-validation.json'))['passed']
plan=json.loads(sealed('extracted-eco-plan.json'))
text=sealed('extracted-setup-before.rpt');candidates=[]
for path in re.findall(r'Startpoint:.*?slack \((?:MET|VIOLATED)\)',text,re.S):
 slack=float(re.search(r'([-+0-9.eE]+)\s+slack \((?:MET|VIOLATED)\)$',path)[1])
 if slack>=reserve:continue
 endpoint=re.search(r'^Endpoint: (\S+)',path,re.M)[1]
 assert '(output port' in path.split('Path Group:')[0], 'Planner is restricted to data output paths'
 previous=None
 for line in path.splitlines():
  match=re.search(r'[\^v] (\S+) \((\S+)\)$',line)
  if not match:continue
  pin,master=match.groups()
  numbers=re.findall(r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?',line[:match.start()])
  if len(numbers)<2:continue
  delay=float(numbers[-2])
  if pin.endswith('/A') and previous and not previous['pin'].startswith(('u_','clk')) and delay>wire:
   assert previous['fanout']==1 and re.match(r'^(?:BUF|CLKBUF|INV)_X',master)
   candidates.append(dict(driver=previous['pin'],driver_master=previous['master'],sink=pin,
       sink_master=master,wire_delay_ns=delay,source_load_fF=previous['cap'],source_fanout=previous['fanout'],
       path_endpoint=endpoint,path_slack_ns=slack))
  if pin.endswith(('/Z','/ZN')):
   assert len(numbers)==5, 'Native fanout/cap/slew/delay/time fields are required'
   previous=dict(pin=pin,master=master,cap=float(numbers[-4]),fanout=int(float(numbers[0])))
assert candidates
print(json.dumps(dict(source=plan['source'],hold_guardband_ns=plan['hold_guardband_ns'],
  inspected_hold_input_guards=plan['hold_input_guards'],candidates=candidates,
  report_path=str(root/'extracted-setup-before.rpt'),report_sha256=manifest['extracted-setup-before.rpt'],
  inspection_manifest_sha256=hashlib.sha256((root/'output.sha256').read_bytes()).hexdigest())))
'''
raw = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', 'yuzelu@10.129.166.172',
                               'python3', '-', a.inspection, str(a.path_reserve_ns), str(a.wire_delay_ns)],
                              input=probe, text=True)
evidence = json.loads(raw)
pins = list(dict.fromkeys(row['driver'] for row in evidence['candidates']))
spec = dict(extracted_eco_source=evidence['source'],
            extracted_hold_guardband_ns=evidence['hold_guardband_ns'],
            extracted_repeaters=[[pin, 'BUF_X8'] for pin in pins])
evidence.update(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                planner_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                path_reserve_ns=a.path_reserve_ns, minimum_wire_delay_ns=a.wire_delay_ns,
                output_spec=target.name, repeater_master='BUF_X8',
                scope='Proposal from sealed actual RC; only single-sink standard-cell data wires. '
                      'No macro/clock mutation or state addition. Native connection, placement, rerouting '
                      'and every final quality gate still required.')
target.write_text(json.dumps(spec, indent=2) + '\n')
(HERE / 'results' / (a.attempt + '-wire-plan.json')).write_text(json.dumps(evidence, indent=2) + '\n')
print(str(target), 'repeaters', len(pins), 'hold input candidates', len(evidence['inspected_hold_input_guards']))
