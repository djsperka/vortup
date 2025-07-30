import json
from dataclasses import asdict, dataclass
from dataclasses_json import dataclass_json
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from vortex import Range
from vortex.engine import Source
from vortex.acquire import alazar
from vortex.scan import RasterScanConfig
from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS, AcquisitionType


# Example of replacing an obj like {"a": 1, "b": 2, "c": 3}, which has specific keys, with something else. 

# json_data = '{"name": "Bob", "age": 25, "city": "Los Angeles", "other": {"a": 1, "b": 2, "c": 3}}'

# # Custom function to convert JSON to a custom object
# def custom_decoder(dct):
#     print("in decoder: ", dct)
#     if 'name' in dct:
#         dct['name'] = dct['name'].upper()
#     elif dct.keys() & {'a', 'b', 'c'}:
#         return 'REPLACEMENT OBJECT'
#     return dct

# decoder = json.JSONDecoder(object_hook=custom_decoder)
# python_obj = decoder.decode(json_data)

# print(python_obj)




# acq=DEFAULT_ACQ_PARAMS
# dct = asdict(acq)
# print(dct)
# acq2 = AcqParams(**dct)
# print(" acq2:", acq2)
# assert(acq == acq2)
# print("ok")


# convert acq2 to dict using facgtory

# def factory(data):
#     print("factory: ", data)
#     return data

# d2 = asdict(acq2, dict_factory = factory)
# print(d2)

#print("\n\n\nVtxEngineParams: \n", params)








# This stuff is needed for when we call asdict() on a VtxEngineParams object. 
# It contains things that cannot be "pickled", and these functions tell the pickler 
# process how to do it. Seems counter-intuitive to need to do this.
import copyreg
def pickle_range(r: Range):
    return Range, (r.min, r.max)
def pickle_source(s: Source):
    return Source, (s.triggers_per_second, s.clock_rising_edges_per_trigger, s.duty_cycle, s.imaging_depth_meters)
copyreg.pickle(Range, pickle_range)
copyreg.pickle(Source, pickle_source)

@dataclass
class BigConfig:
    vtx: VtxEngineParams = DEFAULT_VTX_ENGINE_PARAMS
    acq: AcqParams = DEFAULT_ACQ_PARAMS
    scn: ScanParams = DEFAULT_SCAN_PARAMS


class MyEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            print("MyEncoder.default:", o)
            if isinstance(o, BigConfig):
                value = asdict(o)
            elif isinstance(o, VtxEngineParams):
                value = asdict(o)
            elif isinstance(o, ScanParams):
                print("got Scanparams")
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
                print(o)
                raise TypeError('Unknown type: {0:s}\n'.format(o))
        except TypeError:
            pass
        else:
            return value
        # Let the base class default method raise the TypeError
        return super().default(o)
    

class MyDecoder(json.JSONDecoder):
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=MyDecoder.from_dict)

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
            d['dispersion'] = tuple(d['dispersion'])
        return d




# params = DEFAULT_VTX_ENGINE_PARAMS
# params_str = json.dumps(params, cls=MyEncoder, indent=2)
# print('\n\nstr encoded from DEFAULT_VTX_ENGINE_PARAMS\n', params_str)
# decoder = MyDecoder()
# d = decoder.decode(params_str)
# print('\n\nDict decoded from the encoded params\n', d)
# print(d)

# newparams = VtxEngineParams(**d)
# print('\n\nnew params created from all that\n', newparams)
# print('\n\noriginal params\n', params)


# # test AcqParams
# a=DEFAULT_ACQ_PARAMS
# a_str = json.dumps(a, cls=MyEncoder, indent=2)
# print('\n\nstr encoded from DEFAULT_ACQ_PARAMS\n', a_str)
# decoder = MyDecoder()
# a_d = decoder.decode(a_str)
# print('\n\nDict decoded from the encoded params\n', a_d)
# a2 = AcqParams(**a_d)
# assert(a==a2)
# print("OK")




# if params.acquisition_type != newparams.acquisition_type:
#     print('acq type!')
# if params.galvo_delay != newparams.galvo_delay:
#     print('galvo_delay!')
# if params.galvo_x_voltage_range != newparams.galvo_x_voltage_range or params.galvo_y_voltage_range != newparams.galvo_y_voltage_range:
#     print('ranges')
# if params.galvo_y_units_per_volt != newparams.galvo_y_units_per_volt:
#     print('not source')
# if params.swept_source != newparams.swept_source:
#     print('source')
#     print(params.swept_source)
#     print(newparams.swept_source)
#     if params.swept_source.triggers_per_second != newparams.swept_source.triggers_per_second:
#         print(1)
#     if params.swept_source.clock_rising_edges_per_trigger != newparams.swept_source.clock_rising_edges_per_trigger:
#         print(2)
#     if params.swept_source.duty_cycle != newparams.swept_source.duty_cycle:
#         print(3)
#     if params.swept_source.imaging_depth_meters != newparams.swept_source.imaging_depth_meters:
#         print(4)
#     print('params type ', type(params.swept_source))
#     print("newparsams type: ", type(newparams.swept_source))
# if params.internal_clock != newparams.internal_clock or params.clock_samples_per_second != newparams.clock_samples_per_second or params.external_clock_level_pct != newparams.external_clock_level_pct or params.clock_channel != newparams.clock_channel or params.input_channel != newparams.input_channel:
#     print('channels')
# assert(newparams == params)
# print("awesome")



#
#  THIS WORKS!
b = BigConfig()
b_str = json.dumps(b, cls=MyEncoder, indent=2)
print('\n\nstr encoded from BigConfig\n', b_str)
decoder = MyDecoder()
b_d = decoder.decode(b_str)
print('\n\nDict decoded from the encoded params\n', b_d)
b2 = BigConfig(**b_d)
print('original:\n', b)
print('\nnew\n', b2)



# scfg = ScanParams()
# print("call dumps...")
# scfg_str = json.dumps(scfg, cls=MyEncoder, indent=2)
# print("DUMP json str for ScanParams: \n", scfg_str)
# decoder = MyDecoder()
# scfg_decoded = decoder.decode(scfg_str)
# # print('\n\nDict decoded from the encoded params\n', b_d)
# s2 = ScanParams(**scfg_decoded)
# print('original:\n', scfg)
# print('\nnew\n', s2)



