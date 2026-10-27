"""Build a clearly marked PRIVATE min-output diagnostic; never replace OpenSTA.

Reuses one pinned build's immutable archives/objects, copies libOpenSTA.a,
recompiles only MakeTimingModel, and links a differently named probe. Not a
supported OpenSTA feature or a candidate for signoff. Original license stays.
"""
import argparse
import difflib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

from audit import file_sha, require


def patch_source(text, normalize_driver=False, analysis='min'):
    require(analysis in ('min','max'), 'probe output analysis')
    edits = (("min_max_(MinMax::max()),", f"min_max_(MinMax::{analysis}()),"),
             ("const MinMax *min_max = MinMax::max();", "const MinMax *min_max = min_max_;"))
    for old, new in edits:
        require(text.count(old) == 1, "unsupported MakeTimingModel source; exact two edits required")
        text = text.replace(old, new)
    if normalize_driver:
        extra = [('#include "Path.hh"', '#include "Path.hh"\n#include "PathExpanded.hh"'),
            ('Arrival data_delay = src_path->arrival();', '''Arrival data_delay = src_path->arrival();
    // QA127 probe: boundary starts at the actual input port, after the
    // external driver. Internal input-net RC remains downstream of it.
    PathExpanded boundary_path(src_path, sta_);
    const Path *boundary_start = boundary_path.startPath();
    if (boundary_start && network->isTopLevelPort(boundary_start->pin(sta_)))
      data_delay = delayDiff(data_delay, boundary_start->arrival(), sta_);'''),
            ('Arrival delay = path->arrival();\n          OutputDelays &delays = output_pin_delays[output_pin];', '''Arrival delay = path->arrival();
          // QA127 probe: retain input-net RC, exclude external-driver arrival.
          PathExpanded boundary_path(path, this);
          const Path *boundary_start = boundary_path.startPath();
          if (boundary_start && network_->isTopLevelPort(boundary_start->pin(this)))
            delay = delayDiff(delay, boundary_start->arrival(), this);
          OutputDelays &delays = output_pin_delays[output_pin];''')]
        for old,new in extra:
            require(text.count(old) == 1, 'unsupported driver-boundary patch target')
            text = text.replace(old,new)
    return "// QA127 MODIFIED SOURCE: private boundary diagnostic, not upstream OpenSTA.\n"+text


def execute(source, build, expected_source_sha256, output, normalize_driver=False, analysis='min'):
    source, build, output = Path(source).resolve(), Path(build).resolve(), Path(output).resolve()
    archive, executable = build/'libOpenSTA.a', build/'sta'
    flags_path, link_path = build/'CMakeFiles/OpenSTA.dir/flags.make', build/'CMakeFiles/sta.dir/link.txt'
    require(file_sha(source) == expected_source_sha256, "pinned source mismatch")
    require(not output.is_relative_to(build) and not source.is_relative_to(output), "probe output overlaps original build/source")
    originals = {str(p): file_sha(p) for p in (source, archive, executable, flags_path, link_path)}
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "block-v1-min-output-probe-build/1", "passed": False, "started": time.time(),
               "analysis":analysis,"normalize_external_driver_at_boundary":normalize_driver,
               "purpose": "Private diagnosis only; not upstream OpenSTA or a qualified model exporter",
               "builder_sha256": file_sha(Path(__file__)), "original_inputs": originals, "commands": []}
    def command(argv):
        with (output/'build.log').open('a') as log:
            result = subprocess.run(argv, cwd=build, stdout=log, stderr=subprocess.STDOUT)
        receipt['commands'].append({'argv': argv, 'cwd': str(build), 'returncode': result.returncode})
        require(result.returncode == 0, "probe build command failed; inspect preserved log")
    try:
        raw = source.read_text()
        modified = patch_source(raw,normalize_driver,analysis)
        (output/'MakeTimingModel.cc').write_text(modified)
        (output/'min-output.patch').write_text(''.join(difflib.unified_diff(raw.splitlines(True), modified.splitlines(True),
            fromfile='upstream/search/MakeTimingModel.cc', tofile='private-probe/MakeTimingModel.cc')))
        flags = {}
        for line in flags_path.read_text().splitlines():
            if line.startswith(('CXX_DEFINES =', 'CXX_INCLUDES =', 'CXX_FLAGS =')):
                key, value = line.split('=', 1)
                flags[key.strip()] = shlex.split(value.strip())
        require(set(flags) == {'CXX_DEFINES', 'CXX_INCLUDES', 'CXX_FLAGS'}, "unrecognized compile flags")
        obj = output/'MakeTimingModel.cc.o'
        command(['/usr/bin/c++', *flags['CXX_DEFINES'], *flags['CXX_INCLUDES'], *flags['CXX_FLAGS'], '-iquote', str(source.parent),
                 '-c', str(output/'MakeTimingModel.cc'), '-o', str(obj)])
        copied_archive = output/'libOpenSTA-min-output-probe.a'
        shutil.copyfile(archive, copied_archive)
        members = subprocess.check_output(['/usr/bin/ar','t',str(copied_archive)], text=True).splitlines()
        require(members.count(obj.name) == 1, "archive target member count")
        command(['/usr/bin/ar','r',str(copied_archive),str(obj)])
        argv = shlex.split(link_path.read_text())
        require(argv.count('libOpenSTA.a') == 1 and argv.count('-o') == 1, "unrecognized native link command")
        argv[argv.index('libOpenSTA.a')] = str(copied_archive)
        argv[argv.index('-o')+1] = str(output/('sta-'+analysis+'-output-probe'))
        argv = ['-flto=2' if word == '-flto' else word for word in argv]
        command(argv)
        require(all(file_sha(Path(p)) == h for p,h in originals.items()), "original tool/source modified")
        receipt['original_inputs_unchanged'] = True
        receipt['passed'] = True
        return receipt
    finally:
        receipt['finished'] = time.time()
        receipt['outputs'] = {p.name:file_sha(p) for p in output.iterdir() if p.is_file() and p.name != 'build-receipt.json'}
        (output/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--build',required=True)
    parser.add_argument('--expected-source-sha256',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--normalize-driver',action='store_true')
    parser.add_argument('--analysis',choices=['min','max'],default='min')
    args = parser.parse_args()
    result = execute(args.source,args.build,args.expected_source_sha256,args.output,args.normalize_driver,args.analysis)
    print(json.dumps({'passed': result['passed'], 'original_inputs_unchanged': result.get('original_inputs_unchanged',False)}))
