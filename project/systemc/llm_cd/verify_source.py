"""Bind every staged translation unit/header to the immutable uploaded archive."""
from pathlib import Path
import argparse, ast, hashlib, json, tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('evidence', type=Path)
    args = p.parse_args()
    seal = json.loads((args.evidence / 'sealed-index.json').read_bytes())
    assert sha(args.archive.read_bytes()) == seal['source_archive']['sha256']
    repo = Path(__file__).resolve().parents[3]
    exact, newline_only = [], []
    with tarfile.open(str(args.archive), 'r:gz') as archive:
        def member(name):
            stream = archive.extractfile(name if name.startswith('control-source/') else 'source/' + name)
            assert stream is not None, name
            return stream.read()
        runner = member('project/systemc/llm_cd/run.py').decode('utf-8')
        cmake = [n.value for n in ast.walk(ast.parse(runner))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and n.value.startswith('cmake_minimum_required')]
        assert len(cmake) == 1
        for name, expected in seal['compiled_source_files'].items():
            if name == 'CMakeLists.txt':
                raw = cmake[0].encode('utf-8')
            elif name == 'llm/tensor_link.hpp':
                raw = (args.evidence / 'build-evidence/generated-tensor-link.hpp').read_bytes()
                original = member('project/systemc/llm/tensor_link.hpp').decode('utf-8').replace('\r\n', '\n')
                assert '    return cd_.exchange(input);' in raw.decode('utf-8')
                assert original.count('    if (!enabled)\n      return input;') == 1
            elif name.startswith('include/control/'):
                raw = member('control-source/project/systemc/' + name)
                if name.endswith('/dma.hpp'):
                    raw = raw.decode('utf-8').replace('\r\n', '\n').replace(
                        'std::optional<Completion> completion() const',
                        '[[gnu::noinline]] std::optional<Completion> completion() const').encode('utf-8')
            else:
                source = 'project/systemc/' + name
                if name == 'llm/payload.hpp':
                    source = 'project/systemc/llm_cd/payload.hpp'
                elif name == 'payload_test.cpp':
                    source = 'project/systemc/llm_cd/payload_test.cpp'
                raw = member(source)
            assert dict(bytes=len(raw), sha256=sha(raw)) == expected, name
        # Code published now must match executed archive; documentation and new
        # evidence-only audit scripts were added later and are not execution inputs.
        members = [m.name[len('source/'):] for m in archive.getmembers()
                   if m.isfile() and m.name.startswith('source/')]
        names = [name for name in members if
                 ((name.startswith('project/systemc/llm/') and name.endswith(('.hpp', '.cpp')))
                  or (name.startswith('project/systemc/include/blocks/') and name.endswith('.hpp'))
                  or name in ('project/systemc/llm_cd/run.py', 'project/systemc/llm_cd/payload.hpp',
                                'project/systemc/llm_cd/payload_test.cpp',
                                'project/systemc/llm_cd/remote_suite.py',
                                'project/systemc/llm_cd/remote_suite.sbatch'))]
        for name in names:
            old, current = member(name), (repo / name).read_bytes()
            assert old.replace(b'\r\n', b'\n') == current.replace(b'\r\n', b'\n'), name
            (exact if old == current else newline_only).append(name)
    print(json.dumps(dict(passed=True, archive_sha256=seal['source_archive']['sha256'],
                          compiled_files=len(seal['compiled_source_files']),
                          current_exact=exact, current_newline_only=newline_only), indent=2))


if __name__ == '__main__':
    main()
