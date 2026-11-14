"""Stage a Gather-enabled derivative of the audited main U source."""
from pathlib import Path

PORTS = {
    'req_valid': ('output', 1), 'req_ready': ('input', 1),
    'req_address': ('output', 64), 'req_tag': ('output', 32),
    'req_channel': ('output', 1), 'req_record_beats': ('output', 5),
    'rsp_valid': ('input', 1), 'rsp_ready': ('output', 1),
    'rsp_tag': ('input', 32), 'rsp_data': ('input', 512),
}
ports = ''.join(f'    {direction} wire {f"[{width-1}:0] " if width>1 else ""}dma_{name},\n'
                for name, (direction, width) in PORTS.items())
connections = ', '.join('.dma_'+name for name in PORTS)

def replace(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'source anchor changed: {old}')
    return source.replace(old, new)

def module(source, name, port_anchor):
    source = replace(source, port_anchor, ports + port_anchor)
    if name=='u_n32_controlled_64':
        return replace(source, f'module {name}(', f'module {name} #(parameter ENABLE_INDEXED_GATHER=0) (')
    return replace(source, f'module {name} #(\n',
                   f'module {name} #(\n    parameter ENABLE_INDEXED_GATHER=0,\n')

def dispatch(source):
    source = replace(source, '    reg legacy_active;', '''    reg legacy_active, gather_active;
    wire gather_ready, gather_done, gather_s_valid, gather_s_write, gather_s_take;
    wire [15:0] gather_status;
    wire [31:0] gather_reads, gather_writes;
    wire [9:0] gather_s_addr;
    wire [127:0] gather_s_data;
''')
    source = replace(source, '    wire sending =', '''    // Only a controller command with the native resource can own the S window.
    wire gather_offer = ENABLE_INDEXED_GATHER && operation==16'h0104 &&
        svc_req_kind_o==0 && svc_req_resource_o==0 && !link_reservation;
    wire sending =''')
    source = replace(source, 'wire incoming_admitted = !reset && legacy_available && !sending &&',
                     'wire incoming_admitted = !reset && legacy_available && !sending && !gather_active &&')
    source = replace(source, 'assign svc_req_ready_i = !legacy_active && !preload_busy && (legacy_offer ? e_ready : n_ready);',
                     '''assign svc_req_ready_i = !legacy_active && !gather_active && !preload_busy &&
        (gather_offer ? legacy_available && gather_ready : legacy_offer ? e_ready : n_ready);''')
    source = replace(source, 'assign svc_rsp_valid_i = legacy_active ? e_rsp : n_rsp;',
                     'assign svc_rsp_valid_i = gather_active ? gather_done : legacy_active ? e_rsp : n_rsp;')
    for field in ('kind', 'token', 'sequence', 'job', 'epoch', 'task'):
        lhs = 'task_sequence' if field == 'task' else field
        source = replace(source, f'assign svc_rsp_{lhs}_i = legacy_active ? e_{field}',
                         f'assign svc_rsp_{lhs}_i = (legacy_active || gather_active) ? e_{field}')
    for field, e_field, g_field in (('status', 'status', 'status'), ('read_bytes', 'reads', 'reads'),
                                   ('write_bytes', 'writes', 'writes')):
        source = replace(source, f'assign svc_rsp_{field}_i = legacy_active ? e_{e_field}',
                         f'assign svc_rsp_{field}_i = gather_active ? gather_{g_field} : legacy_active ? e_{e_field}')
    source = replace(source, 'if (reset) begin\n            legacy_active<=0;',
                     'if (reset) begin\n            legacy_active<=0;\n            gather_active<=0;')
    source = replace(source, '            if (legacy_active && e_rsp && svc_rsp_ready_o) begin',
                     '''            if (gather_active && gather_done && svc_rsp_ready_o) gather_active<=0;
            if (gather_offer && svc_req_valid_o && svc_req_ready_i) begin
                gather_active<=1;
                e_kind<=svc_req_kind_o; e_token<=svc_req_token_o; e_sequence<=svc_req_sequence_o;
                e_job<=svc_req_job_o; e_epoch<=svc_req_epoch_o; e_task<=svc_req_task_sequence_o;
            end
            if (legacy_active && e_rsp && svc_rsp_ready_o) begin''')
    for expr in ('l_req', 'l_wr', 'l_addr', 'l_data', 'l_take'):
        selected = dict(l_req='gather_s_valid', l_wr='gather_s_write', l_addr='gather_s_addr',
                        l_data='gather_s_data', l_take='gather_s_take')[expr]
        s = next(line for line in source.splitlines() if f'assign {expr} =' in line)
        rhs = s.split(' = ',1)[1][:-1]
        source = replace(source, s, f'    assign {expr} = gather_active ? {selected} : ({rhs});')
    source = replace(source, 'svc_req_valid_o&&!legacy_offer&&!legacy_active&&!preload_busy',
                     'svc_req_valid_o&&!legacy_offer&&!legacy_active&&!preload_busy&&!gather_offer&&!gather_active')
    source = replace(source, 'svc_req_valid_o&&legacy_offer&&!legacy_active&&!preload_busy',
                     'svc_req_valid_o&&legacy_offer&&!legacy_active&&!preload_busy&&!gather_active')
    source = replace(source, 'svc_rsp_ready_o&&!legacy_active', 'svc_rsp_ready_o&&!legacy_active&&!gather_active')
    source = replace(source, 'legacy_active || link_reservation || receiving',
                     'legacy_active || link_reservation || receiving || gather_active')
    source = replace(source, '    wire e_in_valid,', f'''    if (ENABLE_INDEXED_GATHER) begin: indexed_gather
        u_indexed_gather provider (
            .clk(clk_i),.reset,
            .svc_valid(svc_req_valid_o && gather_offer && svc_req_ready_i),.svc_ready(gather_ready),
            .descriptor(svc_req_descriptor_o),
            .rsp_valid(gather_done),.rsp_ready(gather_active && svc_rsp_ready_o),
            .status(gather_status),.read_bytes(gather_reads),.write_bytes(gather_writes),
            {connections},
            .s_req_valid(gather_s_valid),.s_req_write(gather_s_write),
            .s_req_ready(gather_active && l_ready),.s_req_address(gather_s_addr),.s_req_data(gather_s_data),
            .s_rsp_valid(gather_active && l_rsp),.s_rsp_ready(gather_s_take),.s_rsp_data(l_result)
        );
    end else begin: no_gather
        assign {{gather_ready,gather_done,gather_s_valid,gather_s_write,gather_s_take,
                gather_status,gather_reads,gather_writes,gather_s_addr,gather_s_data}} = '0;
        assign {{dma_req_valid,dma_req_address,dma_req_tag,dma_req_channel,dma_req_record_beats,
                dma_rsp_ready}} = '0;
    end
    wire e_in_valid,''')
    return source

def main():
    p = Path('u_n32_controlled_64.sv')
    p.write_text(module(p.read_text(), 'u_n32_controlled_64', '    input wire incoming_valid,')
                 if '\n    input wire incoming_valid,' in p.read_text()
                 else module(p.read_text(), 'u_n32_controlled_64', 'input wire incoming_valid,'))
    p = Path('wrapper.sv')
    source = module(p.read_text(), 'u_n32_native_frame_64','    input wire incoming_valid,')
    source = replace(source, '    u_n32_controlled_64 local_group (',
                     '    u_n32_controlled_64 #(.ENABLE_INDEXED_GATHER(ENABLE_INDEXED_GATHER)) local_group (')
    source = replace(source, '        .incoming_valid,', '        '+connections+',\n        .incoming_valid,')
    p.write_text(source)
    p = Path('u_n32_legacy_dispatch.svh')
    p.write_text(dispatch(p.read_text()))

if __name__ == '__main__':
    main()
