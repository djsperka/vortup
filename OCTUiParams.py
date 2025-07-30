from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS, AcquisitionType
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from ScanParams import ScanParams, DEFAULT_SCAN_PARAMS
from platformdirs import site_config_dir
from pathlib import PurePath
import json
from dataclasses import asdict, dataclass
import copyreg
from vortex import Range
from vortex.engine import Source
from vortex.acquire import alazar


# default location and name for config file
# on Windows this will go into 'C:\ProgramData\djsperka\octui'
default_app_name = 'octui'
default_author_name = 'djsperka'
default_config_base = 'octui.conf'
default_config_file = PurePath(site_config_dir(default_app_name, default_author_name), default_config_base)


# This stuff is needed for when we call asdict() on a dataclass
# It contains things that cannot be "pickled", and these functions tell the pickler 
# process how to do it. Seems counter-intuitive to need to do this.
def pickle_range(r: Range):
    return Range, (r.min, r.max)
def pickle_source(s: Source):
    return Source, (s.triggers_per_second, s.clock_rising_edges_per_trigger, s.duty_cycle, s.imaging_depth_meters)
copyreg.pickle(Range, pickle_range)
copyreg.pickle(Source, pickle_source)

@dataclass
class __UiParams():
    vtx: VtxEngineParams = DEFAULT_VTX_ENGINE_PARAMS
    acq: AcqParams = DEFAULT_ACQ_PARAMS
    scn: ScanParams = DEFAULT_SCAN_PARAMS


class __encoder(json.JSONEncoder):
    def default(self, o):
        try:
            print("__encoder.default:", o)
            if isinstance(o, OCTUiParams):
                value = asdict(o)
            elif isinstance(o, VtxEngineParams):
                value = asdict(o)
            elif isinstance(o, ScanParams):
                value = asdict(o)
            elif isinstance(o, AcqParams):
                value = asdict(o)
            elif isinstance(o, OCTUiParams):
                value = asdict(o)
            elif isinstance(o, AcquisitionType):
                value = o.value
            elif isinstance(o, Range):
                value = {'min': o.min, 'max': o.max}
            elif isinstance(o, Source):
                value = {'triggers_per_second': o.triggers_per_second, 'clock_rising_edges_per_trigger': o.clock_rising_edges_per_trigger, 'duty_cycle': o.duty_cycle, 'imaging_depth_meters': o.imaging_depth_meters}
            elif isinstance(o, alazar.Channel):
                value = o.value
            else:
                raise TypeError('Unknown type: {0:s}\n'.format(o))
        except TypeError:
            pass
        else:
            return value
        # Let the base class default method raise the TypeError
        return super().default(o)

class OCTUiParams():
    vtx: VtxEngineParams = DEFAULT_VTX_ENGINE_PARAMS
    acq: AcqParams = DEFAULT_ACQ_PARAMS
    scn: ScanParams = DEFAULT_SCAN_PARAMS    
    __filename: str = ''
    

    def __init__(self, config_file = default_config_file):
        __params = self.__load(config_file)        

    def __load(self, config_file = default_config_file):        
        with open(config_file, 'r') as f:
            dct = json.load(f)
        params = __UiParams(**dct)
        self.vtx = params.vtx
        self.acq = params.acq
        self.scn = params.scn
        __filename = config_file

    def load(self, config_file):
        self.__load(config_file)

    def save(self, config_file = None):
        use_this_filename = self.__filename
        if config_file is not None:
            use_this_filename = config_file
        print("saving to {0:s}".format(use_this_filename))
        with open(use_this_filename, mode="w", encoding="utf-8") as f:
            params = __UiParams(self.vtx, self.acq, self.scn)
            json.dump(params, f, indent=2)






    # @staticmethod
    # def __from_dict(d):
    #     if d.keys() == {'min', 'max'}:
    #         return Range(d['min'], d['max'])
    #     elif {'triggers_per_second', 'clock_rising_edges_per_trigger', 'duty_cycle', 'imaging_depth_meters'}.issubset(d.keys()):
    #         return Source(int(d['triggers_per_second']), int(d['clock_rising_edges_per_trigger']), float(d['duty_cycle']), float(d['imaging_depth_meters']))
    #     elif {'acquisition_type',  'galvo_delay', 'galvo_y_voltage_range', 'save_profiler_data'}.issubset(d.keys()):
    #         # This should be the VtxEngineParams object itself. 
    #         d['acquisition_type'] = AcquisitionType(d['acquisition_type'])
    #         d['clock_channel'] = alazar.Channel(d['clock_channel'])
    #         d['input_channel'] = alazar.Channel(d['input_channel'])
    #         d['dispersion'] = tuple(d['dispersion'])
    #     return d



if __name__ == "__main__":
    p=OCTUiParams()
    p.save()
