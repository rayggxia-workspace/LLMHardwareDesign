"""Actual compiled service operations; no graph-level Attention/RMS fallback."""
import struct
from macro_memory import Data
from macro_numeric import rne,checked_s32,quotient_rne,exponents,rms_factor
from macro_service_runner import read_words,write_words,load_span,store_span
from n32_service_descriptor import encode as n_encode,decode_result
from e32_dot_descriptor import encode as dot_encode
from rms_apply_native_descriptor import encode as rms_encode
from indexed_gather_descriptor import encode as gather_encode

def packed(values):return Data.of(struct.pack('<'+'i'*len(values),*(checked_s32(v) for v in values)))
def same_descriptor(raw,expected):
 if raw!=expected:raise ValueError('descriptor does not match implemented RTL service contract')
def dma(raw,store=False):
 word=struct.unpack_from('<H',raw,16)[0];address=struct.unpack_from('<Q',raw,24)[0]
 if address%64 or word>992 or any(raw[18:24]) or any(raw[40 if store else 32:124]):
  raise ValueError('DRL1/DWS1 descriptor extent')
 if store:
  tag=struct.unpack_from('<Q',raw,32)[0]
  if tag+8>1<<64:raise ValueError('DWS1 tag overflow')
  yield from store_span(word,address,512,tag)
 else:yield from load_span(address,word,512)
def add(raw):
 left,right,dst,count=struct.unpack_from('<4H',raw,16)
 if not 0<count<=1024 or max(left,right,dst)+count>1024 or any(raw[24:124]):
  raise ValueError('ADD descriptor extent')
 for i in range(count):
  a=(yield ('sread',left+i)).i32();b=(yield ('sread',right+i)).i32()
  result=packed([x+y for x,y in zip(a,b)])
  yield ('cycles',9);yield ('swrite',dst+i,result)
def n32(raw):
 op=struct.unpack_from('<H',raw,6)[0];topology=struct.unpack_from('<I',raw,12)[0]
 source,count,epsilon,baseline,eps_shift,dst=struct.unpack_from('<HHIbbH',raw,16)
 operation={1:'Softmax',2:'RMSFactor',3:'Argmax'}[op]
 same_descriptor(raw,n_encode(operation=operation,topology=topology,source_word=source,elements=count,
  result_word=None if op==1 else dst,epsilon_mantissa=epsilon,baseline_shift=baseline,epsilon_shift=eps_shift))
 words=(count+3)//4
 first=(yield from read_words(source,words)).i32(count)
 if op==1:
  # Max scan, exponent pass/commit, normalization pass/commit. Unused lanes
  # are zeroed by the actual N macro, not by a host initialization shortcut.
  scores=(yield from read_words(source,words)).i32(count)
  if max(scores)!=max(first):raise ValueError('Softmax input changed during owned SRAM passes')
  exp=exponents(scores);factor=quotient_rne(1<<48,sum(exp))
  yield ('cycles',12*words)
  yield from write_words(source,packed(exp+[0]*(4*words-count)))
  values=(yield from read_words(source,words)).i32(count)
  result=[rne(v*factor,32) for v in values]
  yield ('cycles',64+8*words)
  yield from write_words(source,packed(result+[0]*(4*words-count)))
 elif op==2:
  values=(yield from read_words(source,words)).i32(count)
  if values!=first:raise ValueError('RMS input changed during owned SRAM scan')
  factor,shift,extra=rms_factor(values,epsilon,baseline,eps_shift)
  yield ('cycles',168+6*words)
  yield ('swrite',dst,Data.of(struct.pack('<IIbBB5x',factor,0,shift,extra,1)))
 else:
  maximum=max(first);index=first.index(maximum)
  yield ('cycles',2*words+2)
  yield ('swrite',dst,Data.of(struct.pack('<IIbBB5x',maximum&0xffffffff,index,0,0,2)))
def rms_apply(raw):
 topology=struct.unpack_from('<I',raw,12)[0]
 x,gamma,words,fword,gs=struct.unpack_from('<4Hb',raw,16)
 same_descriptor(raw,rms_encode(topology=topology,x_word=x,gamma_word=gamma,words=words,factor_word=fword,gamma_shift=gs))
 factor=decode_result((yield ('sread',fword)).require(),'RMSFactor')
 fs=14+factor['shift']-factor['extra_shift']
 for i in range(words):
  a=(yield ('sread',x+i)).i32();g=(yield ('sread',gamma+i)).i32()
  normalized=[checked_s32(rne(v*factor['factor'],fs)) for v in a]
  result=packed([rne(v*w,gs) for v,w in zip(normalized,g)])
  yield ('cycles',20);yield ('swrite',x+i,result)
def rope(raw):
 x,cosine,sine,dst=struct.unpack_from('<4H',raw,16)
 cs,ns,na,ss,sa,os,se,ne,oe,ce=struct.unpack_from('<10b',raw,24)
 ranges=sorted((a,a+32) for a in (x,cosine,sine,dst))
 if (any(a<0 or b>1024 for a,b in ranges) or any(b>c for (_,b),(c,_) in zip(ranges,ranges[1:]))
     or any(raw[34:124]) or any(not -63<=s<=63 for s in (cs,ns,na,ss,sa,os))
     or ce!=-14 or se+ce+cs!=oe or ns+na!=0 or se+ce+ss+sa!=oe or oe+os!=ne):
  raise ValueError('RoPE precision/window contract')
 for i in range(32):
  a=(yield ('sread',x+i)).i32();b=(yield ('sread',x+(i+16)%32)).i32()
  c=(yield ('sread',cosine+i)).i32();s=(yield ('sread',sine+i)).i32()
  out=[]
  for av,bv,cv,sv in zip(a,b,c,s):
   ca=checked_s32(rne(av*cv,cs))
   if i<16:
    bv=checked_s32(rne(-bv,ns));bv=checked_s32(rne(bv,na))
   si=checked_s32(rne(bv*sv,ss));si=checked_s32(rne(si,sa))
   total=checked_s32(ca+si);out.append(checked_s32(rne(total,os)))
  yield ('cycles',40 if i<16 else 30)
  yield ('swrite',dst+i,packed(out))
def gather(raw):
 topology=struct.unpack_from('<I',raw,12)[0]
 table,index_addr,rows,offset,size,word,row_shift,index_bytes=struct.unpack_from('<QQIIHHBB',raw,16)
 same_descriptor(raw,gather_encode(topology=topology,table_address=table,index_address=index_addr,
  rows=rows,offset=offset,byte_count=size,sram_word=word,row_shift=row_shift,index_bytes=index_bytes))
 packet=yield ('read',index_addr//64*64)
 index=int.from_bytes(packet.slice(index_addr%64,index_bytes).require(),'little',signed=True)
 if index<0:index+=rows
 if not 0<=index<rows:raise ValueError('GTH2 index outside table')
 yield from load_span(table+(index<<row_shift)+offset,word,size)
def dot(raw):
 topology=struct.unpack_from('<I',raw,12)[0]
 k,columns,shift,word,reserved,a,b,astride,bstride,cstride=struct.unpack_from('<HBBHHQQIII',raw,16)
 enabled,scale_shift,reserved2,scale=struct.unpack_from('<BBHi',raw,52)
 if enabled not in (0,1):raise ValueError('EMD1 scale enable')
 same_descriptor(raw,dot_encode(topology=topology,k=k,columns=columns,shift=shift,result_word=word,
  a_address=a,b_address=b,a_stride=astride,b_k_stride=bstride,b_column_stride=cstride,
  scale=scale if enabled else None,scale_shift=scale_shift))
 cache_address=None;cache=None;acc=[0]*columns
 yield ('cycles',6)
 for pos in range(k):
  values=[]
  for addr in [a+pos*astride]+[b+pos*bstride+lane*cstride for lane in range(columns)]:
   if cache_address!=addr//64*64:
    cache_address=addr//64*64;cache=yield ('read',cache_address)
   values.append(struct.unpack('<i',cache.slice(addr%64,4).require())[0])
   yield ('cycles',1)
  for lane in range(columns):
   acc[lane]+=values[0]*values[lane+1]
   if not -(1<<79)<=acc[lane]<1<<79:raise ValueError('E32 S80 overflow')
  yield ('cycles',8)
 result=[checked_s32(rne(v,shift)) for v in acc]
 yield ('cycles',6)
 if enabled:
  result=[checked_s32(rne(v*scale,scale_shift)) for v in result]
  yield ('cycles',10)
 yield ('swrite',word,packed(result+[0]*(4-columns)))
def gated(raw,packet):
 gate,up,out,words=struct.unpack_from('<4H',raw,16)
 spans=sorted((x,x+words) for x in (gate,up,out))
 if not 0<words<=32 or any(b>1024 for a,b in spans) or any(b>c for (a,b),(c,d) in zip(spans,spans[1:])) or any(raw[24:124]):
  raise ValueError('GSM1 SRAM ranges')
 for i in range(words):
  a=(yield ('sread',gate+i)).i32();b=(yield ('sread',up+i)).i32();values=[]
  for lane in (0,2):
   pair,error=packet(a[lane:lane+2],b[lane:lane+2],True,3)
   if error:raise ValueError('G32 arithmetic error')
   values.extend(pair)
  yield ('cycles',10);yield ('swrite',out+i,packed(values))
