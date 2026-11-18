"""C639 non-DMA control calibration, 300 MHz, no wire parasitics.

Run inside the frozen ORFS container. This does not change product RTL.
LC PM/fetch are cut at their real pins, leaving only the controller shell.
Measured boundary activity is propagated, not a gate-level functional proof.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess

PLATFORM = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
LIB = PLATFORM / 'lib/NangateOpenCellLibrary_typical.lib'
COHORT = 'TOP/test_native_decode638_product_replay/controller/cohort'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()


def save(p, obj):
    p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')


def run(command, log):
    with log.open('w') as f:
        subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, check=True)


def power(tcl, out, expected=None):
    assert 'read_spef' not in tcl and 'estimate_parasitics' not in tcl
    out.mkdir(parents=True, exist_ok=True)
    (out/'power.tcl').write_text(tcl)
    run(['openroad', '-no_init', '-threads', '3', '-exit', str(out/'power.tcl')], out/'power.log')
    s = (out/'power.log').read_text()
    rows = re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)', s)
    ann = re.findall(r'Annotated (\d+) pin activities\.', s)
    if len(rows) != 1 or len(ann) != 1 or re.search(r'(?m)^(Error:|\[ERROR)', s) or 'problem parsing bus' in s:
        raise ValueError('invalid power output: '+str(out))
    if expected is not None and int(ann[0]) < expected: raise ValueError('missing boundary annotation')
    return {'power_w': dict(zip(('internal','switching','leakage','total'), map(float, rows[0]))),
            'annotated':int(ann[0]), 'power_log_sha256':sha(out/'power.log')}


def switch(r, out):
    quiet = r/'c639-switch-power-300-02/result-117841'
    active = r/'c639-switch-active-300-02/result-117856'
    inputs = {str(LIB):sha(LIB)}
    specs = []
    for mode in range(2):
        specs.append(('mode-%d-active'%mode, active/('mode-%d/power'%mode)))
        for phase in ('gate-up', 'down'):
            specs.append(('mode-%d-%s'%(mode,phase), quiet/('mode-%d-%s/power'%(mode,phase))))
    def one(spec):
        name, source = spec
        original = (source/'power.tcl').read_text()
        if original.count('read_spef ') != 1: raise ValueError('unexpected original power setup')
        tcl = '\n'.join(line for line in original.splitlines() if not line.startswith('read_spef '))+'\n'
        for path in re.findall(r'\{([^{}]+)\}', tcl):
            if Path(path).is_file(): inputs[path] = sha(path)
        wave = source/'gate-300mhz.vcd'
        receipt = json.loads((source/'receipt.json').read_text())
        if receipt['timing']['clock_hz'] != 300000000: raise ValueError('wrong clock')
        v = power(tcl,out/name,762)
        v['window_ps']=receipt['timing']['window_ps']
        v['energy_nj']=v['power_w']['total']*v['window_ps']*1e-3
        v['wave_sha256']=sha(wave)
        return name,v
    with ThreadPoolExecutor(max_workers=4) as pool: rows=dict(pool.map(one,specs))
    paired=[]
    for mode in range(2):
        a=rows['mode-%d-active'%mode]
        countpath=active/('mode-%d/handshake-cycles.txt'%mode)
        n=int(countpath.read_text()); assert n>0
        inputs[str(countpath)]=sha(countpath)
        for phase in ('gate-up','down'):
            q=rows['mode-%d-%s'%(mode,phase)]
            # Quiet reference windows need not have equal length; compare mean
            # power over the active duration, never subtract unequal energies.
            delta=(a['power_w']['total']-q['power_w']['total'])*a['window_ps']*1e-3
            paired.append({'mode':mode,'quiet_phase':phase,'handshake_cycles':n,
                           'active_delta_nj':delta,'pj_per_handshake_cycle':delta*1000/n})
    return {'kind':'control_switch','windows':rows,'paired':paired,'input_sha256':inputs,
            'scope':'cohort transport only; add dynamic delta to existing idle, not total power',
            'normalization':'accepted transport cycles; not automatically model service count',
            'netlist_origin':'existing routed cells retained; no SPEF or estimated wire RC loaded'}


def header(f):
    stack=[]; entries={}
    for line in f:
        p=line.split()
        if p[:1]==['$scope']: stack.append(p[2])
        elif p[:1]==['$upscope']: stack.pop()
        elif p[:1]==['$var']: entries['/'.join(stack+[p[4]])]=(p[3],int(p[2]),p[1])
        elif p[:1]==['$enddefinitions']: return entries
    raise ValueError('missing VCD header')


def change(line):
    if line[:1] in ('0','1','x','X','z','Z'): return line[1:].strip(),line[0].lower()
    if line[:1] in ('b','B'):
        p=line.split(); return p[1],p[0][1:].lower()
    return None


def constants(raw, scope, names):
    with raw.open() as f:
        h=header(f); ids={}
        for name in names:
            e=h[scope+'/'+name]
            if e[2]!='parameter': raise ValueError('not elaborated parameter: '+name)
            ids[name]=e
        values={}
        for line in f:
            c=change(line)
            if c: values[c[0]]=c[1]
            if all(v[0] in values for v in ids.values()): break
    return {n:(e[1],int(values[e[0]],2)) for n,e in ids.items()}


def ports_from_header(text):
    """Parse fixed-width ANSI child interfaces; reject unsupported syntax."""
    text=re.sub(r'//[^\n]*','',text)
    # The children have no parameterized widths in their port interfaces.
    start=text.index(')(\n')+3 if ')(\n' in text else text.index('(\n')+2
    body=text[start:text.index(');',start)]
    direction=None; width=''; result={}
    for part in body.split(','):
        part=part.strip()
        m=re.match(r'(input|output)\s+logic\s*(\[\d+:\d+\])?\s*(\w+)$',part)
        if m: direction,width,name=m.groups();width=width or ''
        else:
            if not direction or not re.fullmatch(r'\w+',part): raise ValueError('unsupported child port: '+part)
            name=part
        result[name]=(direction,width)
    return result


def cut_shell(rtl, out):
    parent=rtl/'lc_native_scope_controller.sv'
    text=parent.read_text(); bindings={}; newports=[]; assigns=[]
    for mod,inst in [('lc_program_store_1k','pm'),('lc_scope_fetch128','scope_fetch')]:
        ports=ports_from_header((rtl/(mod+'.sv')).read_text())
        pat=r'\b'+mod+r'\s+'+inst+r'\s*\((.*?)\);'
        found=list(re.finditer(pat,text,re.S)); assert len(found)==1
        body=found[0].group(1); actual={}
        # Split on commas outside expressions, keeping exact original wiring.
        parts=[]; depth=0; begin=0
        for i,c in enumerate(body):
            if c=='(':depth+=1
            elif c==')':depth-=1
            elif c==',' and depth==0:parts.append(body[begin:i]);begin=i+1
        parts.append(body[begin:])
        for part in parts:
            m=re.fullmatch(r'\s*\.(\w+)(?:\((.*)\))?\s*',part,re.S)
            if not m: raise ValueError('unsupported binding '+part)
            actual[m[1]]=m[2] if m[2] is not None else m[1]
        if set(actual)!=set(ports):raise ValueError('child pin mismatch')
        for name,(direction,width) in ports.items():
            if name in ('clk','reset'):continue
            cut='cut_'+inst+'_'+name
            newdir='input' if direction=='output' else 'output'
            newports.append('%s logic %s %s'%(newdir,width,cut))
            expr=actual[name]
            if direction=='output':
                if not re.fullmatch(r'\w+',expr):raise ValueError('non-net child output')
                assigns.append('assign %s = %s;'%(expr,cut))
            else: assigns.append('assign %s = %s;'%(cut,expr))
            bindings[cut]=inst+'/'+name
        text=text[:found[0].start()]+text[found[0].end():]
    pos=text.index(');');text=text[:pos]+',\n'+',\n'.join(newports)+'\n'+text[pos:]
    text=text.replace('endmodule','\n'+'\n'.join(assigns)+'\nendmodule')
    dest=out/'lc_native_scope_controller.sv';dest.write_text(text)
    save(out/'cut-bindings.json',bindings)
    return dest,bindings


def boundary(raw, wave, design, scope, bindings, clock='clk'):
    with raw.open() as src,wave.open('w') as dst:
        h=header(src); selected={}
        dst.write('$timescale 1ps $end\n$scope module dut $end\n')
        for name,p in design['ports'].items():
            e=h[scope+'/'+bindings.get(name,name)];width=len(p['bits'])
            if e[1]!=width: raise ValueError('boundary width mismatch '+name)
            selected.setdefault(e[0],[]).append(name)
            suffix=' [%d:0]'%(width-1) if width>1 else ''
            dst.write('$var wire %d %s %s%s $end\n'%(width,name,name,suffix))
        dst.write('$upscope $end\n$enddefinitions $end\n')
        first=last=None; seen=set(); clockchanges=0; clock_id=h[scope+'/'+clock][0]
        for line in src:
            if line.startswith('#'):
                now=int(line[1:]);first=now if first is None else first;last=now
                dst.write('#%d\n'%((now-first+1)//3));continue
            c=change(line)
            if c and c[0] in selected:
                if re.search('[xz]',c[1]):raise ValueError('unknown boundary value')
                seen.add(c[0])
                if c[0]==clock_id:clockchanges+=1
                for name in selected[c[0]]:dst.write('b%s %s\n'%(c[1],name))
        if seen!=set(selected):raise ValueError('incomplete port activity')
        if first is None or last<=first or clockchanges<2:raise ValueError('empty capture')
    return {'window_ps':(last-first)/3,'clock_changes':clockchanges,'port_bits':sum(len(p['bits']) for p in design['ports'].values())}


def synth(source, top, params, out, include=None):
    src=source.read_text()
    # Set parameters during elaboration, then preserve the original top ports.
    options=' '.join('-G%s=%d\'h%x'%(n,w,v) for n,(w,v) in params.items())
    ys=['read_slang --top %s %s %s %s'%(top,options,('-I'+str(include)) if include else '',source),
        'synth -top %s -flatten -noabc -noshare'%top,'dfflibmap -liberty '+str(LIB),
        'abc -liberty '+str(LIB),'clean','read_liberty -lib '+str(LIB),'check -assert',
        'stat -liberty '+str(LIB),'write_verilog -noattr -noexpr '+str(out/'mapped.v'),
        'write_json '+str(out/'mapped.json')]
    (out/'synth.ys').write_text('\n'.join(ys)+'\n')
    run(['yosys','-l',str(out/'synth.log'),str(out/'synth.ys')],out/'yosys.log')
    d=json.loads((out/'mapped.json').read_text())['modules'][top]
    if any(c['type'].startswith('$') for c in d['cells'].values()):raise ValueError('unmapped cells')
    return d


def local(r,out):
    frozen=r/'c639-g32-gate-01/c639-g32-116937'
    rtl=frozen/'source/project/experiments/shared_x_control/rtl'
    converter=r/'c639-g32-power-03/power-116943/fst_scope_vcd'
    cut,bindings=cut_shell(rtl,out)
    waves={}
    for mode in range(2):
        cases={'active':r/('c639-switch-active-300-01/result-117854/replay-117854/DDR-%d/switch-active.fst'%mode)}
        for phase in ('gate-up','down'):cases[phase]=frozen/('replay-116937/DDR-%d/ffn-%s.fst'%(mode,phase))
        for phase,fst in cases.items():
            raw=out/('mode-%d-%s.vcd'%(mode,phase))
            run([str(converter),str(fst),str(raw),COHORT],raw.with_suffix('.log'))
            waves['mode-%d-%s'%(mode,phase)]=(fst,raw)
    def one(spec):
        site,kind=spec; p=out/('site-%d-%s'%(site,kind));p.mkdir()
        scope=COHORT+'/local_target[%d]/'%site+('local_controller' if kind=='shell' else 'dispatch')
        top='lc_native_scope_controller' if kind=='shell' else 'lc_native_service_router'
        names=['TARGET','IMAGE_ID'] if kind=='shell' else ['PROVIDERS','ROUTES','PORT_BITS','ROUTE_ENABLE','ROUTE_SCHEMA','ROUTE_PROVIDER_ABI','ROUTE_OP','ROUTE_PORT']
        params=constants(waves['mode-0-active'][1],scope,names)
        for fst,raw in waves.values():
            if constants(raw,scope,names)!=params:raise ValueError('inconsistent elaboration')
        source=cut if kind=='shell' else rtl/(top+'.sv')
        save(p/'parameters.json',params)
        design=synth(source,top,params,p)
        rows={}
        for name,(fst,raw) in waves.items():
            q=p/name;q.mkdir();wave=q/'ports-300.vcd'
            timing=boundary(raw,wave,design,scope,bindings if kind=='shell' else {})
            tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
                'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
                'read_verilog {'+str(p/'mapped.v')+'}','link_design '+top,
                'create_clock -name core -period 3.333333333333 [get_ports clk]',
                'set_input_transition 0.05 [all_inputs]','read_vcd -scope dut {'+str(wave)+'}',
                'report_activity_annotation','report_power -digits 9'])+'\n'
            row=power(tcl,q,timing['port_bits']);row.update(timing)
            row['wave_sha256']=sha(wave);row['source_fst_sha256']=sha(fst);rows[name]=row
        result={'site':site,'kind':kind,'scope':scope,'parameters':params,'cell_count':len(design['cells']),
                'source_sha256':sha(source),'netlist_sha256':sha(p/'mapped.v'),'windows':rows}
        save(p/'calibration.json',result)
        return p.name,result
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=dict(pool.map(one,[(i,k) for i in range(4) for k in ('shell','dispatch')]))
    return {'kind':'local_shell_dispatch','instances':rows,
            'input_sha256':{str(p):sha(p) for p in [LIB,converter]+[rtl/(n+'.sv') for n in ('lc_native_scope_controller','lc_program_store_1k','lc_scope_fetch128','lc_native_service_router')]},
            'scope':'4 actual LC shells and 4 dispatch routers; child PM and scope_fetch excluded',
            'activity':'sampled boundary propagation, not full internal gate replay',
            'integration_status':'pending service/boot residency weighting and sampled coverage audit'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['switch','local']);ap.add_argument('runs',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();args.output.mkdir(parents=True)
    result=(switch if args.kind=='switch' else local)(args.runs,args.output)
    result.update({'clock_mhz':300,'wire_parasitics_loaded':False,'timing_signoff':False,
                   'script_sha256':sha(__file__),'library_sha256':sha(LIB)})
    save(args.output/'calibration.json',result)
    print('CONTROL_GAP_'+args.kind.upper()+'_PASS',flush=True)


if __name__=='__main__':main()
