"""Strict complete STA receiver. Input quality, routing and RC coverage are separate.

Use every native endpoint, both native violation counts and real-valued worst
electrical margins. Reported decimals are never used to round away violations.
"""
import json
import math
from pathlib import Path


def inspect(folder):
    endpoints={}
    for line in (folder/'endpoints.tsv').read_text().splitlines():
        name,*values=line.split('\t')
        assert name not in endpoints and len(values)==2
        endpoints[name]=[float(v)for v in values]
    summary={};electrical={};clocks={}
    for line in (folder/'timing-summary.tsv').read_text().splitlines():
        name,*values=line.split('\t')
        if name=='clock':
            assert len(values)==2 and values[0]not in clocks
            clocks[values[0]]=values[1]
        elif name in ('capacitance','slew','fanout'):
            assert name not in electrical and len(values)==3
            count,slack,limit=values
            electrical[name]=dict(count=int(count),slack=float(slack),limit=float(limit))
        else:
            assert name not in summary and len(values)==1
            summary[name]=float(values[0])
    assert set(electrical)=={'capacitance','slew','fanout'}
    assert set(summary)=={'setup_checks','hold_checks','check_setup','time_unit_seconds','capacitance_unit_farads'}
    checks=dict(endpoint_set_nonempty=bool(endpoints),all_endpoint_slacks_finite=bool(endpoints)and all(math.isfinite(v)for row in endpoints.values()for v in row),
        all_setup_nonnegative=bool(endpoints)and all(v[0]>=0 for v in endpoints.values()),
        all_hold_nonnegative=bool(endpoints)and all(v[1]>=0 for v in endpoints.values()),
        native_setup_count_zero=summary['setup_checks']==0,native_hold_count_zero=summary['hold_checks']==0,
        native_check_setup_pass=summary['check_setup']==1,
        native_time_ns=abs(summary['time_unit_seconds']-1e-9)<1e-20,
        native_capacitance_ff=abs(summary['capacitance_unit_farads']-1e-15)<1e-26,
        core_clock_propagated=clocks=={'core':'1'})
    for kind,row in electrical.items():
        finite=all(math.isfinite(row[k])for k in ('slack','limit'))
        # The native API uses a large infinity sentinel for no limit. Preserve
        # it as N/A; it is not a measured positive design-rule margin.
        row['has_limit']=finite and 0<row['limit']<1e30
        checks[kind+'_count_zero']=row['count']==0
        checks[kind+'_margin_nonnegative']=finite and (row['slack']>=0 if row['has_limit']else row['count']==0)
    checks['capacitance_and_slew_limits_exist']=all(electrical[k]['has_limit']for k in ('capacitance','slew'))
    return dict(passed=all(checks.values()),checks=checks,endpoint_count=len(endpoints),
        minimum_setup_ns=min((v[0]for v in endpoints.values()),default=None),
        minimum_hold_ns=min((v[1]for v in endpoints.values()),default=None),
        endpoints_without_finite_both_limits=[n for n,v in endpoints.items()if not all(math.isfinite(x)for x in v)],
        native_summary=summary,electrical=electrical,clocks=clocks,
        scope='Complete native STA only; physical routing/PG/geometry/RC coverage and exact final-netlist functionality remain independently required')


def fixture(root,out,run):
    """Real DFF/STA/SPEF controls exercise the receiver, without PPA claims."""
    def one(name,load_ff,period):
        folder=out/name;folder.mkdir()
        (folder/'probe.v').write_text('module sta_probe(input clk,d,output q); DFF_X1 u0(.CK(clk),.D(d),.Q(q)); endmodule\n')
        (folder/'probe.sdc').write_text('set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um\n'
            'create_clock -name core -period %g [get_ports clk]\nset_clock_uncertainty .1 [get_clocks core]\n'
            'set_clock_transition .05 [get_clocks core]\nset_input_delay -clock core -max .2 [get_ports d]\n'
            'set_input_delay -clock core -min .5 [get_ports d]\nset_output_delay -clock core -max .2 [get_ports q]\n'
            'set_output_delay -clock core -min .01 [get_ports q]\nset_driving_cell -lib_cell BUF_X2 -pin Z [get_ports d]\n'
            'set_load %g [get_ports q]\n'%(period,load_ff))
        spef='*SPEF "IEEE 1481-1998"\n*DESIGN "sta_probe"\n*DATE "2026-10-27"\n*VENDOR "LLMHardwareDesign"\n*PROGRAM "receiver-control"\n*VERSION "1"\n'
        spef+='*DESIGN_FLOW "PIN_CAP NONE"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 FF\n*R_UNIT 1 OHM\n*L_UNIT 1 UH\n*PORTS\nclk I\nd I\nq O\n'
        for net,pin,direction,cap in [('clk','CK','I',1),('d','D','I',1),('q','Q','O',1)]:
            external='O'if net=='q'else'I'
            spef+='\n*D_NET %s %g\n*CONN\n*P %s %s\n*I u0:%s %s\n*CAP\n1 %s %g\n2 u0:%s %g\n*RES\n1 %s u0:%s .1\n*END\n'%(net,cap,net,external,pin,direction,net,cap/2,pin,cap/2,net,pin)
        (folder/'probe.spef').write_text(spef)
        platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
        script='read_liberty {'+str(platform/'lib/NangateOpenCellLibrary_typical.lib')+'}\n'
        for lef in ['NangateOpenCellLibrary.tech.lef','NangateOpenCellLibrary.macro.mod.lef']:
            script+='read_lef {'+str(platform/'lef'/lef)+'}\n'
        script+='read_verilog {'+str(folder/'probe.v')+'}\nlink_design sta_probe\nwrite_db {'+str(folder/'probe.odb')+'}\n'
        (folder/'prepare.tcl').write_text(script)
        # Running each process in its own cwd keeps all real outputs separate.
        import subprocess
        for argv,log in [(['openroad','-no_init','-exit','prepare.tcl'],'prepare.log'),
                         (['openroad','-no_init','-exit',str(root/'project/experiments/block_v1/native_sta.tcl')],'sta.log')]:
            import os
            env=dict(os.environ,BV1_ODB=str(folder/'probe.odb'),BV1_SDC=str(folder/'probe.sdc'),BV1_SPEF=str(folder/'probe.spef'))
            with(folder/log).open('w')as stream:
                code=subprocess.run(argv,cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
            assert code==0,(name,log)
        result=inspect(folder)
        (folder/'sta-quality.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    positive=one('positive',2,10)
    cap=one('bad-capacitance',1000,10)
    clock=one('bad-setup',2,.1)
    record=dict(schema='block-v1-native-sta-receiver-control/1',positive=positive,
        bad_capacitance=cap,bad_setup=clock,scope='Actual native DFF/STA and explicit test SPEF; receiver controls only, no routed physical qualification')
    (out/'native-sta-control.json').write_text(json.dumps(record,indent=2)+'\n')
    assert positive['passed'],'Native positive STA control failed; inspect all actual margins'
    assert not cap['passed']and cap['electrical']['capacitance']['count']>0
    assert not clock['passed']and clock['native_summary']['setup_checks']>0
