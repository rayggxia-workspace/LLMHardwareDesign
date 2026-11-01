# -*- coding: utf-8 -*-
"""Run declared W4 RTL/TBs in fresh local ModelSim directories, retaining failure.

No network/install/PATH changes or license/credential inspection. Native source
bytes are checked against the retained14-file lock before compilation.
"""
import argparse,datetime,hashlib,json,platform,re,subprocess,sys
from pathlib import Path
PARENT='0101cc7e1e6d5718455fb45b61c7428439efc09a';NATIVE='707878621b2add4ed218b8c43df2e95c9a56e2ba'
def info(p):
    b=p.read_bytes();return {'name':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--tool-dir',type=Path,default=Path('D:/EDA/modeltech64_2020.4/win64'));ap.add_argument('--output',type=Path,required=True);ap.add_argument('--suite',choices=['n','f8','all'],default='all');a=ap.parse_args();root=a.root.resolve();out=a.output.resolve()
    if out.exists() and any(out.iterdir()):raise RuntimeError('output must be new/empty; previous attempts retained')
    out.mkdir(parents=True,exist_ok=True);snap=out/'source';snap.mkdir()
    rc={'schema_version':1,'started_at_utc':now(),'suite':a.suite,'research_parent':PARENT,'native_source':NATIVE,'execution_source':'new W4 files uncommitted at run; exact input SHA binds bytes, final delivery commit recorded separately','host':{'python':sys.version,'platform':platform.platform()},'tool':{},'inputs':[],'runs':[],'case_ids':[],'pass_markers':[],'scope':{'actual_RTL':True,'whole_F_or_model':False,'physical':False,'server_or_SSH':False}}
    def save():(out/'run-receipt.json').write_bytes((json.dumps(rc,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8'))
    def run(label,args):
        ent={'label':label,'argv':[str(x) for x in args],'cwd':str(out),'started_at_utc':now()}
        try:r=subprocess.run(ent['argv'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);raw=r.stdout;code=r.returncode
        except (OSError,subprocess.TimeoutExpired) as e:raw=str(e).encode('utf8');code=-1
        try:s=raw.decode('utf8')
        except UnicodeDecodeError:s=raw.decode('mbcs',errors='replace')
        s=s.replace('\r\n','\n').replace('\r','\n');log=out/(label+'.log');log.write_bytes(s.encode('utf8'));ent.update({'exit_code':code,'stdout_raw_sha256':hashlib.sha256(raw).hexdigest(),'log':log.name,'log_sha256':info(log)['sha256'],'finished_at_utc':now()});rc['runs'].append(ent);save();print(label+': exit='+str(code),flush=True)
        if code:raise RuntimeError(label+' failed; retained log')
        return s
    def source(p,scope):
        p=p.resolve();target=snap/p.name
        if target.exists():raise RuntimeError('duplicate source basename '+p.name)
        target.write_bytes(p.read_bytes());rc['inputs'].append(dict(info(target),path=p.relative_to(root).as_posix() if root in p.parents else p.name,origin=str(p),scope=scope));return target
    try:
        ini=out/'modelsim.ini';ini.write_bytes(b'[Library]\nwork = work\n\n[vsim]\nTranscriptFile = transcript\n');rc['configuration']=info(ini)
        for t in ['vlib','vlog','vsim']:rc['tool'][t]=dict(info(a.tool_dir/(t+'.exe')),path=str(a.tool_dir/(t+'.exe')))
        for t in ['vlog','vsim']:rc['tool'][t]['version']=run(t+'-version',[a.tool_dir/(t+'.exe'),'-version']).strip()
        lockp=root/'work/Melodydt/151/phase2-source-lock.json';lock=json.loads(lockp.read_text(encoding='utf8'));rc['inputs'].append(dict(info(lockp),path='work/Melodydt/151/phase2-source-lock.json',scope='native_lock'))
        if lock['selected_PR144_ref']!=NATIVE or len(lock['core_files'])!=14:raise RuntimeError('unexpected native lock')
        files=[]
        for x in lock['core_files']:
            p=source(root/x['path'],'frozen_native_RTL');q=info(p)
            if q['sha256']!=x['sha256'] or q['git_blob_sha1']!=x['sha']:raise RuntimeError('native hash mismatch '+x['path'])
            if p.suffix=='.sv':files.append(p)
        files.append(source(root/'project/rtl/block_connection_p2/block_p2_s_ctrl.sv','existing_S_helper'))
        for n in ['block_w3_e_ctrl.sv','block_w3_g_ctrl.sv','block_w3_ffn8_top.sv']:files.append(source(root/'project/rtl/block_connection_w3'/n,'existing_W3_RTL'))
        for n in ['block_w4_n_ctrl.sv','block_w4_f8_top.sv']:files.append(source(root/'project/rtl/block_connection_w4'/n,'new_W4_RTL'))
        tbroot=root/'project/tb/block_connection_w4'
        for p in sorted(tbroot.glob('*.svh')):source(p,'independent_golden_include')
        tops=[]
        for suite,top,marker in [('n','block_w4_n_tb','PASS_W4_N'),('f8','block_w4_f8_tb','PASS_W4_F8')]:
            if a.suite in [suite,'all']:files.append(source(tbroot/(top+'.sv'),'new_independent_W4_TB'));tops.append((top,marker))
        for n in ['w4-n-vectors.json','w4-f8-vectors.json','w4_integer_reference.py','build_w4_vectors.py']:
            p=root/'work/Melodydt/151'/n;rc['inputs'].append(dict(info(p),path='work/Melodydt/151/'+n,scope='independent_numeric_reference_or_vectors'))
        rc['inputs'].append(dict(info(Path(__file__)),scope='run_script'));rc['native_compile_scope']='14 locked sources/includes; selected N/M/E/G/S/T paths functional only per actual suite; R/legacy syntax only; no physical qualification';save()
        run('vlib',[a.tool_dir/'vlib.exe','work'])
        run('compile',[a.tool_dir/'vlog.exe','-modelsimini','modelsim.ini','-sv','-work','work','+incdir+'+str(snap)]+files)
        for top,marker in tops:
            s=run('simulation-'+top,[a.tool_dir/'vsim.exe','-modelsimini','modelsim.ini','-c','-voptargs=+acc','-onfinish','stop','work.'+top,'-do','onbreak {quit -code 2}; onerror {quit -code 3}; run -all; quit -code 0'])
            if marker not in s or re.search(r'FAIL_(W4|P2|W1)|Fatal:',s):raise RuntimeError('missing PASS or failing trace '+top)
            ids=re.findall(r'CASE_PASS ([A-Z][A-Z0-9_]+)',s)
            if len(ids)!=len(set(ids)):raise RuntimeError('duplicate CASE_PASS IDs '+top)
            rc['case_ids'].extend(ids);rc['pass_markers'].append(marker)
        rc['status']='PASS_REAL_RTL_SIMULATION'
    except Exception as e:rc['status']='FAILED_OR_BLOCKED';rc['failure']=str(e);save();raise
    finally:rc['finished_at_utc']=now();save()
    print('PASS actual W4 RTL '+str(out/'run-receipt.json'),flush=True)
if __name__=='__main__':main()
