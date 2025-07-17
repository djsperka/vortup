from vortex import Range
from PyQt5.QtCore import QRegExp

_regexForExtents = QRegExp("((-?\d+)[\s,]+(-?\d+))|(-?\d+)")


def getRangeFromTextEntry(txt) -> Range:
    # match regex. Validator should ensure that there is ALWAYS a match, but throw exception if not.
    if _regexForExtents.exactMatch(txt):
        if _regexForExtents.cap(4) == '':
            iLow = int(_regexForExtents.cap(2))
            iHigh = int(_regexForExtents.cap(3))
            r = Range(iLow, iHigh)
        else:
            iVal = int(_regexForExtents.cap(4))
            r = Range(-iVal, iVal)
    else:
        raise RuntimeError("Cannot parse X extents: ", )
    print("got range from entry ", txt, "(", r.min, ",", r.max,")")
    return r
