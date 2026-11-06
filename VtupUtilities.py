import logging

from PyQt5.QtCore import QRegExp
from vortex import Range

_regexForExtents = QRegExp(r"((-?\d+)[\s,]+(-?\d+))|(-?\d+)")


def getRangeFromTextEntry(txt) -> Range:
    # match regex. Validator should ensure that there is ALWAYS a match, but throw exception if not.
    if _regexForExtents.exactMatch(txt):
        if _regexForExtents.cap(4) == "":
            iLow = int(_regexForExtents.cap(2))
            iHigh = int(_regexForExtents.cap(3))
            r = Range(iLow, iHigh)
        else:
            iVal = int(_regexForExtents.cap(4))
            r = Range(-iVal, iVal)
    else:
        raise RuntimeError(
            "Cannot parse X extents: ",
        )
    return r


def python_log_level(vortex_level: int) -> int:
    """Convert a vortex (spdlog) log level to a Python logging level.

    vortex levels run the opposite way to Python's: lower is more verbose
    (0=trace, 1=debug, 2=info, 3=warn, 4=error, 5=critical). Python has no
    trace level, so 0 and 1 both map to DEBUG.
    """
    if vortex_level <= 1:
        return logging.DEBUG
    if vortex_level == 2:
        return logging.INFO
    if vortex_level == 3:
        return logging.WARNING
    if vortex_level == 4:
        return logging.ERROR
    return logging.CRITICAL
