"""Full 11008-K scope from the generated plan, using explicit six PFED ranges."""
import json,struct,sys
from collections import Counter
from pathlib import Path
from native_tlm_timing import Clock,S128
from native_tlm_projection import Projection
from native_work_cost import fields
from native_streamed_projection import StreamedProjection

plan=json.loads(Path(sys.argv[1]).read_text());f=fields()['input_key']
chosen=next(c for c in plan['calls'] if c['direction']=='compute'
            and int.from_bytes(bytes.fromhex(c['descriptor_hex'])[:4],'little')==0x02505001
            and struct.unpack_from('<H',bytes.fromhex(c['descriptor_hex']),76)[0]==11008)
raw=bytes.fromhex(chosen['descriptor_hex'])
key=int.from_bytes(raw[f[0]:f[0]+f[1]],'little')
feeds=[bytes.fromhex(c['descriptor_hex']) for c in plan['calls']
       if c['direction']=='supply'
       and int.from_bytes(bytes.fromhex(c['descriptor_hex'])[24:40],'little')==key]
assert len(feeds)==6
clock=Clock();source=S128(clock,core_ps=1000);target=S128(clock,core_ps=1000)
base=struct.unpack_from('<Q',raw,48)[0]
# Independent diagnostic matrix: every weight is 1 with exact FP16 scale 1.
record=bytes([1])*1024+struct.pack('<8H',*([0x3c00]*8))+bytes(48)
stats=Counter()
class TestDram:
    def submit(self,t,callback,channel=None):
        stats['read_beats']+=1
        clock.after(1700+(t.address//64%5)*900,callback)
def memory(address):
    if address<base:raise ValueError('weight address below binding')
    offset=(address-base)%1088
    return record[offset:offset+64]
p=Projection(clock,TestDram(),memory,source,target,source_word=0,scratch_word=512)
stream=StreamedProjection(p,input_key_offset=f[0],input_key_bytes=f[1])
finished=[];feed_done=[]
stream.projection(raw)(lambda:finished.append(clock.now))
def start_range(i):
    feed=feeds[i]
    word,_,_,tiles=struct.unpack_from('<4H',feed,16)
    first=struct.unpack_from('<H',feed,44)[0]
    values=[1+(first+j)%7 for j in range(tiles*128)]
    def store(j):
        if j==len(values)//4:
            def terminal():
                feed_done.append(clock.now)
                if i+1<len(feeds):clock.after(7000,lambda:start_range(i+1))
            stream.supplier(feed)(terminal)
            return
        source.access(word+j,lambda _:store(j+1),struct.pack('<4i',*values[4*j:4*j+4]))
    store(0)
# P must remain pending until the first explicit U command is issued.
clock.after(23000,lambda:start_range(0))
clock.until(lambda:bool(finished))
assert len(feed_done)==6 and stream.feed is None and stream.held is None
out=struct.unpack_from('<H',raw,86)[0]
actual=struct.unpack('<128i',b''.join(target.words[out+i] for i in range(32)))
expected=sum(1+j%7 for j in range(11008))
assert actual==(expected,)*128,(actual[:8],expected)
assert stream.stats=={'supplied_windows':86,'released_windows':86}
report={'passed':True,'K':11008,'output_elements':128,'explicit_feed_calls':6,
        'windows':dict(stream.stats),'ddr':dict(stats),'test_finish_ps':finished[0],
        'scope':'generated full-K descriptor, numerical P model, explicit U feed, synthetic matrix and test DDR timing',
        'performance_calibrated':False,'whole_graph_executed':False}
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
