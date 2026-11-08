import unittest
from copy import deepcopy
from rc_graph import extract
from search import route


class GraphTest(unittest.TestCase):
    def test_branch_and_duplicate_edge(self):
        from test_router import sample
        spec=sample()
        spec['pins']['second']=[[70,6,74,10]]
        spec['nets'][0]['sinks'].append('second')
        routes=route(spec)
        graph=extract(spec,routes,dbu_per_micron=2000,sheet_resistance_ohm=.0102,via_resistance_ohm=.08)
        for row in graph['nets'].values():
            self.assertTrue(all(e['ohm']>0 for e in row['resistors']))
            self.assertEqual(len(row['resistors']),len({(e['a'],e['b']) for e in row['resistors']}))
        altered=deepcopy(routes)
        name=next(iter(altered['routes']))
        altered['routes'][name]['segments']*=2
        other=extract(spec,altered,dbu_per_micron=2000,sheet_resistance_ohm=.0102,via_resistance_ohm=.08)
        self.assertEqual(graph['nets'],other['nets'])


if __name__=='__main__':unittest.main()
