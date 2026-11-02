"""Independent unit checks of the conservative pin bound and physical dedup."""
from native_pin_load import minimum_pin_cap,loads

assert minimum_pin_cap([])==0
assert minimum_pin_cap([None,None])==0
assert minimum_pin_cap(['3','2.5','2.7'])==2.5
for invalid in [-1,float('inf'),float('nan')]:
    try:minimum_pin_cap([invalid])
    except AssertionError:pass
    else:raise AssertionError('Invalid capacitance accepted')
g=dict(instances={'a':'leaf','b':'leaf'},connections={'7':dict(driver=dict(instance='TOP',pin='in'),sinks=[dict(instance='a',pin='x'),dict(instance='a',pin='alias'),dict(instance='b',pin='x')])})
inv={'leaf':{'x':[('gate','BUF','A')],'alias':[('gate','BUF','A')]}}
r=loads(g,inv,lambda m,p:2.5)['net_7']
assert r==dict(minimum_input_pin_cap_ff=5.,actual_input_pin_count=2)
assert loads(g,{'leaf':{'x':[],'alias':[]}},lambda m,p:100)['net_7']==dict(minimum_input_pin_cap_ff=0,actual_input_pin_count=0)
print('PASS: minimum pin bound, invalid values and exact physical dedup')
