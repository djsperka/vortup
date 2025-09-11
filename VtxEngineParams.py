from vortex import Range
from vortex.acquire import alazar
from vortex.engine import source, Source
from dataclasses import dataclass
from enum import Enum

class AcquisitionType(Enum):
    ALAZAR_ACQUISITION = 1
    FILE_ACQUISITION= 2

@dataclass
class VtxEngineParams:
    # acquisition type
    acquisition_type: AcquisitionType

    # left over from scan parameters
    galvo_delay: float

    # other galvo stuff
    galvo_clock_source: str
    galvo_x_voltage_range: Range
    galvo_y_voltage_range: Range
    galvo_x_voltage_range: Range
    galvo_y_voltage_range: Range
    galvo_x_units_per_volt: float
    galvo_y_units_per_volt: float
    galvo_x_device_channel: str
    galvo_y_device_channel: str

    # strobe stuff
    strobe_clock_source: str
    strobe_device_channel: str
    
    # hardware configuration
    swept_source: Source
    internal_clock: bool
    clock_samples_per_second: int
    external_clock_level_pct: int
    clock_channel: str
    input_channel: str
    input_channel_range_millivolts: int
    trigger_range_millivolts: int
    trigger_level_fraction: float

    # engine memory parameters
    blocks_to_allocate: int
    preload_count: int

    # processing control
    process_slots: int

    # logging
    log_level: int

    # other
    save_profiler_data: bool

DEFAULT_VTX_ENGINE_PARAMS = VtxEngineParams(

    acquisition_type=AcquisitionType.ALAZAR_ACQUISITION,
    galvo_delay=0.0,
    galvo_clock_source='pfi12',
    galvo_x_voltage_range=Range(-3,3),
    galvo_y_voltage_range=Range(-3,3),
    galvo_x_units_per_volt=1.5,
    galvo_y_units_per_volt=1.5,
    galvo_x_device_channel='Dev1/ao0',
    galvo_y_device_channel='Dev1/ao1',
    strobe_clock_source='pfi12',
    strobe_device_channel='Dev1/port0',

    # These are probably rig-specific? Hasn't been an issue to use these. 
    blocks_to_allocate=128,
    preload_count=32,

    # hardware configuration
    #swept_source=source.Axsun100k,
    swept_source=Source(100000, 1376, 0.5, 0.0037),
    internal_clock=False,
    clock_samples_per_second=int(500e6),    # ATS 9350 - applies to internal clock only
    external_clock_level_pct=50,        # only relevant if internal_clock is False
    clock_channel='B',
    input_channel='A',
    input_channel_range_millivolts=1000,
    trigger_range_millivolts=5000,
    trigger_level_fraction=0.10,

    # engine memory parameters
    process_slots=2,                    # I think this is for in-stream processing?

    # logging
    log_level=1,                        # 1 is normal, 0 is debug-level

    # other
    save_profiler_data=False
)

@dataclass
class FileSaveConfig:
    type: str       # should be 'ascans' or 'spectra'
    save: bool = False
    filename: str = ''
    extension: str = ''
