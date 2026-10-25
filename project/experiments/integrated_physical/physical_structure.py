"""Keep all original functional cells; explicitly prove replacement of initial tie sources."""
import collections,copy
from decimal import Decimal
from structure import certificate,signature_graph
from common import need

def certify_physical(before,after,lib):
 missing=set(before['cells'])-set(after['cells'])
 if not missing:return certificate(before,after,lib)
 ties={n:c for n,c in before['cells'].items()if lib[c['type']]['transparent']and lib[c['type']]['transparent'][0]=='tie'}
 need(collections.Counter(c['type']for c in ties.values())=={'LOGIC0_X1':1,'LOGIC1_X1':1}and missing<=set(ties),'only original two explicit hilomap tie cells may be replaced; every functional cell retained')
 bc=signature_graph(before,lib);reduced=copy.deepcopy(before);replacement={};removed=[]
 for n in sorted(missing):
  c=before['cells'][n];t=lib[c['type']]['transparent'];need(set(c['connections'])=={t[2]}and len(c['connections'][t[2]])==1,'one fixed constant source pin');bit=c['connections'][t[2]][0];need(bc(bit)==(('constant',t[1]),0),'independent original tie function');replacement[bit]=str(t[1]);removed.append({'name':n,'type':c['type'],'pin':t[2],'constant':t[1],'area_um2':str(lib[c['type']]['area'])});del reduced['cells'][n]
 for c in reduced['cells'].values():
  for pin,bits in c['connections'].items():c['connections'][pin]=[replacement.get(b,b)for b in bits]
 for table in('ports','netnames'):
  for p in reduced[table].values():p['bits']=[replacement.get(b,b)for b in p['bits']]
 cert=certificate(reduced,after,lib);physical_area=sum((lib[c['type']]['area']for c in before['cells'].values()),Decimal(0));cert.update(original_cells=len(before['cells']),original_cells_retained=len(before['cells'])-len(missing),original_pin_bits_checked=cert['original_pin_bits_checked']+len(missing),original_constant_cells_replaced=removed,before_histogram=dict(collections.Counter(c['type']for c in before['cells'].values())),before_area_um2=str(physical_area),added_area_um2=str(Decimal(cert['after_area_um2'])-physical_area),tie_method='Only two proven source-export hilomap ties may be replaced. Their exact 0/1 functions are substituted at every original pin and port; all original non-tie cells, including every FF and buffer, must remain with equivalent pins. Removed and replacement tie areas are both accounted.')
 return cert
