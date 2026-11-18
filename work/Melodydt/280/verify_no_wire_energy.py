"""Audit published v2 input hashes, original windows, scopes and component sums."""
from hashlib import sha256
import json
from math import isclose,isfinite
from pathlib import Path
from seven_model_no_wire_power import MODELS, NEW_TERMS, HERE


def require(test,message):
    if not test:raise ValueError(message)


def verify(model):
    path=HERE/(model+'_tlm_power_v2_no_wire.json')
    result=json.loads(path.read_bytes())
    prior=json.loads((HERE/(model+'_tlm_power_v1.json')).read_bytes())
    require(result['wire_parasitics_loaded'] is False and result['coverage_complete'] is False,
            'scope or wire exclusion missing')
    for relative,digest in result['input_sha256'].items():
        require(sha256((HERE/relative).read_bytes()).hexdigest()==digest,'input changed: '+relative)
    for name,row in result['windows'].items():
        old=prior['windows'][name]
        for key in ('elapsed_ps','tokens','tokens_per_second','ddr_transport_beats_64b'):
            require(row[key]==old[key],model+'/'+name+': frozen '+key)
        require(row['components']['ddr_devices']==old['components']['ddr_devices'],'DDR changed')
        require(set(old['components']) <= set(row['components']),'previous component disappeared')
        require(row['local_pm_installs']==(0 if name=='decode' else 4),'PM boot repeated or missing')
        require(row['local_pm_runtime_reads']==23*sum(row['top_level_service_calls_by_site']),'LC PM mapping')
        for component,values in row['components'].items():
            a,b=values['energy_nj_per_window']
            require(isfinite(a) and isfinite(b) and 0<=a<=b,'invalid component '+component)
        for edge in (0,1):
            components=row['components']
            chip=sum(v['energy_nj_per_window'][edge] for k,v in components.items() if k!='ddr_devices')
            ddr=components['ddr_devices']['energy_nj_per_window'][edge]
            added=sum(components[k]['energy_nj_per_window'][edge] for k in NEW_TERMS if k in components)
            for key,value in [('covered_on_chip_subtotal',chip),('covered_subtotal',chip+ddr),('newly_included_subtotal',added)]:
                m=row[key]
                require(isclose(m['energy_nj_per_window'][edge],value,rel_tol=1e-12),'component sum '+key)
                require(isclose(m['average_power_w'][edge]*row['elapsed_ps']/1000,value,rel_tol=1e-12),'W/ps conversion')
                require(isclose(m['energy_mj_per_token'][edge]*row['tokens']*1e6,value,rel_tol=1e-12),'mJ/token conversion')
            same=row['same_old_components_without_wire']['energy_nj_per_window'][edge]
            require(isclose(same+added,chip+ddr,rel_tol=1e-12),'old/new coverage bridge')
            require(row['read_dma_idle_w'] is None,'unknown read idle changed to a value')
        require(not any(k.startswith('read_dma') for k in row['components']),'proxy entered base total')
    return {'model':model,'windows':3,'passed':True,'result_sha256':sha256(path.read_bytes()).hexdigest()}


if __name__=='__main__':
    result={'scope':'21 frozen windows; input hashes, nonnegative components, units, DDR separation and new coverage',
            'models':[verify(model) for model in MODELS]}
    print(json.dumps(result,indent=2))
