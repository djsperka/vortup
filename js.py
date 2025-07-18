

# import json
# from datetime import datetime, date
# # config = {"key1": "value1", "key2": "value2"}

# # with open('config1.json', 'w') as f:
# #     json.dump(config, f)
# with open('config1.json', 'r') as f:
#     config = json.load(f)

# print(config["key1"])



# def convert_to_serializable(obj):
#     """Convert special Python types to JSON-serializable formats"""
#     if isinstance(obj, (datetime, date)):
#         return obj.isoformat()
#     elif isinstance(obj, set):
#         return list(obj)
#     elif isinstance(obj, bytes):
#         return obj.decode('utf-8')
#     raise TypeError(f"Type {type(obj)} not serializable")

# # Usage example
# complex_data = {
#     "date": datetime.now(),
#     "tags": {"python", "json", "tutorial"},
#     "binary": b"Hello World"
# }
# with open("complex_data.json", "w") as file:
#     json.dump(complex_data, file, indent=2, default=convert_to_serializable)

import json
from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS
from vortex import Range
#import vortex
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from dataclasses import dataclass, asdict, is_dataclass
from dataclasses_json import dataclass_json
import functools
import typing


@dataclass_json
@dataclass
class BigConfig:
    acq: AcqParams = DEFAULT_ACQ_PARAMS
    eng: VtxEngineParams = DEFAULT_VTX_ENGINE_PARAMS



# def serialize(x):
#     return json.dumps(x, default=encode_value)


# # p = DEFAULT_ACQ_PARAMS
# # print(p)

bcfg = BigConfig()
acq = DEFAULT_ACQ_PARAMS

# #db = asdict(b)
# print(b)
# print('-' * 50)
# # json_str = b.to_json()
# # print(json_str)
# # print('-' * 50)

# # dataclass_obj = BigConfig.from_json(json_str)
# # print(dataclass_obj)



# # # Save to file
# # with open("config1.json", "w") as file:
# #     json.dump(db, file, indent=2)


# serialized = serialize(b)
# print(serialized)



class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        print("default ", o)
        if is_dataclass(o):
            return asdict(o)
        elif isinstance(o, Range):
            return "range_encoded"
        return super().default(o)

#json.dumps(foo, cls=EnhancedJSONEncoder)


# class JSONSerializer(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, MyRange):
#             return "range_value"
#         return super().default(obj)
    

# s = json.dumps(b, cls=JSONSerializer)
# print(s)

#print(bcfg.to_json())
print('-' * 50)
with open('config1.json', 'w') as f:
    json.dump(bcfg, f, indent=2, cls=EnhancedJSONEncoder)