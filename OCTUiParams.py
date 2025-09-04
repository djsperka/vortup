from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS, AcquisitionType
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from ScanParams import ScanParams, DEFAULT_SCAN_PARAMS
from platformdirs import site_config_dir
from pathlib import Path
import json
import logging
from dataclasses import asdict, dataclass
import copyreg
from vortex import Range
from vortex.engine import Source
from vortex.acquire import alazar
from typing import Tuple

local_logger = logging.getLogger('OCTUiParams')

# default location and name for config file
# on Windows this will go into 'C:\ProgramData\djsperka\octui'
#default_app_name = 'octui'
#default_author_name = 'djsperka'
default_config_base = 'octui.conf'
#default_config_path = Path(site_config_dir(default_app_name, default_author_name), default_config_base)
default_config_path = Path.home() / '.octui/' / default_config_base

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
class UiParams():
    vtx: VtxEngineParams = DEFAULT_VTX_ENGINE_PARAMS
    acq: AcqParams = DEFAULT_ACQ_PARAMS
    scn: ScanParams = DEFAULT_SCAN_PARAMS
    dsp: Tuple = (-1.8e-05, 0)

def pickle_uiparams(u: UiParams):
    return UiParams, (u.vtx, u.acq, u.scn)
copyreg.pickle(UiParams, pickle_uiparams)


class _octui_encoder(json.JSONEncoder):
    def default(self, o):
        try:
            #print("__encoder.default:", o)
            if isinstance(o, UiParams):
                value = asdict(o)
            elif isinstance(o, VtxEngineParams):
                value = asdict(o)
            elif isinstance(o, ScanParams):
                value = asdict(o)
            elif isinstance(o, AcqParams):
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


class _octui_decoder(json.JSONDecoder):
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=_octui_decoder.from_dict)

    @staticmethod
    def from_dict(d):
        #print('from_dict: ', d.keys())
        if d.keys() == {'min', 'max'}:
            return Range(d['min'], d['max'])
        elif {'triggers_per_second', 'clock_rising_edges_per_trigger', 'duty_cycle', 'imaging_depth_meters'}.issubset(d.keys()):
            return Source(int(d['triggers_per_second']), int(d['clock_rising_edges_per_trigger']), float(d['duty_cycle']), float(d['imaging_depth_meters']))
        elif {'acquisition_type',  'galvo_delay', 'galvo_y_voltage_range', 'save_profiler_data'}.issubset(d.keys()):
            # This should be the VtxEngineParams object itself. 
            d['acquisition_type'] = AcquisitionType(d['acquisition_type'])
            d['clock_channel'] = alazar.Channel(d['clock_channel'])
            d['input_channel'] = alazar.Channel(d['input_channel'])
        elif {'vtx', 'acq', 'scn', 'dsp'}.issubset(d.keys()):
            d['vtx'] = VtxEngineParams(**d['vtx'])
            d['acq'] = AcqParams(**d['acq'])
            d['scn'] = ScanParams(**d['scn'])
            d['dsp'] = tuple(d['dsp'])
        return d



class OCTUiParams():
    def __init__(self, config_file = '', load = True):

        if len(config_file):
            maybepath = Path(config_file)
            if not maybepath.exists():
                local_logger.warning('Config file {0:s} not found.'.format(config_file))
            self.__cfgpath = maybepath
        else:
            self.__cfgpath = default_config_path

        if not load:
            params = UiParams()
            self._vtx = params.vtx
            self._acq = params.acq
            self._scn = params.scn
            self._dsp = params.dsp
            local_logger.info("Saving initial config file {0:s}".format(str(default_config_path)))
            self.save()

        self.load()

    @property
    def vtx(self):
        return self._vtx
    
    @vtx.setter
    def vtx(self, value):
        self._vtx = value

    @property
    def acq(self):
        return self._acq
    
    @acq.setter
    def acq(self, value):
        self._acq = value

    @property
    def scn(self):
        return self._scn

    @property
    def rsc(self):
        return self._scn.getRasterScanConfig()
    
    @scn.setter
    def scn(self, value):
        self._scn = value

    @property
    def dsp(self):
        return self._dsp
    
    @dsp.setter
    def dsp(self, value):
        self._dsp = value

    def load(self, config_file=''):
        if len(config_file):
            maybepath = Path(config_file)
            if not maybepath.exists():
                raise FileNotFoundError('Config file {0:s} not found.'.format(config_file))
            else:
                use_this_path = maybepath
        else:
            if self.__cfgpath.exists():
                use_this_path = self.__cfgpath
            else:
                raise FileNotFoundError('Config file {0:s} not found.'.format(str(self.__cfgpath)))

        local_logger.info("loading OCTUi config from {0:s}".format(str(use_this_path)))
        with use_this_path.open(mode='r') as f:
            dct = json.load(f, cls=_octui_decoder)
        
        params = UiParams(**dct)
        self._vtx = params.vtx
        self._acq = params.acq
        self._scn = params.scn
        self._dsp = params.dsp
        self.__cfgpath = use_this_path

    def path(self):
        return self.__cfgpath

    def save(self, config_file = ''):

        # Save to the given filename.
        # If the filename already exists, overwrite it. 
        # If the filename doesn't exist, create it.
        # If the filename is empty, use the private __cfgpath member, 
        # and apply the same rules to it.
        if len(config_file):
            use_this_path = Path(config_file)
        else:
            use_this_path = self.__cfgpath

        local_logger.info("saving OCTUi config to {0:s}".format(str(use_this_path)))

        # Check if directory exists.
        if not use_this_path.exists():
            local_logger.info("Creating directory {0:s}".format(str(use_this_path.parent)))
            use_this_path.parent.mkdir(exist_ok=True)

        with use_this_path.open(mode="w", encoding="utf-8") as f:
            params = UiParams(self._vtx, self._acq, self._scn, self._dsp)
            json.dump(params, f, indent=2, cls=_octui_encoder)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(description='Initialize/update OCTUi config file.', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--create', action='store_true', help='create new config file')
    parser.add_argument('--update', action='store_true', help='create new config file')
    parser.add_argument('--config', default='', help='path to config file [default = {0:s}]'.format(str(default_config_path)))
    args = parser.parse_args()

    if args.create:
        local_logger.info("creating new config file")
        p=OCTUiParams(config_file=args.config, load=False)
    elif args.update:
        local_logger.info("Load existing config file...")
        p=OCTUiParams(config_file=args.config, load=True)
        p.save()
        local_logger.info("Done.")
    else:
        local_logger.error("Must specify --create or --update")

