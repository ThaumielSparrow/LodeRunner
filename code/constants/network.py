NET_COMMAND_SEPARATOR = "~!"

NET_STATUS_OFFLINE = 1
NET_STATUS_SERVER = 2
NET_STATUS_CLIENT = 3

NET_MESSAGE_UNREGISTERED = 1                        # An unregistered message will carry a message id, and it will not expect any confirmation of receipt.
NET_MESSAGE_REGISTERED = 2                          # A registered message carries a message id also.  Registered messages DO expect a confirmation of receipt.
NET_MESSAGE_RECEIPT = 3                             # "Receipt" messages do not carry game command data; we simply use them to confirm the delivery of previous messages.

NET_LOCK_NONE = 0
NET_LOCK_LOCAL = 1                                  # Lock only the local player from moving; networked players will still do stuff, and the bad guys will still move, etc.
NET_LOCK_GLOBAL = 2                                 # All game logic stops pending the unlock.

SYNC_STATUS_READY = 1
SYNC_STATUS_PENDING = 2

NET_TRANSITION_DELAY = 120                          # Brief waiting period between completing/failing a level and transitioning to the next...

NET_CONSOLE_LINE_LIMIT = 3
NET_CONSOLE_WIDTH = 520
NET_CONSOLE_LINE_WIDTH = 250
NET_CONSOLE_X = 10
NET_CONSOLE_Y = 50
NET_CONSOLE_LINE_LIFESPAN = 1080

LOCK_NONE = 1
LOCK_SOFT = 2
LOCK_HARD = 3

NET_MSG_LOCK_SOFT = 1
NET_MSG_LOCK_HARD = 2
NET_MSG_UNLOCK = 3
NET_MSG_ENTITY_START_MOTION = 4
NET_MSG_ENTITY_STOP_MOTION = 5
NET_MSG_ENTITY_DIG = 6
#NET_MSG_ENTITY_DIG_REQUEST = 7
NET_MSG_ENTITY_DIG_RESPONSE_VALID = 8
NET_MSG_ENTITY_DIG_RESPONSE_INVALID = 9
NET_MSG_PING = 10
NET_MSG_PONG = 11
#NET_MSG_SYNC_MAP = 12
NET_MSG_SYNC_ENEMY_AI = 13
NET_MSG_CALL_SCRIPT = 14
NET_MSG_PLAYER_ID = 15
NET_REQ_CALL_SCRIPT = 16
NET_MSG_OK = 17
NET_MSG_UNAUTHORIZED = 18
NET_REQ_CONFIRM_DIG_TILE = 19
NET_MSG_INVALIDATE_DIG = 20
NET_MSG_SYNC_ONE_GOLD = 21
NET_MSG_SYNC_ALL_GOLD = 22
NET_REQ_VALIDATE_BOMB = 23
NET_MSG_VALIDATE_BOMB_OK = 24
NET_MSG_VALIDATE_BOMB_UNAUTHORIZED = 25
NET_MSG_CREATE_BOMB = 26
NET_MSG_ENTITY_DIE = 27
NET_MSG_ENTITY_RESPAWN = 28
NET_MSG_SYNC_PLAYER = 29
NET_MSG_CLIENT_DISCONNECTING = 30
NET_MSG_SERVER_DISCONNECTING = 31
NET_MSG_CHAT = 32
NET_MSG_REQ_NICK = 33
NET_MSG_SYNC_ALL_PLAYERS = 34
NET_MSG_BEGIN_GAME = 35
NET_MSG_AVATAR_DATA = 36
NET_MSG_VOTE_TO_SKIP = 37
NET_MSG_TRANSITION_TO_MAP = 38
NET_MSG_LEVEL_COMPLETE = 39
NET_MSG_LEVEL_FAILED = 40
NET_MSG_CONFIRM_DISCONNECT = 41                 # Server / client confirms that they received a disconnect notice
NET_MSG_SYNC_PLAYER_BY_ID = 42                  # Different from ordinary SYNC_PLAYER (which simply syncs nick / lobby status / etc.)

NICK_LENGTH_MINIMUM = 3
NICK_LENGTH_MAXIMUM = 8

NICK_OK = 1
NICK_ERROR_LENGTH = 2
NICK_ERROR_INVALID = 3
