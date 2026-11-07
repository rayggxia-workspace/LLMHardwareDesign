"""Compile real leaf recipes and generate their native numerical replay.

Not an LLM benchmark: this integration case verifies the compiler's commands,
layouts and dependencies. Copy timing uses the PR182 virtual interface, and
the schedule/address checker is separate from the macro numerical replay.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from leaf_catalog import read_profiles, inventory, duration
from memory import profile_from_source
from numeric import Format, pack
from run import compile_model


def write(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def model_and_data():
    f={'bits':16,'exponent':-10,'lanes':2}
    dimensions={'x':[1,8],'gamma':[8],'normalized':[1,8],'w':[8,4],
                'projected':[1,4],'activated':[1,4],'residual':[1,4],'sum':[1,4],'out':[1,4]}
    values={n:{'shape':dims,'format':deepcopy(f)} for n,dims in dimensions.items()}
    values['epsilon']={'shape':[],'format':{'bits':32,'exponent':0,'lanes':1}}
    fixed={'old':[128,2],'rx':[2],'next':[128,2],'ry':[2]}
    for n,dims in fixed.items(): values[n]={'shape':dims,'format':{'bits':32,'exponent':-16,'lanes':2}}
    for n in ('key','query'): values[n]={'shape':[128],'format':{'bits':16,'exponent':-14,'lanes':8}}
    values['params']={'shape':[2],'format':{'bits':32,'exponent':-31,'lanes':2,'unsigned':True}}
    values['small']={'shape':[2],'format':deepcopy(f)}
    ops=[('norm','RMSNorm',['x','gamma','epsilon'],['normalized']),
         ('project','MatMul',['normalized','w'],['projected']),
         ('act','SiLU',['projected'],['activated']),
         ('add','Add',['activated','residual'],['sum']),('finish','Handoff',['sum'],['out']),
         ('recurrent','GDNUpdate',['old','key','query','rx','params'],['next','ry']),
         ('narrow','Requantize',['ry'],['small'])]
    m={'tasks':[{'id':tid,'op':op,'numeric':'native typed records','inputs':a,'outputs':b} for tid,op,a,b in ops],
       'values':values,'outputs':['out','next','small'],'weights':['w'],
       'source':'actual native integration case; not a parameter-count LLM benchmark'}
    data={'x':[1024]*8,'gamma':[1024]*8,'epsilon':[1],
          'w':[(k+1)*(c+1)*16 for k in range(8) for c in range(4)],
          'residual':[10,-20,30,-40], 'old':[(r+1)*(c+1)-128 for r in range(128) for c in range(2)],
          'rx':[800,-900],'key':[(r%13)-6 for r in range(128)],
          'query':[(r%17)-8 for r in range(128)],'params':[1<<31,1<<30]}
    return m,data


def generate_replay(model,data,result):
    g,h,p=result['graph'],result['resolved_hardware'],result['plan']
    q=json.dumps
    lines=['#include <map>','#include <memory>',
      'using NativeWord=std::array<uint32_t,4>;using Buffer=std::vector<NativeWord>;',
      'static NativeWord lanes16(const blocks::Reply& r){NativeWord w{};for(unsigned i=0;i<r.count;++i)w[i/2]|=uint32_t(uint16_t(r.lane[i]))<<(16*(i%2));return w;}',
      'static NativeWord lanes32(const blocks::Reply& r){NativeWord w{};for(unsigned i=0;i<4;++i)w[i]=uint32_t(r.lane[i]);return w;}',
      'static std::array<int16_t,8> raw16(const Buffer& b){std::array<int16_t,8> a{};if(!b.empty())for(unsigned i=0;i<8;++i)a[i]=int16_t(b[0][i/2]>>(16*(i%2)));return a;}',
      'template<class D> static D& engine(std::map<std::string,std::unique_ptr<D>>& engines,const std::string& id){auto& p=engines[id];if(!p)p=std::make_unique<D>();return *p;}',
      'void replay_generated_plan(){std::map<std::string,Buffer> values;',
      'std::map<std::string,std::unique_ptr<layer::Matrix>> matrices;',
      'std::map<std::string,std::unique_ptr<layer::Normalizer>> norms;',
      'std::map<std::string,std::unique_ptr<layer::Activation>> activations;',
      'std::map<std::string,std::unique_ptr<Compact>> vectors;',
      'std::map<std::string,std::unique_ptr<TiledRecurrent>> recurrent;',
      'std::map<std::string,std::unique_ptr<Handoff>> handoffs;']
    def literal(words):
        return '{'+','.join('NativeWord{'+','.join(str((w>>(32*i))&0xffffffff)+'u' for i in range(4))+'}' for w in words)+'}'
    for name,v in g['values'].items():
        if 'producer' in v: continue
        if 'offline_layout' in v:
            layout=v['offline_layout']; raw=[0]*64
            for c in range(layout['columns']):
                for k in range(layout['k_valid']):
                    raw[c*8+k]=data[v['tensor']][(layout['k']+k)*layout['matrix_shape'][1]+layout['column']+c]
            words=pack(raw,Format(16,model['values'][v['tensor']]['format']['exponent'],8))
        else:
            raw=data[v['tensor']][v['offset_elements']:v['offset_elements']+v['valid_elements']]
            words=pack(raw,Format.read(v['format']))
        if len(words)!=v['words']: raise ValueError('input layout extent differs')
        lines.append('values['+q(name)+']='+literal(words)+';')
    for task in sorted(g['tasks'],key=lambda t:(p['tasks'][t['id']]['start'],t['id'])):
        service=h['services'][p['tasks'][task['id']]['service']]
        instance=p['tasks'][task['id']]['service'].split(':')[0]
        macro=instance.rsplit('.',1)[1]
        lines.append('{ // '+task['id'])
        for i,name in enumerate(task['inputs']): lines.append(f'const Buffer& a{i}=values.at({q(name)});')
        for i,_ in enumerate(task['outputs']): lines.append(f'Buffer out{i};')
        if macro=='M':
            lines.append('auto& unit=engine(matrices,'+q(instance)+');')
            for command in service['native_program']:
                op=command['command']; lines.append('{MCommand c;')
                lines.append('c.op=MCommand::Op::'+op+';')
                if op.startswith('Load'):
                    source='a0' if op=='LoadA' else 'a1'
                    start=command.get('word_offset',0)
                    count=1 if op=='LoadA' else 4
                    lines.append(f'for(unsigned i=0;i<{count};++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t({source}.at({start}+i)[j])<<(32*(j%2));')
                    lines.append('c.wide_a=c.wide_b=true;')
                    if op=='LoadB':lines.append(f'c.half={command["half"]};')
                elif op=='Execute':
                    lines.append(f'c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns={command["columns"]};c.last_k={command["k"]};c.clear={str(command["clear"]).lower()};')
                elif op=='ReadFinal':lines.append(f'c.half={command["half"]};c.width=16;c.shift={command["shift"]};')
                elif op=='Scale':lines.append('c.coefficient=1;c.shift=0;')
                lines.append('auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");')
                if op=='ReadFinal':lines.append('out0.push_back(lanes32(reply));')
                lines.append('}')
        elif macro=='E':
            command=service['native_program'][0]
            lines.append('auto& unit=engine(vectors,'+q(instance)+');')
            args=','.join('raw16(a'+str(i)+')' for i in range(len(task['inputs'])))
            lines.append(f'out0.push_back(lanes16(unit.execute({command["op"]},{command["shift"]},{args})));')
        elif macro=='G':
            command=service['native_program'][0]
            lines.append('auto& unit=engine(activations,'+q(instance)+');GCommand c;')
            lines.append(f'c.function=GCommand::Function({command["function"]});c.gated={str(command["gated"]).lower()};')
            lines.append('auto x=raw16(a0);for(unsigned i=0;i<2;++i)c.x[i]=x[i];')
            if command['gated']:lines.append('auto b=raw16(a1);for(unsigned i=0;i<2;++i)c.gate[i]=b[i];')
            lines.append('out0.push_back(lanes16(unit.execute(c)));')
        elif macro=='N':
            command=service['native_program'][0]
            lines.append('auto& unit=engine(norms,'+q(instance)+');NCommand c;')
            lines.append(f'c.op=NCommand::Op({command["op"]});c.mode=NCommand::Mode({command["mode"]});c.count={command["count"]};')
            if command['op']==0 and task['inputs']:lines.append('c.epsilon=a0.at(0)[0];')
            elif task['inputs']:
                lines.append('auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);')
                if command['op']==5:lines.append('c.gamma=raw16(a1);')
            lines.append('auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");')
            if task['outputs']:lines.append('out0.push_back(lanes16(reply));')
        elif macro=='R':
            command=service['native_program'][0]; op=command['command']
            lines.append('auto& unit=engine(recurrent,'+q(instance)+');')
            if op in ('R_PREDICT','R_UPDATE'):
                n,cols=command['rows'],command['columns']; stride=(cols+3)//4
                lines.append(f'TiledRecurrent::State state({n});for(unsigned r=0;r<{n};++r)for(unsigned c=0;c<{cols};++c)state[r][c]=int32_t(a0.at(r*{stride}+c/4)[c%4]);')
                lines.append(f'std::vector<int16_t> key({n});for(unsigned r=0;r<{n};++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));')
                if op=='R_PREDICT':lines.append(f'auto next=unit.predict(state,key,a2.at(0)[0],{str(command["clear_dot"]).lower()});')
                else:
                    lines.append(f'std::vector<int16_t> query({n});for(unsigned r=0;r<{n};++r)query[r]=int16_t(a2.at(r/8)[(r%8)/2]>>(16*(r%2)));')
                    lines.append(f'auto next=unit.update(state,key,query,{str(command["clear_dot"]).lower()});')
                lines.append(f'for(unsigned r=0;r<{n};++r)for(unsigned half=0;half<{stride};++half){{NativeWord word{{}};for(unsigned i=0;i<4&&half*4+i<{cols};++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}}')
            elif op=='R_BEGIN':lines.append('unit.pass(7);')
            elif op=='R_ERROR':
                count=g['values'][task['inputs'][0]]['valid_elements']
                lines.append(f'std::array<int32_t,8> x{{}};for(unsigned i=0;i<{count};++i)x[i]=int32_t(a0.at(i/4)[i%4]);unit.error(x,a1.at(0)[1]);')
            elif op=='R_FINISH':
                count=g['values'][task['outputs'][0]]['valid_elements']
                lines.append(f'auto x=unit.pass(5);for(unsigned half=0;half<{(count+3)//4};++half){{NativeWord word{{}};for(unsigned i=0;i<4&&half*4+i<{count};++i)word[i]=uint32_t(x[half*4+i]);out0.push_back(word);}}')
        elif macro=='T':lines.append('out0=engine(handoffs,'+q(instance)+').transfer(a0);')
        else:raise ValueError('unknown native replay macro')
        for i,name in enumerate(task['outputs']):
            lines.append(f'layer::require(out{i}.size()=={g["values"][name]["words"]},"generated output extent");values[{q(name)}]=out{i};')
        lines.append('}')
    # Separate, whole-operator numerical references, not the generated recipe.
    lines.extend(['NEngine nref;NCommand nc;nc.mode=NCommand::Mode::RMS;nc.epsilon=1;nref.execute(nc);',
       'nc.op=NCommand::Op::Stats;nc.count=8;nc.data.fill(1024);nref.execute(nc);',
       'nc.op=NCommand::Op::Finalize;nref.execute(nc);nc.op=NCommand::Op::NormReplay;nc.gamma.fill(1024);auto normalized=nref.execute(nc);',
       'std::array<int16_t,4> projected{};for(unsigned c=0;c<4;++c){blocks::Wide sum=0;for(unsigned k=0;k<8;++k)sum+=normalized.lane[k]*int((k+1)*(c+1)*16);projected[c]=int16_t(blocks::rne(sum,10));}',
       'std::array<int16_t,4> expected{};GEngine gref;const int residual[4]={10,-20,30,-40};',
       'for(unsigned p=0;p<2;++p){GCommand gc;gc.x={projected[p*2],projected[p*2+1]};auto r=gref.execute(gc);for(unsigned i=0;i<2;++i)expected[p*2+i]=int16_t(r.lane[i]+residual[p*2+i]);}',
       'REngine rref;RCommand rc;rc.op=RCommand::Op::Open;rc.length=128;rref.execute(rc);',
       'for(unsigned row=0;row<128;++row){rc=RCommand{};rc.op=RCommand::Op::StateRow;rc.index=row;rc.values[0]=int32_t(row+1)-128;rc.values[1]=int32_t((row+1)*2)-128;rref.execute(rc);rc.op=RCommand::Op::Key;rc.coefficients[0]=int16_t(int(row%13)-6);rref.execute(rc);rc.op=RCommand::Op::Query;rc.coefficients[0]=int16_t(int(row%17)-8);rref.execute(rc);}',
       'rc=RCommand{};rc.op=RCommand::Op::X;rc.values[0]=800;rc.values[1]=-900;rref.execute(rc);',
       'rc=RCommand{};rc.op=RCommand::Op::Parameters;rc.decay=0x80000000;rc.beta=0x40000000;rref.execute(rc);',
       'rc=RCommand{};rc.op=RCommand::Op::Execute;layer::require(!rref.execute(rc).error,"whole R oracle");rc.op=RCommand::Op::ReadOutput;auto ry=rref.execute(rc);rc.op=RCommand::Op::Commit;rref.execute(rc);'])
    for name in g['outputs']:
        value=g['values'][name]; tensor=value['tensor']; offset=value['offset_elements']; count=value['valid_elements']
        if tensor=='out':
            lines.append(f'for(unsigned i=0;i<{count};++i)layer::require(int16_t(values.at({q(name)}).at(0)[i/2]>>(16*(i%2)))==expected[{offset}+i],"whole mixed output");')
        elif tensor=='small':
            lines.append(f'for(unsigned i=0;i<{count};++i)layer::require(int16_t(values.at({q(name)}).at(0)[i/2]>>(16*(i%2)))==int16_t(blocks::rne(ry.lane[i],6)),"whole R converted output");')
        elif tensor=='next':
            lines.append(f'for(unsigned row=0;row<{count//2};++row){{rc=RCommand{{}};rc.op=RCommand::Op::ReadState;rc.index={offset//2}+row;auto state=rref.execute(rc);for(unsigned i=0;i<2;++i)layer::require(int32_t(values.at({q(name)}).at(row)[i])==state.lane[i],"whole next state");}}')
    lines.append(f'std::cout<<"GENERATED_NATIVE_PLAN_PASS tasks={len(g["tasks"])} outputs={len(g["outputs"])}\\n";}}')
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('probe',type=Path);parser.add_argument('sio',type=Path)
    parser.add_argument('qualification',type=Path);parser.add_argument('memory_source',type=Path)
    parser.add_argument('output',type=Path)
    a=parser.parse_args();a.output.mkdir(exist_ok=False)
    logs=[(a.probe/f'native-{i}.log').read_text()+(a.sio/f'native-{i}.log').read_text() for i in range(3)]
    if any('NATIVE_S_IO_PASS' not in log for log in logs): raise ValueError('SRAM measurement missing')
    profile=read_profiles(logs)
    source=a.qualification/'source/project/rtl/s_sram/local_s_base.sv'
    capacity=1<<(int(re.search(r'\[(\d+):0\]\s+req_addr',source.read_text()).group(1))+1)
    hardware={'external':'MEM','sites':{},'resources':{},'services':{},'nets':{},'routes':{},
              'virtual_memory':profile_from_source(a.memory_source.read_text())}
    groups={}
    for i,(name,macros) in enumerate((('P0',['M','G']),('U0',['N','E']),('C0',['R','G','E']),('F0',['G','E']),('J0',['E','T']))):
        groups[name]={'site':name+'.S','words':capacity,'macros':macros,'memory_group':i,
            'io_resource':name+'.S.IO','io_read_ticks':duration(profile,'S_IO',p=int(name=='P0'),write=0),
            'io_write_ticks':duration(profile,'S_IO',p=int(name=='P0'),write=1)}
        if name=='P0':groups[name]['operations']={'G':['GatedSiLU']}
    hardware=inventory(hardware,profile,groups)
    model,data=model_and_data()
    result=compile_model(model,hardware,seconds=3,rounds=2,cover_limit=1,workers=1)
    if result['status']!='planned':raise ValueError(result)
    for name,obj in [('input-model',model),('input-hardware',hardware),('result',result)]:write(a.output/(name+'.json'),obj)
    (a.output/'generated_plan.hpp').write_text(generate_replay(model,data,result))
    summary={'tasks':len(result['graph']['tasks']),'state_groups':len(result['graph']['state_groups']),
        'model_ticks':result['plan']['makespan'],'external_words':result['plan']['external_words'],
        'services_by_instance':sorted({r['service'].split(':')[0] for r in result['plan']['tasks'].values()}),
        'all_private_s_bytes':capacity*16,'static_preconnections':0,'verification':result['verification'],
        'scope':'native primitive functional replay; composed compute/S IO timing; virtual PR182 copies; no full LLM claim'}
    write(a.output/'summary.json',summary)
    print(json.dumps(summary))


if __name__=='__main__':main()
