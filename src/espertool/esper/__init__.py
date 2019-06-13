from . import udp

__all__ = ['udp']


VAR_TYPE_UNKNOWN = 0
VAR_TYPE_NULL = 1
VAR_TYPE_ASCII = 2
VAR_TYPE_BOOL = 3
VAR_TYPE_UINT8 = 4
VAR_TYPE_UINT16 = 5
VAR_TYPE_UINT32 = 6
VAR_TYPE_UINT64 = 7
VAR_TYPE_INT8 = 8
VAR_TYPE_INT16 = 9
VAR_TYPE_INT32 = 10
VAR_TYPE_INT64 = 11
VAR_TYPE_FLOAT32 = 12
VAR_TYPE_FLOAT64 = 13


class EsperException(Exception):
    pass


def EsperGetTypeSize(type):
    if(type == VAR_TYPE_UNKNOWN):
        return 0
    if(type == VAR_TYPE_NULL):
        return 0
    if(type == VAR_TYPE_ASCII):
        return 1
    if(type == VAR_TYPE_BOOL):
        return 1
    if(type == VAR_TYPE_UINT8):
        return 1
    if(type == VAR_TYPE_UINT16):
        return 2
    if(type == VAR_TYPE_UINT32):
        return 4
    if(type == VAR_TYPE_UINT64):
        return 8
    if(type == VAR_TYPE_INT8):
        return 1
    if(type == VAR_TYPE_INT16):
        return 2
    if(type == VAR_TYPE_INT32):
        return 4
    if(type == VAR_TYPE_INT64):
        return 8
    if(type == VAR_TYPE_FLOAT32):
        return 4
    if(type == VAR_TYPE_FLOAT64):
        return 8

    return 0


def EsperGetTypeString(type):
    if(type == VAR_TYPE_UNKNOWN):
        return "unknown"
    if(type == VAR_TYPE_NULL):
        return "null"
    if(type == VAR_TYPE_ASCII):
        return "ascii"
    if(type == VAR_TYPE_BOOL):
        return "bool"
    if(type == VAR_TYPE_UINT8):
        return "uint8"
    if(type == VAR_TYPE_UINT16):
        return "uint16"
    if(type == VAR_TYPE_UINT32):
        return "uint32"
    if(type == VAR_TYPE_UINT64):
        return "uint64"
    if(type == VAR_TYPE_INT8):
        return "int8"
    if(type == VAR_TYPE_INT16):
        return "int16"
    if(type == VAR_TYPE_INT32):
        return "int32"
    if(type == VAR_TYPE_INT64):
        return "int64"
    if(type == VAR_TYPE_FLOAT32):
        return "float32"
    if(type == VAR_TYPE_FLOAT64):
        return "float32"

    return "unknown"
