

def total_ordering(cls):
    """
    Backport to work with Python 2.6

    Class decorator that fills in missing ordering methods

    Code from: http://code.activestate.com/recipes/576685/
    """
    # https://github.com/kvesteri/total-ordering/blob/master/total_ordering.py
    convert = {
        '__lt__': [
            (
                '__gt__',
                lambda self, other: not (self < other or self == other)
            ),
            (
                '__le__',
                lambda self, other: self < other or self == other
            ),
            (
                '__ge__',
                lambda self, other: not self < other
            )],
        '__le__': [
            (
                '__ge__',
                lambda self, other: not self <= other or self == other
            ),
            (
                '__lt__',
                lambda self, other: self <= other and not self == other
            ),
            (
                '__gt__',
                lambda self, other: not self <= other
            )],
        '__gt__': [
            (
                '__lt__',
                lambda self, other: not (self > other or self == other)
            ),
            (
                '__ge__',
                lambda self, other: self > other or self == other
            ),
            (
                '__le__',
                lambda self, other: not self > other
            )],
        '__ge__': [
            (
                '__le__',
                lambda self, other: (not self >= other) or self == other
            ),
            (
                '__gt__',
                lambda self, other: self >= other and not self == other
            ),
            (
                '__lt__',
                lambda self, other: not self >= other
            )]
    }
    roots = set(dir(cls)) & set(convert)
    if not roots:
        raise ValueError(
            'must define at least one ordering operation: < > <= >='
        )
    root = max(roots)  # prefer __lt__ to __le__ to __gt__ to __ge__
    for opname, opfunc in convert[root]:
        if opname not in roots:
            opfunc.__name__ = opname
            opfunc.__doc__ = getattr(int, opname).__doc__
            setattr(cls, opname, opfunc)
    return cls
