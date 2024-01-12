import io
import logging

from wpull.protocol.abstract.client import DurationTimeout
from wpull.errors import ProtocolError

from wpull.protocol.ftp.client import Client
from wpull.protocol.ftp.request import Request, Command
from wpull.protocol.ftp.util import FTPServerError
from wpull.testing.ftp import FTPTestCase
from tornado.testing import gen_test

_logger = logging.getLogger(__name__)


class TestClient(FTPTestCase):
    @gen_test(timeout=30)
    async def test_fetch_file(self):
        client = Client()
        file = io.BytesIO()

        with client.session() as session:
            response = await \
                session.start(Request(self.get_url('/example (copy).txt')))
            await session.download(file)

        self.assertEqual(
            'The real treasure is in Smaug’s heart 💗.\n'.encode('utf-8'),
            response.body.content()
        )

    @gen_test(timeout=30)
    async def test_duration_timeout(self):
        client = Client()
        file = io.BytesIO()

        with self.assertRaises(DurationTimeout), client.session() as session:
            await \
                session.start(Request(self.get_url('/hidden/sleep.txt')))
            await session.download(file, duration_timeout=0.1)

    @gen_test(timeout=30)
    async def test_fetch_no_file(self):
        client = Client()
        file = io.BytesIO()

        with client.session() as session:
            try:
                await \
                    session.start(Request(self.get_url('/asdf.txt')))
                await session.download(file)
            except FTPServerError as error:
                self.assertEqual(550, error.reply_code)
            else:
                self.fail()  # pragma: no cover

    @gen_test(timeout=30)
    async def test_fetch_file_restart(self):
        client = Client()
        file = io.BytesIO()

        with client.session() as session:
            request = Request(self.get_url('/example (copy).txt'))
            request.set_continue(10)
            response = await session.start(request)
            self.assertEqual(10, response.restart_value)
            await session.download(file)

        self.assertEqual(
            'reasure is in Smaug’s heart 💗.\n'.encode('utf-8'),
            response.body.content()
        )

    @gen_test(timeout=30)
    async def test_fetch_file_restart_not_supported(self):
        client = Client()
        file = io.BytesIO()

        with client.session() as session:
            request = Request(self.get_url('/example (copy).txt'))
            request.set_continue(99999)  # Magic value in the test server
            response = await session.start(request)
            self.assertFalse(response.restart_value)
            await session.download(file)

        self.assertEqual(
            'The real treasure is in Smaug’s heart 💗.\n'.encode('utf-8'),
            response.body.content()
        )

    @gen_test(timeout=30)
    async def test_fetch_listing(self):
        client = Client()
        file = io.BytesIO()
        with client.session() as session:
            response = await \
                session.start_listing(Request(self.get_url('/')))
            await session.download_listing(file)

        print(response.body.content())
        self.assertEqual(5, len(response.files))
        self.assertEqual('junk', response.files[0].name)
        self.assertEqual('example1', response.files[1].name)
        self.assertEqual('example2💎', response.files[2].name)
        self.assertEqual('example (copy).txt', response.files[3].name)
        self.assertEqual('readme.txt', response.files[4].name)

    @gen_test(timeout=30)
    async def test_fetch_bad_pasv_addr(self):
        client = Client()
        file = io.BytesIO()

        with client.session() as session:
            original_func = session._log_in

            async def override_func():
                await original_func()
                await session._control_stream.write_command(Command('EVIL_BAD_PASV_ADDR'))
                print('Evil awaits')

            # TODO: should probably have a way of sending custom commands
            session._log_in = override_func

            with self.assertRaises(ProtocolError):
                await \
                    session.start(Request(self.get_url('/example (copy).txt')))

    @gen_test(timeout=30)
    async def test_login_no_password_required(self):
        client = Client()
        file = io.BytesIO()

        with client.session() as session:
            request = Request(self.get_url('/example (copy).txt'))
            request.username = 'no_password_required'
            await session.start(request)
            await session.download(file)
