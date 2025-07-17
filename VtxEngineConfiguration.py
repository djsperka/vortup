import configparser
from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS, AcquisitionType
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from VtupUtilities import getRangeFromTextEntry
from typing import Tuple
from enum import Enum

class VtxEngineConfiguration(configparser.ConfigParser):
    def __init__(self):
        super().__init__(allow_no_value=True)
        self._eng = DEFAULT_VTX_ENGINE_PARAMS

    def load(self, filename: str) -> VtxEngineParams:
        self.read(filename)

        # convert
        self._eng.acquisition_type = AcquisitionType[self.get('etc','acquisition_type')]
        self._eng.galvo_delay = self.getfloat('etc','galvo_delay')
        self._eng.galvo_x_voltage_range = self.getrange('etc','galvo_x_voltage_range')
        self._eng.galvo_y_voltage_range = self.getrange('etc','galvo_y_voltage_range')

    def getrange(self, section: str, option: str): 
        return getRangeFromTextEntry(self.get(section, option))


if __name__ == "__main__":
    import sys
    vcfg = VtxEngineConfiguration()
    vcfg.load('vtxengine.ini')
    print(vcfg._eng.acquisition_type)
    print(vcfg._eng.galvo_delay)
    print(vcfg._eng.galvo_x_voltage_range)
    print(vcfg._eng.galvo_y_voltage_range)
