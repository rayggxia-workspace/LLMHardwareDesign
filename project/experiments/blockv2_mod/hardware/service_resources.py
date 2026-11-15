"""Fixed mod adapter inventory; product choices cannot create active selectors."""
from hashlib import sha256
from pathlib import Path

E32_CLIENTS = {
    'add_s32_service_controller': 0,
    'rope_s32_service_controller': 1,
    'rope_native_service_controller': 1,
    'rms_apply_s32_service_controller': 2,
    'rms_apply_native_service_controller': 2,
}

def register(inventory):
    result={}
    root=Path(__file__).resolve().parents[1]
    source=root/'rtl/resources/e32_service_selector.sv'
    for name,macro in inventory['macro_instances'].items():
        if macro['master'] not in ('e_s32_ap64','e_s32_mac_ap64'):continue
        clients=dict(E32_CLIENTS)
        mac_context=macro['master']=='e_s32_mac_ap64'
        if mac_context:clients['e32_dot_service_controller']=3
        result[name+'.service_selector']={
            'kind':'parent_standard_cell_adapter',
            'rtl_module':'e32_service_selector',
            'rtl_source':str(source.relative_to(root)),
            'rtl_sha256':sha256(source.read_bytes()).hexdigest(),
            'control_owner':macro['control_owner'],
            'parameters':{'CLIENTS':max(clients.values())+1,'MAC_CONTEXT':int(mac_context)},
            'client_slots':clients,'macro':name,
            'arbitration':'fixed priority; both result beats; MAC context held from BEGIN through END/ABORT when enabled',
            'capacity':1,
            'status':'RTL candidate; no area/timing calibration',
        }
        pair=root/'rtl/resources/s128_service_selector.sv'
        result[macro['control_owner']+'.S.elementwise_selector']={
            'kind':'parent_standard_cell_adapter','rtl_module':'s128_service_selector',
            'rtl_source':str(pair.relative_to(root)),'rtl_sha256':sha256(pair.read_bytes()).hexdigest(),
            'control_owner':macro['control_owner'],'parameters':{'CLIENTS':3},
            'client_slots':{'add_s32_service_controller':0,'rope_native_service_controller':1,'rms_apply_native_service_controller':2},
            'capacity':1,'arbitration':'fixed priority; retained owner through accepted SRAM response',
            'status':'explicit parent build resource; physical binding and calibration pending'}
    return result
