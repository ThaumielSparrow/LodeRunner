# Constants pertaining to game scripting

LINK_TYPE_CONSTANT = 1
LINK_TYPE_METHOD = 2
LINK_TYPE_OBJECT = 3
LINK_TYPE_PROPERTY = 4
LINK_TYPE_CONDITIONAL = 5
LINK_TYPE_ITERATOR = 6          # each() function
LINK_TYPE_THIS = 7              # "this" keyword for use within the each() iterator

CONDITION_MET = 1
CONDITION_MET_BUT_PENDING = 2
CONDITION_NOT_MET = 3
EXECUTE_RESULT_PENDING = 4
EXECUTE_RESULT_DONE = 5
