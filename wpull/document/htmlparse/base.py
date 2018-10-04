import abc


class BaseParser(object, metaclass=abc.ABCMeta):
    def parse(self, file, encoding=None):
        '''Parse the document for elements.

        Returns:
            iterator: Each item is either :class:`lxml.etree._Comment`
            or :class:`lxml.etree._Element`
        '''

    @abc.abstractproperty
    def parser_error(self):
        '''Return the Exception class for parsing errors.'''
