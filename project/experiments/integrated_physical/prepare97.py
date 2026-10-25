"""Export actual accepted97 netlist; declared storage cut, explicit real tie cells."""
import argparse,copy,traceback
from common import *
from admission97 import admit,MAP,SOURCE

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);m={'status':'ERROR','source':sources(),'task':'prepare97','resources':resource_snapshot()}
 try:
  admission=admit();put(a.out/'admission.json',admission);raw=load(MAP/'mapped.json');top=raw['modules']['chain97'];stores=[(n,c)for n,c in top['cells'].items()if c['type']=='store82'];need(len(stores)==1,'exact single store')
  name,store=stores[0];need(set(store['connections'])=={'clk','reset','req','wr','addr','din','take','ready','valid','dout'},'exact store port inventory')
  for n in('clk',):need(store['connections'][n]==top['ports'][n]['bits'],'store clock same top')
  put(a.out/'mapped.json',raw);cut=copy.deepcopy(raw);t=cut['modules']['chain97'];ports=[]
  for port,bits in store['connections'].items():
   if port=='clk':continue
   n='store_'+port;need(n not in t['ports'],'unique cut port');direction='input'if store['port_directions'][port]=='output'else'output';t['ports'][n]={'direction':direction,'bits':bits};ports.append({'port':n,'original_pin':port,'direction':direction,'bits':bits,'width':len(bits)})
  del t['cells'][name];cut['modules'].pop('store82',None);put(a.out/'cut-source.json',cut);put(a.out/'cut-contract.json',{'original_cell':name,'original_connections':store,'ports':ports,'excluded_store_clock':['clk'],'reset_preserved_as_cut_output':True,'memory_bytes':16384,'port_width':128,'ports_1RW':1,'physical_macro_qualified':False})
  ys=a.out/'export.ys';ys.write_text(f'read_json {a.out}/mapped.json\nwrite_verilog -noattr -noexpr {a.out}/mapped.v\ndesign -reset\nread_liberty -ignore_miss_func -ignore_miss_dir {LIB}\nwrite_verilog -noattr {a.out}/cells.v\ndesign -reset\nread_json {a.out}/cut-source.json\nwrite_verilog -noattr -noexpr {a.out}/cut-source.v\nhilomap -singleton -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\ncheck -assert\nwrite_json {a.out}/cut.json\nwrite_verilog -noattr -noexpr {a.out}/cut.v\ntee -o {a.out}/stat.json stat -liberty {LIB} -json\n')
  command(a.out,'export',['yosys','-s',ys],300)
  (a.out/'chain_gate.cpp').write_bytes((SOURCE/'project/experiments/v_consumer/sim.cpp').read_bytes())
  m.update(status='EXACT_ACCEPTED97_GATE_EXPORT_AND_DECLARED_MEMORY_CUT',admission_sha256=sha(a.out/'admission.json'),top='chain97',library_sha256=sha(LIB))
 except Exception as e:m.update(error=str(e),traceback=traceback.format_exc());raise
 finally:manifest(a.out,m)
 print(m['status'])
if __name__=='__main__':main()
