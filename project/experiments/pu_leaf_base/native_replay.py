"""Exercise ordinary E descriptors and simultaneous SEND through real U LCs."""
from pathlib import Path

def stage_native(design, mode):
    if mode not in ('duplex', 'fma-duplex'):
        raise ValueError(mode)
    image = design / 'images.py'
    text = image.read_text()
    begin, end = text.index('    ops = ['), text.index('    mother_program =')
    setup = '''    ops = []
    for side in range(2):
        rows = []
'''
    if mode == 'fma-duplex':
        setup += '''        rows += [command(0, 3, (23, 24), 26), command(0, 3, (23, 24, 25), 27)]
        sources = (26, 27, 41, 43)
        destinations = (41, 43, 45, 47)
'''
    else:
        setup += '''        sources = (40, 41)
        destinations = (41, 43)
'''
    setup += '''        for source, destination in zip(sources, destinations):
            rows += [dict(native_op=RESERVE, native0=destination),
                     dict(native_op=SEND, native0=source | destination << 10),
                     dict(native_op=RECEIVE)]
        ops.append(rows)
'''
    text = text[:begin] + setup + text[end:]
    text = text.replace('(2 if kind < 0 else kind) if block == 0 else 0', '0')
    image.write_text(text)
    path = design / 'tb_native_pair.sv'
    text = path.read_text()
    text = text.replace('i==0 ? (SINGLE_KIND<0 ? 2 : SINGLE_KIND) : 0', '0')
    # Hold the first request until both independent sources have obtained S
    # data. An unbuffered TX deterministically locks both S response ports.
    old = '    wire accept_request = stall==0 || cycle%7==1;'
    assert text.count(old)==1
    text = text.replace(old, '''    reg [1:0] offered=0;
    always @(posedge clk_i) begin
        if (!rst_ni) offered<=0;
        else offered<=offered | link_valid;
    end
    wire accept_request = (&offered) && (stall==0 || cycle%7==1);''')
    text = text.replace('transfers<=transfers+1;', "transfers<=transfers+int'(link_ack[0] && link_ack_ready[1])+int'(link_ack[1] && link_ack_ready[0]);")
    begin = text.index('            default: begin', text.index('task automatic configure_and_start'))
    end = text.index('            end', begin)+len('            end')
    if mode=='fma-duplex':
        seeds = '''            default: begin
                seed(0,0,{8{16'd5}}); seed(1,0,{8{16'd5}});
                seed(0,23,{8{16'd2}}); seed(0,24,{8{16'd3}}); seed(0,25,{8{16'd5}});
                seed(1,23,{8{16'd3}}); seed(1,24,{8{16'd4}}); seed(1,25,{8{16'd7}});
            end'''
        per_side, writes = 4, 192
        expected = """                0: expected_word={8{16'(i==0 ? 6 : 12)}};
                1: expected_word={8{16'(i==0 ? 11 : 19)}};
                2: expected_word={8{16'(i==0 ? 12 : 6)}};
                3: expected_word={8{16'(i==0 ? 19 : 11)}};"""
    else:
        seeds = '''            default: begin
                seed(0,40,INPUT_WORD); seed(1,40,RESULT_WORD);
            end'''
        per_side, writes = 2, 64
        expected = '''                0: expected_word=i==0 ? INPUT_WORD : RESULT_WORD;
                1: expected_word=i==0 ? RESULT_WORD : INPUT_WORD;'''
    text = text[:begin] + seeds + text[end:]
    text = text.replace('(SINGLE_KIND<0 ? 2 : 0)', str(per_side*2))
    assert text.count('(fault!=0 ? 48 : 80)')==1
    text = text.replace('(fault!=0 ? 48 : 80)', str(writes))
    begin = text.index('            default: begin', text.index('case (SINGLE_KIND)', text.index('while(!result_valid_o)')))
    end = text.index('            end', begin)+len('            end')
    text = text[:begin] + f'''            default: begin
                if (sent[0]!={per_side} || sent[1]!={per_side})
                    $fatal(1,"incomplete bidirectional SRAM replay");
            end''' + text[end:]
    monitor = '''    integer sent[2];
    reg [1:0] was_stalled=0;
    reg [127:0] stalled_data[2];
    reg [9:0] stalled_addr[2];
    for (genvar i=0; i<2; i=i+1) begin: scoreboard
        reg [127:0] expected_word;
        always @* begin
            expected_word=0;
            case(sent[i])
''' + expected + '''
                default: expected_word=0;
            endcase
        end
        always @(posedge clk_i) begin
            if (!rst_ni) begin sent[i]<=0; was_stalled[i]<=0; end
            else begin
                if (was_stalled[i] && (!link_valid[i] || link_data[i]!==stalled_data[i] || link_addr[i]!==stalled_addr[i]))
                    $fatal(1,"U%0d changed blocked SEND payload",i);
                was_stalled[i]<=link_valid[i] && !(link_ready[1-i] && accept_request);
                stalled_data[i]<=link_data[i]; stalled_addr[i]<=link_addr[i];
                if (link_valid[i] && link_ready[1-i] && accept_request) begin
                    if (link_data[i]!==expected_word)
                        $fatal(1,"U%0d send %0d got=%032h expected=%032h",i,sent[i],link_data[i],expected_word);
                    sent[i]<=sent[i]+1;
                end
            end
        end
    end
'''
    text = text.replace('    localparam [127:0] SENTINEL=', monitor+'    localparam [127:0] SENTINEL=')
    path.write_text(text)
    runner = design / 'run.sh'
    text = runner.read_text()
    old = 'if [[ $kind == -1 ]]; then cases+=("stalled 1 0 0" "fault 0 1 0" "stalled-fault 1 1 0" "reset 1 0 1"); fi'
    assert text.count(old)==1
    runner.write_text(text.replace(old, 'if [[ $kind == -1 ]]; then cases+=("stalled 1 0 0" "reset 1 0 1"); fi'))
