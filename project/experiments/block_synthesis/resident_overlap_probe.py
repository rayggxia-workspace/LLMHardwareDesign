"""Execute commuting actor streams on unchanged native P/M/E/S RTL.

The host enforces certified partial orders and virtual channel exclusion;
actual completion handshakes release successors. This is a numeric/protocol
probe, not DMA/controller implementation or a system performance measurement.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil

from native_pointwise import execute
from resident_overlap import build,search
from resident_probe import analyse
from resident_replay import replay
from row_tile_probe import sha
from verify_resident_overlap import verify


def prepare(origin,out,*,width=8):
    analyse(origin,origin/'simulate-0.log',write_summary=False)
    old=json.loads((origin/'manifest.json').read_text());out.mkdir(parents=True,exist_ok=False)
    sources=(origin/'compile.f').read_text().splitlines()
    files=set(sources[1:])|{'p_resident_common.svh','compile.f'}
    files.update(str(f.relative_to(origin)).replace('\\','/') for f in (origin/'rtl').rglob('*.svh'))
    for name in files:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin/name,target)
    bench=(origin/'tb_resident_probe.sv').read_text()
    bench=bench.replace('for(integer i=0;i<EXTERNAL_WORDS;i=i+1)external_memory[i]=\'x;',
        "for(integer i=0;i<EXTERNAL_WORDS;i=i+1)begin external_memory[i]='x;external_valid[i]=0;end\n"
        '  for(integer i=0;i<EVENT_WORDS;i=i+1)event_done[i]=0;\n'
        '  for(integer i=0;i<2;i=i+1)channel_turn[i]=0;')
    bench=bench.replace('logic[127:0] got;\n  if(actor==0)access(1,address,external_memory[ext],got);',
        'logic[127:0] got;\n  if(!external_valid[ext])$fatal(1,"LOAD before STORE committed case=%0d",case_id);\n'
        '  if(actor==0)access(1,address,external_memory[ext],got);')
    bench=bench.replace('external_memory[ext]=got;stores=stores+1;',
        'external_memory[ext]=got;external_valid[ext]=1;stores=stores+1;')
    if 'LOAD before STORE committed' not in bench or 'channel_turn[i]=0' not in bench:
        raise ValueError('frozen probe template no longer matches')
    monitor='''
 logic external_valid[0:EXTERNAL_WORDS-1];
 logic[EVENT_WORDS-1:0] event_done=0;
 integer event_op[0:EVENT_WORDS-1],event_channel[0:EVENT_WORDS-1],event_rank[0:EVENT_WORDS-1];
 integer event_next[0:EVENT_WORDS-1],event_deps[0:EVENT_WORDS-1][0:DEPENDENCY_WORDS-1];
 integer event_dep_count[0:EVENT_WORDS-1],event_args[0:EVENT_WORDS-1][0:7],inject_event=-1;
 task automatic run_actor(input integer first);
  integer current;logic[EVENT_WORDS-1:0] mask;
  current=first;
  while(current>=0)begin
   mask=0;
   for(integer d=0;d<event_dep_count[current];d=d+1)mask[event_deps[current][d]]=1;
   wait((event_done & mask)==mask);
   if(event_channel[current]>=0)wait(channel_turn[event_channel[current]]==event_rank[current]);
   if(inject_event==current)begin event_done[current]=1;repeat(100000)@(negedge clk);end
   case(event_op[current])
    0:load_word(event_args[current][0],event_args[current][1],event_args[current][2]);
    1:store_word(event_args[current][0],event_args[current][1],event_args[current][2],event_args[current][3]);
    2:m_term(event_args[current][0],event_args[current][1],event_args[current][2],event_args[current][3],event_args[current][4],event_args[current][5],event_args[current][6]);
    3:m_final(event_args[current][0],event_args[current][1],event_args[current][2],event_args[current][3]);
    4:e_command(event_args[current][0],event_args[current][1],event_args[current][2],event_args[current][3],event_args[current][4],event_args[current][5],event_args[current][6],event_args[current][7]);
    5:check_reuse(event_args[current][0],event_args[current][1],event_args[current][2],event_args[current][3]);
    6:begin end
    default:$fatal(1,"invalid concurrent event opcode");
   endcase
   if(event_channel[current]>=0)channel_turn[event_channel[current]]=channel_turn[event_channel[current]]+1;
   event_done[current]=1;current=event_next[current];
  end
 endtask
 integer channel_turn[0:1],overlap_case_cycles=0,overlap_total_cycles=0;
 logic overlap_p=0,overlap_e=0,overlap_f=0;
 always @(posedge clk)begin
  if(reset)begin overlap_p<=0;overlap_e<=0;overlap_f<=0;overlap_case_cycles<=0;end
  else begin
   if(cmd_valid && cmd_ready)overlap_p<=1;
   if(cmd_done)overlap_p<=0;
   if(e_cmd && e_ready)overlap_e<=1;
   if(e_done)overlap_e<=0;
   if(load_valid && load_ready)overlap_f<=1;
   if(load_done)overlap_f<=0;
   if((overlap_p || overlap_f) && overlap_e)begin
    overlap_case_cycles<=overlap_case_cycles+1;
    overlap_total_cycles<=overlap_total_cycles+1;
   end
  end
 end
'''
    bench=bench.replace('endmodule',monitor+'endmodule')
    bench=bench.replace('case_count=case_count+1;',
        '$display("OVERLAP_CASE {\\"id\\":%0d,\\"native_overlap_cycles\\":%0d}",case_id,overlap_case_cycles);\n  case_count=case_count+1;')
    bench=bench.replace('$display("PASS native resident record programs");',
        'if(overlap_total_cycles<1)$fatal(1,"no native actor overlap exercised");\n'
        '  $display("OVERLAP_TOTAL %0d",overlap_total_cycles);\n  $display("PASS native resident record programs");')
    (out/'tb_resident_probe.sv').write_text(bench,newline='\n')
    vectors=[];lines=[];records=[];maxexternal=maxevents=maxdeps=0;negative=None
    def vector(value):vectors.append(value);return len(vectors)-1
    for source in old['cases']:
        # Keep every actual sample, tight-S and numeric boundary, using the
        # strongest selected residency policy rather than a weaker spill plan.
        if source['strategy']!='reuse_future_greedy':continue
        graph=source['graph'];body=source['plan'];values={(n,i):v for n,i,v in source['values']}
        replay(graph,body,values);gold=execute(source['original_graph'],values)
        actors=body['actors'];codes={n:0 if a['kind']=='M' else 1 for n,a in actors.items()}
        if sorted(codes.values())!=[0,1]:raise ValueError('probe requires independent M/E services')
        offsets=source['physical_window_offsets'];maxevents=max(maxevents,len(body['events']))
        addresses=sorted({body['zero_address']}|{o['external_address'] for o in graph['objects'].values()})
        amap={a:i for i,a in enumerate(addresses)};maxexternal=max(maxexternal,len(addresses))
        for shared_channel in (False,True):
            channels={n:0 if shared_channel else code for n,code in codes.items()};dag=build(graph,body,channels)
            greedy=min((search(dag,width=1,policy=p) for p in ('makespan','critical_path')),key=lambda s:s['makespan'])
            dp=search(dag,width=width,backbone=greedy)
            for strategy,schedule in (('strong_greedy',greedy),('backbone_dp',dp)):
                certificate=verify(graph,body,dag,schedule,channels);cid=len(records)
                lines.append(f'begin_case({cid});\n');initial={body['zero_address']:0}
                for o in graph['objects'].values():
                    if o['kind']=='produced':continue
                    word=(o['literal'] if 'literal' in o else values[(o['tensor'],o['index'])])&0xffffffff
                    address=o['external_address']
                    if address in initial and initial[address]!=word:raise ValueError('external fixture alias')
                    initial[address]=word
                for a,w in initial.items():
                    lines.append(f'external_memory[{amap[a]}]=fixture[{vector(w)}];external_valid[{amap[a]}]=1;\n')
                ranks={}
                for channel in sorted(set(channels.values())):
                    ordered=sorted((r for r in schedule['decisions'] if dag['nodes'][r['event']]['channel']==channel),key=lambda r:(r['start'],r['end']))
                    ranks.update({r['event']:rank for rank,r in enumerate(ordered)})
                lines.append(f'inject_event=-1; // NEGATIVE_CASE_{cid}\n')
                for name,stream in dag['streams'].items():
                    for si,ei in enumerate(stream):
                        e=body['events'][ei];kind=e['op'];node=dag['nodes'][ei];actor=codes[name]
                        maxdeps=max(maxdeps,len(node['deps']))
                        def at(key):return e[key]+offsets[name]
                        if kind in ('LOAD','LOAD_ZERO'):line=f"load_word({actor},{at('address')},{amap[e['external_address']]});\n"
                        elif kind in ('STORE','STORE_COMMIT'):
                            line=f"store_word({actor},{at('address')},{amap[e['external_address']]},{vector(gold[e['record']])});\n"
                        elif kind=='M_TERM':line=f"m_term({at('a')},{0 if e['reuse_b'] else at('b')},{int(e['reuse_b'])},{e['k']},{e['coefficient']},{e['scale_shift']},{int(e['clear'])});\n"
                        elif kind=='M_FINAL':line=f"m_final({at('address')},{e['width']},{e['shift']},{vector(gold[e['record']])});\n"
                        elif kind=='E':
                            args=[x+offsets[name] for x in e['inputs']]+[0]*(3-len(e['inputs']))
                            line='e_command('+','.join(map(str,[len(e['inputs']),*args,at('address'),e['opcode'],e['shift'],vector(gold[e['record']])]))+');\n'
                        elif kind=='REUSE':line=f"check_reuse({actor if e['where']=='S' else 2},{at('address') if e['where']=='S' else 0},{amap[e['external_address']] if e['where']=='external' else 0},{vector(gold[e['record']])});\n"
                        elif kind=='DISCARD':line=f'// DISCARD metadata {ei}\n'
                        else:raise ValueError('unknown concurrent event')
                        # Fail an actual consumer if a producer reports an ACK
                        # before its external STORE really completes.
                        if negative is None and not shared_channel and kind=='STORE':
                            for j,consumer in enumerate(body['events']):
                                if (consumer['op']!='LOAD' or consumer['actor']==name or ei not in dag['nodes'][j]['deps'] or
                                    consumer['external_address']!=e['external_address'] or e['external_address'] in initial):continue
                                ancestors=set();pending=[d for d in dag['nodes'][j]['deps'] if d!=ei]
                                while pending:
                                    d=pending.pop()
                                    if d==ei or d in ancestors:continue
                                    ancestors.add(d);pending.extend(dag['nodes'][d]['deps'])
                                if any(d>ei and dag['nodes'][d]['actor']==name for d in ancestors):continue
                                negative=(f'inject_event=-1; // NEGATIVE_CASE_{cid}\n',ei);break
                        if kind=='DISCARD':command='discard';args=[]
                        else:
                            match=re.fullmatch(r'(\w+)\((.*)\);\n',line)
                            if not match:raise ValueError('event arguments no longer match dispatch ABI')
                            command=match[1];args=[int(x) for x in match[2].split(',')]
                        opcode={'load_word':0,'store_word':1,'m_term':2,'m_final':3,'e_command':4,'check_reuse':5,'discard':6}[command]
                        lines.append(f'event_op[{ei}]={opcode};event_next[{ei}]={stream[si+1] if si+1<len(stream) else -1};'
                            f"event_channel[{ei}]={node['channel'] if node['channel'] is not None else -1};event_rank[{ei}]={ranks.get(ei,-1)};"
                            f"event_dep_count[{ei}]={len(node['deps'])};\n")
                        for di,dep in enumerate(node['deps']):lines.append(f'event_deps[{ei}][{di}]={dep};\n')
                        for ai,arg in enumerate(args):lines.append(f'event_args[{ei}][{ai}]={arg};\n')
                lines.append('fork\n'+''.join(f'run_actor({stream[0] if stream else -1});\n' for stream in dag['streams'].values())+'join\n')
                for i in range(len(body['events'])):lines.append(f'if(!event_done[{i}])$fatal(1,"event completion lost");\n')
                for _,record in source['original_graph']['live_out'].items():
                    lines.append(f"check_commit({amap[graph['objects'][record]['external_address']]},{vector(gold[record])});\n")
                work=Counter(e['op'] for e in body['events']);expected={'loads':body['external_load_words'],
                    'stores':body['external_store_words'],'m':work['M_FINAL'],'e':work['E']}
                lines.append('end_case('+','.join(map(str,expected.values()))+');\n')
                records.append({'id':cid,'description':source['description'],'strategy':strategy,'source_case':source['id'],
                    'graph':graph,'original_graph':source['original_graph'],'values':source['values'],'plan':body,
                    'expected':expected,'physical_window_offsets':offsets,'channel_by_actor':channels,
                    'dag':dag,'schedule':schedule,'certificate':certificate})
    if negative is None:raise ValueError('no executable cross-actor early-ACK negative found')
    cases=''.join(lines);(out/'cases.svh').write_text(cases,newline='\n');marker,ei=negative
    if cases.count(marker)!=1:raise ValueError('ambiguous early-ACK marker')
    (out/'negative-ack.svh').write_text(cases.replace(marker,f'inject_event={ei}; // actual early-ACK injection\n',1),newline='\n')
    (out/'tb_negative_ack.sv').write_text(bench.replace('`include "cases.svh"','`include "negative-ack.svh"'),newline='\n')
    (out/'vectors.hex').write_text(''.join(f'{v:032x}\n' for v in vectors),newline='\n')
    (out/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(vectors)},EXTERNAL_WORDS={maxexternal},CASE_COUNT={len(records)},EVENT_WORDS={maxevents},DEPENDENCY_WORDS={max(1,maxdeps)};\n',newline='\n')
    for name in ('resident_overlap_probe.py','resident_overlap.py','verify_resident_overlap.py'):
        shutil.copyfile(Path(__file__).parent/name,out/('overlap-generator-'+name))
    manifest={'kind':'native-resident-record-v1','cases':records,'origin_timing':old['origin_timing'],
        'origin_manifest_sha256':sha(origin/'manifest.json'),'native_rtl_sha256':{name:sha(out/name) for name in sources[1:]},
        'scope':'same native commands/finite SRAM addresses/ACK; concurrent independent actor streams, actual boundary values and S32 edge cases',
        'excluded':'MC/LC/DMA execution, system/physical/SystemC/energy/token/s; channel model is host-enforced, not DMA RTL',
        'cycles':'observer reads and held responses included; concurrent probe cycles are not calibrated performance'}
    manifest['sha256']={f.relative_to(out).as_posix():sha(f) for f in out.rglob('*') if f.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    print(json.dumps({'cases':len(records),'negative_event':ei,'manifest_sha256':sha(out/'manifest.json')}))


def analyse_overlap(directory,log):
    report=analyse(directory,log,write_summary=False);raw=log.read_bytes()
    rows=[json.loads(m) for m in re.findall(rb'OVERLAP_CASE (\{[^\r\n]*\})',raw)]
    if [r['id'] for r in rows]!=list(range(report['cases'])):raise ValueError('concurrent monitor coverage differs')
    total=re.findall(rb'OVERLAP_TOTAL (\d+)',raw)
    if len(total)!=1 or int(total[0])!=sum(r['native_overlap_cycles'] for r in rows) or int(total[0])<1:
        raise ValueError('no verified native actor overlap')
    return {**report,'overlap_records':rows,'native_overlap_cycles':int(total[0])}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('origin',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--width',type=int,default=8);a=p.parse_args();prepare(a.origin,a.output,width=a.width)
