import subprocess,sys,tempfile,unittest
from pathlib import Path
from router_trial_pool import run


class PoolTest(unittest.TestCase):
    def test_failed_attempts_refill_before_slow_original_finishes(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);gate=root/'gate'
            code="import sys,time;from pathlib import Path;i=int(sys.argv[1]);p=Path(sys.argv[2]);p.touch()if i==3 else None;end=time.monotonic()+5\nwhile i==0 and not p.exists()and time.monotonic()<end:time.sleep(.01)\nsys.exit(0 if i==0 and p.exists()else 1)"
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

    def test_launch_failure_releases_own_started_child(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);pidfile=root/'pid'
            def launch(i):
                if i:
                    import time
                    end=time.monotonic()+3
                    while not pidfile.exists()and time.monotonic()<end:time.sleep(.01)
                    self.assertTrue(pidfile.exists())
                    raise RuntimeError('deliberate launch failure')
                return [sys.executable,'-c',"import os,time;from pathlib import Path;Path(__import__('sys').argv[1]).write_text(str(os.getpid()));time.sleep(30)",str(pidfile)],root/'first.log'
            with self.assertRaisesRegex(RuntimeError,'deliberate launch failure'):run(2,4,launch,.01)
            import os
            pid=int(pidfile.read_text())
            if os.name!='nt':
                with self.assertRaises(ProcessLookupError):os.kill(pid,0)

    def test_invalid_envelopes_rejected(self):
        for width,attempts in [(0,4),(17,32),(4,3),(2,257)]:
            with self.assertRaises(AssertionError):run(width,attempts,None)


if __name__=='__main__':unittest.main()
