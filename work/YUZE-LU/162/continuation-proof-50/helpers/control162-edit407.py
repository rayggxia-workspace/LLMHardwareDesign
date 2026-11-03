from pathlib import Path
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1')
p=r/'router_trial_pool.py';assert not p.exists();p.write_text('''"""Finite own-child search pool; refill failed attempts without a batch barrier."""
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
''',encoding='utf-8')
p=r/'test_router_trial_pool.py';p.write_text('''import subprocess,sys,tempfile,unittest
from pathlib import Path
from router_trial_pool import run


class PoolTest(unittest.TestCase):
    def test_failed_attempts_refill_before_slow_original_finishes(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);gate=root/'gate'
            code="import sys,time;from pathlib import Path;i=int(sys.argv[1]);p=Path(sys.argv[2]);p.touch()if i==3 else None;end=time.monotonic()+5\\nwhile i==0 and not p.exists()and time.monotonic()<end:time.sleep(.01)\\nsys.exit(0 if i==0 and p.exists()else 1)"
            def launch(i):return [sys.executable,'-c',code,str(i),str(gate)],root/(str(i)+'.log')
            result=run(2,4,launch,.01)
            self.assertEqual(result['winner'],0);self.assertEqual(result['attempts_started'],4)
            self.assertEqual(result['maximum_active'],2)
            records=result['records'];self.assertLess(records[2]['started_at'],records[0]['finished_at'])
            self.assertTrue(all('returncode'in v for v in records.values()))

    def test_finite_exhaustion_stays_failed(self):
        with tempfile.TemporaryDirectory()as temp:
            result=run(2,5,lambda i:([sys.executable,'-c','raise SystemExit(7)'],Path(temp)/(str(i)+'.log')),.01)
            self.assertIsNone(result['winner']);self.assertEqual(result['attempts_started'],5)
            self.assertTrue(all(v['returncode']==7 for v in result['records'].values()))
            self.assertEqual(result['maximum_active'],2)

    def test_invalid_envelopes_rejected(self):
        for width,attempts in [(0,4),(17,32),(4,3),(2,257)]:
            with self.assertRaises(AssertionError):run(width,attempts,None)


if __name__=='__main__':unittest.main()
''',encoding='utf-8')
p=r/'tree_router_cpp.py';s=p.read_text();assert 'pareto_wire_budget=False):'in s;s=s.replace('pareto_wire_budget=False):','pareto_wire_budget=False,trial_attempts=0):');s=s.replace('    assert heuristic_weight in (1,4,8,16,32)','    assert trial_attempts==0 or (1<trials<=trial_attempts<=256)\n    assert heuristic_weight in (1,4,8,16,32)',1)
old="""        for index in range(trials):
            actual_seed=seed*101+index;folder=out/('trial-'+str(index));folder.mkdir()"""
assert old in s
start=s.index('        for index in range(trials):');end=s.index("        (out/'trial-index.json').write_text",start)
original=s[start:end]
# Preserve the legacy path exactly when the new optional attempt limit is zero.
new="""        if trial_attempts:
            from router_trial_pool import run as run_pool
            def launch(index):
                actual_seed=seed*101+index;folder=out/('trial-'+str(index));folder.mkdir()
                (folder/'input.txt').write_text(f'{nx} {ny} {len(terminals)} {actual_seed} {max_rounds} {heuristic_weight} {len(locked_names)} 1 {int(negotiated_priority)} {int(defer_access_vias)} {congestion_scale} {int(history_product)}{suffix}\\n'+body)
                return [str(binary),str(folder/'input.txt'),str(folder/'output.txt')],folder/'router.log'
            trial_proof=run_pool(trials,trial_attempts,launch)
            winner=trial_proof['winner'];records=trial_proof['records']
            for index,row in records.items():row['seed']=seed*101+index
            trial_proof.update(trials=trials,available_bytes=memory['MemAvailable'],forecast_gib_per_trial=2,
                scope='Finite independent own-child attempts refill failures within the same16CPU step; memory forecast depends on active width, not total attempts. All returned routes still require original independent checks.')
        else:
"""+''.join('    '+line+'\n'for line in original.splitlines())
s=s[:start]+new+s[end:];s=s.replace('resource_search_header_sha256=sha(source.with_name("resource_search.h")),','resource_search_header_sha256=sha(source.with_name("resource_search.h")),\n        trial_pool_source_sha256=sha(source.with_name("router_trial_pool.py"))if trial_attempts else None,');p.write_text(s,encoding='utf-8')
p=r/'system_upper.py';s=p.read_text();needle="    p.add_argument('--route-adaptive-heuristic'";assert needle in s;s=s.replace(needle,"    p.add_argument('--route-trial-attempts',type=int,default=0,help='Search only: finite attempt budget with failed-attempt refill within unchanged active trial width; zero preserves legacy pool')\n"+needle,1);s=s.replace('pareto_wire_budget=bool(a.route_residual_budget))','pareto_wire_budget=bool(a.route_residual_budget),trial_attempts=a.route_trial_attempts)');p.write_text(s,encoding='utf-8')
print('edited 4 files')
