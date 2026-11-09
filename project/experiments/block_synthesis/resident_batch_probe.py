"""Run complete finite-S row programs on frozen native P/M/E/feeder/S RTL.

The host moves whole external words only. No host arithmetic, packing,
local copying or invented path implements any compiler operation.
"""
import hashlib,json,re,shutil
from pathlib import Path
from verify_resident_batch import replay


def sha(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def prepare(origin,programfile,output,strategies):
    origin=Path(origin);output=Path(output);data=json.loads(Path(programfile).read_text());tile=data['tile']
    old=json.loads((origin/'manifest.json').read_text());sources=(origin/'compile.f').read_text().splitlines()
    output.mkdir(exist_ok=False)
    files=set(sources[1:])|{'compile.f','p_resident_common.svh'}
    files.update(p.relative_to(origin).as_posix() for p in (origin/'rtl').rglob('*.svh'))
    for name in files:
        if sha(origin/name)!=old['sha256'][name]:raise ValueError('frozen program RTL changed: '+name)
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin/name,target)
    bench=(Path(__file__).parent/'tb_resident_probe.sv').read_text()
    bench=bench.replace('if(pattern<0 || pattern>2)','if(pattern<0 || pattern>3)')
    bench=bench.replace('if($value$plusargs("sinit=%d",pattern))begin',
        'if($value$plusargs("sinit=%d",pattern))begin\n    $display("BATCH_INIT bank=%0d pattern=%0d",bank,pattern);')
    bench=bench.replace('dut.store.storage.banks[bank].memory.mem[wi]=seed;',
        "if(pattern==3)seed='x;\n     dut.store.storage.banks[bank].memory.mem[wi]=seed;")
    bench=bench.replace("for(integer i=0;i<EXTERNAL_WORDS;i=i+1)external_memory[i]='x;",
        "for(integer i=0;i<EXTERNAL_WORDS;i=i+1)begin external_memory[i]='x;external_valid[i]=0;end")
    bench=bench.replace('if(actor==0)access(1,address,external_memory[ext],got);',
        'if(!external_valid[ext])$fatal(1,"batch LOAD before STORE ACK");\n  if(actor==0)access(1,address,external_memory[ext],got);')
    bench=bench.replace('external_memory[ext]=got;stores=stores+1;','external_memory[ext]=got;external_valid[ext]=1;stores=stores+1;')
    extra='''
 logic external_valid[0:EXTERNAL_WORDS-1];
 integer event_op[0:EVENT_WORDS-1],event_args[0:EVENT_WORDS-1][0:7];
 task automatic m_term_row(input integer nr,input integer abase,input integer bbase,input bit reuse_weight,
  input integer k,input integer coefficient,input integer shift,input bit clear);
  logic[127:0] got;
  rows=4'(nr);load_a_address=10'(abase);load_b_address=10'(bbase);feed(reuse_weight);
  command(4,0,64'(coefficient&65535)|(64'(shift)<<16),0,0,got);
  command(10,0,(64'(nr)<<15)|64'h1103|(64'(k)<<4)|(clear?64'd4:64'd0),0,0,got);
 endtask
 task automatic m_final_row(input integer nr,input integer rr,input integer dst,input integer width,input integer shift,input integer expected);
  logic[127:0] got,stored;
  rows=4'(nr);
  command(5,($test$plusargs("badrow")?0:rr)<<3,(width==16?64'h100:64'h200)|64'(shift),1,dst,got);
  if(got!==fixture[expected])$fatal(1,"resident M result mismatch case=%0d row=%0d",case_id,rr);
  access(0,dst,0,stored);if(stored!==fixture[expected])$fatal(1,"batch M SRAM/ACK mismatch");
  native_m=native_m+1;
 endtask
 task automatic run_events(input integer first,input integer last);
  for(integer ei=first;ei<last;ei=ei+1)begin
   case(event_op[ei])
    0:load_word(event_args[ei][0],event_args[ei][1],event_args[ei][2]);
    1:store_word(event_args[ei][0],event_args[ei][1],event_args[ei][2],event_args[ei][3]);
    2:m_term_row(event_args[ei][0],event_args[ei][1],event_args[ei][2],event_args[ei][3],event_args[ei][4],event_args[ei][5],event_args[ei][6],event_args[ei][7]);
    3:m_final_row(event_args[ei][0],event_args[ei][1],event_args[ei][2],event_args[ei][3],event_args[ei][4],event_args[ei][5]);
    4:e_command(event_args[ei][0],event_args[ei][1],event_args[ei][2],event_args[ei][3],event_args[ei][4],event_args[ei][5],event_args[ei][6],event_args[ei][7]);
    default:$fatal(1,"unknown batch event");
   endcase
  end
 endtask
 task automatic check_commit(input integer address,input integer expected);
  if(!external_valid[address] || external_memory[address]!==fixture[expected])$fatal(1,"batch output commit mismatch");
 endtask
'''
    monitor='''
 integer issue_cycles=0,active_slots=0,native_nonidle=0;
 always @(posedge clk)begin
  if(!reset)begin
   if(dut.multiply.state!=0)native_nonidle=native_nonidle+1;
   if(dut.multiply.state==1)begin
    issue_cycles=issue_cycles+1;
    active_slots=active_slots+int'(dut.multiply.active_n)*
     ((int'(dut.multiply.issue_tile)+1<int'(dut.multiply.tiles))?8:int'(dut.multiply.last_k));
   end
  end
 end
'''
    bench=bench.replace('case_id=id;loads=0;', 'issue_cycles=0;active_slots=0;native_nonidle=0;case_id=id;loads=0;')
    bench=bench.replace('case_count=case_count+1;',
        '$display("BATCH_UTIL {\\"id\\":%0d,\\"issue_cycles\\":%0d,\\"active_digit_slots\\":%0d,\\"issue_capacity\\":%0d,\\"native_nonidle\\":%0d}",case_id,issue_cycles,active_slots,64*issue_cycles,native_nonidle);\n  case_count=case_count+1;')
    bench=bench.replace('endmodule',extra+monitor+'\nendmodule');(output/'tb_resident_probe.sv').write_text(bench,newline='\n')
    addresses=sorted({o['external_address'] for o in tile['graph']['objects'].values()}|
        {c['external_address'] for c in tile['graph']['external_commits']}|
        {data['programs'][n]['zero_address'] for n in strategies});amap={a:i for i,a in enumerate(addresses)}
    vectors=[];indices={};lines=[];cases=[];event_index=0
    def vector(v):
        if v not in indices:indices[v]=len(vectors);vectors.append(v)
        return indices[v]
    for trial,fixture in enumerate(data['fixtures']):
        values={(n,i):v for n,i,v in fixture['inputs']}
        for name in strategies:
            p=data['programs'][name];gold=replay(tile,p,values)['observed_native_outputs']
            for relative,want in p['scalar_timing']['rtl_sha256'].items():
                if relative.startswith('rtl/') and sha(output/relative)!=want:raise ValueError('program scalar RTL differs: '+relative)
            codes={n:0 if a['kind']=='M' else 1 for n,a in p['actors'].items()}
            if sorted(codes.values())!=[0,1]:raise ValueError('native probe needs one independent M and E actor')
            cid=len(cases);lines.append(f'begin_case({cid});\n');initial={p['zero_address']:0}
            for key,o in tile['graph']['objects'].items():
                if o['kind']=='produced':continue
                v=(o['literal'] if 'literal' in o else values[(o['tensor'],o['index'])])&0xffffffff
                oldvalue=initial.setdefault(o['external_address'],v)
                if oldvalue!=v:raise ValueError('batch external source alias')
            for address,value in initial.items():lines.append(f'external_memory[{amap[address]}]=fixture[{vector(value)}];external_valid[{amap[address]}]=1;\n')
            start=event_index;counts={'loads':0,'stores':0,'m':0,'e':0}
            for e in p['events']:
                kind=e['op'];actor=codes[e['actor']]
                if kind in ('LOAD','LOAD_ZERO'):op=0;args=[actor,e['address'],amap[e['external_address']]];counts['loads']+=1
                elif kind in ('STORE','STORE_COMMIT'):op=1;args=[actor,e['address'],amap[e['external_address']],vector(gold[e['record']])];counts['stores']+=1
                elif kind=='ROW_M_TERM':op=2;args=[e['rows'],e['a'],0 if e['reuse_b'] else e['b'],int(e['reuse_b']),e['k'],e['coefficient'],e['scale_shift'],int(e['clear'])]
                elif kind=='ROW_M_FINAL':op=3;args=[e['rows'],e['row'],e['address'],e['width'],e['shift'],vector(gold[e['record']])];counts['m']+=1
                elif kind=='E':op=4;args=[len(e['inputs']),*(e['inputs']+[0]*(3-len(e['inputs']))),e['address'],e['opcode'],e['shift'],vector(gold[e['record']])];counts['e']+=1
                else:raise ValueError('unqualified batch event')
                lines.append(f'event_op[{event_index}]={op};'+''.join(f'event_args[{event_index}][{j}]={v};' for j,v in enumerate(args))+'\n');event_index+=1
            lines.append(f'run_events({start},{event_index});\n')
            for c in tile['graph']['external_commits']:lines.append(f"check_commit({amap[c['external_address']]},{vector(gold[c['record']])});\n")
            lines.append('end_case('+','.join(str(counts[k]) for k in ('loads','stores','m','e'))+');\n')
            cases.append({'id':cid,'trial':trial,'strategy':name,'expected':counts})
    (output/'cases.svh').write_text(''.join(lines),newline='\n')
    (output/'vectors.hex').write_text(''.join(f'{v:032x}\n' for v in vectors),newline='\n')
    (output/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(vectors)},EXTERNAL_WORDS={len(addresses)},CASE_COUNT={len(cases)},EVENT_WORDS={event_index};\n',newline='\n')
    shutil.copyfile(programfile,output/'programs.json');shutil.copyfile(__file__,output/Path(__file__).name)
    m={'kind':'native-finite-row-program-v1','cases':cases,'source_program_sha256':sha(programfile),
        'scope':'actual native M/E/feeder and two finite SRAMs; host full-word external transactions and observer cycles, not MC/LC/DMA/system timing'}
    m['sha256']={p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()}
    (output/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m


def analyse(directory,log,state):
    directory=Path(directory);m=json.loads((directory/'manifest.json').read_text())
    for name,want in m['sha256'].items():
        if sha(directory/name)!=want:raise ValueError('batch program input changed: '+name)
    raw=Path(log).read_bytes()
    if raw.count(b'PASS native resident record programs')!=1 or b'FATAL' in raw:raise ValueError('native batch program did not pass')
    modes=[x for x in raw.splitlines() if x.startswith(b'BATCH_INIT ')]
    if sorted(modes)!=[f'BATCH_INIT bank={bank} pattern={state}'.encode() for bank in range(4)]:raise ValueError('batch SRAM state differs')
    rows=[json.loads(v) for v in re.findall(rb'RESIDENT_CASE (\{[^\r\n]*\})',raw)]
    if len(rows)!=len(m['cases']):raise ValueError('batch program case coverage differs')
    for expected,actual in zip(m['cases'],rows):
        if actual['id']!=expected['id'] or actual['cycles']<1 or any(actual[k]!=v for k,v in expected['expected'].items()):raise ValueError('batch program counts differ')
    utilization=[json.loads(v) for v in re.findall(rb'BATCH_UTIL (\{[^\r\n]*\})',raw)]
    if b'BATCH_UTIL ' in (directory/'tb_resident_probe.sv').read_bytes() and len(utilization)!=len(rows):
        raise ValueError('passive native utilization coverage missing')
    if utilization and ([v['id'] for v in utilization]!=list(range(len(rows))) or
        any(v['issue_cycles']<1 or not 0<v['active_digit_slots']<=v['issue_capacity'] or v['issue_capacity']!=64*v['issue_cycles'] for v in utilization)):
        raise ValueError('invalid passive native utilization counters')
    return {'passed':True,'cases':len(rows),'state':state,'records':rows,'utilization':utilization,
        'utilization_scope':'requested digit-product slots / 64 slots during ISSUE only; not whole-chip utilization, switching activity or calibrated performance',
        'log_sha256':sha(log),'manifest_sha256':sha(directory/'manifest.json'),'scope':m['scope']}
