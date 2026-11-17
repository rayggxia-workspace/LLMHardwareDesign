from pathlib import Path
import json,sys
before,after,out=map(Path,sys.argv[1:])
a=before.read_text().splitlines();b=after.read_text().splitlines()
def pg(s):
 x=s.split('\t');return (x[0]=='PIN' and x[1] in ('VDD','VSS')) or (x[0]=='MACROPIN' and x[3] in ('VDD','VSS','vdd','gnd'))
sa=sorted(x for x in a if not pg(x));sb=sorted(x for x in b if not pg(x))
r={'signal_die_macro_exact':sa==sb,'removed_pg_shapes':sorted(set(x for x in a if pg(x))-set(x for x in b if pg(x))),'added_pg_shapes':sorted(set(x for x in b if pg(x))-set(x for x in a if pg(x)))}
out.write_text(json.dumps(r,indent=2)+'\n')
assert r['signal_die_macro_exact'], 'Signal/macro/die geometry differs'
