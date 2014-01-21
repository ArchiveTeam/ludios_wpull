# encoding=utf-8
import sys
import time
import tornado.testing

from wpull.backport.testing import unittest
from wpull.util import (to_bytes, sleep, to_str, datetime_str, OrderedDefaultDict,
    wait_future, TimedOut, python_version)


class TestUtil(unittest.TestCase):
    def test_to_bytes(self):
        self.assertEqual(b'hi', to_bytes('hi'))
        self.assertEqual([b'hi'], to_bytes(['hi']))
        self.assertEqual({b'hi': b'hello'}, to_bytes({'hi': 'hello'}))

    def test_to_str(self):
        self.assertEqual('hi', to_str(b'hi'))
        self.assertEqual(['hi'], to_str([b'hi']))
        self.assertEqual({'hi': 'hello'}, to_str({b'hi': b'hello'}))

    def test_datetime_str(self):
        self.assertEqual(20, len(datetime_str()))

    def test_ordered_default_dict(self):
        mapping = OrderedDefaultDict(lambda: 2)
        mapping['a'] += 4
        mapping['b'] += 3
        mapping['c'] += 2

        self.assertEqual(
            [('a', 6), ('b', 5), ('c', 4)],
            list(mapping.items())
        )

    def test_python_version(self):
        version_string = python_version()
        nums = tuple([int(n) for n in version_string.split('.')])
        self.assertEqual(3, len(nums))
        self.assertEqual(nums, sys.version_info[0:3])


class TestUtilAsync(tornado.testing.AsyncTestCase):
    @tornado.testing.gen_test
    def test_sleep(self):
        start_time = time.time()
        yield sleep(1.0)
        end_time = time.time()

        self.assertAlmostEqual(1.0, end_time - start_time, delta=0.5)

    @tornado.testing.gen_test
    def test_wait_future(self):
        @tornado.gen.coroutine
        def test_func():
            yield sleep(0.1)

        yield wait_future(test_func(), 2)

    @tornado.testing.gen_test
    def test_wait_future_none(self):
        @tornado.gen.coroutine
        def test_func():
            yield sleep(0.1)

        yield wait_future(test_func(), None)

    @tornado.testing.gen_test
    def test_wait_future_timeout(self):
        @tornado.gen.coroutine
        def test_func():
            yield sleep(60.0)

        try:
            yield wait_future(test_func(), 0.1)
        except TimedOut:
            pass
        else:
            self.assertTrue(False)

    @tornado.testing.gen_test
    def test_wait_future_error(self):
        @tornado.gen.coroutine
        def test_func():
            yield sleep(0.1)
            raise ValueError('uh-oh')

        try:
            yield wait_future(test_func(), 2.0)
        except ValueError as error:
            self.assertEqual('uh-oh', error.args[0])
        else:
            self.assertTrue(False)
