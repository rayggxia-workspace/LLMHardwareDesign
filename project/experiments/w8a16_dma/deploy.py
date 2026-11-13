"""Freeze exact DMA source in a fresh own Slurm root; no local RTL execution."""
import argparse,hashlib,io,json,shlex,subprocess,tarfile
from pathlib import Path
HOST='yuzelu@10.129.166.172'
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--skids-per-channel',type=int,choices=(2,3,4),default=3);a=p.parse_args();assert a.root.startswith('/public/home/yuzelu/project-circuit/issue250-dma-20261111-');assert not a.receipt.exists();a.receipt.mkdir(parents=True)
 commit=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip();paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--','project/rtl/mother_control_native/mc_dma_fabric.sv','project/experiments/w8a16_dma']).decode().splitlines();data={x:subprocess.check_output(['git','show',commit+':'+x])for x in paths};data['source-commit.txt']=(commit+'\n').encode();manifest=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n'for k,v in sorted(data.items()));package=a.receipt/'source.tar.gz'
 with tarfile.open(package,'w:gz')as tar:
  for k,v in data.items():
   entry=tarfile.TarInfo('source/'+k);entry.size=len(v);tar.addfile(entry,io.BytesIO(v))
  v=manifest.encode();entry=tarfile.TarInfo('source.sha256');entry.size=len(v);tar.addfile(entry,io.BytesIO(v))
 subprocess.run(['ssh',HOST,'mkdir '+shlex.quote(a.root)],check=True);subprocess.run(['scp','-q',str(package),HOST+':'+a.root+'/source.tar.gz'],check=True);result=subprocess.check_output(['ssh',HOST,'cd '+shlex.quote(a.root)+' && tar xzf source.tar.gz && sbatch --output='+shlex.quote(a.root+'/slurm-%j.log')+' --export=ALL,ISSUE250_DMA_SKIDS_PER_CHANNEL='+str(a.skids_per_channel)+' source/project/experiments/w8a16_dma/job.sh']).decode().strip();record=dict(source_commit=commit,remote_root=a.root,return_skids_per_channel=a.skids_per_channel,package_SHA256=hashlib.sha256(package.read_bytes()).hexdigest(),submit=result);(a.receipt/'submission.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
if __name__=='__main__':main()
