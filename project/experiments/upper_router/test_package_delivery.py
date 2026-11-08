import json
from pathlib import Path
import tempfile
import unittest
from check import digest
from native_inventory import sha
from package_delivery import package,verify


class PackageDeliveryTest(unittest.TestCase):
    def fixture(self,root):
        delivery=root/'qualified';delivery.mkdir();flat=root/'flat';flat.mkdir()
        artifacts={}
        for name in ('design.def','design.odb','design.v','design.gds','design.spef','design.sdc'):
            path=delivery/name;path.write_text('test fixture '+name)
            artifacts[name]={'path':str(path),'sha256':sha(path)}
        tech=root/'technology.lef';tech.write_text('fixture technology')
        vias=root/'upper-vias.lef';vias.write_text('fixture custom vias')
        (flat/'source-proof.json').write_text(json.dumps({
            'technology':{'path':str(tech),'sha256':sha(tech)},'upper_vias':{'path':str(vias),'sha256':sha(vias)}}))
        views={}
        for name in ('first','second'):
            folder=root/name;folder.mkdir();rows={}
            for kind,suffix in [('lefs','.lef'),('liberties','.lib')]:
                path=folder/('same-basename'+suffix);path.write_text(name+' '+kind)
                rows[kind]=[{'path':str(path),'sha256':sha(path)}]
            views[name]={'views':rows}
        viewfile=flat/'views.json';viewfile.write_text(json.dumps(views))
        manifest={'paths':{'flat_views':str(viewfile),'flat_odb':str(flat/'assembled.odb')}}
        (delivery/'input-manifest.json').write_text(json.dumps(manifest))
        qualification={'passed':True,'physical_qualified':True,'manifest_sha256':digest(manifest),
            'artifacts':artifacts,'coverage':{'collector_test_only':True},'qualification':'fixture only',
            'not_claimed':[],'timing_variants':[{'variant':'distributed-coupling-1','slack_ns':{'max':.1,'min':.1}}]}
        q=delivery/'qualification.json';q.write_text(json.dumps(qualification))
        index=root/'index.json';index.write_text(json.dumps({'qualification':{'sha256':sha(q)}}))
        source=root/'source.tar';source.write_bytes(b'fixture source')
        return delivery,index,source

    def test_duplicate_view_basenames_and_relocatable_scripts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);args=self.fixture(root);out=root/'package'
            result=package(*args,out)
            self.assertNotEqual((out/'views/t000/lefs/0000.lef').read_bytes(),
                                (out/'views/t001/lefs/0000.lef').read_bytes())
            self.assertNotIn(str(root),(out/'load_timing.tcl').read_text())
            self.assertIn('file join $handoff_root',(out/'load_def.tcl').read_text())
            self.assertEqual((out/'views/upper-vias.lef').read_text(),'fixture custom vias')
            self.assertTrue(result['replay_required'])

    def test_changed_view_refused_before_package_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);args=self.fixture(root);out=root/'package'
            (root/'first/same-basename.lef').write_text('stale geometry')
            with self.assertRaises(AssertionError):package(*args,out)
            self.assertFalse(out.exists())

    def test_changed_copied_artifact_refused_before_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);args=self.fixture(root);out=root/'package'
            package(*args,out);(out/'design.v').write_text('changed circuit')
            with self.assertRaises(AssertionError):verify(out)


if __name__=='__main__':unittest.main()
