"""Generic upper routing CLI. Inputs are geometry or a bound #227 manifest."""
import argparse
import json
from pathlib import Path
from search import route
from check import verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='standalone spec, or #227 request with --base/--technology')
    p.add_argument('output', type=Path)
    p.add_argument('--base', type=Path)
    p.add_argument('--technology', type=Path, help='object with technology and optional obstacles')
    p.add_argument('--rounds', type=int, default=8)
    p.add_argument('--max-expansions', type=int, default=100000, help='per-net per-round node budget')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--check', type=Path, help='verify existing route instead of searching')
    a = p.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    request = None
    spec = read(a.input)
    if a.base or a.technology:
        from adapter import bind_request
        from route_contract import read_base
        if not (a.base and a.technology):
            p.error('--base and --technology must be supplied together')
        request = spec
        rules = read(a.technology)
        spec = bind_request(request, read_base(a.base), rules['technology'], rules.get('obstacles', []))
    if a.check:
        result = verify(spec, read(a.check))
    else:
        result = route(spec, rounds=a.rounds, max_expansions=a.max_expansions, seed=a.seed)
        if request:
            from adapter import failure_feedback
            result['feedback'] = failure_feedback(request, result, str(a.output))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    if not a.check and result['failed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
