"""Regenerate in memory: no production RTL mutation during regression."""
import runpy,sys,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path('hardware').resolve()))
class Tests(unittest.TestCase):
 def test_read_queue_generators_match_checked_in_rtl(self):
  for name in ('projection','n32','e32'):
   target=Path('rtl/control/'+name+'_service_cluster.sv').resolve();captured={}
   def capture(path,text,*args,**kwargs):
    self.assertEqual(path.resolve(),target);captured['text']=text;return len(text)
   with patch.object(Path,'write_text',capture):
    runpy.run_path('hardware/build_'+name+'_service_cluster.py')
   self.assertEqual(captured['text'].rstrip(),target.read_text().rstrip(),name+' generator drift')
   self.assertNotIn('read_busy',captured['text'])

 def test_shared_memory_generator_keeps_read_windows(self):
  captured={}
  def capture(path,text,*args,**kwargs):captured[path.name]=text;return len(text)
  with patch.object(Path,'write_text',capture):
   runpy.run_path('hardware/build_shared_memory_plane.py')
  self.assertEqual(captured['native_shared_memory_plane.sv'],Path('rtl/control/native_shared_memory_plane.sv').read_text())
  manifest=json.loads(captured['shared-memory-plane.json'])
  self.assertEqual(manifest['instances']['native64_dma_read_window_client'],9)
  self.assertEqual(manifest['instances']['native64_dma_serial_client'],9)
  self.assertEqual(manifest['read_slots_per_owner'],4)
if __name__=='__main__':unittest.main()
