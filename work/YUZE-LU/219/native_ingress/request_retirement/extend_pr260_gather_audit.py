"""Stage the strict PR 260 RTL audit with explicit post-CALL Gather checks."""
import argparse
from pathlib import Path


def replace_one(text, old, new):
    if text.count(old) != 1:
        raise ValueError('unsupported PR 260 audit revision: '+old[:70])
    return text.replace(old, new)


def extend(text):
    text = replace_one(text, 'from struct import pack, unpack\n',
                       'from struct import pack, unpack\n\n'
                       'from gather_index_evidence import EVENT_FIELDS as GATHER_EVENTS, GatherIndexEvidence\n')
    text = replace_one(text, 'def verify_pages(lines, program, evidence, signatures=None, inputs=None):',
                       'def verify_pages(lines, program, evidence, signatures=None, inputs=None, gather=None):')
    text = replace_one(text, '    observed_inputs = 0\n', '''    observed_inputs = 0
    gather = {} if gather is None else gather
    observed_gather = set()
    gather_checker = None
''')
    text = replace_one(text, '        elif name in PAGE_EVENTS:', '''        elif name in GATHER_EVENTS:
            if gather_checker is None or complete:
                raise ValueError("unexpected post-CALL Gather handshake")
            gather_checker.consume(line)
            if gather_checker.cycle <= last_page_cycle:
                raise ValueError("Gather handshake is out of order with request events")
            last_page_cycle = gather_checker.cycle
        elif name in PAGE_EVENTS:''')
    text = replace_one(text, '                    bindings = inputs.get(tuple(row[:2]), ())\n', '''                    key = tuple(row[:2])
                    bindings = inputs.get(key, ())
                    if key in gather:
                        selected = gather[key]
                        if (bindings != [(selected["word"], None)] or
                                selected["generation"] != row[2] or row[6] != 1 << selected["target"]):
                            raise ValueError("post-CALL Gather differs from sealed runtime index or target")
                        gather_checker = GatherIndexEvidence(
                            step=key[0], page=key[1], generation=row[2], target=selected["target"],
                            word=selected["word"], token=input_token, launch_cycle=cycle)
                        bindings = ()
''')
    text = replace_one(text, '                evidence["page_count"] = active\n', '''                if gather_checker is not None:
                    gather_checker.finish(cycle)
                    observed_gather.add(gather_checker.identity[:2])
                    observed_inputs += 1
                    gather_checker = None
                evidence["page_count"] = active
''')
    text = replace_one(text, '    if inputs is not None:\n        if index_commits', '''    if observed_gather != gather.keys():
        raise ValueError("missing configured Gather handshake evidence")
    if gather:
        evidence["post_call_gather_pages"] = len(observed_gather)
    if inputs is not None:
        if index_commits''')
    text = replace_one(text, '    args = parser.parse_args()\n', '''    parser.add_argument("--gather-bindings", type=Path)
    parser.add_argument("--gather-bindings-sha256")
    args = parser.parse_args()
''')
    text = replace_one(text, '    with args.rtl_log.open', '''    gather = None
    if args.gather_bindings or args.gather_bindings_sha256:
        if not (args.gather_bindings and args.gather_bindings_sha256):
            raise ValueError("post-CALL Gather requires a pinned phase binding")
        from gather_index_evidence import load_bindings
        gather = load_bindings(args.gather_bindings, args.gather_bindings_sha256, program_evidence,
                               state_contract["phases"])
    with args.rtl_log.open''')
    return replace_one(text, 'program_evidence, signatures, inputs), state_contract, binding)',
                       'program_evidence, signatures, inputs, gather), state_contract, binding)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(extend(args.source.read_text()))


if __name__ == '__main__':
    main()
