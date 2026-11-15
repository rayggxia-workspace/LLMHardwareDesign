"""Unify reads and writes under the same finite transport, no extra DDR credits."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'rtl/control/native_shared_read_dma.sv'
s=source.read_text().replace('module native_shared_read_dma','module native_shared_memory_dma')
s=s.replace('native64 services 12..20','native64 reads 12..20 and writes 21..29')
for old,new in [('[20:0]','[29:0]'),('[0:20]','[0:29]'),('[1343:0]','[1919:0]'),
 ('[671:0]','[959:0]'),('[104:0]','[149:0]'),('[10751:0]','[15359:0]'),('[188:0]','[269:0]'),
 ('<21','<30'),('%21','%30')]:s=s.replace(old,new)
s=s.replace('output wire [31:0] debug_generation','output wire transport_idle,\n output wire [31:0] debug_generation')
s=s.replace(' assign debug_generation=transport_generation;', ' assign debug_generation=transport_generation;\n assign transport_idle=!reset&&empty_transport&&fence_state==F_IDLE&&desc_live==0&&c_cancel_ack_valid==0&&!fault_valid&&c_req_valid==0;')
p=ROOT/'rtl/control/native_shared_memory_dma.sv';p.write_text(s)
old=json.loads((ROOT/'hardware/shared-read-dma-revision.json').read_text())
old.update(schema='shared-memory-dma-revision/1',implementation='native_shared_memory_dma',
 source=str(p.relative_to(ROOT)),sha256=sha256(p.read_bytes()).hexdigest(),
 derived_from={'path':str(source),'sha256':sha256(source.read_bytes()).hexdigest()})
old['clients'] += [dict(x,client=x['client']+9,kind='write_service') for x in old['clients'][12:21]]
old['delta']['client_count']=[12,30]
old['scope']='unified read/write transport; shared 64 entries, 384B return skids and rolling issue limit'
(ROOT/'hardware/shared-memory-dma-revision.json').write_text(json.dumps(old,indent=2)+'\n')
