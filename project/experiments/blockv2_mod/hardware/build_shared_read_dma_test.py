"""Extend the upstream mixed-client stress rather than replacing it with a smoke test."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/mother_control_native/typed_dma/typed.cpp')
s=p.read_text().replace('Vmc_dma_fabric_typed_p','Vnative_shared_read_dma')
s=s.replace(',12>',',21>').replace('c<12','c<21')
s=s.replace('zero(t.c_req_address,24)','zero(t.c_req_address,42)')
for field in ['c_req_tag','c_close_tag_base','c_cancel_tag','c_fence_cookie']:
 s=s.replace('zero(t.'+field+',12)','zero(t.'+field+',21)')
s=s.replace('zero(t.c_fence_epoch,4)','zero(t.c_fence_epoch,6)')
s=s.replace('t.c_req_record_beats=0','zero(t.c_req_record_beats,4)')
s=s.replace('t.c_req_record_beats|=uint64_t(p.length)<<(5*c);',
 'for(int b=0;b<5;++b)if((p.length>>b)&1)t.c_req_record_beats[(5*c+b)/32]|=1U<<((5*c+b)%32);')
s=s.replace('uint16_t(', 'uint32_t(').replace('4095','2097151')
s=s.replace('(tag>>6)&15U','(tag>>5)&31U').replace('need(client<12','need(client<21')
s=s.replace('t.fault_client==15','t.fault_client==31')
s=s.replace('client<9?1:5','(client<9||client>=12)?1:5')
s=s.replace('c<9?2:17+(round&1)','c<9?2:(c<12?17+(round&1):1)')
marker=' need(expected.empty()&&accepted==returned+cancelled'
assert marker in s
extra="""
 // Fixed native clients run concurrently with actual LC and M records.
 // No runtime P mode change, doubled records, or extra backend bandwidth.
 int service_begin=accepted;
 for(int row=0;row<64;++row){
  for(int c=12;c<21;++c)queues[size_t(c)].push_back(one(c,50000+row,(row+c)&1));
  if(row%8==0){add_record(4,51000+row,2,0);add_record(10,52000+row,18,1);}
 }
 quiet();need(accepted-service_begin==736,"mixed native service workload");
 for(int c=12;c<21;++c)submit_bad(one(c,50063,c&1));
 auto service_odd=one(20,60000,0);service_odd.tag|=1;submit_bad(service_odd);
 submit_bad(packet(20,60000,0,2,0));
 auto service_align=one(19,60000,1);service_align.address+=16;submit_bad(service_align);
 // Fencing service20 must not release service19's replay protection.
 fence_client=20;fence_cookie=0x1850cc20;fence_epoch=300;fence_request=true;
 oldf=fences;wait([&]{return !fence_request&&fences>oldf&&!backend_fence&&!t.c_fence_done_valid;},
                 "service20 namespace fence with 9-bit epoch");
 queues[20].push_back(one(20,1,1));quiet();
 submit_bad(one(19,1,1));
"""
s=s.replace(marker,extra+marker).replace('PASS DMA clients=12','PASS DMA clients=21')
(ROOT/'tests/shared_read_dma.cpp').write_text(s)
