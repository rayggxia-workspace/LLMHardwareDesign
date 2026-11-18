"""Give every connected mapped pin an alias to its actual zero-delay gate waveform."""
from pathlib import Path
from hashlib import sha256
import json,re

def digest(path):
    h=sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def native_pin_coverage(raw,graph):
    """Prefer already traced physical pin names; verify every connected pin and its initial value."""
    stack=[];scope=None;scale=None;masks={};top=set();required_ids={};internal=0
    with raw.open() as f:
        for line in f:
            parts=line.split()
            if not parts:continue
            if parts[0]=='$timescale':scale=' '.join(parts[1:-1])
            elif parts[0]=='$scope':
                stack.append(parts[2])
                if stack[-1]=='dut':scope=tuple(stack)
            elif parts[0]=='$upscope':stack.pop()
            elif parts[0]=='$var' and scope:
                width=int(parts[2]);code=parts[3];name=parts[4];matched=False
                if tuple(stack)==scope:
                    if re.fullmatch(r'_\d+_',name):internal+=1
                    if name in graph['ports']:
                        assert width==len(graph['ports'][name]['bits'])
                        assert name not in top
                        top.add(name);matched=True
                elif len(stack)==len(scope)+1 and tuple(stack[:-1])==scope and stack[-1] in graph['cells']:
                    cell_name=stack[-1];connections=graph['cells'][cell_name]['connections']
                    if name in connections and connections[name]:
                        assert width==len(connections[name])==1
                        index=list(connections).index(name)
                        mask=masks.get(cell_name,0)
                        assert not mask&(1<<index),(cell_name,name)
                        masks[cell_name]=mask|(1<<index);matched=True
                if matched:
                    assert code not in required_ids or required_ids[code]==width
                    required_ids[code]=width
            elif parts[0]=='$enddefinitions':break
        complete=top==set(graph['ports'])
        for name,cell in graph['cells'].items():
            wanted=sum(1<<i for i,b in enumerate(cell['connections'].values()) if b)
            if masks.get(name,0)!=wanted:complete=False;break
        if not complete:return None
        assert scale=='1ps'
        seen=set();initial_time=None
        for line in f:
            if line.startswith('#'):
                timestamp=int(line[1:])
                if initial_time is None:initial_time=timestamp;assert timestamp==0
                elif timestamp>0:break
            elif line and line[0] in '01xz':
                code=line.strip()[1:]
                if code in required_ids:
                    assert required_ids[code]==1 and line[0] in '01'
                    seen.add(code)
            elif line and line[0] in 'bB':
                value,code=line[1:].split()
                if code in required_ids:
                    assert len(value)<=required_ids[code] and set(value)<=set('01')
                    seen.add(code)
        assert seen==set(required_ids),'native pin initial values missing'
    expected=sum(len(v) for c in graph['cells'].values() for v in c['connections'].values())+sum(len(p['bits']) for p in graph['ports'].values())
    return dict(scope='/'.join(scope),connected_pin_declarations=expected,
                observed_required_ids=len(seen),original_internal_net_declarations=internal,
                uses_original_vcd=True,method='Native mapped-cell pin names and top ports are already fully traced; every connected pin and every required initial waveform value is verified. Original VCD is used directly.')

def map_pins(raw,graph_path,output,source_sha256):
    raw,graph_path,output=map(Path,(raw,graph_path,output))
    receipt_path=output.with_suffix('.json')
    inputs=dict(raw_vcd_sha256=source_sha256,graph_sha256=digest(graph_path),mapper_sha256=digest(__file__))
    if receipt_path.exists():
        prior=json.loads(receipt_path.read_text())
        assert prior['inputs']==inputs and digest(raw if prior.get('uses_original_vcd') else output)==prior['pin_vcd_sha256']
        return prior
    graph=json.loads(graph_path.read_bytes())['modules']['block_v1_r']
    native=native_pin_coverage(raw,graph)
    if native is not None:
        native.update(inputs=inputs,pin_vcd_sha256=source_sha256)
        receipt_path.write_text(json.dumps(native,indent=2)+'\n')
        return native
    required={bit for c in graph['cells'].values() for bits in c['connections'].values() for bit in bits}
    required.update(bit for p in graph['ports'].values() for bit in p['bits'])
    assert all(isinstance(b,int) or b in ('0','1') for b in required),'unknown constant on connected pin'
    sources={};stack=[];scope=None;codes=set();internal=0;scale=None
    with raw.open() as f:
        for line in f:
            parts=line.split()
            if not parts:continue
            if parts[0]=='$timescale':scale=' '.join(parts[1:-1])
            elif parts[0]=='$scope':
                stack.append(parts[2])
                if stack[-1]=='dut':scope='/'.join(stack)
            elif parts[0]=='$upscope':stack.pop()
            elif parts[0]=='$var' and stack and stack[-1]=='dut':
                width=int(parts[2]);code=parts[3];name=parts[4]
                codes.add(code)
                if re.fullmatch(r'_\d+_',name):internal+=1
                if name not in graph['netnames']:continue
                wire=graph['netnames'][name]
                assert not wire.get('upto',0) and not wire.get('offset',0),name
                assert width==len(wire['bits']),(name,width,len(wire['bits']))
                for index,bit in enumerate(wire['bits']):
                    if isinstance(bit,int) and bit in required:
                        candidate=(code,index,width)
                        if bit not in sources or (width==1 and sources[bit][2]!=1):sources[bit]=candidate
            elif parts[0]=='$enddefinitions':break
    assert scale=='1ps' and scope,(scale,scope)
    missing={x for x in required if isinstance(x,int)}-sources.keys()
    assert not missing,(len(missing),sorted(missing)[:20])
    scalar_codes=set();derived={};ids={}
    for bit,(code,index,width) in sources.items():
        if width==1:
            ids[bit]=code;scalar_codes.add(code)
        else:
            ident='zzpin_'+str(bit)
            assert ident not in codes
            ids[bit]=ident
            derived.setdefault(code,[]).append((index,ident,width))
    for bit in ('0','1'):
        ids[bit]='zzconstant_'+bit
        assert ids[bit] not in codes
    declarations=0;last_derived={};seen_scalar=set();last_time=None
    with output.open('w') as out,raw.open() as inp:
        out.write('$version Mapped pin aliases of validated zero-delay gate trace $end\n$timescale 1ps $end\n')
        for part in scope.split('/'):out.write('$scope module '+part+' $end\n')
        for name,port in graph['ports'].items():
            for index,bit in enumerate(port['bits']):
                pin=name if len(port['bits'])==1 else name+'['+str(index)+']'
                out.write('$var wire 1 '+ids[bit]+' '+pin+' $end\n');declarations+=1
        for name,cell in graph['cells'].items():
            assert not re.search(r'\s',name),name
            out.write('$scope module '+name+' $end\n')
            for pin,bits in cell['connections'].items():
                if not bits:continue
                assert len(bits)==1,(name,pin,len(bits))
                out.write('$var wire 1 '+ids[bits[0]]+' '+pin+' $end\n');declarations+=1
            out.write('$upscope $end\n')
        for part in scope.split('/'):out.write('$upscope $end\n')
        out.write('$enddefinitions $end\n')
        for line in inp:
            if '$enddefinitions' in line:break
        for line in inp:
            if line.startswith('#'):
                last_time=int(line[1:]);out.write(line)
                if last_time==0:
                    for bit in ('0','1'):
                        if bit in required:out.write(bit+ids[bit]+'\n')
            elif line and line[0] in '01xz':
                code=line.strip()[1:]
                if code in scalar_codes:
                    assert line[0] in '01','unknown connected signal'
                    out.write(line);seen_scalar.add(code)
            elif line and line[0] in 'bB':
                value,code=line[1:].split()
                if code in scalar_codes:
                    assert len(value)==1 and value in ('0','1')
                    out.write(value+code+'\n');seen_scalar.add(code)
                if code in derived:
                    width=derived[code][0][2]
                    assert set(value)<=set('01'),'unknown connected bus'
                    value=value.zfill(width)
                    assert len(value)==width
                    for index,ident,_ in derived[code]:
                        v=value[-1-index]
                        if last_derived.get(ident)!=v:
                            out.write(v+ident+'\n');last_derived[ident]=v
    expected=sum(len(v) for c in graph['cells'].values() for v in c['connections'].values())+sum(len(p['bits']) for p in graph['ports'].values())
    assert declarations==expected
    assert seen_scalar==scalar_codes,'scalar waveform values missing'
    assert len(last_derived)==sum(len(v) for v in derived.values()),'vector waveform values missing'
    result=dict(inputs=inputs,pin_vcd_sha256=digest(output),scope=scope,
                connected_pin_declarations=declarations,mapped_signal_bits=len(required),
                observed_scalar_ids=len(seen_scalar),observed_derived_vector_bits=len(last_derived),
                original_internal_net_declarations=internal,final_timestamp_ps=last_time,
                method='All connected pins alias the same Yosys graph bit waveform; vector bits are expanded without changing transition times. Only names/representation change.')
    receipt_path.write_text(json.dumps(result,indent=2)+'\n')
    return result
