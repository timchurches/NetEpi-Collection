#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "NetEpi Collection". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.
#
#   Copyright (C) 2004-2011 Health Administration Corporation, Australian
#   Government Department of Health and Ageing, and others.
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#

class TupleStruct(object):
    __slots__ = ()

    def __init__(self, *args, **kw):
        if args:
            if len(args) != len(self):
                raise TypeError('%s requires %d values, %d given' % 
                                (self.__class__.__name__, len(self), len(args)))
            for a, v in zip(self.__slots__, args):
                setattr(self, a, v)
        elif kw:
            if len(kw) != len(self):
                raise TypeError('%s requires %d values, %d given' % 
                                (self.__class__.__name__, len(self), len(kw)))
            for a, v in kw.items():
                setattr(self, a, v)

    def __getstate__(self):
        return [getattr(self, a) for a in self.__slots__]

    def __setstate__(self, state):
        assert len(state) == len(self.__slots__)
        for a, v in zip(self.__slots__, state):
            setattr(self, a, v)

    def __getitem__(self, i):
        return getattr(self, self.__slots__[i])

    def __setitem__(self, i, v):
        setattr(self, self.__slots__[i], v)

    def __len__(self):
        return len(self.__slots__)

    def __repr__(self):
        values = ['%s=%r' % (a, getattr(self, a)) for a in self.__slots__]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(values))

if __name__ == '__main__':
    class SS(TupleStruct): __slots__ = 'a', 'b'
    ss = SS(3, 4)
    assert (ss.a, ss.b) == (3, 4)
    assert tuple(ss) == (3, 4)
    try:
        ss.x
    except AttributeError:
        pass
    else:
        assert 0, "attribute error not raised"
