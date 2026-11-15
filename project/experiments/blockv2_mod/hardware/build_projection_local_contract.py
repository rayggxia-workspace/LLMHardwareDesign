"""Register macro endpoints for an unselected local-source projection option."""
from pathlib import Path
from hashlib import sha256
import json,re
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project')
def ports(p):
    text=p.read_text()
    text=re.sub(r'`ifdef USE_POWER_PINS.*?`endif','',text,flags=re.S)
    return read(text)
def main():
    source=ROOT/'rtl/services/projection_local_service_controller.sv'
    sp=ports(source)
    specifications=[
       ('m','m_native_leaf_s32',BASE/'rtl/w8a16_v1/m_native_leaf_s32.sv',
        {n:n[len('resource_m_'):] for n in sp if n.startswith('resource_m_')}),
       ('s','local_s_p',BASE/'rtl/s_sram/local_s_p.sv',
        {'s_req_valid':'req_valid','s_req_write':'req_write','s_req_ready':'req_ready',
         's_req_address':'req_addr','s_req_data':'req_data','s_rsp_valid':'rsp_valid',
         's_rsp_ready':'rsp_ready','s_rsp_data':'rsp_data'})]
    requirements=[]
    for role,master,path,mapping in specifications:
        mp=ports(path);bindings=[]
        for pin,macro_pin in mapping.items():
            s,m=sp[pin],mp[macro_pin]
            assert s['shape']==m['shape'] and s['direction']!=m['direction'],(pin,s,m)
            bindings.append(dict(service_pin=pin,macro_pin=macro_pin,**s))
        requirements.append({'resource':role,'required_native_master':master,
            'selection':'Algo1 must select explicit macro-to-parent-controller connections',
            'native_source':str(path),'native_source_sha256':sha256(path.read_bytes()).hexdigest(),
            'ports':bindings})
    contract={'module':'projection_local_service_controller','rtl':str(source.relative_to(ROOT)),
        'rtl_sha256':sha256(source.read_bytes()).hexdigest(),'hard_boundary':False,
        'resource_requirements':requirements,'execution_admitted':False,
        'unresolved_requirements':['LC MPR1 dispatch and complete graph candidate integration',
          'finite DDR activation and M weight client arbitration',
          'SRAM arbitration with other selected services and feeder exclusion',
          'unused S_P feeder pins tied or assigned by actual parent assembly',
          'full projection numerical verification with real M and S_P',
          'plan-selected endpoint realization'],
        'assumed_connections':[],
        'sram_response_error_policy':'S_P has no error pin; tie s_rsp_error low only at verified S_P binding',
        'scope':'unselected structural option, not an executable whole-graph candidate'}
    p=ROOT/'hardware/service-controller-contracts.json'
    data=json.loads(p.read_text())
    data['services']=[s for s in data['services'] if s['module']!=contract['module']]+[contract]
    p.write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main()
