from vortex import Range
from vortex.acquire import alazar
from vortex.engine import source, Source
from dataclasses import dataclass, field
from enum import Enum

class AcquisitionType(Enum):
    ALAZAR_ACQUISITION = 1
    FILE_ACQUISITION= 2

@dataclass
class VtxEngineParams:
    # acquisition type
    acquisition_type: AcquisitionType = AcquisitionType.ALAZAR_ACQUISITION

    # left over from scan parameters
    galvo_delay: float = 0.0

    # other galvo stuff
    galvo_enabled: bool = True
    galvo_clock_source: str = "pfi12"
    galvo_x_voltage_range: Range = field(default_factory=lambda: Range(-1,1))
    galvo_y_voltage_range: Range = field(default_factory=lambda: Range(-1,1))
    galvo_x_units_per_volt: float = 1.5
    galvo_y_units_per_volt: float = 1.5
    galvo_x_device_channel: str = "Dev1/ao0"
    galvo_y_device_channel: str = "Dev1/ao1"

    # strobe stuff
    strobe_enabled: bool = True
    strobe_clock_source: str = "pf12"
    strobe_device_channel: str = "Dev1/port0"
    
    # hardware configuration
    ssrc_triggers_per_second: int = 100000
    ssrc_clock_rising_edges_per_trigger: int = 1280

    internal_clock: bool = False
    clock_samples_per_second: int = int(500e6)
    external_clock_level_pct: int = 50
    clock_channel: str = 'B'
    input_channel: str = 'A'
    input_channel_range_millivolts: int = 1000
    trigger_range_millivolts: int = 5000
    trigger_level_fraction: float = 0.1

    # engine memory parameters
    blocks_to_allocate: int = 128
    preload_count: int = 32

    # processing control
    process_slots: int = 2

    # logging
    log_level: int = 1

    # other
    save_profiler_data: bool = False

DEFAULT_VTX_ENGINE_PARAMS = VtxEngineParams(

    acquisition_type=AcquisitionType.ALAZAR_ACQUISITION,
    galvo_delay=0.0,
    galvo_enabled=True,
    galvo_clock_source='pfi12',
    galvo_x_voltage_range=Range(-3,3),
    galvo_y_voltage_range=Range(-3,3),
    galvo_x_units_per_volt=1.5,
    galvo_y_units_per_volt=1.5,
    galvo_x_device_channel='Dev1/ao0',
    galvo_y_device_channel='Dev1/ao1',
    strobe_enabled=True,
    strobe_clock_source='pfi12',
    strobe_device_channel='Dev1/port0',

    # These are probably rig-specific? Hasn't been an issue to use these. 
    blocks_to_allocate=128,
    preload_count=32,

    # hardware configuration
    #swept_source=source.Axsun100k,
    ssrc_triggers_per_second=100000,
    ssrc_clock_rising_edges_per_trigger=1280,
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
