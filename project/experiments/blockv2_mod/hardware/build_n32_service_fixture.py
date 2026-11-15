"""Verification fixture only: one service controller plus one selected N macro."""
from pathlib import Path
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1]
service=read((ROOT/'rtl/services/n32_service_controller.sv').read_text())
macro=read((ROOT/'rtl/macros/n_s32_mod.sv').read_text())
external={n:p for n,p in service.items() if not n.startswith('resource_n_')}
lines=['module n32_selected_service_fixture #(parameter logic [31:0] TOPOLOGY=18503)(']
lines.append(',\n'.join(' '+p['direction']+' wire '+p['signed']+p['shape']+n for n,p in external.items()))
lines.append(');')
for n,p in service.items():
    if n.startswith('resource_n_'):lines.append(' wire '+p['signed']+p['shape']+n+';')
lines.append(' n32_service_controller #(.TOPOLOGY(TOPOLOGY)) control(.*);')
connections=[]
for n,p in macro.items():
    connection=n if n in ('clk','reset') else 'resource_n_'+n
    assert connection in service
    if n not in ('clk','reset'):
        q=service[connection]
        assert p['shape']==q['shape'] and p['signed']==q['signed'],(n,p,q)
        assert p['direction']!=q['direction']
    connections.append('.'+n+'('+connection+')')
lines.append(' n_s32_mod N('+','.join(connections)+');')
lines.append('endmodule')
out=ROOT/'evidence/architecture-revision-185/n32_selected_service_fixture.sv'
out.write_text('// Verification fixture. Not a physical Block or a selected product plan.\n'+'\n'.join(lines)+'\n')
print(out)
