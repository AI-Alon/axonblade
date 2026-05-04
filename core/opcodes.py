from enum import Enum, auto


class Opcode(Enum):
    # Stack
    PUSH_CONST = auto()
    PUSH_NULL = auto()
    PUSH_TRUE = auto()
    PUSH_FALSE = auto()
    POP = auto()

    # Variables
    LOAD_VAR = auto()
    DEFINE_VAR = auto()
    STORE_VAR = auto()

    # Upvalues (captured closure variables)
    LOAD_DEREF = auto()
    STORE_DEREF = auto()

    # Arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    POW = auto()
    NEG = auto()

    # Comparison
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()

    # Logic
    AND = auto()
    OR = auto()
    NOT = auto()

    # Jumps
    JUMP = auto()
    JUMP_IF_FALSE = auto()
    JUMP_IF_TRUE = auto()

    # Collections
    MAKE_LIST = auto()
    MAKE_DICT = auto()
    GET_INDEX = auto()
    SET_INDEX = auto()
    GET_SLICE = auto()

    # Attributes
    GET_ATTR = auto()
    SET_ATTR = auto()

    # Functions
    MAKE_FN = auto()
    CALL = auto()
    RETURN = auto()

    # Classes
    MAKE_CLASS = auto()

    # Strings
    BUILD_FSTRING = auto()

    # Exceptions
    SETUP_TRY = auto()
    POP_TRY = auto()
    RAISE = auto()

    # Modules
    IMPORT = auto()
