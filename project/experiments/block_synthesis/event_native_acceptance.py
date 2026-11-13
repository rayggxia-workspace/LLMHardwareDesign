"""Deploy a complete repeated native graph in the frozen two-U RTL fixture."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from event_native_u import assemble_u64, compact_assembler_image, load_assembler
from run import compile_event_graph
from test_event_compiler import native_fixture, pack


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('unexpected native fixture anchor: ' + old)
    return text.replace(old, new)


def reference(layers, seeds):
    values = {'x': seeds['x']}
    current = values['x']
    for i in range(1, layers+1):
        operand = seeds['c0' if i % 2 else 'c1']
        raw = (a+b if i % 2 else a*b for a,b in zip(current,operand))
        current = [max(-32768,min(32767,n)) for n in raw]
        values[f'v{i}'] = current
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path, help='qualified fixture with design and staged source')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir()
    fixture = output/'fixture'
    fixture.mkdir()
    shutil.copytree(args.reference/'design', fixture/'design')
    shutil.copytree(args.reference/'staged', fixture/'staged')
    generated = output/'generated'
    generated.mkdir()

    layers = 16
    model, hardware = native_fixture(layers)
    result = compile_event_graph(model, hardware, budget=0)
    if result['status'] != 'planned' or not result['verification']['passed']:
        raise ValueError('native graph did not compile')
    program = result['outputs']['program']
    source = fixture/'staged/project/control_p_compute_v0_1/run_a2.py'
    lock = hardware['event_model']['native_control']['assembler_sha256']
    binaries = assemble_u64(program,result['resolved_hardware'],
                            load_assembler(source,lock),compact_assembler_image)
    for name, payload in binaries.items():
        (generated/(name+'.bin')).write_bytes(payload)
        words = [int.from_bytes(payload[i:i+16],'little') for i in range(0,len(payload),16)]
        (generated/(name+'.mem')).write_text(''.join(f'{word:032x}\n' for word in words), encoding='ascii')
    (generated/'compile.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

    seeds = {'x': [-100,-20,-5,0,1,12,100,500],
             'c0': [6,-1,1,3,-2,4,2,-3], 'c1': [1,-1,2,-1,1,-2,1,1]}
    numeric = reference(layers,seeds)
    word = lambda value: int.from_bytes(pack(value),'little')
    moves = []
    for row in result['plan']['tasks']:
        for event in row['evaluation']['events']:
            if event['kind'] == 'move':
                src, dst = (result['resolved_hardware']['event_model']['windows'][event[side]]
                            for side in ('src','dst'))
                moves.append((int(src['site'][1]),int(dst['site'][1]),dst['offset']//16,word(numeric[event['value']])))
    expected_writes = 16*(len(moves)+layers)
    bench = fixture/'design/tb_native_pair.sv'
    text = bench.read_text(encoding='utf-8')
    for group, address, name, pattern in (
            (0,42,'x', r"seed\(0,10'd40,128'h[0-9a-f]+\);"),
            (0,40,'c0',r"seed\(0,10'd41,128'h[0-9a-f]+\);"),
            (1,40,'c1',r"seed\(1,10'd40,128'h[0-9a-f]+\);")):
        text,count = re.subn(pattern,f"seed({group},10'd{address},128'h{word(seeds[name]):032x});",text)
        if count != 1:
            raise ValueError('seed anchor changed')
    text = replace_once(text,'|| transfers!=3)',f'|| transfers!={len(moves)})')
    text = replace_once(text,'result_confirmed_write_bytes_o!=80',f'result_confirmed_write_bytes_o!={expected_writes}')
    text = replace_once(text,'commits!=3 ||',f'commits!={len(moves)} ||')
    bench.write_text(text,encoding='utf-8')

    runner = fixture/'design/generated-run.sh'
    text = runner.read_text(encoding='utf-8')
    for field,name in (('MWORDS','mother'),('WORDS0','local0'),('WORDS1','local1')):
        text,count = re.subn(r'\+'+field+r'=\d+',f'+{field}={len(binaries[name])//16}',text)
        if count != 1:
            raise ValueError('image length anchor changed')
    runner.write_text(text,encoding='utf-8')
    logs = fixture/'results'
    subprocess.run(['bash',str(runner),str(fixture),str(logs),'-1'],check=True)

    cases = []
    for path in sorted(logs.glob('*.log')):
        if path.name == 'compile.log':
            continue
        text = path.read_text(encoding='utf-8').split('EPOCH_BEGIN')[-1]
        # The qualified U wrapper has no debug read port. Read the actual
        # SRAM model's committed-write trace for U1.S word 43 (bank 3, row 10).
        final_writes = re.findall(
            r'Writing tb_native_pair\.local_block\[1\].endpoint\.programmable_u\.implementation'
            r'\.datapath\.store\.storage\.banks\[3\]\.memory addr0=00001010 din0=([01]{128})',
            text)
        if len(final_writes) != layers // 2 or int(final_writes[-1],2) != word(numeric[f'v{layers}']):
            raise ValueError('final integer SRAM commit differs: '+path.name)
        def entries(kind):
            return [(int(a),int(b),int(c),int(d,16),int(t)) for a,b,c,d,t in re.findall(
                kind+r' src=(\d+) dst=(\d+) addr=(\d+) data=([0-9a-f]+) cycle=(\d+)',text)]
        writes, commits = entries('WRITE'),entries('COMMIT')
        if [row[:4] for row in writes] != moves or [row[:4] for row in commits] != moves:
            raise ValueError('RTL transfer data or address differs: '+path.name)
        releases = [(int(a),int(t)) for a,t in re.findall(r'RELEASE block=(\d+) cycle=(\d+)',text)]
        if releases != [(row[0],row[-1]) for row in commits] or any(a[-1]>=b[-1] for a,b in zip(writes,commits)):
            raise ValueError('source release/ACK order differs: '+path.name)
        summary = re.search(r'GENERATED_CONTROL_PASS cycles=(\d+) commits=(\d+) confirmed_bytes=(\d+)',text)
        start = re.search(r'START cycle=(\d+)',text)
        if not summary or not start or int(summary[3]) != expected_writes:
            raise ValueError('missing or incorrect RTL retirement summary: '+path.name)
        cases.append({'name':path.stem,'commits':len(commits),'confirmed_bytes':expected_writes,
                      'cycles':int(summary[1])-int(start[1]),'final_sram':numeric[f'v{layers}']})
    if len(cases) != 9:
        raise ValueError('incomplete RTL acceptance')
    report = {'layers':layers,'transfers':len(moves),'images':{k:len(v) for k,v in binaries.items()},
              'cases':cases,'plan_sha256':program['source']['plan_sha256']}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
