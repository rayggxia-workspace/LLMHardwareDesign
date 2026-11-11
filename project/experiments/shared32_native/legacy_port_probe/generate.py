"""Generate a single-factor fork; never edit the frozen shared-pool sources."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('single-factor anchor count: ' + repr(before))
    return text.replace(before, after)


def generate(repo, out, r1, r2, r4, feeder_bytes):
    if feeder_bytes not in (16, 32):
        raise ValueError('only 16/32-byte shared consumers are permitted')
    repo, out = Path(repo).resolve(), Path(out).resolve()
    frozen = repo / 'project/experiments/shared_pool_study'
    original = load(frozen / 'generate_shared_pool.py', 'frozen_pool_generator')
    prior = original.generate(repo, out, r1, r2, r4)
    changes = []
    if feeder_bytes == 16:
        header = out / 'shared_pool.hpp'
        before = header.read_text(encoding='utf8')
        after = once(before,
            'for(U offset=0;offset<take;offset+=32){const U n=std::min<U>(32,take-offset);',
            'for(U offset=0;offset<take;offset+=16){const U n=std::min<U>(16,take-offset);')
        # Disabled-pool RESULT is exactly unchanged, including its metadata.
        after = once(after, r'\"A_feeder_bytes_per_cycle\":32"',
                     r'\"A_feeder_bytes_per_cycle\":"<<(capacity?16:32)')
        header.write_bytes(after.encode('utf8'))
        changes = ['shared consumer quantum/advance 32 -> 16 bytes',
                   'enabled-pool metadata reports 16; disabled pool retains 32']
    generated = {p.name: sha(p) for p in out.iterdir()
                 if p.suffix in ('.cpp', '.hpp', '.inc')}
    changed = sorted(name for name, digest in generated.items()
                     if digest != prior['generated_sha256'][name])
    if changed != (['shared_pool.hpp'] if feeder_bytes == 16 else []):
        raise ValueError('single-factor generated source closure changed: ' + repr(changed))
    result = dict(schema=1, shared_consumer_bytes_per_cycle=feeder_bytes,
                  changes=changes, frozen_generation=prior,
                  generated_sha256=generated,
                  generator_sha256=sha(__file__),
                  local_suffix_bytes_per_cycle_unchanged=32,
                  native_full_model_tokens_per_second=None)
    (out / 'port-generation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    return result


def derive_audit(frozen_path, out, feeder_bytes):
    """Strengthen the frozen independent audit to the selected shared width."""
    text = Path(frozen_path).read_text(encoding='utf8')
    if feeder_bytes == 16:
        text = once(text, 'A_feeder_bytes_per_cycle=32', 'A_feeder_bytes_per_cycle=16')
        text = once(text, "((w['consumed_bytes'] + 31) // 32)",
                    "((w['consumed_bytes'] + 15) // 16)")
        text = once(text, 'its 32B/cycle feeder', 'its 16B/cycle feeder')
    Path(out).write_bytes(text.encode('utf8'))
    return load(out, 'port_probe_audit_' + str(feeder_bytes))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for arg in ('repo', 'out', 'r1-calibration', 'r2-calibration', 'r4-calibration'):
        parser.add_argument('--' + arg, type=Path, required=True)
    parser.add_argument('--feeder-bytes', type=int, choices=(16, 32), required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.repo, args.out, args.r1_calibration,
                              args.r2_calibration, args.r4_calibration, args.feeder_bytes), indent=2))
