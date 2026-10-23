"""Positive and physical-open/wrong-signal negatives on actual routed DEF."""
import argparse
import copy
import json
from pathlib import Path
import re
from upper_connectivity import verify
from freeze_audit import section

p=argparse.ArgumentParser()
for name in ('def_file','plan','partition','tech','output'):p.add_argument(name,type=Path)
a=p.parse_args()
text=a.def_file.read_text();plan=json.loads(a.plan.read_text());parts=json.loads(a.partition.read_text());tech=a.tech.read_text()
positive=verify(text,plan,parts['access_landings'],tech)
assert positive['passed']
first=section(text,'NETS')[0]
header=re.split(r'\+ ROUTED |\n\s*NEW ',first)[0]
bad=text.replace(first,header,1)
negative=verify(bad,plan,parts['access_landings'],tech)
assert not negative['passed'],'Physical open accepted'
wrong=copy.deepcopy(plan);wrong['forests'][0]['original_net']='incorrect_signal'
try:verify(text,wrong,parts['access_landings'],tech)
except AssertionError:alias_rejected=True
else:raise AssertionError('Wrong signal mapping accepted')
a.output.write_text(json.dumps(dict(passed=True,actual_forests=positive['forest_count'],physical_open_rejected=True,
    wrong_alias_rejected=alias_rejected,scope='Actual routed positive and deliberately disconnected/wrong-net negative controls; no source mutation'),indent=2)+'\n')
print('Actual upper conductor graph and two independent negatives passed.')
