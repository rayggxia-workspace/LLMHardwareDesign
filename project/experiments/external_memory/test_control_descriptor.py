import unittest
from control_descriptor import encode

class Descriptor(unittest.TestCase):
    def test_units_and_reserved_fields(self):
        for mode in (0, 1):
            words=encode(mode, 0x1000, 512, 3, 7, 16, 32)
            self.assertEqual(words,[mode,0x1000,256<<12,112,3|(512<<16),512,0,0])
    def test_full_s_and_last_external_word(self):
        self.assertEqual(encode(0,0,16384,1,1024,0,1024)[3],16384)
        self.assertEqual(encode(1,2**32-16,16,1,1,1023,1)[1],2**32-16)
    def test_rejections(self):
        good=[0,0x1000,512,3,7,16,32]
        for index,value in [(0,2),(0,3),(1,1),(1,2**32),(2,1),(3,0),(3,1025),(4,0),(4,1025),(5,1024),(6,6),(6,2048)]:
            with self.subTest(index=index,value=value):
                bad=good.copy();bad[index]=value
                with self.assertRaises(ValueError):encode(*bad)
        for args in [(0,2**32-16,32,2,1,0,1),(0,0,16384,2,1024,0,1024),(0,0,512,2,7,1020,7)]:
            with self.assertRaises(ValueError):encode(*args)

if __name__=='__main__':unittest.main()
