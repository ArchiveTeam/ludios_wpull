# encoding=utf-8
import contextlib
import functools
import io
import warnings

from trollius import From
from wpull.abstract.client import DurationTimeout

from wpull.connection import ConnectionPool, Connection
from wpull.errors import NetworkError
from wpull.http.client import Client
from wpull.http.request import Request
from wpull.recorder.base import BaseRecorder, BaseRecorderSession
from wpull.testing.badapp import BadAppTestCase
import wpull.testing.async


DEFAULT_TIMEOUT = 30


class MockRecorder(BaseRecorder):
    def __init__(self):
        self.pre_request = None
        self.request = None
        self.pre_response = None
        self.response = None
        self.request_data = b''
        self.response_data = b''

    @contextlib.contextmanager
    def session(self):
        yield MockRecorderSession(self)


class MockRecorderSession(BaseRecorderSession):
    def __init__(self, recorder):
        self.recorder = recorder

    def pre_request(self, request):
        self.recorder.pre_request = request

    def request(self, request):
        self.recorder.request = request

    def pre_response(self, response):
        self.recorder.pre_response = response

    def response(self, response):
        self.recorder.response = response

    def request_data(self, data):
        self.recorder.request_data += data

    def response_data(self, data):
        self.recorder.response_data += data


class MyException(ValueError):
    pass


class TestClient(BadAppTestCase):
    @wpull.testing.async.async_test(timeout=DEFAULT_TIMEOUT)
    def test_basic(self):
        client = Client()

        with client.session() as session:
            request = Request(self.get_url('/'))
            response = yield From(session.fetch(request))

            self.assertEqual(200, response.status_code)
            self.assertEqual(request, response.request)

            file_obj = io.BytesIO()
            yield From(session.read_content(file_obj))

            self.assertEqual(b'hello world!', file_obj.getvalue())

            self.assertTrue(request.url_info)
            self.assertTrue(request.address)
            self.assertTrue(response.body)

    @wpull.testing.async.async_test(timeout=DEFAULT_TIMEOUT)
    def test_client_exception_throw(self):
        client = Client()

        with client.session() as session:
            request = Request('http://wpull-no-exist.invalid')

        with self.assertRaises(NetworkError):
            yield From(session.fetch(request))

    @wpull.testing.async.async_test(timeout=DEFAULT_TIMEOUT)
    def test_client_duration_timeout(self):
        client = Client()

        with self.assertRaises(DurationTimeout), client.session() as session:
            request = Request(self.get_url('/sleep_long'))
            yield From(session.fetch(request))
            yield From(session.read_content(duration_timeout=0.1))

    @wpull.testing.async.async_test(timeout=DEFAULT_TIMEOUT)
    def test_client_exception_recovery(self):
        connection_factory = functools.partial(Connection, timeout=2.0)
        connection_pool = ConnectionPool(connection_factory=connection_factory)
        client = Client(connection_pool=connection_pool)

        for dummy in range(7):
            with client.session() as session:
                request = Request(self.get_url('/header_early_close'))
                try:
                    yield From(session.fetch(request))
                except NetworkError:
                    pass
                else:
                    self.fail()  # pragma: no cover

        for dummy in range(7):
            with client.session() as session:
                request = Request(self.get_url('/'))
                response = yield From(session.fetch(request))
                self.assertEqual(200, response.status_code)
                yield From(session.read_content())
                self.assertTrue(session.done())

    @wpull.testing.async.async_test(timeout=DEFAULT_TIMEOUT)
    def test_client_recorder(self):
        recorder = MockRecorder()
        client = Client(recorder=recorder)

        with client.session() as session:
            request = Request(self.get_url('/'))
            response = yield From(session.fetch(request))
            yield From(session.read_content())
            self.assertEqual(200, response.status_code)

        self.assertTrue(recorder.pre_request)
        self.assertTrue(recorder.request)
        self.assertTrue(recorder.pre_response)
        self.assertTrue(recorder.response)

        self.assertIn(b'GET', recorder.request_data)
        self.assertIn(b'hello', recorder.response_data)

    @wpull.testing.async.async_test(timeout=DEFAULT_TIMEOUT)
    def test_client_did_not_complete(self):
        client = Client()

        with warnings.catch_warnings(record=True) as warn_list:
            warnings.simplefilter("always")

            with client.session() as session:
                request = Request(self.get_url('/'))
                yield From(session.fetch(request))
                self.assertFalse(session.done())

            for warn_obj in warn_list:
                print(warn_obj)

            # Unrelated warnings may occur in PyPy
            # https://travis-ci.org/chfoo/wpull/jobs/51420202
            self.assertGreaterEqual(len(warn_list), 1)

            for warn_obj in warn_list:
                if str(warn_obj.message) == 'HTTP session did not complete.':
                    break
            else:
                self.fail('Warning did not occur.')

        client = Client()

        with self.assertRaises(MyException):
            with client.session() as session:
                request = Request(self.get_url('/'))
                yield From(session.fetch(request))
                raise MyException('Oops')
