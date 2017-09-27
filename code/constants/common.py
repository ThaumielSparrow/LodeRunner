import os

import pygame

from sys import maxint

from pygame.locals import *
#PI = 3.1415926535897931
from math import pi


UID = 1
def get_next_UID():
    global UID
    UID += 1
    return UID

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480



SPLASH_MODE_NORMAL = 1
SPLASH_MODE_GREYSCALE_INSTANT = 2
SPLASH_MODE_GREYSCALE_ANIMATED = 3


FADE_CONCENTRIC = 1
FADE_LTR = 2


STENCIL_MODE_NONE = 1               # No stencil testing
STENCIL_MODE_PAINT = 2              # Paint anywhere, impress / etch onto stencil buffer
STENCIL_MODE_ERASE = 3              # Paint anywhere, but erase (mark as "unpainted") the stencil buffer along the way
STENCIL_MODE_PAINTED_ONLY = 4       # Paint only on areas where we've previously painted (according to stencil buffer)
STENCIL_MODE_UNPAINTED_ONLY = 5     # Paint only on areas where we have not previously painted (according to stencil buffer)


GAME_MENU_MIN_SLIDE = 0
GAME_MENU_MAX_SLIDE = 500




# For debug print statements
SHOW_HACKS = False

#SCREEN_WIDTH = 713
#SCREEN_HEIGHT = 509

#SCREEN_WIDTH = 1024
#SCREEN_HEIGHT = 768


# The default colors for the shipped player sprite.  We'll reference these
# for color-replacement tasks.
DEFAULT_PLAYER_COLORS = {
    "primary": (96, 96, 255),
    "secondary": (128, 128, 255),
    "primary:bg": (64, 64, 128),
    "gun": (128, 160, 0)
}


INFINITY = (maxint / 2) - 2 # don't laugh

EDITOR_KEYS = {
    "ring-in": K_PAGEDOWN,
    "ring-out": K_PAGEUP,
    "paint-tile": K_SPACE
}

EDITOR_GRID_MINOR_SIZE = 24
EDITOR_GRID_MAJOR_SIZE = 240

EDITOR_MAP_FRAME_THICKNESS = 2

EDITOR_PRIMARY_FRAME_COLOR = (227, 151, 9)
EDITOR_SECONDARY_FRAME_COLOR = (75, 75, 125)

INPUT_MOVE_LEFT = 1
INPUT_MOVE_RIGHT = 2
INPUT_MOVE_UP = 3
INPUT_MOVE_DOWN = 4
INPUT_DIG = 5
INPUT_DIG_LEFT = 6
INPUT_DIG_RIGHT = 7
# Note:  INPUT_DIG_FORWARD is later in list (late addition)
INPUT_BOMB = 8
INPUT_BOMB_LEFT = 9
INPUT_BOMB_RIGHT = 10
INPUT_ACTION = 11
INPUT_SELECTION_UP = 12
INPUT_SELECTION_DOWN = 13
INPUT_SELECTION_ACTIVATE = 14
INPUT_SELECTION_LEFT = 15
INPUT_SELECTION_RIGHT = 16
INPUT_ACTIVATE_SKILL_1 = 17
INPUT_ACTIVATE_SKILL_2 = 18
INPUT_DEACTIVATE_SKILL_1 = 19
INPUT_DEACTIVATE_SKILL_2 = 20
INPUT_SELECTION_HOME = 21
INPUT_SELECTION_END = 22
INPUT_SELECTION_PAGEUP = 23
INPUT_SELECTION_PAGEDOWN = 24
INPUT_SUICIDE = 25
INPUT_NET_CHAT = 26
INPUT_MINIMAP = 27
INPUT_DIG_FORWARD = 28 # late addition

INPUT_DEBUG = 100


# Translate map view type to user-friendly label
WORLDMAP_VIEW_LABELS = {
    "gold": "Gold Map",
    "puzzle": "Puzzle Rooms",
    "challenge": "Challenge Rooms"
}


# Minimap size
MINIMAP_WIDTH = 320
MINIMAP_HEIGHT = 240


#SKILL_LIST = ("sprint", "matrix", "hacking", "persuasion", "hologram", "fright", "jackhammer", "earth-mover", "personal-shield", "wall", "remote-bomb", "mega-bomb", "invisibility", "pickpocket")
SKILL_LIST = ("sprint", "matrix", "hacking", "persuasion", "hologram", "fright", "jackhammer", "earth-mover", "personal-shield", "wall", "remote-bomb", "mega-bomb", "invisibility", "pickpocket")
ACTIVE_SKILL_LIST = ("sprint", "matrix", "hologram", "fright", "jackhammer", "earth-mover", "personal-shield", "wall", "remote-bomb", "mega-bomb", "invisibility", "pickpocket")

SKILLS_BY_CATEGORY = {
    "movement": ("sprint", "matrix"),
    #"control": ("hacking", "persuasion"),
    "deception": ("hologram", "fright"),
    "laser": ("jackhammer", "earth-mover"),
    "shield": ("personal-shield", "wall"),
    "bombadier": ("remote-bomb", "mega-bomb"),
    "stealth": ("invisibility", "pickpocket")
}

CATEGORIES_BY_SKILL = {
    "sprint": "movement",
    "matrix": "movement",
    "hacking": "control",
    "persuasion": "control",
    "hologram": "deception",
    "fright": "deception",
    "jackhammer": "laser",
    "earth-mover": "laser",
    "personal-shield": "shield",
    "wall": "shield",
    "remote-bomb": "bombadier",
    "mega-bomb": "bombadier",
    "invisibility": "stealth",
    "pickpocket": "stealth"
}

SKILL_OPPOSITES = {
    "sprint": "matrix",
    "matrix": "sprint",
    "hacking": "persuasion",
    "persuasion": "hacking",
    "hologram": "fright",
    "fright": "hologram",
    "jackhammer": "earth-mover",
    "earth-mover": "jackhammer",
    "personal-shield": "wall",
    "wall": "personal-shield",
    "remote-bomb": "mega-bomb",
    "mega-bomb": "remote-bomb",
    "invisibility": "pickpocket",
    "pickpocket": "invisibility"
}

SKILL_LABELS = {
    "sprint": "Sprint",
    "matrix": "Matrix",
    "hacking": "Hacking",
    "persuasion": "Persuasion",
    "hologram": "Hologram",
    "fright": "Fright",
    "jackhammer": "Jackhammer",
    "earth-mover": "Earth Mover",
    "personal-shield": "Personal Shield",
    "wall": "Wall",
    "remote-bomb": "Remote Bomb",
    "mega-bomb": "Mega Bomb",
    "invisibility": "Invisibility",
    "pickpocket": "Pickpocket"
}

CATEGORY_LABELS = {
    "movement": "Movement",
    "control": "Control",
    "deception": "Deception",
    "laser": "Laser",
    "shield": "Defense",
    "bombadier": "Bombadier",
    "stealth": "Stealth"
}

SKILL_ICON_INDICES = {
    "sprint": 2,
    "matrix": 2,
    "hacking": 10,
    "persuasion": 10,
    "hologram": 11,
    "fright": 11,
    "jackhammer": 5,
    "earth-mover": 5,
    "personal-shield": 0,
    "wall": 0,
    "remote-bomb": 1,
    "mega-bomb": 1,
    "invisibility": 20,
    "pickpocket": 20
}

SKILL_ICON_WIDTH = 24
SKILL_ICON_HEIGHT = 24

COMMON_SKILL_DURATIONS = {
    "sprint": {
        1: 3 * 60,
        2: 1.5 * 60,
        3: 2.0 * 60
    },
    "matrix": {
        1: 2 * 60,
        2: 2.5 * 60,
        3: 3 * 60
    },
    "hacking": {
        1: 0,
        2: 0,
        3: 0
    },
    "persuasion": {
        1: 0,
        2: 0,
        3: 0
    },
    "hologram": {
        1: 3 * 60,
        2: 3 * 60,
        3: 4 * 60
    },
    "fright": {
        1: 1 * 60,
        2: 1.5 * 60,
        3: 2.0 * 60
    },
    "jackhammer": {
        1: 0,
        2: 0,
        3: 0
    },
    "earth-mover": {
        1: 0,
        2: 0,
        3: 0
    },
    "personal-shield": {
        1: 2 * 60,
        2: 2.25 * 60,
        3: 2.5 * 60
    },
    "wall": {
        1: 3 * 60,
        2: 5 * 60,
        3: 10 * 60
    },
    "remote-bomb": {
        1: 0,
        2: 0,
        3: 0
    },
    "mega-bomb": {
        1: 0,
        2: 0,
        3: 0
    },
    "invisibility": {
        1: 2 * 60,
        2: 3 * 60,
        3: 4 * 60
    },
    "disguise": {
        1: 5 * 60,
        2: 7 * 60,
        3: 10 * 60
    },
    "pickpocket": {
        1: 0,
        2: 0,
        3: 0
    },
}

COMMON_SKILL_RECHARGE_TIMES = {
    "sprint": {
        1: 10 * 60,
        2: 8 * 60,
        3: 6 * 60
    },
    "matrix": {
        1: 20 * 60,
        2: 17 * 60,
        3: 15 * 60
    },
    "hacking": {
        1: 0,
        2: 0,
        3: 0
    },
    "persuasion": {
        1: 0,
        2: 0,
        3: 0
    },
    "hologram": {
        1: 15 * 60,
        2: 12 * 60,
        3: 10 * 60
    },
    "fright": {
        1: 25 * 60,
        2: 21 * 60,
        3: 15 * 60
    },
    "jackhammer": {
        1: 25 * 60,
        2: 20 * 60,
        3: 15 * 60
    },
    "earth-mover": {
        1: 25 * 60,
        2: 20 * 60,
        3: 15 * 60
    },
    "personal-shield": {
        1: 30 * 60,
        2: 27 * 60,
        3: 25 * 60
    },
    "wall": {
        1: 20 * 60,
        2: 10 * 60,
        3: 1 * 60
    },
    "remote-bomb": {
        1: 15 * 60,
        2: 12 * 60,
        3: 10 * 60
    },
    "mega-bomb": {
        1: 15 * 60,
        2: 12 * 60,
        3: 0*60#25 * 60
    },
    "invisibility": {
        1: 45 * 60,
        2: 38 * 60,
        3: 32 * 60
    },
    "disguise": {
        1: 40 * 60,
        2: 35 * 60,
        3: 30 * 60
    },
    "pickpocket": {
        1: 40 * 60,
        2: 35 * 60,
        3: 30 * 60
    },
}


HUD_ELEMENT_LENGTH = 150
HUD_ELEMENT_HEIGHT = 24

HUD_NOTE_LIFESPAN = 360             # Duration of each HUD note (in frames)
HUD_NOTE_ALPHA_MAX = 0.75           # Maximum alpha of a HUD note's text
HUD_NOTE_FADE_IN_END = 0.2          # Percentage point of a note's lifespan at which the fade in should finish
HUD_NOTE_FADE_OUT_BEGIN = 0.7       # Percentage point of a note's lifespan at which the fade out should begin


SPIKE_DAMAGE = 1
BOMB_DAMAGE = 50

SHIELD_BAR_WIDTH = 24
SHIELD_BAR_HEIGHT = 4

SHIELD_BAR_BORDER_COLOR = (105, 105, 105, 1.0)
SHIELD_BAR_BACKGROUND_COLOR = (225, 25, 25)
SHIELD_BAR_COLOR = (49, 98, 255, 0.8)

SHIELD_GL_COLOR = (0.2, 0.4, 1.0, 0.8)
SHIELD_GL_COLOR_WARNING = (1.0, 0.2, 0.2, 0.8)

INVISIBILITY_BAR_COLOR = (95, 225, 95, 0.8)

DISGUISE_BAR_COLOR = (225, 45, 45, 0.8)

SLIDE_MENU_ITEM_HEIGHT = 20
SLIDE_MENU_ITEM_PADDING = 5

SLIDE_MENU_INDENT_AMOUNT = 20

LETTERBOX_HEIGHT = 50
LETTERBOX_ALPHA_MAX = 0.75

LETTERBOX_TEXT_PADDING = 15
LETTERBOX_BAR_HEIGHT = 3

LETTERBOX_DEFAULT_TIMER = 240


RATE_OF_GRAVITY = 2.0

DIG_RESULT_SUCCESS = 1
DIG_RESULT_UNDIGGABLE = 2
DIG_RESULT_EMPTY = 3

DIG_MAX_TIME = 200                  # The timer will start here
DIG_FILL_BEGIN = 12                 # At this point (as the timer counts down), the block will show signs of filling in
DIG_FILL_FRAMES = 12                # How many frames of fill will occur?  (We use the fill patterns with this many frames...)
DIG_PATTERN_IDS = (1, 2, 3, 4, 5)   # Well, I have 5 possible patterns currently.
DIG_QUEUE_TIME = 20                 # For jackhammer / earth-mover, how long between queued digs?

DIG_FILL_FRAME_DELAYS = (
    50, 45, 40, 35, 30, 25, 20, 15, 15, 15, 10, 10
)


PATTERN_SHEET_WIDTH = 128
PATTERN_SHEET_FRAMES_WIDE = 4


# Each map will build a "collision boundary" plane that defines collision values
# on adjacent (perimeter) maps.  How many tiles shall we sample from surrounding maps, as a radius?
COLLISION_BOUNDARY_SIZE = 2


COLLISION_NONE = 1
COLLISION_DIGGABLE = 2
COLLISION_UNDIGGABLE = 3
COLLISION_LADDER = 4
COLLISION_MONKEYBAR = 5
COLLISION_DEADLY = 6
COLLISION_BRIDGE = 7
COLLISION_SPIKES_LEFT = 8
COLLISION_SPIKES_RIGHT = 9

TILESHEET_COLLISION_VALUES = (
    (1, 3, 1, 1, 8, 9, 4, 1, 1, 1, 1, 2, 2, 2, 2, 2, 4, 6, 6, 6),
    (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 2, 2, 2),
    (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3),
    (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 1, 1, 1, 1),
    (2, 2, 2, 2, 6, 6, 6, 6, 6, 6, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2),
    (2, 2, 2, 2, 6, 6, 6, 6, 6, 6, 7, 7, 2, 2, 2, 2, 2, 2, 2, 2),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 1, 1, 1, 1, 1),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 1, 1, 1, 1, 1),
    (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2),
    (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2),
    (2, 2, 2, 2, 2, 2, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 5, 5, 5, 5),
    (2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 4, 4, 4, 1, 1),
    (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 1, 1),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    (1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1),
    (1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1),
)


VERY_DETERMINED = 1
SOMEWHAT_DETERMINED = 2
BARELY_DETERMINED = 3
NOT_DETERMINED = 4


AI_MAX_FREEZE_RESISTANCE = 10

AI_MAX_TRAP_TIME = 100
AI_MAX_TRAP_EXCEPTION_TIME = 100

AI_MAX_PATIENCE = 60

AI_ENEMY_RESPAWN_TIME = 60
AI_ENEMY_FLASH_TIME = 90
AI_ENEMY_FLASH_DURATION = 15

AI_ENEMY_INITIAL_DELAY = 60

AI_ENEMY_TRAP_ESCAPE_WARNING_PERIOD_LENGTH = 60
AI_ENEMY_TRAP_ESCAPE_FLASH_DURATION = 15


MAX_ENEMY_COUNT = 8


GENUS_ENEMY = 1
GENUS_PLAYER = 2
GENUS_NPC = 3
GENUS_RESPAWN_ENEMY = 5
GENUS_GOLD = 6
GENUS_RESPAWN_PLAYER1 = 7
GENUS_RESPAWN_PLAYER2 = 8
GENUS_LEVER = 9
GENUS_BOMB = 10
GENUS_HOLOGRAM = 11
GENUS_RESPAWN_PLAYER = 12


NONCOLLIDING_ENTITY_TYPES = (GENUS_NPC, GENUS_BOMB, GENUS_LEVER, GENUS_HOLOGRAM)


AI_BEHAVIOR_NORMAL = 1          # Standard pursuit
AI_BEHAVIOR_TERRIFIED = 2       # Opposite of standard pursuit; flee!
AI_BEHAVIOR_ANGRY = 3           # ???
AI_BEHAVIOR_TERRITORIAL = 4     # ???
AI_BEHAVIOR_PATROLLING = 5
AI_BEHAVIOR_HOLOGRAM = 6

AI_MOOD_NORMAL = 1
AI_MOOD_ANGRY = 2
AI_MOOD_SCARED = 3

AI_BEHAVIOR_TRANSLATIONS = {
    "normal": AI_BEHAVIOR_NORMAL,
    "terrified": AI_BEHAVIOR_TERRIFIED,
    "angry": AI_BEHAVIOR_ANGRY,
    "territorial": AI_BEHAVIOR_TERRITORIAL,
    "patrolling": AI_BEHAVIOR_PATROLLING
}

AI_BEHAVIOR_REVERSE_TRANSLATIONS = {
    AI_BEHAVIOR_NORMAL: "normal",
    AI_BEHAVIOR_TERRIFIED: "terrified",
    AI_BEHAVIOR_ANGRY: "angry",
    AI_BEHAVIOR_TERRITORIAL: "territorial",
    AI_BEHAVIOR_PATROLLING: "patrolling"
}


SPECIES_NORMAL = 1              # Your ordinary bad guy
SPECIES_SECURITY = 2            # Disposable; they never respawn


PARTICLE_SPAWN_GRAVITY             = -8     # The particle begins with this gravity value
PARTICLE_SPAWN_GRAVITY_VARIANCE    = 2      # Add a little random variance...
PARTICLE_SPEED                     = 0      # The particle will move horizontally
PARTICLE_SPEED_VARIANCE            = 4      # Wild randomness!
PARTICLE_ROTATIONAL_SPEED          = 10     # The particle rotates at this velocity
PARTICLE_ROTATIONAL_SPEED_VARIANCE = 5      # A little variance
PARTICLE_MAX_GRAVITY               = 7      # Don't leave too quickly...
PARTICLE_RATE_OF_GRAVITY           = 0.45   # A little different for particles...
PARTICLE_WIDTH                     = 8      # 3 wide per tile
PARTICLE_HEIGHT                    = 8      # 3 high per tile

COLORCLE_WIDTH = 3
COLORCLE_HEIGHT = 3

NUMBERCLE_WIDTH = 12
NUMBERCLE_HEIGHT = 12

NUMBERCLE_LIFESPAN = 120

GOLD_SPINNER_LIFESPAN = 20
WALLET_TICK_DELAY_MAX = 20 # 3 ticks per second, 60FPS (hard-coded)


MAGIC_WALL_TILE_INDEX_DEFAULT = 1
MAGIC_WALL_TILE_INDEX_SPIKES_LEFT = 4
MAGIC_WALL_TILE_INDEX_SPIKES_RIGHT = 5
MAGIC_WALL_BRICK_DELAY = 2
MAGIC_WALL_BRICK_WIDTH = 6
MAGIC_WALL_BRICK_HEIGHT = 4
MAGIC_WALL_BRICK_DROP_HEIGHT = 48





TRIGGER_BEHAVIOR_WAYPOINT = 1
TRIGGER_BEHAVIOR_PASSIVE = 2
TRIGGER_BEHAVIOR_ACTIVATED = 3
TRIGGER_BEHAVIOR_NONE = 4
TRIGGER_BEHAVIOR_INTERVAL = 5
TRIGGER_BEHAVIOR_FOLLOWING = 6
TRIGGER_BEHAVIOR_ALARM = 7

ALARM_LASER_SIZE = 2


FALL_REGION_TIMER_MAX = 120


TOOLTIP_DELAY = 60

# Try to keep tooltips on the screen, with a little room to spare...
TOOLTIP_MIN_PADDING_X = 20
TOOLTIP_MIN_PADDING_Y = 20

LAYER_FOREGROUND = 1
LAYER_BACKGROUND = 2

BACKGROUND_MAP_SCALE = 0.75
BACKGROUND_MAP_PARALLAX_SCALE = 0.85

SCALE_BY_LAYER = {
    LAYER_BACKGROUND: 0.75,
    LAYER_FOREGROUND: 1.0
}

PARALLAX_BY_LAYER = {
    LAYER_BACKGROUND: 0.85,
    LAYER_FOREGROUND: 1.0
}



MIN_MAP_SCROLL_X = 200
MIN_MAP_SCROLL_Y = 150

MAX_PERIMETER_SCROLL_X = 48
MAX_PERIMETER_SCROLL_Y = 96

CAMERA_SPEED = 22.5

CAMERA_CENTER_ON_PLAYER = 1
CAMERA_CENTER_ON_LEVEL = 2


DEFAULT_LIGHTBOX_ALPHA_PERCENTAGE = 0.5


QUEST_STATUS_INACTIVE = 0
QUEST_STATUS_IN_PROGRESS = 1
QUEST_STATUS_COMPLETE = 2
QUEST_STATUS_FAILED = 3


ACHIEVEMENT_STATUS_ACTIVE = 1
ACHIEVEMENT_STATUS_COMPLETE = 2
ACHIEVEMENT_STATUS_FAILED = 3


XP_PER_LEVEL = 500.0
XP_BAR_ANIMATION_DURATION = 480



CONVERSATION_WIDTH = 480
CONVERSATION_X = 80

MIN_SPEAKER_HEIGHT = 120
MIN_RESPONSE_HEIGHT = 120

SPEAKER_X = 20

SPEAKER_WIDTH = 48
SPEAKER_HEIGHT = 48

RESPONDER_X = 412
DIALOGUE_RESPONSE_X = 20

DIALOGUE_WIDTH = 310
DIALOGUE_HIGHLIGHT_WIDTH = 350
DIALOGUE_X = 150

DIALOGUE_ALPHA_MAX = 0.95
DIALOGUE_ALPHA_SPEED = 0.01
DIALOGUE_ALPHA_TEXT_BONUS = 0.25


COMPUTER_SIMPLE_WIDTH = 240


DIG_DELAY = 20

BOMB_FUSE_LENGTH = 160#41#160
BOMB_FUSE_INTERVAL = 15 # How often will we advance the animation frame?

BOMB_FRAME_COUNT = 4


REPUTATION_READY = 60 * 60 * 15 # How long (in frames played) until we use the "been here a while" reputation  menu screen


PAUSE_MENU_X = 56
PAUSE_MENU_Y = 48

PAUSE_MENU_WIDTH = 528
PAUSE_MENU_HEIGHT = 380

PAUSE_MENU_SIDEBAR_X = 10
PAUSE_MENU_SIDEBAR_Y = 10
PAUSE_MENU_SIDEBAR_WIDTH = 140
PAUSE_MENU_SIDEBAR_CONTENT_WIDTH = 120

PAUSE_MENU_CONTENT_X = 160
PAUSE_MENU_CONTENT_Y = 10
PAUSE_MENU_CONTENT_WIDTH = 346
PAUSE_MENU_CONTENT_HEIGHT = 360

PAUSE_MENU_PROMPT_WIDTH = 320
PAUSE_MENU_PROMPT_CONTENT_WIDTH = 300

PAUSE_MENU_PRIZE_AD_HEIGHT = 170


OVERWORLD_GAME_OVER_MENU_WIDTH = 240


MAX_SKILL_SLOTS = 2


MAX_QUICKSAVE_SLOTS = 2
MAX_AUTOSAVE_SLOTS = 1


DATE_WIDTH = 120

SKILL_PREVIEW_WIDTH = 160
SKILL_PREVIEW_HEIGHT = 120


TERMINAL_FRAME_DURATION = 10
TERMINAL_FRAME_COUNT = 4
TERMINAL_FINAL_FRAME_PAUSE = 60

HACK_PANEL_WIDTH = 240
HACK_PANEL_HEIGHT = 240

HACK_PANEL_TEMPORARY_STATUS_DURATION = 90


PROMPT_PANEL_WIDTH = 480
PROMPT_PANEL_HEIGHT = 240

PROMPT_PANEL_TEMPORARY_STATUS_DURATION = 90


DIALOGUE_PANEL_X = 78

DIALOGUE_PANEL_WIDTH = 484
DIALOGUE_PANEL_HEIGHT = 100

DIALOGUE_PANEL_CONTENT_WIDTH = 396


CORNER_SIZE = 6

ACTUAL_WIDTH = 640
ACTUAL_HEIGHT = 480

TILESHEET_WIDTH = 480
TILESHEET_HEIGHT = 432

TILESHEET_TILES_WIDE = TILESHEET_WIDTH / 24

ANIMATION_TILESHEET_WIDTH = 120
ANIMATION_TILESHEET_HEIGHT = 120

TILE_SIZE = 24.0

TILE_WIDTH = 24
TILE_HEIGHT = 24

HALF_TILE_HEIGHT = TILE_HEIGHT / 2

GRID_WIDTH = 27
GRID_HEIGHT = 14

X_OFFSET = 0

TILE_LAYER = 1
OBJECT_LAYER = 2

LAYER_TILE = 1
LAYER_MASK = 2

GAME_WIDTH = SCREEN_WIDTH
GAME_HEIGHT = 14 * TILE_SIZE

GAME_OFFSET_X = 0
GAME_OFFSET_Y = (SCREEN_HEIGHT - GAME_HEIGHT) / 2

GAME_WINDOW = (GAME_OFFSET_X, GAME_OFFSET_Y, GAME_WIDTH, GAME_HEIGHT)
GRID_WINDOW = (0, 0, GAME_WIDTH, GAME_HEIGHT)

PREVIEW_WIDTH = SCREEN_WIDTH / 4
PREVIEW_HEIGHT = SCREEN_HEIGHT / 4

SCREEN_EXPLODER_PIECE_INITIAL_GRAVITY = -5
SCREEN_EXPLODER_PIECE_GRAVITY_DELAY = 2
SCREEN_EXPLODER_PIECE_MAX_GRAVITY = 10


MODE_GAME = 1
MODE_EDITOR = 2

X_AXIS = 1
Y_AXIS = 2

CAMERA_MOVE_IMMEDIATE = 1
CAMERA_MOVE_ANIMATED = 2

CAMERA_ANIMATION_SPEED = 3

MAX_GRAVITY = 7.5
GRAVITATIONAL_FORCE = 0.25

DIR_NONE = -1

DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3
DIR_DIG_RIGHT = 4
DIR_DIG_LEFT = 5
DIR_SWING_RIGHT = 6
DIR_SWING_LEFT = 7

# Makes templating easier if I reference directions by string
LITERAL_POSITION_TRANSLATIONS = {
    "left": DIR_LEFT,
    "right": DIR_RIGHT,
    "top": DIR_UP,
    "bottom": DIR_DOWN
}

FORWARD = 1
BACKWARD = 2

BACKGROUND = 1
FOREGROUND = 2

NOTIFICATION_WIDTH = 120
NOTIFICATION_DURATION = 200

TOP = 0
RIGHT = 1
BOTTOM = 2
LEFT = 3

PLAYER_WEIGHT = 2

SHAKE_WEAK = 5
SHAKE_STRONG = 9

SHAKE_BRIEFLY = 1
SHAKE_LONGER = 2
SHAKE_FOREVER = 3
SHAKE_END = 4


PAD_AXIS = 1
PAD_HAT = 2
PAD_BUTTON = 3
