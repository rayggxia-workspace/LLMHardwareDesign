"""Exact seven-native physical contract for the tested PR168 R256 topology.

This contract extends the declared scene, never leaf or physical acceptance.
Legacy six-native scenes retain their original checks and frozen sources.
"""
import copy,hashlib,re

SCHEMA='r256-seven-native/1'
RTL_SHA256='3beb3ad5dd2fd45d67a0b905a301617a436f9c0f8cd79404c4de47cba6ccb475'
SPECIAL={
    'reset_distribution':('control_reset_distribution','BRANCHES',28,'control_reset_distribution_r28'),
    'controller':('control_c','ENDPOINTS',8,'control_c_r8'),
    'routes':('control_route','ENDPOINTS',8,'control_route_r8'),
    'system_status':('control_status','QUEUES',8,'control_status_r8'),
    's_port':('control_s_arbiter','CLIENTS',7,'control_s_arbiter_r7'),
    'macro_r':('r_stream_local','WORDS',256,'r_stream_local'),
}
BASE={'host':'control_axil_bridge','endpoint_0':'control_d',
      'macro_1':'block_v2_m','macro_2':'block_v2_n','macro_3':'block_v2_e',
      'macro_4':'block_v2_g','macro_s':'block_feed_s_macro','macro_t':'transaction6k'}
BASE.update({'endpoint_'+str(i):'control_adapter_'+role for i,role in enumerate('mnegstr',1)})
BASE.update({'queue_'+str(i):'control_endpoint_queue'for i in range(8)})
BASE.update({name:row[3]for name,row in SPECIAL.items()})
assert len(BASE)==29 and len(set(BASE.values()))==22


def fixed_top(data):
    """Only replace exact parameter bindings with qualified named variants."""
    assert hashlib.sha256(data).hexdigest()==RTL_SHA256,'Different R256 integration source'
    text=data.decode()
    for name,(old,parameter,value,new)in SPECIAL.items():
        pattern=r'\b'+old+r'\s*#\s*\(\s*\.'+parameter+r'\('+str(value)+r'\)\s*\)\s+'+name+r'\s*\('
        text,count=re.subn(pattern,new+' '+name+'(',text)
        assert count==1,(name,count)
    assert not re.search(r'\b(?:control_\w+|r_stream_local)\s*#',text)
    return text


def is_r256(instances):
    return instances.get('macro_r')=='r_stream_local'


def validate_base(instances,leaf_names):
    base={name:top for name,top in instances.items()if top!='control_link8'}
    assert base==BASE,('R256 scene requires the exact 29 tested physical owners',base)
    expected=set(BASE.values())|({'control_link8'}if len(instances)>29 else set())
    assert set(leaf_names)==expected,'R256 scene contains missing or extra physical types'
    return 29,22


def placement_pin_maps(manifest,pins):
    """Cost-only coordinates for a rigid R translation, never edited pins."""
    if 'r_stream_local'not in manifest['leaves']:return pins
    assert manifest.get('scene')==SCHEMA
    assert manifest['leaves']['r_stream_local']['placement_phase_um']==[.095,.07]
    result=copy.deepcopy(pins)
    for pin in result['r_stream_local'].values():
        x,y=pin.get('xy_um',[(pin.get('box_dbu',[0]*4)[0]+pin.get('box_dbu',[0]*4)[2])/4000,(pin.get('box_dbu',[0]*4)[1]+pin.get('box_dbu',[0]*4)[3])/4000])
        assert abs(x/4-round(x/4))<1e-7 and abs(y/4-round(y/4))<1e-7
        pin['xy_um']=[x+.095,y+.07]
    return result


def phase_placement(manifest,instances,positions,reused=False):
    if not is_r256(instances):return positions
    assert manifest.get('scene')==SCHEMA
    assert manifest['leaves']['r_stream_local']['placement_phase_um']==[.095,.07]
    result=copy.deepcopy(positions)
    x,y=result['macro_r'];dx,dy=.095,.07
    if reused:
        assert abs((x-dx)/4-round((x-dx)/4))<1e-7 and abs((y-dy)/4-round((y-dy)/4))<1e-7
    else:
        assert abs(x/4-round(x/4))<1e-7 and abs(y/4-round(y/4))<1e-7
        result['macro_r']=[x+dx,y+dy]
    return result
