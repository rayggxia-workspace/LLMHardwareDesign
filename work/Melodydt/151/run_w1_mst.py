# -*- coding: utf-8 -*-
"""Bounded local ModelSim runner; copies declared sources and writes only --output.

No network, install, environment/PATH changes, license or credential inspection.
Each attempt requires a fresh output directory; failed attempts are retained.
"""
import argparse,datetime,hashlib,json,platform,re,subprocess,sys
from pathlib import Path
PARENT='bfe62ad179af72aef591622aa5c7a000f5d8b681'
NATIVE='707878621b2add4ed218b8c43df2e95c9a56e2ba'

def info(p):
    raw=p.read_bytes();return {'name':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--tool-dir',type=Path,default=Path('D:/EDA/modeltech64_2020.4/win64'));ap.add_argument('--output',type=Path,required=True);ap.add_argument('--suite',choices=['w1','regression','all'],default='all');a=ap.parse_args()
    root=a.root.resolve();out=a.output.resolve()
    if out.exists() and any(out.iterdir()):raise RuntimeError('output must be new/empty; retain all previous attempts')
    out.mkdir(parents=True,exist_ok=True);snap=out/'source';snap.mkdir()
    receipt={'schema_version':1,'started_at_utc':now(),'suite':a.suite,'research_parent':PARENT,'native_source':NATIVE,'execution_source':'W1/new tests uncommitted at run; exact input SHA binds bytes; delivery commit recorded separately','host':{'python':sys.version,'platform':platform.platform()},'tool':{},'inputs':[],'runs':[],'case_ids':[],'pass_markers':[],'scope':{'actual_RTL':True,'physical':False,'whole_model':False,'server_or_SSH':False}}
    def save():(out/'run-receipt.json').write_bytes((json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8'))
    def run(label,args):
        ent={'label':label,'argv':[str(x) for x in args],'cwd':str(out),'started_at_utc':now()}
        try:
            r=subprocess.run(ent['argv'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);raw=r.stdout;code=r.returncode
        except (OSError,subprocess.TimeoutExpired) as e:raw=str(e).encode('utf8');code=-1
        try:s=raw.decode('utf8')
        except UnicodeDecodeError:s=raw.decode('mbcs',errors='replace')
        s=s.replace('\r\n','\n').replace('\r','\n');log=out/(label+'.log');log.write_bytes(s.encode('utf8'))
        ent.update({'exit_code':code,'stdout_raw_sha256':hashlib.sha256(raw).hexdigest(),'log':log.name,'log_sha256':info(log)['sha256'],'finished_at_utc':now()});receipt['runs'].append(ent);save();print(label+': exit='+str(code),flush=True)
        if code:raise RuntimeError(label+' failed; see retained log')
        return s
    def source(p,scope):
        p=p.resolve();target=snap/p.name
        if target.exists():raise RuntimeError('duplicate source basename '+p.name)
        target.write_bytes(p.read_bytes());receipt['inputs'].append(dict(info(target),path=str(p.relative_to(root)) if root in p.parents else p.name,origin=str(p),scope=scope));return target
    try:
        # Local, task-owned library mapping; never copy the installation ini.
        (out/'modelsim.ini').write_bytes(b'[Library]\nwork = work\n\n[vsim]\nTranscriptFile = transcript\n')
        for t in ['vlib','vlog','vsim']:receipt['tool'][t]=dict(info(a.tool_dir/(t+'.exe')),path=str(a.tool_dir/(t+'.exe')))
        for t in ['vlog','vsim']:receipt['tool'][t]['version']=run(t+'-version',[a.tool_dir/(t+'.exe'),'-version']).strip()
        lockp=root/'work/Melodydt/151/phase2-source-lock.json';lock=json.loads(lockp.read_text(encoding='utf8'));receipt['inputs'].append(dict(info(lockp),path='work/Melodydt/151/phase2-source-lock.json',scope='source_lock'))
        if lock['selected_PR144_ref']!=NATIVE or len(lock['core_files'])!=14:raise RuntimeError('unexpected native source lock')
        files=[]
        for row in lock['core_files']:
            f=source(root/row['path'],'frozen_native_RTL');v=info(f)
            if v['sha256']!=row['sha256'] or v['git_blob_sha1']!=row['sha']:raise RuntimeError('native source mismatch '+row['path'])
            if f.suffix=='.sv':files.append(f)
        files.append(source(root/'project/rtl/block_connection_p2/block_p2_s_ctrl.sv','existing_S_helper'))
        tops=[]
        if a.suite in ['regression','all']:
            for name in ['block_p2_mother_rom.sv','block_p2_mst_top.sv']:files.append(source(root/'project/rtl/block_connection_p2'/name,'unchanged_P2_RTL'))
            for name,marker in [('phase2_s_ctrl_tb','PASS_P2_S_CTRL'),('phase2_mst_tb','PASS_P2_MST')]:files.append(source(root/'project/tb/block_connection_p2'/(name+'.sv'),'unchanged_P2_TB'));tops.append((name,marker))
        if a.suite in ['w1','all']:
            for name in ['block_w1_mother_rom.sv','block_w1_mst_top.sv']:files.append(source(root/'project/rtl/block_connection_w1'/name,'new_W1_RTL'))
            files.append(source(root/'project/tb/block_connection_w1/block_w1_mst_tb.sv','new_independent_W1_TB'));tops.append(('block_w1_mst_tb','PASS_W1_MST'))
        for n in ['w0-evidence-gates.json','w0-index.json']:
            p=root/'work/Melodydt/151'/n;receipt['inputs'].append(dict(info(p),path='work/Melodydt/151/'+n,scope='fixed_W0_contract'))
        receipt['inputs'].append(dict(info(Path(__file__)),scope='run_script'))
        receipt['native_compile_scope']='14 locked sources/includes; only syntax compile for N/E/G/R/legacy, no functional or physical qualification';save()
        run('vlib',[a.tool_dir/'vlib.exe','work'])
        run('compile',[a.tool_dir/'vlog.exe','-modelsimini','modelsim.ini','-sv','-work','work','+incdir+'+str(snap)]+files)
        for top,marker in tops:
            s=run('simulation-'+top,[a.tool_dir/'vsim.exe','-modelsimini','modelsim.ini','-c','-voptargs=+acc','-onfinish','stop','work.'+top,'-do','onbreak {quit -code 2}; onerror {quit -code 3}; run -all; quit -code 0'])
            if marker not in s or re.search(r'FAIL_(?:P2|W1)|Fatal:',s):raise RuntimeError('missing pass marker or failing trace '+top)
            ids=re.findall(r'CASE_PASS ([A-Z][A-Z0-9_]+)',s)
            if len(ids)!=len(set(ids)):raise RuntimeError('duplicate CASE_PASS ID '+top)
            receipt['case_ids'].extend(ids);receipt['pass_markers'].append(marker)
        receipt['status']='PASS_REAL_RTL_SIMULATION'
    except Exception as e:
        receipt['status']='FAILED_OR_BLOCKED';receipt['failure']=str(e);save();raise
    finally:receipt['finished_at_utc']=now();save()
    print('PASS actual RTL; '+str(out/'run-receipt.json'),flush=True)
if __name__=='__main__':main()
