# encoding=utf-8
import collections
import gettext
import io

from wpull.util import to_str, OrderedDefaultDict


_ = gettext.gettext


class NameValueRecord(collections.MutableMapping):
    def __init__(self):
        self._map = OrderedDefaultDict(list)
        self.raw = None
        self.encoding = 'utf-8'

    def parse(self, string, encoding_fallback='latin1'):
        if isinstance(string, bytes):
            try:
                string = string.decode(self.encoding, 'strict')
            except UnicodeError:
                if encoding_fallback:
                    string = string.decode(encoding_fallback)
                    self.encoding = encoding_fallback
                else:
                    raise

        if not self.raw:
            self.raw = string
        else:
            self.raw += string

        line_ending = guess_line_ending(string)
        lines = unfold_lines(string).split(line_ending)
        for line in lines:
            if line:
                name, value = line.split(':', 1)
                name = name.strip()
                value = value.strip()
                self.add(name, value)

    def __getitem__(self, name):
        normalized_name = normalize_name(name)

        if normalized_name in self._map:
            if self._map[normalize_name(name)]:
                return self._map[normalize_name(name)][0]

        raise KeyError(name)

    def __setitem__(self, name, value):
        self._map[normalize_name(name)][:] = (value,)

    def __delitem__(self, name):
        del self._map[normalize_name(name)]

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def add(self, name, value):
        self._map[normalize_name(name)].append(value)

    def get_list(self, name):
        return self._map[normalize_name(name)]

    def get_all(self):
        for name, values in self._map.items():
            for value in values:
                yield (name, value)

    def __str__(self):
        pairs = []
        for name, value in self.get_all():
            if value:
                pairs.append('{0}: {1}'.format(name, value))
            else:
                pairs.append('{0}:'.format(name))

        pairs.append('')
        return '\r\n'.join(pairs)

    def __bytes__(self):
        return str(self).encode(self.encoding)


def normalize_name(name):
    return name.title()


def guess_line_ending(string):
    assert isinstance(string, str)
    crlf_count = string.count('\r\n')
    lf_count = string.count('\n')

    if crlf_count >= lf_count:
        return '\r\n'
    else:
        return '\n'


def unfold_lines(string):
    assert isinstance(string, str)
    line_ending = guess_line_ending(string)
    lines = string.split(line_ending)
    line_buffer = io.StringIO()

    for line_number in range(len(lines)):
        line = lines[line_number]
        if line and line[0:1] in (' ', '\t'):
            line_buffer.write(' ')
        elif line_number != 0:
            line_buffer.write(line_ending)
        line_buffer.write(line.strip())

    return line_buffer.getvalue()
