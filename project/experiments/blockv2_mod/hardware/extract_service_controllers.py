"""Reproducible extraction of control-only services from audited RTL.

Resource pins belong to parent standard-cell service controllers, not to a
physical Block. This tool does not instantiate, select or connect a macro.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'evidence/architecture-revision-185'

def close(text, pos):
    assert text[pos] == '('
    depth = 1
    for end in range(pos+1,len(text)):
        depth += (text[end] == '(') - (text[end] == ')')
        if not depth:
            return end
    raise ValueError('unclosed parentheses')

def arguments(text):
    values = {}
    i = 0
    while i < len(text):
        match = re.match(r'\s*,?\s*\.([A-Za-z_][A-Za-z_0-9]*)\s*',text[i:])
        if not match:
            if not text[i:].strip(): break
            raise ValueError('unsupported named connection '+text[i:i+60])
        name=match[1];i+=match.end()
        if i < len(text) and text[i]=='(':
            end=close(text,i);expression=text[i+1:end].strip();i=end+1
        else: expression=name
        if name in values: raise ValueError('duplicate connection '+name)
        values[name]=expression
    return values

def ports(xml, master):
    root=ET.parse(xml).getroot()
    types={t.get('id'):t for t in root.findall('./netlist/typetable/*')}
    modules=[m for m in root.findall('./netlist/module') if m.get('origName')==master]
    if not modules: raise ValueError('master absent '+master)
    result={}
    for v in modules[0].findall('./var'):
        direction=v.get('dir')
        if not direction:continue
        t=types[v.get('dtype_id')]
        if t.tag!='basicdtype': raise ValueError('non scalar-packed port '+v.get('name'))
        shape=('['+t.get('left')+':'+t.get('right')+'] ') if t.get('left') else ''
        result[v.get('name')]=(direction,shape)
    return result

def extract(source, new_name, resources, xml):
    path=ROOT/source
    original=path.read_text()
    text=original
    declared=[];assigns=[];requirements=[]
    for instance,master,resource_id in resources:
        pattern=r'\b'+re.escape(master)+r'\s+'+re.escape(instance)+r'\s*\('
        matches=list(re.finditer(pattern,text))
        if len(matches)!=1:raise ValueError('instance must resolve exactly once '+instance)
        m=matches[0];end=close(text,m.end()-1)
        if text[end+1:].lstrip()[0]!=';':raise ValueError('bad instance end')
        stop=end+1
        while text[stop].isspace():stop+=1
        stop+=1
        args=arguments(text[m.end():end])
        spec=ports(xml,master)
        if set(args)-set(spec):raise ValueError('unknown native ports '+str(set(args)-set(spec)))
        endpoints=[]
        for pin,(direction,shape) in spec.items():
            if pin in ('clk','reset'):
                if args.get(pin)!=pin:raise ValueError('resource reset/clock needs explicit ownership')
                continue
            expr=args.get(pin,'')
            if not expr:continue
            service_pin='resource_'+resource_id+'_'+pin
            client_direction={'input':'output','output':'input'}[direction]
            declared.append('    '+client_direction+' wire '+shape+service_pin)
            if direction=='input':assigns.append('    assign '+service_pin+' = '+expr+';')
            else:assigns.append('    assign '+expr+' = '+service_pin+';')
            endpoints.append({'service_pin':service_pin,'macro_pin':pin,
                              'direction':client_direction,'shape':shape.strip() or 'scalar'})
        text=text[:m.start()]+'// Resource '+resource_id+' is supplied by the selected parent binding.\n'+text[stop:]
        requirements.append({'resource':resource_id,'required_native_master':master,
            'selection':'Algo1 instance binding required','ports':endpoints,
            'exclusive_until':'service completion and all accepted responses drained'})
    m=re.search(r'\bmodule\s+(\w+)',text)
    old_name=m[1]
    pos=text.index('(',m.end())
    if text[m.end():pos].strip()=='#':
        pos=text.index('(',close(text,pos)+1)
    end=close(text,pos)
    text=text[:end].rstrip()+',\n'+',\n'.join(declared)+'\n'+text[end:]
    text=re.sub(r'\bmodule\s+'+re.escape(old_name), 'module '+new_name,text,count=1)
    text=text.replace('endmodule','\n'+'\n'.join(assigns)+'\nendmodule',1)
    text=text.replace("// Execute RMSNorm over two leased halves of U0's existing 16 KiB private SRAM.", '// Descriptor-controlled SRAM service; resource instances are selected separately.')
    header='// Control-only service. No physical Block boundary or selected macro instance.\n'
    output=ROOT/'rtl/services'/(new_name+'.sv')
    if new_name=='add_s32_service_controller':
        from normalize_add_service import normalize
        text=normalize(text)
    if new_name=='gated_s32_service_controller':
        from normalize_gated_service import normalize
        text=normalize(text)
    output.write_text(header+text)
    return {'module':new_name,'rtl':str(output.relative_to(ROOT)),
            'source':source,'source_sha256':sha256(original.encode()).hexdigest(),
            'hard_boundary':False,'control_owner':'assigned by Algo1 subject to registered controller capability',
            'resource_requirements':requirements,
            'admission':'not executable until all requirements bind to actual macro implementations',
            'fixed_product_connections':[]}

def main():
    recipes=[
      ('rtl/u0/u_resident_add.sv','add_s32_service_controller',
       [('qkv_e','e_s32_ap64','e')],'u'),
      ('rtl/u0/u_resident_rms_core.sv','rms_s32_service_controller',
       [('norm','block_v2_n','n'),('arithmetic','e_s32_ap64','e')],'u'),
      ('rtl/p_services/rope_e32_s128_commit.sv','rope_s32_service_controller',
       [('provider','e_s32_ap64','e')],'p'),
      ('rtl/p_services/gated_s32_scope.sv','gated_s32_service_controller',
       [('G','g_s32','g')],'p'),
    ]
    services=[extract(s,n,r,AUDIT/(x+'-elaboration.xml')) for s,n,r,x in recipes]
    source=ROOT/'rtl/u0/s32_rms_apply_s128.sv'
    original=source.read_text()
    name='rms_apply_s32_service_controller'
    text=original.replace('module s32_rms_apply_s128','module '+name,1)
    eports=ports(AUDIT/'u-elaboration.xml','e_s32_ap64')
    bindings=[]
    for pin,(direction,shape) in eports.items():
        if pin in ('clk','reset'):continue
        old_pin='e_'+pin
        new_pin='resource_e_'+pin
        text=re.sub(r'\b'+old_pin+r'\b',new_pin,text)
        bindings.append({'service_pin':new_pin,'macro_pin':pin,
                         'direction':{'input':'output','output':'input'}[direction],
                         'shape':shape.strip() or 'scalar'})
    target=ROOT/'rtl/services'/(name+'.sv')
    target.write_text('// Control-only RMS application stage; no selected E instance.\n'+text)
    services.append({'module':name,'rtl':str(target.relative_to(ROOT)),
        'source':str(source.relative_to(ROOT)),'source_sha256':sha256(original.encode()).hexdigest(),
        'hard_boundary':False,'control_owner':'selected registered owner',
        'resource_requirements':[{'resource':'e','required_native_master':'e_s32_ap64',
                                  'ports':bindings,'exclusive_until':'last result consumed'}],
        'admission':'requires command encoder, selected macro and finite SRAM binding',
        'fixed_product_connections':[]})
    from rtl_ports import read
    native=read((ROOT/'rtl/macros/n_s32_mod.sv').read_text())
    control_path=ROOT/'rtl/services/n32_service_controller.sv'
    control=read(control_path.read_text())
    bindings=[]
    for pin,decl in native.items():
        if pin in ('clk','reset'):continue
        service_pin='resource_n_'+pin
        assert service_pin in control
        client=control[service_pin]
        assert decl['shape']==client['shape'] and decl['direction']!=client['direction']
        bindings.append({'service_pin':service_pin,'macro_pin':pin,
                         'direction':client['direction'],'shape':client['shape'].strip() or 'scalar'})
    services.append({'module':'n32_service_controller','rtl':str(control_path.relative_to(ROOT)),
        'source_sha256':sha256(control_path.read_bytes()).hexdigest(),
        'hard_boundary':False,'control_owner':'selected N macro owner',
        'resource_requirements':[{'resource':'n','required_native_master':'n_s32_mod',
                                  'ports':bindings,'exclusive_until':'macro response and SRAM result commit'}],
        'descriptor':{'schema':'NSV1','abi':0x02504e03,'opcodes':{'Softmax':1,'RMSFactor':2,'Argmax':3}},
        'admission':'unit RTL verified; LC dispatch and full plan binding pending',
        'fixed_product_connections':[]})
    for service in services:
        if service['module']=='rms_s32_service_controller':
            service['diagnostic_only']=True
            service['admission']='retired monolithic RMS diagnostic; not an executable candidate'
            service['replacement']='N32 mod RMSFactor stage, explicit selected data transfer, E32 RMS apply stage'
    (ROOT/'hardware/service-controller-contracts.json').write_text(
        json.dumps({'schema':'macro-service-controllers/1','services':services},indent=2)+'\n')
    from build_projection_local_contract import main as register_projection
    register_projection()
    from build_e32_dot_contract import main as register_dot
    register_dot()
    from build_rope_native_contract import main as register_rope
    register_rope()
    from build_rms_apply_native_contract import main as register_rms_apply
    register_rms_apply()
    print('Extracted',len(services),'service controllers and registered local projection; no macro pairing selected')

if __name__=='__main__':main()
