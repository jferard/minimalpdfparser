import unittest

from pdf_operation import ModifyCTM, AppendRectangle


class OperationTestCase(unittest.TestCase):
    def test_repr(self):
        self.assertEqual("ModifyCTM(a=1,b=2,c=3,d=4,e=5,f=6)", str(ModifyCTM(1, 2, 3, 4, 5, 6)))
        self.assertEqual("AppendRectangle(x=1,y=2,w=3,h=4)", str(AppendRectangle(1, 2, 3, 4)))


if __name__ == '__main__':
    unittest.main()
