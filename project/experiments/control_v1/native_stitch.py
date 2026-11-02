"""Join complete native RC networks at real ports without overwriting peer access.

The zero-upper mode is a diagnostic. It retains every original native resistor,
ground/coupling entry and physical pin. Its ideal joins cannot grant qualification.
"""
import collections,hashlib,json,re,shutil
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unescape(s):return re.sub(r'\\(.)',r'\1',s)

def stitch(manifest,graph,out):
    assert graph['passed'] and graph['no_unassigned_active_logic']
    ids={};names=[];bindings={};boundaries={};counters=collections.Counter();aliases={}
    expected=set();seen=set();statistics=collections.Counter();source_files={}
    def intern(name):
        if name not in ids:ids[name]=len(names)+1;names.append(name)
        return '*'+str(ids[name])
    def node(final,key):
        identity=(final,key)
        if identity not in aliases:counters[final]+=1;aliases[identity]=intern(final)+':'+str(counters[final])
        return aliases[identity]
    for bit,row in graph['connections'].items():
        final='net_'+bit
        boundaries[final]=dict(total=0.,connections={},caps=[],resistors=[],ports=[])
        for end in [row['driver'],*row['sinks']]:
            if end['instance']!='TOP':
                key=(end['instance'],end['pin']);assert key not in bindings
                bindings[key]=final;expected.add(key)
            else:
                direction='I' if end['direction']=='output' else 'O'
                pin=intern(end['pin']);boundaries[final]['connections'][pin]=f'*P {pin} {direction}'
                boundaries[final]['ports'].append(pin)
    body=out/'stitched-body.tmp'
    with body.open('w') as stream:
        def emit(final,part):
            stream.write('*D_NET '+intern(final)+' '+format(part['total'],'.12g')+'\n*CONN\n')
            for line in part['connections'].values():stream.write(line+'\n')
            stream.write('*CAP\n')
            for index,line in enumerate(part['caps'],1):stream.write(str(index)+' '+line+'\n')
            stream.write('*RES\n')
            for index,line in enumerate(part['resistors'],1):stream.write(str(index)+' '+line+'\n')
            stream.write('*END\n\n')
        for instance,top in graph['instances'].items():
            entry=manifest['leaves'][top]['final_files']['6_final.spef'];path=Path(entry['path'])
            assert sha(path)==entry['sha256'];source_files[str(path)]=entry['sha256']
            text=path.read_text();assert '*C_UNIT 1 PF' in text and '*R_UNIT 1 OHM' in text
            mapping=dict(re.findall(r'^\*(\d+) ([^\n]+)$',text.split('*D_NET',1)[0],re.M))
            mapping={k:v.strip() for k,v in mapping.items()};assert mapping
            reverse={unescape(value):key for key,value in mapping.items()}
            def parts(token,port=False):
                match=re.fullmatch(r'\*(\d+)(?::(.+))?',token)
                if match:return match.groups()
                decoded=unescape(token)
                if decoded in reverse:return reverse[decoded],None
                if port:
                    key='literal-port:'+decoded;mapping[key]=token;reverse[decoded]=key
                    return key,None
                base,separator,suffix=decoded.rpartition(':')
                assert separator and base in reverse,('Unresolved literal native SPEF node',instance,token)
                return reverse[base],suffix
            sections=list(re.finditer(r'^\*D_NET (\*\d+) ([^\n]+)\n(.*?)^\*END\s*$',text,re.M|re.S))
            assert sections
            renames={};port_ids=set();port_parents={}
            for section in sections:
                net_id=section[1][1:];targets=set()
                for p in re.finditer(r'^\*P (\S+) ([IOB])(?: .*)?$',section[3],re.M):
                    port_id,suffix=parts(p[1],port=True);assert suffix is None
                    assert port_id not in port_parents or port_parents[port_id]==net_id
                    port_parents[port_id]=net_id
                    port_ids.add(port_id);key=(instance,unescape(mapping[port_id]))
                    if key in bindings:targets.add(bindings[key]);assert key not in seen;seen.add(key)
                assert len(targets)<=1,('Native port aliases cross distinct boundary nets',instance,net_id,targets)
                renames[net_id]=next(iter(targets)) if targets else instance+'/'+mapping[net_id]
            for port_id,parent in port_parents.items():
                if port_id in renames:assert renames[port_id]==renames[parent]
                else:renames[port_id]=renames[parent]
            def resolve(token):
                old,suffix=parts(token);assert old in mapping
                if suffix is not None and not suffix.isdigit():return intern(instance+'/'+mapping[old])+':'+suffix
                assert old in renames,('No native net for parasitic node',instance,token)
                if suffix is None:assert old in port_ids,('Unexpected bare RC node',instance,token)
                return node(renames[old],(instance,old,suffix))
            for section in sections:
                old=section[1][1:];final=renames[old]
                part=dict(total=float(section[2]),connections={},caps=[],resistors=[],ports=[])
                phase=None
                for line in section[3].splitlines():
                    line=line.strip()
                    if not line:continue
                    if line in ('*CONN','*CAP','*RES'):phase=line;continue
                    fields=line.split()
                    if phase=='*CONN':
                        if fields[0]=='*P':
                            part['ports'].append(resolve(fields[1]));statistics['native_port_connections']+=1
                        else:
                            assert fields[0]=='*I';pin=resolve(fields[1]);assert pin not in part['connections']
                            part['connections'][pin]='*I '+pin+' '+' '.join(fields[2:]);statistics['native_physical_pin_connections']+=1
                    elif phase in ('*CAP','*RES'):
                        assert fields[0].isdigit()
                        count=len(fields)-2
                        assert count in ((1,2) if phase=='*CAP' else (2,))
                        converted=' '.join([*(resolve(t) for t in fields[1:-1]),fields[-1]])
                        part['caps' if phase=='*CAP' else 'resistors'].append(converted)
                        statistics['native_ground_caps' if phase=='*CAP' and count==1 else 'native_coupling_caps' if phase=='*CAP' else 'native_resistors']+=1
                    else:raise AssertionError(('Unknown SPEF phase',instance,line))
                statistics['native_nets']+=1
                if final in boundaries:
                    target=boundaries[final];target['total']+=part['total']
                    assert not set(target['connections']) & set(part['connections'])
                    target['connections'].update(part['connections'])
                    for kind in ('caps','resistors','ports'):target[kind]+=part[kind]
                else:emit(final,part)
        assert seen==expected,('Missing boundary native RC ports',sorted(expected-seen)[:20])
        for final,part in boundaries.items():
            ends=part['ports'];assert len(ends)>=2,(final,ends)
            # Deliberately ideal inter-macro joins for diagnostic use only.
            # Native access is retained independently on both sides of each join.
            for peer in ends[1:]:part['resistors'].append(ends[0]+' '+peer+' 0.000001')
            statistics['ideal_upper_joins']+=len(ends)-1
            emit(final,part)
    target=out/'stitched-native.spef'
    with target.open('w') as stream:
        stream.write('*SPEF "IEEE 1481-1998"\n*DESIGN "control_system"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER []\n*T_UNIT 1 NS\n*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*L_UNIT 1 HENRY\n*NAME_MAP\n')
        for index,name in enumerate(names,1):stream.write('*'+str(index)+' '+name+'\n')
        stream.write('\n')
        with body.open() as source:shutil.copyfileobj(source,stream)
    proof=dict(passed=True,mode='native-access-plus-ideal-upper-diagnostic',inputs=source_files,
               statistics=dict(statistics),boundary_port_count=len(seen),boundary_net_count=len(boundaries),
               output=str(target),output_sha256=sha(target),whole_system_qualified=False,
               scope='Every complete native RC section retained and namespaced; ideal upper joins only. No physical upper-RC qualification.')
    (out/'native-stitch.json').write_text(json.dumps(proof,indent=2)+'\n')
    return target,proof
