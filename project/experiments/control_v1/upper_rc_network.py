"""Distributed research RC from independently read-back actual upper geometry.

Uses the already declared uniform 2um model, including its 0.7/1/1.5 variants.
This is not a calibrated twelve-layer process extraction.
"""
import collections,json,math
from pathlib import Path


class UpperRC:
    def __init__(self,folder,graph,manifest,variant,bind):
        self.folder=folder;self.graph=graph;self.variant=variant
        bind(Path(__file__))
        path=folder/'receipt.json';bind(path);receipt=json.loads(path.read_text())
        assert receipt['passed'] and receipt['actual_odb_def_readback'] and receipt['actual_joined_gds_readback']
        for name,digest in receipt['outputs'].items():bind(folder/name,digest)
        for path,digest in receipt['inputs'].items():bind(path,digest)
        readback=json.loads((folder/'joined-readback.json').read_text())
        assert readback['passed'] and all(readback['checks'].values()) and all(readback['native_masks_xor_zero'].values())
        request=json.loads((folder/'join-input.json').read_text())
        assert set(request['native'])==set(graph['instances'])
        for instance,top in graph['instances'].items():
            entry=manifest['leaves'][top]['final_files']['6_final.gds']
            assert request['native'][instance]['sha256']==entry['sha256']
        self.fixture=json.loads((folder/'routing.json').read_text())
        self.edges=json.loads((folder/'edges.json').read_text())
        expected={'net_'+bit for bit in graph['connections']}
        assert set(self.edges)==expected|{'net_PG_VDD','net_PG_VSS'}
        assert set(self.fixture['terminals'])==set(self.edges)
        self.names={row['driver']['pin'] if row['driver']['instance']=='TOP' else 'net_'+bit:bit for bit,row in graph['connections'].items()}
        spec=Path(__file__).resolve().parents[1]/'block_v1/technology-2um-v1.json';bind(spec)
        self.spec=json.loads(spec.read_text());g=self.spec['geometry_um'];e=self.spec['electrical']
        factor=e['estimate_variants'][variant]
        self.r_per_um=e['sheet_resistance_ohm']/g['width']*factor
        self.c_pf_per_um=.0088541878128*e['relative_permittivity']*(g['width']/g['dielectric_gap']+2*g['thickness']/g['spacing'])*factor/1000
        self.via_r=e['via_resistance_ohm']*factor
        assert all(math.isfinite(v) and v>0 for v in (self.r_per_um,self.c_pf_per_um,self.via_r))
        self.statistics=collections.Counter();self.nets={}

    def join(self,final,part,ports,intern,node):
        bit=self.names[final];name='net_'+bit;row=self.graph['connections'][bit]
        ends=[row['driver'],*row['sinks']];xy=self.fixture['terminals'][name]
        assert len(ends)==len(xy)==len(part['ports'])
        expected_ports=[];caps=collections.Counter();vertices=set();edges=set()
        def vertex(v):return node(final,('actual-upper',*v))
        for pair in self.edges[name]:
            first,last=map(tuple,pair);assert sum(abs(a-b) for a,b in zip(first,last))==1
            assert first[2] in (0,1) and last[2] in (0,1)
            key=tuple(sorted((first,last)));assert key not in edges;edges.add(key);vertices.update((first,last))
            if first[2]!=last[2]:
                assert first[:2]==last[:2] and (first[0]+first[1])%2==0
                resistance=self.via_r;self.statistics['via11']+=1
            else:
                length=self.spec['geometry_um']['pitch'];resistance=length*self.r_per_um
                capacitance=length*self.c_pf_per_um
                caps[first]+=capacitance/2;caps[last]+=capacitance/2
                self.statistics['wire_length_um']+=length;self.statistics['wire_edges']+=1
            part['resistors'].append(vertex(first)+' '+vertex(last)+' '+format(resistance,'.12g'))
        for end,point,kind in zip(ends,xy,self.fixture['terminal_kinds'][name]):
            x=(point[0]-190)/8000;y=(point[1]-140)/8000
            assert int(x)==x and int(y)==y
            site=(int(x),int(y),0);assert site in vertices
            if end['instance']=='TOP':
                assert kind=='external';port=intern(end['pin']);resistance=.000001
                self.statistics['zero_length_external_contacts']+=1
            else:
                assert kind=='native';port=ports[end['instance'],end['pin']];resistance=self.via_r
                self.statistics['via10']+=1
            expected_ports.append(port)
            part['resistors'].append(port+' '+vertex(site)+' '+format(resistance,'.12g'))
        assert collections.Counter(expected_ports)==collections.Counter(part['ports'])
        total=sum(caps.values());part['total']+=total
        for v,cap in caps.items():part['caps'].append(vertex(v)+' '+format(cap,'.12g'))
        self.nets[name]=dict(native_and_external_ports=len(expected_ports),upper_edges=len(edges),
                            distributed_ground_cap_pf=total,upper_vertices=len(vertices))

    def proof(self):
        assert len(self.nets)==len(self.graph['connections'])
        return dict(passed=True,variant=self.variant,geometry=str(self.folder),net_count=len(self.nets),
            statistics=dict(self.statistics),nets=self.nets,r_ohm_per_um=self.r_per_um,c_pf_per_um=self.c_pf_per_um,
            via_resistance_ohm=self.via_r,calibrated_twelve_layer_extraction=False,whole_system_qualified=False,
            scope='Distributed wire RC and explicit via10/via11 resistance on actual read-back upper geometry; same declared uncalibrated uniform geometry model. Wire fringe/coupling represented by existing lumped ground-cap coefficient; separate via/end capacitance is not supplied by that research model. Every native RC element retained.')
