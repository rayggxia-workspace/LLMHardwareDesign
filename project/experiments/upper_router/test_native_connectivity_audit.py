from copy import deepcopy
import unittest
from native_connectivity_audit import audit


def fixture():
    terms={name:{'signal_type':role,'native_net':name,'shapes':[{'layer':'metal10'}]}
           for name,role in [('a','SIGNAL'),('b','SIGNAL'),('arbitrary-p','POWER'),('arbitrary-g','GROUND')]}
    topology={'passed':True,'boundary_probes':{name:{'native_net':name,'probes':[{'token':[name]}]} for name in ('a','b')},
              'power_probes':[{'label':name,'token':[name]} for name in ('arbitrary-p','arbitrary-g')]}
    return {'terms':terms},topology


class NativeConnectivityTests(unittest.TestCase):
    def test_roles_use_inventory_and_all_terminals_are_required(self):
        inventory,topology=fixture()
        self.assertTrue(audit(inventory,topology)['passed'])
        bad=deepcopy(topology);bad['power_probes'].pop()
        with self.assertRaisesRegex(AssertionError,'PG terminal coverage'):audit(inventory,bad)
        bad=deepcopy(topology);del bad['boundary_probes']['b']
        with self.assertRaisesRegex(AssertionError,'signal terminal coverage'):audit(inventory,bad)

    def test_pg_and_signal_shorts_rejected(self):
        inventory,topology=fixture()
        bad=deepcopy(topology);bad['power_probes'][1]['token']=['arbitrary-p']
        with self.assertRaisesRegex(AssertionError,'power physically shorted'):audit(inventory,bad)
        bad=deepcopy(topology);bad['power_probes'][1]['token']=['a']
        with self.assertRaisesRegex(AssertionError,'signal physically shorted'):audit(inventory,bad)
        bad=deepcopy(topology);bad['boundary_probes']['b']['probes'][0]['token']=['a']
        with self.assertRaisesRegex(AssertionError,'native signal short'):audit(inventory,bad)


if __name__=='__main__':unittest.main()
