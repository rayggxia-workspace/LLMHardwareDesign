from pathlib import Path
from hashlib import sha256
import json
from build_projection_local_contract import ports,ROOT,BASE
def main():
 source=ROOT/'rtl/services/e32_dot_service_controller.sv';sp=ports(source)
 requirements=[]
 for role,master,path,mapping in [
  ('e','e_s32_mac_ap64',ROOT/'rtl/macros/e_s32_mac_ap64.sv',
   {n:n[len('resource_e_'):] for n in sp if n.startswith('resource_e_')}),
  ('s','local_s_base',BASE/'rtl/s_sram/local_s_base.sv',
   {'s_req_valid':'req_valid','s_req_write':'req_write','s_req_ready':'req_ready',
    's_req_address':'req_addr','s_req_data':'req_data','s_rsp_valid':'rsp_valid',
    's_rsp_ready':'rsp_ready','s_rsp_data':'rsp_data'})]:
  mp=ports(path);pins=[]
  for name,pin in mapping.items():
   assert sp[name]['shape']==mp[pin]['shape'] and sp[name]['direction']!=mp[pin]['direction']
   pins.append(dict(service_pin=name,macro_pin=pin,**sp[name]))
  requirements.append({'resource':role,'required_native_master':master,'ports':pins})
 contract={'module':'e32_dot_service_controller','rtl':str(source.relative_to(ROOT)),
  'rtl_sha256':sha256(source.read_bytes()).hexdigest(),'hard_boundary':False,
  'resource_requirements':requirements,'descriptor':{'schema':0x31444d45,'abi':0x02504503,'opcode':1},
  'completion':'result stored ACK; all accepted DDR reads and E results drained',
  'parent_resources':{'ddr_outstanding_reads':1,'cache_lines':1,'cache_line_bytes':64,
                      'e_operand_words':1,'e_result_words':1},
  'required_exclusivity':'E32 MAC context through END/ABORT result; SRAM destination until write ACK',
  'admission':'actual E/S fixture numeric pass 114666; full owner dispatcher and graph admission pending',
  'assumed_product_connections':[]}
 p=ROOT/'hardware/service-controller-contracts.json';d=json.loads(p.read_text())
 d['services']=[s for s in d['services'] if s['module']!=contract['module']]+[contract]
 p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':main()
