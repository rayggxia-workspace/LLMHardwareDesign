"""Derive finite shared-A width/bank studies without editing frozen sources."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('single source anchor count: ' + repr(before))
    return text.replace(before, after)


RESERVE = r'''  // Each group is four 128-bit 1RW lanes. Distinct groups can serve
  // distinct requests together; same-address requests are never broadcast.
  U address_group(U address)const{return @GROUP_EXPR@;}
  U reserve(U at,bool write,U address){
   const U group=address_group(address),duration=port_cycles*C;
   U request=at;
   // DDR fill remains one global 64B write per clock, even with two groups.
   if(write)request=fill_port.reserve(at,duration)-duration;
   const U end=group_ports[group].reserve(request,duration),start=end-duration;
   if(write)require(start==request,"fill ingress/group scheduling conflict");
   for(U lane=0;lane<4;++lane){const U e=banks[group*4+lane].reserve(start,duration);
    require(e==end,"lane bank schedule differs from group");}
   // Aggregate counters are sums of work, not a fictitious serial port.
   port.busy+=duration;port.queue_wait+=start-at;
   group_wait[group]+=start-at;
   if(write){++group_writes[group];++write_beats;write_bus_bytes+=64;write_wait+=start-at;}
   else{++group_reads[group];++read_beats;read_bus_bytes+=64;}
   return end;
  }
'''


def advanced_header(before, width, groups, mapping):
    text = before
    text = once(text, '  capacity=cap;depth=fifo;latency=delay;port_cycles=cycles_per_port;',
                '  require(cap==0||cap==32768,"width study requires a fixed 32KiB pool");\n'
                '  capacity=cap;depth=fifo;latency=delay;port_cycles=cycles_per_port;')
    text = once(text, ' U active=0,completed_tiles=0;',
                ' U active=0,completed_tiles=0;\n'
                ' U consumer_cycles=0,consumer_peak_bytes_per_cycle=0,two_line_consume_cycles=0,issue_peak_per_cycle=0;')
    text = once(text, ' Calendar port; std::array<Calendar,4> banks; std::array<Worker,2> workers;',
                f' Calendar port,fill_port; std::array<Calendar,{groups}> group_ports;\n'
                f' std::array<Calendar,{groups*4}> banks; std::array<Worker,2> workers;\n'
                f' std::array<U,{groups}> group_reads{{}},group_writes{{}},group_wait{{}};')
    start = text.index('  // A 64B access') if '  // A 64B access' in text else text.index(' // A 64B access')
    stop = text.index(' U write(', start)
    expr = 'U(0)' if groups == 1 else ('(address/16384)%2' if mapping == 'contiguous' else '(address/64)%2')
    replacement = RESERVE.replace('@GROUP_EXPR@', expr)
    if groups == 1:
        replacement = replacement.replace('U address)const{return U(0);}', 'U address)const{(void)address;return U(0);}')
    text = text[:start] + replacement + text[stop:]
    text = once(text, 'end=reserve(end,true);', 'end=reserve(end,true,p*64);')
    if width == 128:
        start, stop = text.index(' U feed('), text.index(' void end()')
        text = text[:start] + (HERE / 'feed128.inc').read_text(encoding='utf8') + text[stop:]
    else:
        text = once(text, 'end=reserve(issued,false)', 'end=reserve(issued,false,address)')
        text = once(text, 'for(U offset=0;offset<take;offset+=32){const U n=std::min<U>(32,take-offset);consumer+=C;w.consumed_bytes+=n;',
                    f'for(U offset=0;offset<take;offset+={width}){{const U n=std::min<U>({width},take-offset);consumer+=C;w.consumed_bytes+=n;\n'
                    '     ++w.consumer_cycles;w.consumer_peak_bytes_per_cycle=std::max(w.consumer_peak_bytes_per_cycle,n);')
        text = once(text, 'next_issue=issued+C;', 'next_issue=issued+C;w.issue_peak_per_cycle=1;')
    text = once(text,
        r'<<",\"banks\":4,\"bank_width_bits\":128,\"bank_mode\":\"1RW lockstep lanes\",\"fabric_bytes\":64,\"A_feeder_bytes_per_cycle\":32"',
        f'<<",\\\"banks\\\":{groups*4},\\\"bank_width_bits\\\":128,\\\"bank_mode\\\":\\\"1RW lockstep lanes per group\\\",\\\"fabric_bytes\\\":{groups*64},\\\"A_feeder_bytes_per_cycle\\\":{width}"')
    text = once(text,
        '<<",\\\"completed_tiles\\\":"<<w.completed_tiles',
        '<<",\\\"consumer_cycles\\\":"<<w.consumer_cycles\n'
        '    <<",\\\"consumer_peak_bytes_per_cycle\\\":"<<w.consumer_peak_bytes_per_cycle\n'
        '    <<",\\\"two_line_consume_cycles\\\":"<<w.two_line_consume_cycles\n'
        '    <<",\\\"issue_peak_per_cycle\\\":"<<w.issue_peak_per_cycle\n'
        '    <<",\\\"completed_tiles\\\":"<<w.completed_tiles')
    old_tail = '   out<<"],\\\"bank_service_subcycles\\\":[";for(int i=0;i<4;++i){if(i)out<<",";out<<banks[i].busy;}out<<"]}";'
    # The frozen source has two leading spaces on this line.
    old_tail = old_tail[1:]
    new_tail = f'''  out<<"],\\\"bank_service_subcycles\\\":[";for(U i=0;i<{groups*4};++i){{if(i)out<<",";out<<banks[i].busy;}}
  out<<"],\\\"service_groups\\\":{groups},\\\"bank_mapping\\\":\\\"{mapping}\\\",\\\"fill_ingress_bytes_per_cycle\\\":64";
  out<<",\\\"group_service_subcycles\\\":[";for(U i=0;i<{groups};++i){{if(i)out<<",";out<<group_ports[i].busy;}}
  out<<"],\\\"group_read_beats\\\":[";for(U i=0;i<{groups};++i){{if(i)out<<",";out<<group_reads[i];}}
  out<<"],\\\"group_write_beats\\\":[";for(U i=0;i<{groups};++i){{if(i)out<<",";out<<group_writes[i];}}
  out<<"],\\\"group_wait_subcycles\\\":[";for(U i=0;i<{groups};++i){{if(i)out<<",";out<<group_wait[i];}}out<<"]}}";'''
    return once(text, old_tail, new_tail)


def generate(repo, out, r1, r2, r4, width, groups=1, mapping='single'):
    if width not in (16, 32, 64, 128) or groups not in (1, 2):
        raise ValueError('width must be 16/32/64/128; groups must be 1/2')
    if (groups == 1 and mapping != 'single') or (groups == 2 and mapping not in ('contiguous', 'striped')):
        raise ValueError('mapping must be single for one group, contiguous/striped for two')
    repo, out = Path(repo).resolve(), Path(out).resolve()
    frozen = repo / 'project/experiments/shared_pool_study'
    original = load(frozen / 'generate_shared_pool.py', 'frozen_width_pool_generator')
    prior = original.generate(repo, out, r1, r2, r4)
    header = out / 'shared_pool.hpp'
    before = header.read_text(encoding='utf8')
    legacy = groups == 1 and width in (16, 32)
    if legacy:
        after = before
        if width == 16:
            after = once(after, 'for(U offset=0;offset<take;offset+=32){const U n=std::min<U>(32,take-offset);',
                         'for(U offset=0;offset<take;offset+=16){const U n=std::min<U>(16,take-offset);')
            after = once(after, r'\"A_feeder_bytes_per_cycle\":32"', r'\"A_feeder_bytes_per_cycle\":"<<(capacity?16:32)')
    else:
        after = advanced_header(before, width, groups, mapping)
    header.write_bytes(after.encode('utf8'))
    generated = {p.name: sha(p) for p in out.iterdir() if p.suffix in ('.cpp', '.hpp', '.inc')}
    changed = sorted(name for name, digest in generated.items() if digest != prior['generated_sha256'][name])
    expected = [] if width == 32 and groups == 1 else ['shared_pool.hpp']
    if changed != expected:
        raise ValueError('generated source closure changed: ' + repr(changed))
    result = dict(schema=1, shared_consumer_bytes_per_cycle=width, service_groups=groups,
                  bank_mapping=mapping, fifo_beat_bytes=64, fill_ingress_bytes_per_cycle=64,
                  issue_limit_per_P_per_cycle=2 if width == 128 else 1,
                  frozen_generation=prior, generated_sha256=generated, changed_generated_files=changed,
                  generator_sha256=sha(__file__), template_sha256={'feed128.inc': sha(HERE / 'feed128.inc')},
                  changes=[] if width == 32 and groups == 1 else
                    [f'shared consumer {width} B/clock', f'{groups} service group(s), {mapping} mapping',
                     'fill ingress remains one 64B write/clock',
                     'explicit finite two-line issue/consume' if width == 128 else 'one line request/P/clock'],
                  legacy_control=legacy, local_suffix_bytes_per_cycle_unchanged=32,
                  native_full_model_tokens_per_second=None,
                  arbitration='per-group arrival-order Calendar; finite P credits; no broadcast',
                  mapping_contract='contiguous: (byte_address/16384)%2; striped: (byte_address/64)%2',
                  limitations=['Only conditional timing, not RTL or physical qualification.',
                               'S32/K256/S96, local suffix and all other frozen arithmetic remain unchanged.',
                               '128B consumer requires two already returned 64B line entries.'])
    (out / 'width-generation.json').write_bytes((json.dumps(result, indent=2)+'\n').encode('utf8'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('repo', 'out', 'r1-calibration', 'r2-calibration', 'r4-calibration'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--width', type=int, choices=(16, 32, 64, 128), required=True)
    parser.add_argument('--groups', type=int, choices=(1, 2), default=1)
    parser.add_argument('--mapping', choices=('single', 'contiguous', 'striped'), default='single')
    args = parser.parse_args()
    print(json.dumps(generate(args.repo, args.out, args.r1_calibration, args.r2_calibration,
                              args.r4_calibration, args.width, args.groups, args.mapping), indent=2))
