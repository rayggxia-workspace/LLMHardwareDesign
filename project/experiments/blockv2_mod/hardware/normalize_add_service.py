"""Replace the historical compact U shim with the full native service ABI."""
from pathlib import Path
import re
from rtl_ports import read,close
ROOT=Path(__file__).resolve().parents[1]
def normalize(text):
 if 'input wire service_valid' in text:
  if 'input wire s_rsp_error' not in text:
   text=text.replace(' input wire s_rsp_valid,',' input wire s_rsp_valid,\n input wire s_rsp_error,')
  return text.replace(".s_rsp_error(1'b0)",'.s_rsp_error(s_rsp_error)')
 old=read(text)
 scope=read((ROOT/'rtl/p_services/s32_add_scope.sv').read_text())
 service={n:p for n,p in scope.items() if n in ('clk','reset') or n.startswith('service_')}
 service.update({n:p for n,p in old.items() if n.startswith(('s_req_','s_rsp_','resource_e_'))})
 m=re.search(r'\bmodule\s+add_s32_service_controller',text)
 start=text.index('(',m.end());end=close(text,start)
 body=text[end+2:]
 body=re.sub(r' wire \[1023:0\] service_descriptor = [^;]+;\n','',body)
 renames={'svc_valid':'service_valid','svc_ready':'service_ready','rsp_valid':'service_done_valid',
          'rsp_ready':'service_done_ready','status':'service_done_status',
          'read_bytes':'service_done_read_bytes','write_bytes':'service_done_write_bytes'}
 for a,b in renames.items():body=re.sub(r'\b'+a+r'\b',b,body)
 replacements={
  '.TOPOLOGY(25001)':'.TOPOLOGY(TOPOLOGY)',
  ".service_owner(128'd0)":'.service_owner(service_owner)',
  ".service_ticket(32'd0)":'.service_ticket(service_ticket)',
  ".service_cancel_valid(1'b0)":'.service_cancel_valid(service_cancel_valid)',
  '.service_cancel_ready(qkv_cancel_ready[2])':'.service_cancel_ready(service_cancel_ready)',
  '.service_done_owner(qkv_owner[2])':'.service_done_owner(service_done_owner)',
  '.service_done_ticket()':'.service_done_ticket(service_done_ticket)'}
 for a,b in replacements.items():
  assert a in body,a
  body=body.replace(a,b)
 assert '25001' not in body and 'descriptor[512' not in body
 header=['// Parent ADD service; native descriptor/identity/completion, selected E macro.',
   'module add_s32_service_controller #(parameter logic [31:0] TOPOLOGY=0)(',
   ',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in service.items()),');']
 return normalize('\n'.join(header)+body)
if __name__=='__main__':
 p=ROOT/'rtl/services/add_s32_service_controller.sv'
 p.write_text(normalize(p.read_text()))
