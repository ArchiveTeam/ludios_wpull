'''Parsing using html5-parser and lxml.'''
import io

import html5_parser
import lxml.html

from wpull.collections import EmptyFrozenDict, FrozenDict
from wpull.document.htmlparse.base import BaseParser
from wpull.document.htmlparse.element import Element, Comment
from wpull.document.xml import XMLDetector
import wpull.util


class HTMLParserTarget(object):
    '''An HTML parser target.

    Args:
        callback: A callback function. The function should accept one
            argument from :mod:`.document.htmlparse.element`.
    '''
    def __init__(self, callback):
        self.callback = callback
        self.tag = None
        self.attrib = None
        self.buffer = None
        self.tail_buffer = None

    def start(self, tag, attrib):
        if self.buffer:
            self.callback(Element(
                self.tag, self.attrib,
                self.buffer.getvalue(),
                None, False
            ))
            self.buffer = None

        if self.tail_buffer:
            self.callback(Element(
                self.tag, EmptyFrozenDict(),
                None,
                self.tail_buffer.getvalue(),
                True
            ))
            self.tail_buffer = None

        self.tag = tag
        self.attrib = FrozenDict(attrib)
        self.buffer = io.StringIO()

    def data(self, data):
        if self.buffer:
            self.buffer.write(data)

        if self.tail_buffer:
            self.tail_buffer.write(data)

    def end(self, tag):
        if self.buffer:
            self.callback(Element(
                tag, self.attrib,
                self.buffer.getvalue(),
                None, False
            ))
            self.buffer = None

        if self.tail_buffer:
            self.callback(Element(
                self.tag, EmptyFrozenDict(),
                None,
                self.tail_buffer.getvalue(),
                True
            ))
            self.tail_buffer = None

        self.tail_buffer = io.StringIO()
        self.tag = tag

    def comment(self, text):
        self.callback(Comment(text))

    def close(self):
        if self.buffer:
            self.callback(Element(
                self.tag, self.attrib,
                self.buffer.getvalue(),
                None, False
            ))
            self.buffer = None

        if self.tail_buffer:
            self.callback(Element(
                self.tag, EmptyFrozenDict(),
                None,
                self.tail_buffer.getvalue(),
                True
            ))
            self.tail_buffer = None

        return True


class HTMLParser(BaseParser):
    '''HTML document parser.

    This reader uses html5-parser or lxml as the parser.
    '''
    @property
    def parser_error(self):
        return lxml.etree.LxmlError

    def parse(self, file, encoding=None):
        parser_type = self.detect_parser_type(file, encoding=encoding)

        for element in self.parse_html(file, encoding=encoding,
                                       parser_type=parser_type):
            yield element

    def parse_html(self, file, encoding=None, parser_type='html'):
        '''Return an iterator of elements found in the document.

        Args:
            file: A file object containing the document.
            encoding (str): The encoding of the document.
            parser_type (str): The type of parser to use. Accepted values:
                ``html``, ``xhtml``, ``xml``.

        Returns:
            iterator: Each item is an element from
            :mod:`.document.htmlparse.element`
        '''
        content = file.read()
        if parser_type == 'html':
            tree = html5_parser.parse(content, transport_encoding=encoding)
        elif parser_type == 'xhtml':
            tree = html5_parser.parse(content, transport_encoding=encoding, maybe_xhtml=True)
        else:
            parser = lxml.etree.XMLParser(encoding=encoding, recover=True)
            tree = parser.parse(content)
            parser.close()

        for element in tree.getiterator():
            yield element

    @classmethod
    def parse_doctype(cls, file, encoding=None):
        '''Get the doctype from the document.

        Returns:
            str, None
        '''
        try:
            parser = lxml.etree.XMLParser(encoding=encoding, recover=True)
            tree = lxml.etree.parse(
                io.BytesIO(wpull.util.peek_file(file)), parser=parser
            )
            if tree.getroot() is not None:
                return tree.docinfo.doctype
        except lxml.etree.LxmlError:
            pass

    @classmethod
    def detect_parser_type(cls, file, encoding=None):
        '''Get the suitable parser type for the document.

        Returns:
            str
        '''
        is_xml = XMLDetector.is_file(file)
        doctype = cls.parse_doctype(file, encoding=encoding) or ''

        if not doctype and is_xml:
            return 'xml'

        if 'XHTML' in doctype:
            return 'xhtml'

        return 'html'
