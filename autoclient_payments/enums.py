from enum import Enum


class CustomEnum(Enum):
    @classmethod
    def as_dict(cls):
        return {x.value: x.name for x in cls}


class TransactionType(CustomEnum):
    CREDIT = "C"
    DEBIT = "D"


class TransactionKind(CustomEnum):
    REAL = "r"
    INFO = "i"


class TransactionStatus(CustomEnum):
    PROCESSING = "p"
    RECORDED = "r"
    TERMINATED = "t"
    NULLIFIED = "n"
