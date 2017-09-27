from common import SCREEN_WIDTH, SCREEN_HEIGHT

NEWSFEEDER_MARGIN = 10

NEWSFEEDER_ITEM_Y = 50

NEWSFEEDER_ITEM_WIDTH = 250
NEWSFEEDER_ITEM_RIGHT_MARGIN = 10

NEWSFEEDER_ITEM_LIFESPAN = 240

NEWSFEEDER_X = (SCREEN_WIDTH - 10)
NEWSFEEDER_Y = 50


NEWS_GENERIC_ITEM = 1               # The most generic of newsfeeder items

NEWS_QUEST_NEW = 10                 # New quest available
NEWS_QUEST_UPDATE = 11              # Quest updated
NEWS_QUEST_FAILED = 12              # Quest failed
NEWS_QUEST_COMPLETE = 13            # Quest completed

NEWS_ITEM_NEW = 20                  # New item gained
NEWS_ITEM_UPGRADE = 21              # Upgraded an item
NEWS_ITEM_LOST = 22                 # Lost / gave an item away

NEWS_SKILL_NEW = 30                 # New skill unlocked
NEWS_SKILL_UPGRADED = 31             # Existing skill upgraded
NEWS_SKILL_UNLOCKED = 32            # Alert when a new skill tree becomes available
NEWS_SKILL_TREE_UNLOCKED = 33       # Player unlocked a new skill tree (choose from 2 skills)

NEWS_GAME_CONTROLS_SAVED = 40       # Saved controls
NEWS_GAME_SAVE_COMPLETE = 41        # Saved game successfully
NEWS_GAME_LOAD_COMPLETE = 42        # Loaded game successfully
NEWS_GAME_GAMEPAD_NEW = 43          # On startup, found a new gamepad
NEWS_GAME_GAMEPAD_REMEMBERED = 44   # On startup, found the last gamepad used
NEWS_GAME_GAMEPAD_DEFAULT = 45      # On startup, could not find the last gamepad used, but found a default
NEWS_GAME_GAMEPAD_SELECTED = 46     # Selected a new gamepad device
NEWS_GAME_GAMEPAD_NOT_FOUND = 47    # Could not find the last gamepad used.  No default alternative found.
NEWS_GAME_GAMEPAD_RESET = 48        # Reset controls for active gamepad
NEWS_GAME_KEYBOARD_RESET = 49       # Reset controls for keyboard

NEWS_CHARACTER_LEVEL_UP = 50        # Character levels up

NEWS_MAP_COMPLETED = 60             # Character successfully acquires all of the gold on a single level

NEWS_DLC_DOWNLOAD_COMPLETE = 70     # Completed download of a DLC story
NEWS_DLC_DOWNLOAD_FAILED = 71       # Failed download of a DLC story
NEWS_DLC_DOWNLOAD_BEGINNING = 72    # Beginning to download a DLC story

NEWS_NET_LEVEL_SKIP = 200           # Players voted to skip level
NEWS_NET_LOCAL_DEATH = 201          # Local player dies
NEWS_NET_REMOTE_DEATH = 202         # Another player in the game dies
NEWS_NET_LEVEL_COMPLETE = 203       # All gold collected
NEWS_NET_LEVEL_FAILED = 204         # All players died, back to lobby
NEWS_NET_PLAYER_WAITING = 205       # Player has joined the game in-progress, must wait for lobby
NEWS_NET_JOINED_IN_PROGRESS = 206   # Local player joined in progress, must wait for level to end / restart
NEWS_NET_PLAYER_CONNECTED = 207     # A player connected
NEWS_NET_PLAYER_DISCONNECTED = 208  # A player disconnected
NEWS_NET_PLAYER_TIMED_OUT = 209     # Lost connection to a client
NEWS_NET_SERVER_UNAVAILABLE = 210   # Client player lost connection with the server, timed out
NEWS_NET_SERVER_ONLINE = 211        # User has launched a new co-op game.  Waiting for players to join...
NEWS_NET_CLIENT_ONLINE = 212        # User has joined a game.  Maybe in lobby, maybe in progress.  That comes later.
NEWS_NET_SERVER_DISCONNECTED = 213  # Server ended the session
