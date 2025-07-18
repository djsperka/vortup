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



    # swept_source: Source
    # Source constructor:
    #
    # triggers_per_second: int = ..., clock_rising_edges_per_trigger: int = ..., duty_cycle: float = ..., imaging_depth_meters: float = ...
    #
    #
    # internal_clock: bool
    # clock_samples_per_second: int
    # external_clock_level_pct: int
    # clock_channel: alazar.Channel
    # input_channel: alazar.Channel
    # input_channel_range_millivolts: int
    # trigger_range_millivolts: int
    # trigger_level_fraction: float
    # engine memory parameters
#     blocks_to_allocate: int
#     preload_count: int

#     # processing control
#     process_slots: int
#     dispersion: Tuple[float, float]

#     # logging
#     log_level: int

#     # other
#     save_profiler_data: bool

# DEFAULT_VTX_ENGINE_PARAMS = VtxEngineParams(

#     acquisition_type=AcquisitionType.ALAZAR_ACQUISITION,
#     galvo_delay=0.0,
#     galvo_x_voltage_range=Range(-3,3),
#     galvo_y_voltage_range=Range(-3,3),
#     galvo_x_units_per_volt=1.5,
#     galvo_y_units_per_volt=1.5,

#     # These are probably rig-specific? Hasn't been an issue to use these. 
#     blocks_to_allocate=128,
#     preload_count=32,

#     # hardware configuration
#     swept_source=source.Axsun100k,
#     internal_clock=False,
#     clock_samples_per_second=int(500e6),    # ATS 9350 - applies to internal clock only
#     external_clock_level_pct=50,        # only relevant if internal_clock is False
#     clock_channel=alazar.Channel.B,    # only relevant if internal_clock is True
#     input_channel=alazar.Channel.A,
#     input_channel_range_millivolts=1000,
#     trigger_range_millivolts=5000,
#     trigger_level_fraction=0.10,

#     # engine memory parameters
#     process_slots=2,                    # I think this is for in-stream processing?
#     dispersion=(2.8e-5, 0),             # no idea

#     # logging
#     log_level=1,                        # 1 is normal, 0 is debug-level

#     # other
#     save_profiler_data=False
# )





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
