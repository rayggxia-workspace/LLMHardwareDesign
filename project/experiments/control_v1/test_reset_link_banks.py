import copy
import unittest
from reset_link_banks import assign, validate


COUNTS = dict(controller=48, macro_1=18, macro_2=18, macro_3=18,
              macro_4=7, macro_t=21, macro_r=84, s_port=102)


def fixture():
    outputs = list(range(100, 153))
    cells = dict(reset_distribution=dict(type='control_reset_distribution_r53',
                                        connections=dict(reset_out=outputs)))
    rows = []
    for index, (source, count) in enumerate(sorted(COUNTS.items())):
        cells[source] = dict(connections=dict(reset=[outputs[index]]))
        for serial in range(count):
            name = 'link_'+source+'_'+str(serial)
            cells[name] = dict(connections=dict(reset=[outputs[index]]))
            rows.append(dict(instance=name, source_instance=source, reset_bit=outputs[index]))
    module = dict(cells=cells)
    proof = assign(module, rows)
    graph = dict(boundary_links=dict(links=rows), connections={})
    for bank in proof['banks']:
        graph['connections'][str(bank['bit'])] = dict(
            driver=dict(instance='reset_distribution', pin='reset_out['+str(bank['output'])+']', direction='output'),
            sinks=[dict(instance=n, pin='reset', direction='input') for n in bank['link_instances']])
    return module, graph, proof


class Banks(unittest.TestCase):
    def test_all_actual_owner_counts_and_partition(self):
        module, graph, proof = fixture()
        validate(graph, proof)
        self.assertEqual(len(proof['banks']), 25)
        for row in graph['boundary_links']['links']:
            self.assertEqual(module['cells'][row['instance']]['connections']['reset'], [row['reset_bit']])

    def test_corrupt_driver_member_state_and_branch_rejected(self):
        _, graph, proof = fixture()
        mutations = [
            lambda g, p: p.update(extra_state_bits=1),
            lambda g, p: p['banks'][0].update(output=27),
            lambda g, p: p['banks'][0]['link_instances'].pop(),
            lambda g, p: g['connections'][str(p['banks'][0]['bit'])]['driver'].update(instance='hidden_buffer'),
            lambda g, p: g['boundary_links']['links'][0].update(reset_bit=-1),
            lambda g, p: p['banks'][0].update(source_instance='macro_r'),
        ]
        for mutation in mutations:
            g, p = copy.deepcopy(graph), copy.deepcopy(proof)
            mutation(g, p)
            with self.assertRaises(AssertionError):
                validate(g, p)


if __name__ == '__main__':
    unittest.main()
