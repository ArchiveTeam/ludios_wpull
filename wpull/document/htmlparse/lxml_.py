'''Parsing using html5-parser and lxml.'''
import io

import html5_parser
import lxml.html

from wpull.document.htmlparse.base import BaseParser
from wpull.document.xml import XMLDetector
import wpull.util


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
            iterator: Each item is either :class:`lxml.etree._Comment`
            or :class:`lxml.etree._Element`
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

        return tree.getiterator()

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
