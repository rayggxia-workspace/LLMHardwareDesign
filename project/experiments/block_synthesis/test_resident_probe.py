from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from resident_probe import analyse


class TestResidentProbe(unittest.TestCase):
    def test_raw_launcher_encoding_does_not_drop_first_case_or_hide_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);expected={'loads':3,'stores':1,'m':1,'e':1}
            m={'kind':'native-resident-record-v1','sha256':{},'cases':[{'id':0,'expected':expected}],
               'scope':'unit fixture','excluded':'RTL','cycles':'fixture'}
            (p/'manifest.json').write_text(json.dumps(m))
            record=b'RESIDENT_CASE '+json.dumps({'id':0,**expected,'cycles':42}).encode()+b'\n'
            content='launcher\r\n'.encode('utf-16-le')+record+b'PASS native resident record programs\n'
            log=p/'log';log.write_bytes(content)
            with redirect_stdout(io.StringIO()):self.assertTrue(analyse(p,log)['passed'])
            for bad in (content+b'FATAL: bad result\n',content.replace(record,b''),content+record,
                        content.replace(b'"loads": 3',b'"loads": 2')):
                log.write_bytes(bad)
                with self.assertRaises(ValueError):analyse(p,log)


if __name__=='__main__':unittest.main()
