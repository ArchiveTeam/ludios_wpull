'''HTML document readers.'''

from wpull.document.base import BaseHTMLReader, BaseDocumentDetector
import wpull.string


class HTMLReadElement:
    '''Results from :meth:`HTMLReader.read_links`.

    Attributes:
        tag (str): The element tag name.
        attrib (dict): The element attributes.
        text (str, None): The element text.
        tail (str, None): The text after the element.
        end (bool): Whether the tag is an end tag.
    '''
    __slots__ = ('tag', 'attrib', 'text', 'tail', 'end')

    def __init__(self, tag, attrib, text, tail, end):
        self.tag = tag
        self.attrib = attrib
        self.text = text
        self.tail = tail
        self.end = end

    def __repr__(self):
        return 'HTMLReadElement({0}, {1}, {2}, {3}, {4})'.format(
            repr(self.tag), repr(self.attrib), repr(self.text),
            repr(self.tail), repr(self.end)
        )


class HTMLReader(BaseDocumentDetector, BaseHTMLReader):
    '''HTML document reader.

    Arguments:
        html_parser (:class:`.document.htmlparse.BaseParser`): An HTML parser.
    '''
    def __init__(self, html_parser):
        self._html_parser = html_parser

    @classmethod
    def is_response(cls, response):
        '''Return whether the Response is likely to be HTML.'''
        if 'html' in response.fields.get('content-type', '').lower():
            return True

        if response.body:
            return cls.is_file(response.body)

    @classmethod
    def is_request(cls, request):
        '''Return whether the Request is likely to be a HTML.'''
        return cls.is_url(request.url_info)

    @classmethod
    def is_url(cls, url_info):
        '''Return whether the URLInfo is likely to be a HTML.'''
        path = url_info.path.lower()
        if '.htm' in path or '.dhtm' in path or '.xht' in path:
            return True

    @classmethod
    def is_file(cls, file):
        '''Return whether the file is likely to be HTML.'''
        peeked_data = wpull.string.printable_bytes(
            wpull.util.peek_file(file)).lower()

        if b'<!doctype html' in peeked_data \
           or b'<head' in peeked_data \
           or b'<title' in peeked_data \
           or b'<html' in peeked_data \
           or b'<script' in peeked_data \
           or b'<table' in peeked_data \
           or b'<a href' in peeked_data:
            return True

    def iter_elements(self, file, encoding=None):
        return self._html_parser.parse(file, encoding)
