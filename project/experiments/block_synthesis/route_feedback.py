"""Package scoped observations; no automatic hard constraints or success claim."""
import argparse
import json
from pathlib import Path
from route_contract import feedback, verify_feedback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('observations', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8'))
    observations = json.loads(args.observations.read_text(encoding='utf-8'))
    result = feedback(request, observations)
    verify_feedback(result, request)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
