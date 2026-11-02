"""Build a parallel C/D experiment without changing the original llm sources."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,os
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--control-root',type=Path,default=ROOT.parents[1],help='Repository containing the control contract; defaults to this checkout')
 p.add_argument('--systemc-prefix',required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--save-evidence',type=Path,required=True)
 p.add_argument('--no-sanitize',action='store_true',help='Remote Release baseline when sanitizer runtime unavailable; numerical gates unchanged')
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 # The integrated checkout already contains include/control. Copy arithmetic
 # first, then the explicitly selected control source once; Python3.6 compatible.
 stage=out/'source';stage.mkdir();shutil.copytree(ROOT/'include',stage/'include',ignore=shutil.ignore_patterns('control'));shutil.copytree(ROOT/'llm',stage/'llm',ignore=shutil.ignore_patterns('results','__pycache__'))
 control=a.control_root.resolve()/'project/systemc/include/control';shutil.copytree(control,stage/'include/control')
 # GCC8 inlines std::optional's empty return into DModule and diagnoses its
 # disengaged payload as uninitialized. Keep this accessor out of line; no
 # state, return value, gate or upstream source is changed.
 dma=stage/'include/control/dma.hpp';dma_text=dma.read_text()
 dma_text=dma_text.replace('std::optional<Completion> completion() const', '[[gnu::noinline]] std::optional<Completion> completion() const')
 dma.write_text(dma_text)
 shutil.copyfile(HERE/'payload.hpp',stage/'llm/payload.hpp');shutil.copyfile(HERE/'payload_test.cpp',stage/'payload_test.cpp')
 provenance={str(p):sha(p) for p in (list(control.glob('*.hpp'))+list((ROOT/'include').rglob('*.hpp'))+list(HERE.glob('*'))+list((ROOT/'llm').glob('*.hpp'))+list((ROOT/'llm').glob('*.cpp'))) if p.is_file()}
 link=stage/'llm/tensor_link.hpp';text=link.read_text();text=text.replace('#include "flow.hpp"','#include "flow.hpp"\n#include "payload.hpp"')
 text=text.replace('  unsigned width_, capacity_', '  llm_cd::Payload cd_{"cd"};\n  unsigned width_, capacity_')
 needle='    if (!enabled)\n      return input;'
 assert text.count(needle)==1
 text=text.replace(needle,needle+'\n    return cd_.exchange(input);')
 text=text.replace('    std::ofstream f(directory + "/tensor-link.json");','    std::ofstream cdfile(directory + "/cd-payload.json");\n    cdfile << "{\\"windows\\":" << cd_.windows << ",\\"words\\":" << cd_.words << ",\\"bursts\\":" << cd_.burst_count << "}\\n";\n    std::ofstream f(directory + "/tensor-link.json");')
 link.write_text(text)
 (stage/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
project(llm_cd LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(SystemCLanguage CONFIG REQUIRED)
enable_testing()
add_executable(cd_payload_test payload_test.cpp)
add_executable(llm_cd_bench llm/llm_bench.cpp)
foreach(t cd_payload_test llm_cd_bench)
 target_include_directories(${t} PRIVATE include llm)
 target_link_libraries(${t} PRIVATE SystemC::systemc)
  target_compile_options(${t} PRIVATE -Wall -Wextra -Werror)
  if(CD_SANITIZE)
   target_compile_options(${t} PRIVATE -fsanitize=undefined -fno-sanitize-recover=all)
   target_link_options(${t} PRIVATE -fsanitize=undefined)
  endif()
endforeach()
add_test(NAME payload COMMAND cd_payload_test)
add_test(NAME model_selftest COMMAND llm_cd_bench --selftest)
set_tests_properties(model_selftest PROPERTIES ENVIRONMENT "LLM_LINK=1;LLM_PRECISE_ADAPTER=1;LLM_BLOCK_SCALES=1;LLM_ACCURATE_SILU=1" TIMEOUT 180)
''')
 receipt=dict(passed=False,sanitizer=not a.no_sanitize,generated_control_dma_sha256=sha(dma),control_copy_adjustment='completion accessor noinline for GCC8 optional false positive; semantics unchanged',scope='parallel C/D payload at Tensor boundaries; weights/raw recurrent state and compute scheduling remain host mediated; assumed timing',inputs=provenance,tools={name:subprocess.check_output([name,'--version'],universal_newlines=True).splitlines()[0] for name in ['cmake','c++']})
 try:
  for name,argv in [('configure',['cmake','-S',stage,'-B',out/'build','-DCMAKE_PREFIX_PATH='+a.systemc_prefix,'-DCMAKE_BUILD_TYPE=Release','-DCD_SANITIZE='+('OFF' if a.no_sanitize else 'ON')]),('build',['cmake','--build',out/'build','-j4']),('tests',['ctest','--test-dir',out/'build','--output-on-failure'])]:
   with (out/(name+'.log')).open('w') as f:subprocess.run(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,check=True)
  proof=(out/'build/Testing/Temporary/LastTest.log').read_text()
  import re
  counts=re.findall(r'CD_EXECUTED windows=(\d+) words=(\d+) bursts=(\d+) C_submitted=(\d+) C_completed=(\d+)',proof)
  assert len(counts)==2 and all(int(w)>0 and int(s)==int(c) and int(s)>0 for w,_,_,s,c in counts),'C/D not actually exercised'
  receipt['executed_counts']=counts
  receipt['passed']=True
 finally:
  # Explicit verbose results demonstrate that both selected programs ran.
  last=out/'build/Testing/Temporary/LastTest.log'
  if last.exists():shutil.copyfile(last,out/'LastTest.log')
  receipt['outputs']={str(p.relative_to(out)):sha(p) for p in out.glob('*.log')}
  (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
  saved=a.save_evidence.resolve();saved.mkdir(parents=True,exist_ok=False)
  for p in out.iterdir():
   if p.is_file():shutil.copyfile(p,saved/p.name)
  shutil.copytree(stage/'include/control',saved/'control-snapshot')
  shutil.copyfile(link,saved/'generated-tensor-link.hpp')
 print(json.dumps(receipt))
if __name__=='__main__':main()
