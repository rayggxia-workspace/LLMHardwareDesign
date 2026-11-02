"""PRIVATE single-export probe: cache native drive load-delay, retain wire RC.

Only the pinned source hashes below are accepted. This is a research probe,
not upstream OpenSTA or a general multi-design/signoff tool.
"""
import argparse
import difflib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

from audit import require,file_sha
from build_min_probe import patch_source

MODEL_SHA='ee117099f485ce17f9fdd24bbaf62569cb3f56107615bf88411aaebd889acde0'
GRAPH_SHA='d03e3c98a7428ae3670168ca95c76a8fa84115d4a22084ac0445a2bbeaee1518'

CACHE=r'''
// QA127 private cache: one source design and one model export per process.
using QaDriveKey = std::tuple<const Pin*,const RiseFall*,const Scene*,const MinMax*>;
struct QaDriveValue { Delay delay; const TimingArc *arc; bool ambiguous; bool reported; };
static std::map<QaDriveKey,QaDriveValue> qa_drive_cache;
static std::mutex qa_drive_mutex;
Delay qaNativeInputDriveDelay(const Path *start, const StaState *sta)
{
  const Pin *pin=start->pin(sta);
  const RiseFall *rf=start->transition(sta);
  const Scene *scene=start->scene(sta);
  const MinMax *mm=start->minMax(sta);
  const QaDriveKey key{pin,rf,scene,mm};
  std::lock_guard<std::mutex> lock(qa_drive_mutex);
  auto found=qa_drive_cache.find(key);
  if (found==qa_drive_cache.end() || found->second.ambiguous)
    throw std::runtime_error("QA127 requires one cached native driver arc per input/edge/scene/analysis");
  auto &value=found->second;
  if (!value.reported) {
    std::cerr << "QA127_DRIVER_COMPONENT\t" << sta->network()->pathName(pin)
              << "\t" << rf->shortName() << "\t" << mm->to_string()
              << "\t" << delayAsFloat(value.delay) << "\n";
    value.reported=true;
  }
  return value.delay;
}
'''

def patches(model,graph,analysis):
    model=patch_source(model,True,analysis)
    model=model.replace('namespace sta {','namespace sta {\nDelay qaNativeInputDriveDelay(const Path*,const StaState*);',1)
    for state in ['sta_','this']:
        old=f'boundary_start->arrival(), {state}'
        require(model.count(old)==1,'private native drive model target')
        model=model.replace(old,f'qaNativeInputDriveDelay(boundary_start, {state}), {state}')
    require(graph.count('namespace sta {')==1,'native drive namespace target')
    graph=graph.replace('namespace sta {','namespace sta {\n'+CACHE,1)
    marker='const ArcDelay load_delay = delayDiff(gate_delay, intrinsic_delay, this);'
    require(graph.count(marker)==1,'native drive component target')
    graph=graph.replace(marker,marker+r'''
    // Capture the exact native component BEFORE annotation adds wire delay.
    {
      const QaDriveKey key{drvr_pin,drvr_rf,scene,min_max};
      std::lock_guard<std::mutex> lock(qa_drive_mutex);
      auto found=qa_drive_cache.find(key);
      if (found==qa_drive_cache.end())
        qa_drive_cache.emplace(key,QaDriveValue{load_delay,arc,false,false});
      else {
        found->second.ambiguous |= found->second.arc != arc;
        found->second.delay=load_delay;
      }
    }
''',1)
    graph='// QA127 MODIFIED SOURCE: private native drive diagnostic, not upstream.\n#include <map>\n#include <tuple>\n#include <mutex>\n#include <stdexcept>\n#include <iostream>\n#include "Path.hh"\n'+graph
    return model,graph

def execute(source_root,build,output,analysis):
    source_root,build,output=[Path(p).resolve()for p in (source_root,build,output)]
    sources=[source_root/'search/MakeTimingModel.cc',source_root/'dcalc/GraphDelayCalc.cc']
    require([file_sha(p) for p in sources]==[MODEL_SHA,GRAPH_SHA],'private pinned source hashes')
    archive,exe=build/'libOpenSTA.a',build/'sta'
    flags_path,link_path=build/'CMakeFiles/OpenSTA.dir/flags.make',build/'CMakeFiles/sta.dir/link.txt'
    require(not output.is_relative_to(build) and not source_root.is_relative_to(output),'private output overlap')
    originals={str(p):file_sha(p) for p in [*sources,archive,exe,flags_path,link_path]}
    output.mkdir(parents=True,exist_ok=False)
    (output/'builder.py').write_bytes(Path(__file__).read_bytes())
    receipt={'schema':'block-v1-min-output-probe-build/1','passed':False,'started':time.time(),'analysis':analysis,
        'variant':'native-driver-load-component','scope':'One source design/export per process; one native arc per input context; private diagnostic only',
        'builder_sha256':file_sha(Path(__file__)),'model_patcher_sha256':file_sha(Path(__file__).with_name('build_min_probe.py')),
        'original_inputs':originals,'commands':[]}
    def command(argv):
        with (output/'build.log').open('a')as log:
            code=subprocess.run(argv,cwd=build,stdout=log,stderr=subprocess.STDOUT).returncode
        receipt['commands'].append({'argv':argv,'cwd':str(build),'returncode':code})
        require(code==0,'private arc probe build failed')
    try:
        modified=patches(*(p.read_text()for p in sources),analysis)
        flags={}
        for line in flags_path.read_text().splitlines():
            if line.startswith(('CXX_DEFINES =','CXX_INCLUDES =','CXX_FLAGS =')):
                key,value=line.split('=',1);flags[key.strip()]=shlex.split(value.strip())
        require(len(flags)==3,'private compile flags')
        objects=[]
        patch=[]
        for source,text in zip(sources,modified):
            copied=output/source.name;copied.write_text(text)
            patch.extend(difflib.unified_diff(source.read_text().splitlines(True),text.splitlines(True),fromfile='upstream/'+str(source.relative_to(source_root)),tofile='private/'+source.name))
            obj=output/(source.name+'.o');objects.append(obj)
            command(['/usr/bin/c++',*flags['CXX_DEFINES'],*flags['CXX_INCLUDES'],*flags['CXX_FLAGS'],'-iquote',str(source.parent),'-c',str(copied),'-o',str(obj)])
        (output/'native-driver.patch').write_text(''.join(patch))
        copied_archive=output/'libOpenSTA-private.a';shutil.copyfile(archive,copied_archive)
        members=subprocess.check_output(['/usr/bin/ar','t',str(copied_archive)],text=True).splitlines()
        require(all(members.count(p.name)==1 for p in objects),'private archive members')
        command(['/usr/bin/ar','r',str(copied_archive),*[str(p)for p in objects]])
        argv=shlex.split(link_path.read_text());require(argv.count('libOpenSTA.a')==1 and argv.count('-o')==1,'private link command')
        argv[argv.index('libOpenSTA.a')]=str(copied_archive);argv[argv.index('-o')+1]=str(output/('sta-'+analysis+'-output-probe'))
        command(['-flto=2'if word=='-flto'else word for word in argv])
        require(all(file_sha(Path(p))==h for p,h in originals.items()),'private original inputs modified')
        receipt.update(passed=True,original_inputs_unchanged=True)
        return receipt
    finally:
        receipt['finished']=time.time();receipt['outputs']={p.name:file_sha(p)for p in output.iterdir()if p.is_file()and p.name!='build-receipt.json'}
        (output/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['source-root','build','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--analysis',choices=['min','max'],required=True)
    args=parser.parse_args();result=execute(args.source_root,args.build,args.output,args.analysis)
    print(json.dumps({'passed':result['passed']}))
