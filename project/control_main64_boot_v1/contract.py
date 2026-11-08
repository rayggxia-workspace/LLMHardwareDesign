"""R8.1: explicit, bounded contract for the main64 deployment candidate."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NAMES = ('U', 'F', 'C', 'P', 'J')
PAIRS = ((0,0),(1,1),(2,2),(3,3),(4,4),(0,3),(1,3),(2,3),(4,3))
ABI = 0x01930001
CAPACITY = 0x17630001


def topology(kind, peer=None):
    if type(kind) is not int or kind not in range(5):
        raise ValueError('unknown Block kind')
    peer=kind if peer is None else peer
    if type(peer) is not int or peer not in range(5):raise ValueError('unknown peer kind')
    return 0x01938000 + kind*16 + peer


def common_ports():
    import re
    text = (ROOT / 'project/control_rtl_min_v0_1/ports.svh').read_text()
    result = {}
    for direction, width, name in re.findall(r'(input|output) wire\s*(\[\d+:\d+\])?\s*(\w+)', text):
        if not name.startswith(('svc_', 'close_', 'trace_')):
            result[name] = [direction, width]
    return result


def native_sources(kind, lane, sources):
    """Capability validation for tools; not a replacement for main RTL checks."""
    topology(kind)
    maxima = {0:(3,2), 1:(2,2), 2:(2,2,1)}
    if kind not in maxima or type(lane) is not int or lane not in range(len(maxima[kind])):
        raise ValueError('lane not available')
    if type(sources) is not int or not 0 <= sources <= maxima[kind][lane]:
        raise ValueError('source arity not available')
    return True


def host_allowed(kind, op, deployed=False):
    topology(kind)
    if op == 11:
        return kind in (1,2,3)
    if op == 12:
        return kind != 4 and not deployed
    if op in (13,14):
        return kind == 4
    return op in range(11)


def contract():
    profiles = []
    for kind, name in enumerate(NAMES):
        profiles.append(dict(name=name, kind=kind, block_ids=[0,1], same_type_topology=topology(kind),
            topology_rule='one cohort ID, identical in mother and both locals; selected by pair',
            native_abi=ABI, capacity_id=CAPACITY,
            local_module=('r82_u_pu_u_controlled_64','r82_f_cfj_group_f','r82_c_cfj_group_c',
                          'r82_p_pu_p_controlled_64','r82_j_cfj_group_j')[kind],
            native_ops=([0x100,0x101,0x102,0x103,0x104] if kind==0 else
                        [0x100,0x101,0x102,0x103] if kind in (1,2) else
                        [0x110,0x111,0x112] if kind==3 else [0x120,0x121]),
            max_lane_sources=({0:[3,2],1:[2,2],2:[2,2,1]}.get(kind)),
            host_s_read=host_allowed(kind,11), host_s_write_before_deploy=host_allowed(kind,12),
            host_s_write_after_deploy=False, fragment_and_committed_output=kind==4,
            direct_edges=({0:'N-to-E 128-bit loop, paired native op 0x104',
                           1:'G-to-E 32-bit loop',2:'G-to-E 32-bit loop',
                           3:'M-to-G 32-bit loop',4:'E-to-S 128-bit writeback loop'}[kind])))
    return dict(schema='main64-deployment-contract/1', issue=179,
        upstream_main='c4d7b960599b9d292f27eb4429d5f226a7156c95', branch_parent='f087c3c863e8f6b703e94f112f734ed4f68e34f7',
        instruction_bits=64,image_version=2,pm_port_bits=128,pm_bytes_each=16384,pm_banks_each=4,
        mother_targets=2,global_tokens=8,resident_tasks_per_local=1,inflight_services_per_local=1,
        maximum_image_bytes={'mother':4736,'local':8320},instruction_count_max=256,execution_descriptors_max=16,
        clock_period_ns='3.333333333',clock_domains=1,
        configuration=dict(request_op_bits=3,address_bits=14,address_unit='byte',alignment_bytes=16,
            ops={'0':'BEGIN','1':'WRITE16','2':'READ16','3':'VERIFY/proof','4':'PREPARE','5':'ABORT'},
            host_target={'0':'mother','1':'LC0','2':'LC1','3':'cohort'},
            pm_ownership='mother internal; two external local PMs; no program memory in testbench',
            host_management_ops={str(i):n for i,n in enumerate(('RELEASE','BEGIN','WRITE16','READ16','VERIFY','PREPARE','ABORT','DEPLOY','START','STATUS','RESULT','S_READ','S_WRITE','READ_J_OUTPUT','WRITE_J_FRAGMENT'))}),
        messages=dict(bits=512,identity=['job','epoch','task_sequence','token','service_sequence'],
            data_bits=128,data_address_unit='16-byte S row',data_address_bits=10,
            route='fixed opposite endpoint; P accepts passive writes only while its LC is READY',
            ack='actual destination SRAM write response; never request acceptance',
            recovery_qualification='R8.4 pending; cohort reset only in this candidate'),
        qualified_instruction_subset={'mother':['G_CALL','G_WAIT','G_END'],'local':['L_EXEC','L_WAIT','L_END']},
        namespace='generated LC/service module identifiers are mechanically renamed per type; main raw sources unchanged; JOIN-only unused outputs explicitly open',
        optional_ports='P/U close inputs tied zero and outputs unused; CFJ trace outputs explicitly unused; object-close programs outside the admitted subset',
        cf_host_read='main group_top verify_read option; held response adapter; new candidate, not old physical qualification',
        bounded_j=dict(output_fifo_words=4,joins_per_task=1,epoch_min=1,epoch_max=255),
        pairs=[{'name':NAMES[a]+'/'+NAMES[b],'kinds':[a,b],'topology':topology(a,b)} for a,b in PAIRS],profiles=profiles,
        pending=['R8.3 task compiler/audit alignment','R8.4 complete transport/recovery supervision',
                 'R8.5 complete system matrix/coverage','R8.6 presynthesis refreeze and later combined STA/physical'])


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args()
    data=json.dumps(contract(),ensure_ascii=False,indent=2)+'\n'
    if a.out:a.out.write_text(data,encoding='utf-8',newline='\n')
    else:print(data)
