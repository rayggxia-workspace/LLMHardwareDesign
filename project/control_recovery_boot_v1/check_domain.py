"""Check the declared single-clock/reset contract against this RTL shell."""
from pathlib import Path
import json,re,hashlib,argparse
H=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args()
 c=json.loads((H/'clock-reset-contract.json').read_text());assert c['clock_domains']==1 and c['clock_ports']==['clk_i'] and not c['asynchronous_host_supported']
 rtl=[x for x in H.glob('*.sv') if not x.name.startswith('tb_')]
 events={x.name:re.findall(r'posedge\s+(\w+)',x.read_text()) for x in rtl}
 assert all(set(v)<=set(c['clock_ports']) for v in events.values()),events
 outer=(H/'recovery_boot_top.sv').read_text();inner=(H/'recovery_control_top.sv').read_text()
 assert '(* async_reg="true" *) reg [1:0] outer_reset_release' in outer
 assert '.rst_ni(outer_rst_ni)' in outer and "outer_reset_release<={outer_reset_release[0],1'b1}" in outer
 assert '(* async_reg="true" *) reg [1:0] reset_release' in inner
 assert "reset_release<={reset_release[0],1'b1}" in inner
 assert 'wire core_rst_ni=reset_release[1]' in inner
 s=(H/'recovery_supervisor.sv').read_text()
 assert 'if(!pass)begin' in s and 'saved_reads<=observed_reads_o' in s
 assert 'state<=RESET' in s and 'inner_rst_ni=rst_ni && state!=RESET' in s
 d={'schema':'recovery-domain-check/1','passed':True,'domains':1,'clock_events':events,'scope':'RTL contract inventory, not physical CDC/RDC signoff','source_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in rtl}}
 if a.out:a.out.write_text(json.dumps(d,indent=2)+'\n')
 print('PASS declared single-clock and two-level synchronized reset release')
if __name__=='__main__':main()
