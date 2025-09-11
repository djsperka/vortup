from enum import IntEnum, Enum
from vortex.acquire import alazar
class ATS9350InputRange(IntEnum):
    _40mV = 40
    _100mV = 100
    _200mV = 200
    _400mV = 400
    _1000mV = 1000
    _2000mV = 2000
    _4000mV = 4000

AlazarChannelValueDict = {
    """This dictionary is used to translate the channel names for alazar cards into the alazar.Channel types used in vortex. This is because the 
    class vortex.acquire.alazar.Channel has numeric values (they are used as bits and can be combined in special cases). Keeping this map allows us to 
    map the dialog-selected letters to the value, which can then be converted to the actual Channel object like this:
    from DAQConst import AlazarChannelValueDict
    if letter in AlazarChannelValueDict:   
        channel = vortex.acquire.alazar.Channel(AlazarChannelValueDict(letter)) 
    else
        channel = vortex.acquire.alazar.Channel.A
    """
    'A': 1, 'B': 2, 'C': 4, 'D': 8, 'E': 16, 'F': 32, 'G': 64, 'H': 128, 'I': 256, 'J': 512, 'K': 1024, 'L': 2048, 'M': 4096, 'N': 8192, 'O': 16384, 'P': 32768
}

def getAlazarChannel(letter: str) -> alazar.Channel:
    if letter in AlazarChannelValueDict:
        return alazar.Channel(AlazarChannelValueDict[letter])
    else:
        return alazar.Channel.A
