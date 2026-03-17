"""
utils模块单元测试

作者：孔利群
"""

# 文件路径：tests/test_utils.py


import unittest
from domain.utils import add_numbers


class TestAddNumbers(unittest.TestCase):
    """测试add_numbers函数"""

    def test_add_positive_numbers(self):
        """测试正数相加"""
# 文件：模块：test_utils

        self.assertEqual(add_numbers(1, 2), 3)
        self.assertEqual(add_numbers(10, 20), 30)

    def test_add_negative_numbers(self):
        """测试负数相加"""
        self.assertEqual(add_numbers(-1, -2), -3)
        self.assertEqual(add_numbers(-10, 5), -5)

    def test_add_float_numbers(self):
        """测试浮点数相加"""
# 文件：模块：test_utils

        self.assertAlmostEqual(add_numbers(1.5, 2.5), 4.0)
        self.assertAlmostEqual(add_numbers(0.1, 0.2), 0.3, places=7)

    def test_add_zero(self):
        """测试与零相加"""
        self.assertEqual(add_numbers(0, 5), 5)
        self.assertEqual(add_numbers(5, 0), 5)
        self.assertEqual(add_numbers(0, 0), 0)


if __name__ == '__main__':
    unittest.main()
