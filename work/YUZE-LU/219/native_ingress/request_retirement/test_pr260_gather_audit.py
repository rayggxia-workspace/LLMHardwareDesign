"""Exercise the strict page reader with observed Gather and protocol peers."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from audit_gather_index_trace import marker, negative_controls, verify
from gather_index_evidence import load_bindings
from hashlib import sha256
import json


def module(path):
    spec = spec_from_file_location('pr260_reader', path)
    result = module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main(code, log, bindings):
    reader = module(code)
    source = [x for x in log.read_text().splitlines() if x.startswith('NATIVE_GATHER_')]
    identity = dict(step=1, page=0, generation=2, target=3, word=512, token=81917)
    terminal = verify(source, **identity)
    *_, start = marker(source[0], ('step','page','generation','token','cycle'))
    deployed = [(0,0,1,64,160,111,1), (1,0,2,256,160,222,8)]
    before = [
        'NATIVE_PHASE_START job=7 step=0 input=0 cycle=1 ps=10',
        'NATIVE_INPUT_COMMIT step=0 page=0 generation=1 word=4 data=ab cycle=2',
        'NATIVE_PAGE_LAUNCH step=0 page=0 generation=1 base=64 bytes=160 crc=111 targets=1 cycle=3',
        'NATIVE_PAGE_COMMIT generation=1 status=0 cycle=4',
        'NATIVE_PHASE_COMMIT job=7 step=0 kv=512 token=81917 cycle=5 ps=50',
        'NATIVE_TOKEN_RETIRE job=7 step=0 token=81917 cycle=6 ps=60',
        'NATIVE_PHASE_START job=7 step=1 input=81917 cycle=7 ps=70',
        f'NATIVE_PAGE_LAUNCH step=1 page=0 generation=2 base=256 bytes=160 crc=222 targets=8 cycle={start}',
    ]
    end = terminal['cycle']
    after = [
        f'NATIVE_PAGE_COMMIT generation=2 status=0 cycle={end}',
        f'NATIVE_PHASE_COMMIT job=7 step=1 kv=513 token=17 cycle={end+1} ps={(end+1)*10}',
        f'NATIVE_TOKEN_RETIRE job=7 step=1 token=17 cycle={end+2} ps={(end+2)*10}',
        f'NATIVE_REQUEST_DONE outputs=2 error=0 cycle={end+3}',
    ]
    inputs = {(0,0): [(4,0xab)], (1,0): [(512,None)]}
    gather = {(1,0): dict(generation=2,target=3,word=512)}
    evidence = {'expected_pages':2}
    list(reader.verify_pages(before+source[1:-1]+after,iter(deployed),evidence,inputs=inputs,gather=gather))
    assert evidence['input_pages']==2 and evidence['page_count']==2 and evidence['post_call_gather_pages']==1
    legacy = before[:-1]+[f'NATIVE_INPUT_COMMIT step=1 page=0 generation=2 word=512 data={81917<<64:x} cycle=8',before[-1]]+after
    list(reader.verify_pages(legacy,iter(deployed),{'expected_pages':2},inputs=inputs))
    mutations = [source[2:-1], source[1:-2], source[1:3]+source[4:-1]]
    for events in mutations:
        try:
            list(reader.verify_pages(before+events+after,iter(deployed),{'expected_pages':2},inputs=inputs,gather=gather))
        except ValueError:
            continue
        raise AssertionError('accepted incomplete post-CALL Gather trace')
    negative_controls(source, identity)
    data=bindings.read_bytes()
    table=json.loads(data)
    program={'deployment_sha256':table['request_sha256'],'expected_pages':table['total_pages']}
    actual=load_bindings(bindings,sha256(data).hexdigest(),program,table['phases'])
    assert len(actual)==127 and actual[127,0]['word']==512
    print('PASS legacy input, strict post-CALL input, incomplete traces rejected, actual 127 page bindings')


if __name__ == '__main__':
    main(*(Path(x) for x in sys.argv[1:]))
