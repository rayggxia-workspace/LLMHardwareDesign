"""Finite own-child search pool; refill failed attempts without a batch barrier."""
import subprocess,time
from pathlib import Path


def run(width,attempts,launch,poll_seconds=0.05):
    assert 1<=width<=16 and width<=attempts<=256
    active={};logs={};records={};next_index=0;winner=None;peak_rss=0;maximum_active=0
    try:
        while (active or next_index<attempts)and winner is None:
            while len(active)<width and next_index<attempts:
                index=next_index;command,log=launch(index);next_index+=1
                logs[index]=Path(log).open('w')
                process=subprocess.Popen(command,stdout=logs[index],stderr=subprocess.STDOUT)
                active[index]=process
                records[index]=dict(command=command,pid=process.pid,started_at=time.time())
                maximum_active=max(maximum_active,len(active))
            rss=0
            for index,process in list(active.items()):
                try:
                    for line in Path('/proc/'+str(process.pid)+'/status').read_text().splitlines():
                        if line.startswith('VmRSS:'):rss+=int(line.split()[1])*1024
                except OSError:pass
                rc=process.poll()
                if rc is not None:
                    records[index].update(returncode=rc,finished_at=time.time());logs[index].close();del active[index]
                    if rc==0:winner=index;break
            peak_rss=max(peak_rss,rss)
            if active and winner is None:time.sleep(poll_seconds)
    finally:
        # Only Popen objects created above belong to this pool. A launch error
        # must also release these own children; never signal a parent/foreign PID.
        for index,process in active.items():
            if process.poll()is None:
                process.terminate();records[index]['termination_reason']='Another own trial completed; awaiting independent verification'if winner is not None else'Own pool interrupted or launch failed'
        for index,process in active.items():
            records[index].update(returncode=process.wait(),finished_at=time.time());logs[index].close()
        for log in logs.values():log.close()
    return dict(winner=winner,records=records,attempt_limit=attempts,attempts_started=next_index,
                active_width=width,maximum_active=maximum_active,sampled_peak_aggregate_rss_bytes=peak_rss,
                dynamic_failed_attempt_refill=True)
