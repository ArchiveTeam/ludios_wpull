# encoding=utf-8
'''Document readers.'''
import abc
import lxml.html
import re

import wpull.util
import wpull.http.util


class BaseDocumentReader(object, metaclass=abc.ABCMeta):
    '''Base class for classes that read documents.'''

    @abc.abstractmethod
    def parse(self, file):
        '''Read and return a document.

        The arguments and return value will depend on the implementation.
        '''
        pass

    @classmethod
    def is_supported(cls, file):
        '''Return whether the reader is likely able to read the document.

        The arguments will depend on the implementation.

        Returns:
            bool: If True, reader should be able to read it.
        '''
        # Python 2.6 doesn't support abc.abstractclassmethod
        raise NotImplementedError()


class HTMLReader(BaseDocumentReader):
    '''HTML document reader.

    This reader uses lxml as the parser.
    '''
    def parse(self, file, encoding=None, base_url=None):
        '''Parse the HTML file and return the document.

        Args:
            file: A file object.
            encoding (str): If provided, it will override the encoding
                specified in the document.
            base_url (str): If provided, it will override the base URL
                specified in the document.

        Returns:
            _ElementTree: An instance of :class:`lxml.etree._ElementTree`.
        '''
        if encoding:
            # XXX: Workaround lxml not liking utf-16-le
            encoding = encoding.replace('-', '')

        parser = lxml.html.HTMLParser(encoding=encoding)

        with wpull.util.reset_file_offset(file):
            tree = lxml.html.parse(
                file,
                base_url=base_url,
                parser=parser,
            )
            return tree

    @classmethod
    def is_supported(cls, file, request=None, response=None, url_info=None):
        '''Return whether the file is likely to be HTML.'''
        if response and cls.is_html_response(response) \
        or request and cls.is_html_request(request) \
        or url_info and cls.is_html_url_info(url_info):
            return True

        if cls.is_html_file(file):
            return True

    @classmethod
    def is_html(cls, request, response):
        '''Return whether Request/Response is likely to be HTML.'''
        return cls.is_html_request(request) or cls.is_html_response(response)

    @classmethod
    def is_html_response(cls, response):
        '''Return whether the Response is likely to be HTML.'''
        if 'html' in response.fields.get('content-type', '').lower():
            return True

        if response.body:
            return cls.is_html_file(response.body.content_file)

    @classmethod
    def is_html_request(cls, request):
        '''Return whether the Request is likely to be a HTML.'''
        return cls.is_html_url_info(request.url_info)

    @classmethod
    def is_html_url_info(cls, url_info):
        '''Return whether the URLInfo is likely to be a HTML.'''
        if '.htm' in url_info.path.lower():
            return True

    @classmethod
    def is_html_file(cls, file):
        '''Return whether the file is likely to be HTML.'''
        peeked_data = wpull.util.peek_file(file).replace(b'\x00', b'').lower()

        if b'<html' in peeked_data \
        or b'<head' in peeked_data \
        or b'<title' in peeked_data \
        or b'<table' in peeked_data \
        or b'<a href' in peeked_data:
            return True


class CSSReader(BaseDocumentReader):
    '''Cascading Stylesheet Document Reader.'''
    def parse(self, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def is_supported(cls, file, request=None, response=None, url_info=None):
        '''Return whether the file is likely to be CSS.'''
        if request and cls.is_css_request(request) \
        or response and cls.is_css_response(response) \
        or url_info and cls.is_css_url_info(url_info):
            return True

        return cls.is_css_file(file)

    @classmethod
    def is_css(cls, request, response):
        '''Return whether the document is likely to be CSS.'''
        if cls.is_css_request(request) or cls.is_css_response(response):
            return True

        if response.body:
            if 'html' in response.fields.get('content-type', '').lower() \
            and cls.is_css_file(response.body.content_file):
                return True

    @classmethod
    def is_css_url_info(cls, url_info):
        '''Return whether the document is likely to be CSS.'''
        if '.css' in url_info.path.lower():
            return True

    @classmethod
    def is_css_request(cls, request):
        '''Return whether the document is likely to be CSS.'''
        return cls.is_css_url_info(request.url_info)

    @classmethod
    def is_css_response(cls, response):
        '''Return whether the document is likely to be CSS.'''
        if 'css' in response.fields.get('content-type', '').lower():
            return True

    @classmethod
    def is_css_file(cls, file):
        '''Return whether the file is likely CSS.'''
        peeked_data = wpull.util.peek_file(file).lower()

        if b'<html' in peeked_data:
            return False

        if re.search(br'@import |color:|background[a-z-]*:|font[a-z-]*:',
        peeked_data):
            return True


def get_heading_encoding(response):
    '''Return the document encoding from a HTTP header.

    Args:
        response (Response): An instance of :class:`.http.Response`.

    Returns:
        ``str``, ``None``: The codec name.
    '''
    encoding = wpull.http.util.parse_charset(
        response.fields.get('content-type', ''))

    if encoding:
        return wpull.util.normalize_codec_name(encoding)
    else:
        return None


def get_encoding(response, is_html=False, peek=10485760):
    '''Return the likely encoding of the document.

    Args:
        response (Response): An instance of :class:`.http.Response`.
        is_html (bool): See :func:`.util.detect_encoding`.
        peek (int): The number of bytes to read of the document.

    Returns:
        ``str``, ``None``: The codec name.
    '''
    encoding = wpull.http.util.parse_charset(
        response.fields.get('content-type', '')
    )

    encoding = wpull.util.detect_encoding(
        response.body.content_peek(peek), encoding=encoding, is_html=is_html
    )

    return encoding
