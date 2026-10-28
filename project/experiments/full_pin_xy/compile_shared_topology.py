"""Compile and verify the shared passive topology before any physical freeze.

Both original bit graphs remain intact. Only 256 original two-terminal read
nets per design are cut, with 256 real finite-wire resources planned for reuse.
Mode-specific passive edges restore the exact original connections. Clock-stop
and the 37 distinct literal output drivers are explicit infrastructure, never
new compute blocks. This is a graph proof, not routed hardware/function signoff.
"""
from pathlib import Path
from collections import defaultdict
import argparse, csv, hashlib, json
from inventory import load, owner, pin_names
from prepare_controlled_parent import escaped


class DSU:
    def __init__(self,keys):self.p={k:k for k in keys}
    def find(self,a):
        if self.p[a]!=a:self.p[a]=self.find(self.p[a])
        return self.p[a]
    def union(self,a,b):self.p[self.find(a)]=self.find(b)


def compile_graph(root,preparation,out):
    root,preparation,out=map(Path,[root,preparation,out]);assert not out.exists()
    graphs={d:load(root/'partition-r02'/(d+'_partition_graph.json.gz')) for d in ['opentpu','llaccel']}
    nets=load(preparation/'complete_mode_nets.json')
    bindings=list(csv.DictReader((preparation/'shared_prewire_bindings.csv').open()))
    selected={d:{r['original_parent_bit']:r for r in bindings if r['mode']==d} for d in graphs}
    assert all(len(v)==256 for v in selected.values())
    components={};terminal_component={};original_terminals={};clock_bits={};infra=[];cut_pairs={d:{} for d in graphs}
    def term_key(design,term):
        return design+':'+(term['case']+'/'+term['pin'] if term['kind']=='ITERM' else 'TOP_IO/'+term['pin'])
    def add(name,terms):
        assert name not in components;components[name]=terms
        for t in terms:
            key=t['terminal'];assert key not in terminal_component,key;terminal_component[key]=name
    for design,g in graphs.items():
        clock_bits[design]=str(g['top_module']['ports']['clk']['bits'][0])
        for bit,terms in nets[design].items():
            ts=[dict(t,terminal=term_key(design,t)) for t in terms]
            original_terminals[design,bit]=[t['terminal'] for t in ts]
            prefix=design+':'+bit
            if bit in selected[design]:
                assert len(ts)==2 and all(t['kind']=='ITERM' for t in ts)
                driver=next(t for t in ts if t['direction']=='output');sink=next(t for t in ts if t['direction']=='input')
                add(prefix+':source',[driver]);add(prefix+':sink',[sink]);cut_pairs[design][bit]=(prefix+':source',prefix+':sink')
            elif bit==clock_bits[design]:
                top=[t for t in ts if t['kind']=='TOP_IO'];sinks=[t for t in ts if t['kind']=='ITERM']
                assert len(top)==1 and len(sinks)==3
                add(prefix+':external_clock',top);add(prefix+':clock_sinks',sinks)
            else:
                literals=[t for t in ts if 'literal' in t]
                if literals:
                    assert len(ts)==len(literals)==1 and literals[0]['literal'] in ['0','1']
                    i=len(infra);t={'kind':'INFRA','terminal':'INFRA/literal_'+str(i)+'/Z','direction':'output','master':'LOGIC'+literals[0]['literal']+'_X1','instance':'u_literal_'+str(i),'original_literal_top_pin':ts[0]['pin']}
                    infra.append(t);ts.append(t)
                add(prefix,ts)
    assert len(infra)==37
    idle={'kind':'INFRA','terminal':'INFRA/idle_clock/Z','direction':'output','master':'LOGIC0_X1','instance':'u_idle_clock_zero'}
    infra.append(idle);add('INFRA:idle_clock_zero',[idle])
    for i in range(256):add('SHARED:R'+format(i,'04d'),[])
    proofs={};mode_edges={}
    for mode in graphs:
        dsu=DSU(components);edges=[]
        def connect(a,b,reason):
            assert a!=b;dsu.union(a,b);edges.append({'component_a':a,'component_b':b,'connection':reason,'allowed_adaptation_layers':'metal11 metal12; legal via10/11; original leaf layers unchanged','routed':False})
        used=[]
        for design in graphs:
            for bit,(source,sink) in cut_pairs[design].items():
                if design==mode:
                    resource='SHARED:'+selected[design][bit]['resource'];connect(source,resource,'ACTIVE original source to shared fixed conductor');connect(resource,sink,'ACTIVE shared conductor to original sink');used.append(resource)
                else:connect(source,sink,'INACTIVE original source-to-sink bypass; original sink not floating')
            clock=design+':'+clock_bits[design]
            connect(clock+(':external_clock' if design==mode else ':clock_sinks'),clock+':clock_sinks' if design==mode else 'INFRA:idle_clock_zero','ACTIVE original external clock' if design==mode else 'INACTIVE physically driven constant clock')
        # Every original bit is connected and no two bits in either design are
        # accidentally aliased. Only inactive external clock is deliberately
        # isolated from its stopped sink domain.
        group_bits=defaultdict(set);checked=0
        for (design,bit),terms in original_terminals.items():
            if design!=mode and bit==clock_bits[design]:terms=[t for t in terms if ':TOP_IO/' not in t]
            groups={dsu.find(terminal_component[t]) for t in terms};assert len(groups)==1,(mode,design,bit,'split')
            group_bits[next(iter(groups))].add((design,bit));checked+=len(terms)
        assert all(len(bits)==1 for bits in group_bits.values()),(mode,'unintended merge between different original bits')
        assert len(used)==len(set(used))==256
        mode_edges[mode]=edges;proofs[mode]={'all_original_bits_connected':True,'different_original_bits_not_merged':True,
              'original_active_clock_bit_graph_preserved':True,'inactive_sink_clock_explicitly_driven_low':True,
              'inactive_clock_TOP_IO_retained_but_not_connected_to_stopped_sinks':True,
              'shared_resource_ids':sorted(used),'checked_original_terminals':checked,'adaptation_graph_edges':len(edges),
              'physical_connectivity_proven':False,'RTL_or_netlist_formal_equivalence_executed':False}
    assert proofs['opentpu']['shared_resource_ids']==proofs['llaccel']['shared_resource_ids']
    original_pin_count=sum(t['kind']=='ITERM' for ts in components.values() for t in ts);assert original_pin_count==24767
    # Actual reusable structural netlist. Internal access pads are construction
    # ports; they must be lowered to preserved wire geometry before freeze/STA.
    wire_names={name:'w'+format(i,'06d') for i,name in enumerate(sorted(components))}
    access=sorted({e[k] for edges in mode_edges.values() for e in edges for k in ['component_a','component_b']})
    pad_names={name:'access_'+format(i,'04d') for i,name in enumerate(access)}
    top_ports=[d+'__'+n for d,g in graphs.items() for n in g['top_module']['ports']]+list(pad_names.values())
    verilog=['// Construction netlist only; not routed, frozen, or STA-qualified.','module hpy_common_base_construction('+', '.join(escaped(n) for n in top_ports)+');']
    for d,g in graphs.items():
        for name,p in g['top_module']['ports'].items():
            n=len(p['bits']);offset=p.get('offset',0);assert not p.get('upto',0)
            verilog.append(p['direction']+' '+('['+str(offset+n-1)+':'+str(offset)+'] ' if n>1 else '')+escaped(d+'__'+name)+';')
    verilog+=['inout '+name+';' for name in pad_names.values()]+['wire '+w+';' for w in wire_names.values()]
    for name,pad in pad_names.items():verilog.append('assign '+pad+' = '+wire_names[name]+';')
    for d,g in graphs.items():
        for name,p in g['top_module']['ports'].items():
            for pin,index in zip(pin_names(name,p),range(len(p['bits']))):
                wire=wire_names[terminal_component[d+':TOP_IO/'+pin]];ref=escaped(d+'__'+name)+('['+str(p.get('offset',0)+index)+']' if len(p['bits'])>1 else '')
                assert p['direction'] in ['input','output'];verilog.append('assign '+(wire+' = '+ref if p['direction']=='input' else ref+' = '+wire)+';')
        for instance,cell in g['top_module']['cells'].items():
            case=owner(instance,d);ports=[]
            for name,p in g['frontier'][cell['type']]['ports'].items():
                wires=[wire_names[terminal_component[d+':'+case+'/'+pin]] for pin in pin_names(name,p)]
                ports.append('.'+escaped(name)+'('+('{' + ','.join(reversed(wires))+'}' if len(wires)>1 else wires[0])+')')
            verilog.append('p126_'+case+' '+escaped('u_'+case)+'('+', '.join(ports)+');')
    for t in infra:verilog.append(t['master']+' '+t['instance']+'(.Z('+wire_names[terminal_component[t['terminal']]]+'));')
    verilog.append('endmodule')
    out.mkdir(parents=True)
    (out/'base_construction.v').write_text('\n'.join(verilog)+'\n',encoding='utf-8')
    def write(name,v):(out/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write('components.json',components);write('component_wire_names.json',wire_names);write('access_pads.json',pad_names);write('infrastructure.json',infra)
    for mode,edges in mode_edges.items():write(mode+'_adaptation_edges.json',edges)
    write('topology_proof.json',{'status':'PASS_COMPILED_BIT_GRAPH_ONLY_NOT_PHYSICAL_IMPLEMENTATION','source_preparation_SHA':hashlib.sha256((preparation/'preparation_contract.json').read_bytes()).hexdigest(),
      'all_original_signal_pins':original_pin_count,'fixed_components':len(components),'added_constant_driver_instances':len(infra),
      'computational_instances':6,'shared_planned_components':256,'modes':proofs,'frozen':False,
      'external_inactive_input_contract':'Original external inputs remain physically connected; both-mode testbench/board must drive inactive non-clock inputs to specified reset/idle values. Reset polarity and complete stimulus still require original RTL verification.',
      'construction_port_lowering_required_before_freeze_and_STA':True,'native_Verilog_link_and_physical_views_not_yet_executed':True,
      'required_physical_checks':['real 256 shared conductors reused','native/whole signal and dual PG','same M1-M10 geometric union and lower-via/cell/pin manifests','RC/STA/electrical including new clock-tie fanout','complete-rule/SRAM qualification ledger','RTL or gate equivalence']})
    write('artifact_index.json',{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.is_file()})
    print('PASS_COMPILED_SHARED_GRAPH_ONLY',original_pin_count,'pins',len(components),'fixed components;',len(infra),'costed constant-driver declarations; NOT routed/frozen')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--preparation',required=True);p.add_argument('--out',required=True);a=p.parse_args();compile_graph(a.root,a.preparation,a.out)
