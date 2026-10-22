"""Check parent/child SPEF stitching against an explicit flat RC reference."""
import json
import re


def spef(design, ports, nets):
    text='''*SPEF "IEEE 1481-1998"
*DESIGN "%s"
*DATE "2026-10-22"
*VENDOR "LLMHardwareDesign"
*PROGRAM "controlled-stitch-selftest"
*VERSION "1"
*DESIGN_FLOW "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
*PORTS
''' % design
    text+=''.join(name+' '+direction+'\n' for name,direction in ports)
    for name,connections,caps,resistors in nets:
        text+='*D_NET '+name+' '+str(sum(c for n,c in caps))+'\n*CONN\n'
        text+=''.join(kind+' '+pin+' '+direction+'\n' for kind,pin,direction in connections)
        text+='*CAP\n'+''.join(str(i)+' '+node+' '+str(cap)+'\n' for i,(node,cap) in enumerate(caps,1))
        text+='*RES\n'+''.join(str(i)+' '+a+' '+b+' '+str(r)+'\n' for i,(a,b,r) in enumerate(resistors,1))+'*END\n'
    return text


def execute(root,run_tcl,technology,liberty):
    (root/'fixture.v').write_text('''module fixture_child(input A, CK, output Q);
wire n;
BUF_X1 b(.A(A),.Z(n));
DFF_X1 f(.D(n),.CK(CK),.Q(Q));
endmodule
module fixture_top(input A, CK, output Q);
wire boundary;
BUF_X2 p(.A(A),.Z(boundary));
fixture_child u(.A(boundary),.CK(CK),.Q(Q));
endmodule
''')
    ports=[('A','I'),('CK','I'),('Q','O')]
    def chain(name,driver,load,cap,resistance,driver_port=False,load_port=False):
        return (name,[('*P' if driver_port else '*I',driver,'I' if driver_port else 'O'),
                      ('*P' if load_port else '*I',load,'O' if load_port else 'I')],
                [(driver,cap/2),(load,cap/2)],[(driver,load,resistance)])
    parent=[chain('A','A','p:A',.002,20,True),chain('boundary','p:Z','u:A',.010,100),
            chain('CK','CK','u:CK',.002,20,True),chain('Q','u:Q','Q',.002,20,False,True)]
    child=[chain('A','A','b:A',.010,100,True),chain('n','b:Z','f:D',.010,100),
           chain('CK','CK','f:CK',.001,20,True),chain('Q','f:Q','Q',.002,20,False,True)]
    flat=[parent[0],chain('u/n','u/b:Z','u/f:D',.010,100)]
    for name,driver,junction,load,c1,c2,r1,r2,dp,lp in [
        ('boundary','p:Z','boundary:1','u/b:A',.010,.010,100,100,False,False),
        ('CK','CK','CK:1','u/f:CK',.002,.001,20,20,True,False),
        ('Q','u/f:Q','Q:1','Q',.002,.002,20,20,False,True)]:
        flat.append((name,[('*P' if dp else '*I',driver,'I' if dp else 'O'),
                           ('*P' if lp else '*I',load,'O' if lp else 'I')],
                     [(driver,c1/2),(junction,(c1+c2)/2),(load,c2/2)],
                     [(driver,junction,r1),(junction,load,r2)]))
    for name,design,nets in [('parent','fixture_top',parent),('child','fixture_child',child),('flat','fixture_top',flat)]:
        (root/(name+'.spef')).write_text(spef(design,ports,nets))
    results={}
    for name in ['hierarchical','flat','missing_parent_negative_control']:
        text=technology+'read_liberty {'+str(liberty)+'}\nread_verilog {'+str(root/'fixture.v')+'}\n'
        text+='link_design '+('-hier ' if name!='flat' else '')+'fixture_top\n'
        text+='create_clock -period 2.5 [get_ports CK]\nset_input_delay .1 [get_ports A]\n'
        text+='set_output_delay .1 [get_ports Q]\nset_input_transition .05 [get_ports A]\nset_load 5 [get_ports Q]\n'
        if name=='flat':text+='read_spef {'+str(root/'flat.spef')+'}\n'
        else:
            if name=='hierarchical':text+='read_spef {'+str(root/'parent.spef')+'}\n'
            text+='read_spef -path u {'+str(root/'child.spef')+'}\n'
        text+='set_propagated_clock [all_clocks]\nreport_parasitic_annotation -report_unannotated\n'
        text+='report_worst_slack -max -digits 9\nreport_worst_slack -min -digits 9\n'
        text+='report_checks -path_delay max -format full_clock_expanded -digits 9\ncheck_setup -verbose\n'
        run_tcl('stitch-'+name,text)
        log=(root/('stitch-'+name+'.log')).read_text()
        results[name]={k:float(re.search('worst slack '+k+r'\s+([-\d.]+)',log)[1]) for k in ['max','min']}
    errors={k:abs(results['hierarchical'][k]-results['flat'][k]) for k in ['max','min']}
    negative=max(abs(results['hierarchical'][k]-results['missing_parent_negative_control'][k]) for k in ['max','min'])
    passed=max(errors.values())<.000001 and negative>.001
    (root/'stitch-validation.json').write_text(json.dumps(dict(passed=passed,results=results,
        absolute_errors_ns=errors,missing_parent_effect_ns=negative,
        scope='Controlled two-level buffer/DFF network: parent and child boundary RC versus explicitly joined flat SPEF; missing-parent negative control'),indent=2)+'\n')
    assert passed, 'Hierarchical SPEF RC stitch differs from flat reference'
