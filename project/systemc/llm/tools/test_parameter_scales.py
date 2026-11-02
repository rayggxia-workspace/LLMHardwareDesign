"""Positive reconstruction and exact rejection causes for static parameter metadata."""
import struct,subprocess,sys,tempfile
from pathlib import Path

def main():
    with tempfile.TemporaryDirectory(prefix='llm-static-parameters-')as folder:
        root=Path(folder)
        (root/'weights.index').write_text('test 1 2 -14 0\n')
        (root/'weights.bin').write_bytes(struct.pack('<hh',16384,8192))
        (root/'prompt.txt').write_text('0\n')
        def run(scales,version='parameter_groups_version 1\n'):
            (root/'metadata.txt').write_text(version)
            p=root/'parameters.scales'
            if scales is None:
                if p.exists():p.unlink()
            else:p.write_text(scales)
            return subprocess.run([sys.argv[1],'--check-parameters',str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        for data,expected in [(None,'0 0 0'),('test 2 1 2 -14 -13\n','1 2 2'),('test 2 8 1 -14\n','1 2 1.5')]:
            r=run(data,''if data is None else'parameter_groups_version 1\n');assert r.returncode==0 and 'STATIC_PARAMETERS_VALID '+expected in r.stdout,(r.stdout,r.stderr)
        for data,version,error in [('test 2 2 1 -14\n','parameter_groups_version 1\n','scale shape'),
                                   ('test 2 1 1 -14\n','parameter_groups_version 1\n','scale shape'),
                                   ('test 0 1 0\n','parameter_groups_version 1\n','scale shape'),
                                   ('test 2 1 2 -14 999\n','parameter_groups_version 1\n','exponent'),
                                   ('test 2 1 2 -14 -13 extra\n','parameter_groups_version 1\n','trailing scale'),
                                   ('test 2 1 2 -14 -13\n','','scale version'),
                                   (None,'parameter_groups_version 1\n','scale version')]:
            r=run(data,version);assert r.returncode!=0 and 'static parameter '+error in r.stderr,(r.stdout,r.stderr)
    print('STATIC_PARAMETER_CONTRACT PASS: legacy/scalar/group8 and seven exact rejection controls')

if __name__=='__main__':main()
