from typing import Any

__all__ = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
    'LOCATION',
    'RETRY_AFTER',
    'EQUITY',
    'Alpha',
    'MultiAlpha',
    'Region',
    'Delay',
    'Universe',
    'InstrumentType',
    'DataCategory',
    'FieldType',
    'DatasetsOrder',
    'FieldsOrder',
    'Status',
    'AlphaType',
    'AlphaCategory',
    'Language',
    'Color',
    'Neutralization',
    'UnitHandling',
    'NanHandling',
    'Pasteurization',
    'AlphasOrder',
    'Null',
    'NULL',
]

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
PATCH = 'PATCH'
DELETE = 'DELETE'
HEAD = 'HEAD'
OPTIONS = 'OPTIONS'

LOCATION = 'Location'
RETRY_AFTER = 'Retry-After'

EQUITY = 'EQUITY'

Alpha = Any
MultiAlpha = Any

Region = Any
Delay = Any
Universe = Any
InstrumentType = Any
DataCategory = Any
FieldType = Any
DatasetsOrder = Any
FieldsOrder = Any
Status = Any
AlphaType = Any
AlphaCategory = Any
Language = Any
Color = Any
Neutralization = Any
UnitHandling = Any
NanHandling = Any
Pasteurization = Any
AlphasOrder = Any


class Null:
    pass


NULL = Null()
