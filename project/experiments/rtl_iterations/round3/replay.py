"""Compare actual RTL control traces to the independent finite-controller probe."""
import collections
import hashlib
from pathlib import Path

ALWAYS=(0,1,2,4,5,7,8,14,15,16,20,23,24,25,26)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def split_control(source,inputs,actual):
 count=0;previous=None
 with Path(source).open(encoding='utf8') as source,Path(inputs).open('w',encoding='utf8') as inp,Path(actual).open('w',encoding='utf8') as act:
  for line in source:
   fields=line.split()
   if len(fields)!=47:raise ValueError('control row must contain47 decimal integers')
   values=[int(x) for x in fields]
   if any(x<0 for x in values) or values[0]!=values[20]:raise ValueError('bad control cycle')
   if previous is not None and values[0]!=previous+1:raise ValueError('noncontiguous RTL control')
   previous=values[0];count+=1
   inp.write(' '.join(fields[:20])+'\n');act.write('CONTROL '+' '.join(fields[20:])+'\n')
 if not count:raise ValueError('empty RTL control')
 return count

def compare(inputs,actual,observed,mutation=None):
 count=0;fields_checked=0;seen_reset=False;ignored=0;mutation_applied=False
 with Path(inputs).open() as fi,Path(actual).open() as fa,Path(observed).open() as fo:
  while True:
   il,al,ol=fi.readline(),fa.readline(),fo.readline()
   if not il and not al and not ol:break
   if not il or not al or not ol:raise ValueError('replay line count differs')
   iv=[int(v) for v in il.split()]
   if not al.startswith('CONTROL ') or not ol.startswith('CONTROL '):raise ValueError('missing CONTROL prefix')
   av=[int(v) for v in al.split()[1:]];ov=[int(v) for v in ol.split()[1:]]
   if len(iv)!=20 or len(av)!=27 or len(ov)!=27 or not iv[0]==av[0]==ov[0]:raise ValueError('control schema/cycle mismatch')
   if not seen_reset:
    if not iv[1]:raise ValueError('first observed edge must reset the RTL')
    seen_reset=True;ignored+=1;count+=1;continue
   selected=list(ALWAYS)
   if av[2]:selected.append(3)
   if av[5]:selected.append(6)
   if av[8]:selected.extend(range(9,14))
   if av[14]:selected.extend(range(17,20))
   if av[20]:selected.extend((21,22))
   if mutation and not mutation_applied and av[2]:
    ov[3]^=1;mutation_applied=True
   for index in selected:
    if av[index]!=ov[index]:raise ValueError('control mismatch cycle=%s field=%s actual=%s model=%s'%(iv[0],index,av[index],ov[index]))
   fields_checked+=len(selected);count+=1
 if not seen_reset or not fields_checked:raise ValueError('no initialized control compared')
 if mutation and not mutation_applied:raise ValueError('mutation fixture lacked accepted read')
 return dict(passed=True,cycles=count,compared_fields=fields_checked,initial_reset_rows_ignored=ignored,
             invalid_payload_policy='valid-mask only; all valid request/done/leaf/commit payload checked',
             input_sha256=sha(inputs),actual_sha256=sha(actual),probe_sha256=sha(observed))

def service_events(inputs,actual,first,last):
 """Derive response latency and finite peaks from real handshakes, not estimates."""
 rq=collections.deque();wq=collections.deque();rdelays=[];wdelays=[];reads=writes=0
 leaf=commits=commands=done=0;peak_buffers=peak_reads=peak_reservations=0;events=[]
 observed_first=None;observed_last=None
 with Path(inputs).open() as fi,Path(actual).open() as fa:
  for il,al in zip(fi,fa):
   cycle=int(il.split(' ',1)[0])
   if cycle<first:continue
   if cycle>last:break
   iv=[int(x) for x in il.split()];av=[int(x) for x in al.split()[1:]]
   if iv[1]:raise ValueError('reset inside a completed measurement')
   peak_buffers=max(peak_buffers,av[26]);peak_reads=max(peak_reads,av[25]);peak_reservations=max(peak_reservations,av[24])
   if iv[16] and av[4]:
    if not rq:raise ValueError('unmatched real read ACK')
    origin,address=rq.popleft();rdelays.append(cycle-origin);events.append(dict(cycle=cycle,kind='read_ack',request_cycle=origin,address=address))
   if iv[18] and av[7]:
    if not wq:raise ValueError('unmatched real write ACK')
    origin,address=wq.popleft();wdelays.append(cycle-origin);events.append(dict(cycle=cycle,kind='write_ack',request_cycle=origin,address=address))
   if iv[15] and av[2]:rq.append((cycle,av[3]));reads+=1;events.append(dict(cycle=cycle,kind='read',address=av[3],bytes=64))
   if iv[17] and av[5]:wq.append((cycle,av[6]));writes+=1;events.append(dict(cycle=cycle,kind='write',address=av[6],bytes=16))
   if iv[2] and av[1]:
    if observed_first is None:observed_first=cycle
    commands+=1;events.append(dict(cycle=cycle,kind='command',ctx=iv[3],ki=iv[5],k=iv[7]))
   if av[16]:leaf+=1;events.append(dict(cycle=cycle,kind='leaf',ctx=av[17],end=av[18]))
   if av[20]:commits+=1;events.append(dict(cycle=cycle,kind='commit',ctx=av[21],end=av[22]))
   if av[8] and iv[19]:
    observed_last=cycle;done+=1;events.append(dict(cycle=cycle,kind='done',ctx=av[9],next=av[11],error=av[13]))
 if rq or wq:raise ValueError('measurement ends with outstanding real S response')
 if observed_first!=first or observed_last!=last:raise ValueError('measurement boundary is not an actual command/done handshake')
 return dict(first_accept_cycle=first,last_done_cycle=last,accepted_to_done_cycles=last-first,
   commands=commands,read_lines=reads,write_words=writes,read_acks=len(rdelays),write_acks=len(wdelays),
   leaf_accepts=leaf,commits=commits,completions=done,
   peak_buffers=peak_buffers,peak_reads=peak_reads,peak_reservations=peak_reservations,
   read_ack_cycle_deltas=sorted(set(rdelays)),write_ack_cycle_deltas=sorted(set(wdelays)),events=events)
