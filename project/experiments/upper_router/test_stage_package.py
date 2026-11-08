import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from stage_package import sha, stage


def archive(path,members):
    with tarfile.open(path,'w:gz') as t:
        for name,data in members.items():
            info=tarfile.TarInfo(name);info.size=len(data)
            t.addfile(info,io.BytesIO(data))


class PackageTests(unittest.TestCase):
    def test_real_bytes_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=root/'a.tar.gz';out=root/'stage'
            payload=b'qualified fixture bytes'
            archive(a,{'native/input':payload,'FILES.sha256':
                       (hashlib.sha256(payload).hexdigest()+'  native/input\n').encode()})
            stage(a,sha(a),out)
            self.assertEqual((out/'native/input').read_bytes(),payload)
            with self.assertRaises(FileExistsError):stage(a,sha(a),out)

    def test_outside_paths_rejected(self):
        for name in ('../escaped','/escaped','C:/escaped'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);a=root/'a.tar.gz'
                archive(a,{name:b'bad'})
                with self.assertRaisesRegex(ValueError,'unsafe archive member'):
                    stage(a,sha(a),root/'stage')
                self.assertFalse((root/'escaped').exists())

    def test_wrong_archive_or_member_hash_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=root/'a.tar.gz'
            archive(a,{'native/input':b'bad','FILES.sha256':('0'*64+'  native/input\n').encode()})
            with self.assertRaisesRegex(ValueError,'archive SHA-256'):
                stage(a,'0'*64,root/'first')
            self.assertFalse((root/'first').exists())
            with self.assertRaisesRegex(ValueError,'member SHA-256'):
                stage(a,sha(a),root/'second')


if __name__=='__main__':unittest.main()
