"""Explicit control-transport assembly; hierarchy is never a physical endpoint."""
from pathlib import Path
from hashlib import sha256
import json
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project')
original=BASE/'rtl/mother_control_native/mc_dma_fabric_typed_p.sv'
serial=BASE/'rtl/mother_control_native/native64_dma_serial_client.sv'
core=ROOT/'rtl/control/native_shared_read_dma.sv'
ports=read(original.read_text());cp=read(core.read_text())
lines=['// Parent standard cells: explicit fixed DMA control links, no functional macros or U/P data wiring.',
 'module native_shared_read_plane #(parameter logic [30:0] SERVICE_SERIAL_LIMIT=31\'h7fffffff,',
 " parameter logic [15:0] TRANSPORT_SERIAL_LIMIT=16'hffff)("]
external={n:p for n,p in ports.items() if not n.startswith('p_mode_') and n!='p_req_rejected'}
external['fault_client']=dict(external['fault_client'],shape='[4:0] ')
for n,d,shape in [
 ('service_req_valid','input','[8:0]'),('service_req_ready','output','[8:0]'),
 ('service_req_address','input','[575:0]'),('service_req_tag','input','[575:0]'),
 ('service_rsp_valid','output','[8:0]'),('service_rsp_ready','input','[8:0]'),
 ('service_rsp_tag','output','[575:0]'),('service_rsp_data','output','[4607:0]'),
 ('service_rsp_error','output','[8:0]'),('service_idle','output','[8:0]'),
 ('service_protocol_fault','output','[8:0]')]:
 external[n]={'direction':d,'shape':shape+' ','signed':''}
lines.append(',\n'.join(p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items())+');')
for n,p in cp.items():
 if n.startswith('c_'):lines.append('wire '+p['shape']+'all_'+n+';')
# Slice low clients directly; high native service clients are separately owned.
for n,p in ports.items():
 if not n.startswith('c_'):continue
 bits={'[11:0]':12,'[767:0]':768,'[383:0]':384,'[59:0]':60,
       '[6143:0]':6144,'[107:0]':108}[p['shape'].strip()]
 if p['direction']=='input':lines.append('assign all_'+n+'['+str(bits-1)+':0]='+n+';')
 else:lines.append('assign '+n+'=all_'+n+'['+str(bits-1)+':0];')
connections=[]
for n in cp:
 if n.startswith('c_'):value='all_'+n
 elif n=='p_mode_client_drained':value="3'b111"
 elif n in ('p_mode_valid','p_mode_native64'):value="3'b000"
 elif n in ('p_mode_ready','p_mode_active','p_req_rejected'):value=''
 else:value=n
 connections.append('.'+n+'('+value+')')
lines.append('native_shared_read_dma #(.SERIAL_LIMIT(TRANSPORT_SERIAL_LIMIT)) transport('+','.join(connections)+');')
lines.append('for(genvar k=0;k<9;k=k+1)begin: service_client')
links={
 'clk':'clk','reset':'reset',
 'req_valid':'service_req_valid[k]','req_ready':'service_req_ready[k]',
 'req_address':'service_req_address[k*64+:64]','req_tag':'service_req_tag[k*64+:64]',
 'rsp_valid':'service_rsp_valid[k]','rsp_ready':'service_rsp_ready[k]',
 'rsp_tag':'service_rsp_tag[k*64+:64]','rsp_data':'service_rsp_data[k*512+:512]',
 'rsp_error':'service_rsp_error[k]',
 'dma_valid':'all_c_req_valid[k+12]','dma_ready':'all_c_req_ready[k+12]',
 'dma_address':'all_c_req_address[(k+12)*64+:64]','dma_tag':'all_c_req_tag[(k+12)*32+:32]',
 'dma_rsp_valid':'all_c_rsp_valid[k+12]','dma_rsp_ready':'all_c_rsp_ready[k+12]',
 'dma_rsp_tag':'all_c_rsp_tag[(k+12)*32+:32]','dma_rsp_data':'all_c_rsp_data[(k+12)*512+:512]',
 'fence_valid':'all_c_fence_valid[k+12]','fence_ready':'all_c_fence_ready[k+12]',
 'fence_cookie':'all_c_fence_cookie[(k+12)*32+:32]','fence_epoch':'all_c_fence_epoch[(k+12)*9+:9]',
 'fence_done_valid':'all_c_fence_done_valid[k+12]','fence_done_ready':'all_c_fence_done_ready[k+12]',
 'fence_done_cookie':'all_c_fence_done_cookie[(k+12)*32+:32]','fence_done_epoch':'all_c_fence_done_epoch[(k+12)*9+:9]',
 'idle':'service_idle[k]','protocol_fault':'service_protocol_fault[k]'}
assert set(links)==set(read(serial.read_text()))
lines.append('native64_dma_serial_client #(.SERIAL_LIMIT(SERVICE_SERIAL_LIMIT)) serial('+','.join('.'+n+'('+v+')' for n,v in links.items())+');')
lines.extend([
 'assign all_c_req_channel[k+12]=service_req_address[k*64+11];',
 "assign all_c_req_record_beats[(k+12)*5+:5]=5'd1;",
 "assign all_c_close_valid[k+12]=1'b0;",
 "assign all_c_close_tag_base[(k+12)*32+:32]=32'd0;",
 "assign all_c_cancel_valid[k+12]=1'b0;",
 "assign all_c_cancel_tag[(k+12)*32+:32]=32'd0;",
 "assign all_c_cancel_ack_ready[k+12]=1'b1;",
 'end','endmodule'])
target=ROOT/'rtl/control/native_shared_read_plane.sv'
target.write_text('\n'.join(lines)+'\n')
manifest={'schema':'shared-read-plane/1','hard_boundary':False,
 'sources':{str(p):sha256(p.read_bytes()).hexdigest() for p in (original,serial,core,target)},
 'instances':{'native_shared_read_dma':1,'native64_dma_serial_client':9},
 'service_client_map':{o:12+i for i,o in enumerate(('P0','P1','P2','C0','U0','J0','F0','U1','J1'))},
 'service_outstanding_per_owner':1,'tag_semantics':'full 64-bit owner tag retained; serial reused only after matching fence',
 'fixed_links_scope':'registered DMA controller/client transport only; no inter-owner data connections',
 'functional_acceptance':False,'whole_base_accepted':False}
(ROOT/'hardware/shared-read-plane.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(target)
