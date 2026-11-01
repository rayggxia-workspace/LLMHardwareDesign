"""Reject route/placement/connection edits and geometrically disconnected pins."""
import unittest
from postroute_buffer_audit import compare_def_lines, pin_contact_audit


class AuditTest(unittest.TestCase):
    def test_exact_def_and_unrelated_changes(self):
        old=[b'COMPONENTS 1 ;\n', b'    - place571072 BUF_X4 + SOURCE TIMING + PLACED ( 1110360 1727600 ) N ;\n', b'NETS 1 ;\n', b'    - n ( place571072 Z ) ( ff D ) ;\n']
        new=old.copy();new[1]=new[1].replace(b'BUF_X4',b'CLKBUF_X3')
        self.assertTrue(compare_def_lines(old,new)['unchanged_all_routes_and_ports'])
        for index, token in ((1,b'1727600'), (3,b'ff D')):
            broken=new.copy();broken[index]=broken[index].replace(token,b'bad')
            with self.assertRaises(AssertionError):compare_def_lines(old,broken)
        with self.assertRaises(AssertionError):compare_def_lines(old,old)
        with self.assertRaises(AssertionError):compare_def_lines(old,new+[b'NEW route\n'])

    def test_physical_contact_and_misalignment(self):
        rows=['BUF_X4\t2660\t2800\tA\tINPUT\tmetal1\t120\t1050\t340\t1400',
              'BUF_X4\t2660\t2800\tZ\tOUTPUT\tmetal1\t1230\t300\t1370\t2500',
              'CLKBUF_X3\t1900\t2800\tA\tINPUT\tmetal1\t120\t1050\t380\t1400',
              'CLKBUF_X3\t1900\t2800\tZ\tOUTPUT\tmetal1\t850\t840\t1730\t1120']
        wires=['A\tmetal1\twire-via\t1110520\t1728690\t1110660\t1728830',
               'Z\tmetal1\twire-via\t1111620\t1728510\t1111760\t1728650']
        self.assertTrue(pin_contact_audit(rows,wires)['passed'])
        broken=rows.copy();broken[-1]=broken[-1].replace('\t840\t1730\t1120','\t1500\t1730\t1800')
        with self.assertRaises(AssertionError):pin_contact_audit(broken,wires)
        with self.assertRaises(AssertionError):pin_contact_audit(rows,wires[:1])


if __name__=='__main__':unittest.main()
