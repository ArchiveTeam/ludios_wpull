# encoding=utf-8
from packaging.version import parse
import unittest

import wpull.version
from wpull.version import get_version_tuple


class TestVersion(unittest.TestCase):
    def test_valid_version_str(self):
        parse(wpull.version.__version__)

    def test_version_string_buidler(self):
        self.assertEqual(
            (0, 0, 0, 'final', 0),
            get_version_tuple('0.0')
        )
        self.assertEqual(
            (0, 1, 0, 'final', 0),
            get_version_tuple('0.1')
        )
        self.assertEqual(
            (0, 1, 1, 'final', 0),
            get_version_tuple('0.1.1')
        )
        self.assertEqual(
            (0, 1, 1, 'alpha', 0),
            get_version_tuple('0.1.1a0')
        )
        self.assertEqual(
            (0, 1, 0, 'beta', 0),
            get_version_tuple('0.1b0')
        )
        self.assertEqual(
            (0, 1, 0, 'candidate', 3),
            get_version_tuple('0.1c3')
        )
        self.assertEqual(
            (1, 0, 0, 'final', 0),
            get_version_tuple('1.0')
        )
        self.assertEqual(
            (100000, 0, 0, 'final', 0),
            get_version_tuple('100000.0')
        )
