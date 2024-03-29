# encoding=utf-8
import unittest

from wpull.protocol.http.request import Request, Response
from wpull.cookiewrapper import convert_http_request, HTTPResponseInfoWrapper


class TestWrapper(unittest.TestCase):
    def test_http_request(self):
        request = Request('http://example.com')
        request.fields['hello'] = 'world'
        new_request = convert_http_request(request)

        self.assertEqual('example.com', new_request.host)
        self.assertEqual('world', new_request.get_header('Hello'))

    def test_http_response(self):
        response = Response(200, 'OK', version='HTTP/1.0')
        response.fields['hello'] = 'world'

        new_response = HTTPResponseInfoWrapper(response)
        info = new_response.info()

        self.assertEqual('world', info.get('hello'))
