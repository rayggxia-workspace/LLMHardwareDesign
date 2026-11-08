import unittest
from assembly_sta import translate_sdc


class ConstraintsTest(unittest.TestCase):
    def test_namespace_preserves_timing_limits_and_multiline_false_paths(self):
        raw='''current_design local
create_clock -name clk -period 3.3333 [get_ports {clk_i}]
set_clock_uncertainty 0.1000 clk
set_driving_cell -lib_cell BUF_X4 [get_ports {data_i[0]}]
set_load -pin_load 50.0000 [get_ports {data_o[0]}]
set_output_delay 0.8000 -clock [get_clocks {clk}] [get_ports {late_o}]
set_false_path\\
 -from [get_pins {controller/register/CK}]\\
 -to [get_pins {controller/register/D}]
'''
        text,removed=translate_sdc(raw,'P0','P',{'late_o'})
        self.assertIn(r'-period 3.3333 [get_ports {P0\/clk_i}]',text)
        self.assertIn('set_clock_uncertainty 0.1000 P0__clk',text)
        self.assertIn('-lib_cell SRC_P_BUF_X4',text)
        self.assertIn(r'set_load -pin_load 50.0000 [get_ports {P0\/data_o[0]}]',text)
        self.assertIn(r'[get_pins {P0\/controller/register/CK}]',text)
        self.assertIn(r'[get_pins {P0\/controller/register/D}]',text)
        self.assertEqual(len(removed),1);self.assertNotIn('late_o',text)

    def test_unsupported_constraints_fail_instead_of_disappearing(self):
        with self.assertRaises(AssertionError):
            translate_sdc('create_clock -name clk -period 3.3 [get_ports {clk}]\nset_max_delay 9 -to [all_outputs]\n','U0','U',set())


if __name__=='__main__':unittest.main()
