# Miscellaneous calls, the 100 group
UNKNOWN = 10000
DEBUG = 10001
OVERLAY = 10002
CAMERA_MESSAGE = 10003
SHOUT = 10004
SLEEP = 10005
POST_NEWSFEEDER_ITEM = 10006


# Map calls, the 500 group
DIG_TILE = 50001
PURGE_TILE = 50002
SET_MAP_STATUS_MESSAGE = 50003

CUTSCENE_BEGIN = 50010
CUTSCENE_END = 50011
CUTSCENE_CONTROL = 50012

SET_MAP_PARAM = 50020
GET_MAP_PARAM = 50021 # I don't expect to use this, just future-proofing

CALL_SCRIPT = 50030

RELOAD_MAP = 50040
LOAD_MAP = 50041
MARK_MAP_AS_COMPLETED = 50042

SPAWN_RANDOM_ENEMY = 50050
REMOVE_RANDOM_ENEMIES = 50051


# Map plane calls, the 510 group
PLANAR_SLIDE = 51001
PLANAR_MESSAGE = 51010
PLANAR_SHIFT = 51020


# Map entity calls, the 520 group
ENTITY_MESSAGE = 52001
LEVER_HAS_POSITION = 52010
SET_NPC_INDICATOR = 52020


# Map trigger calls, the 530 group
TRIGGER_CONTAINS = 53001
TRIGGER_MESSAGE = 53010


# Conditions, the 200 group
CONDITION_IF = 20001
CONDITION_THEN = 20002
CONDITION_ELSE = 20003

CONDITION_SWITCH = 20004
CONDITION_WHEN = 20005


# Variable operations, the 201 group
VARS_PLUS = 20101
VARS_SUM = 20102
VARS_DIFF = 20103
VARS_SET = 20104
VARS_COPY = 20105


# Dialogue display calls, the 300 group
DIALOGUE = 30001
DIALOGUE_RESPONSE = 30002
DIALOGUE_SHOP = 30003
DIALOGUE_COMPUTER = 30004
DIALOGUE_FYI = 30005
SHOP = 30006

# Dialogue dismissal calls, the 301 group (rarely used)
DISMISS_FYI = 30101             # Dismiss an fyi dialogue panel.  Triggers "continue" event, which can lead to another fyi text if the current fyi has a redirect.

# Dialogue line status calls, the 302 group
DIALOGUE_UPDATE_LINES_AND_RESPONSES = 30201

DIALOGUE_ENABLE_LINES_BY_CLASS = 30210
DIALOGUE_DISABLE_LINES_BY_CLASS = 30211


# Quest calls, the 600 group
FLAG_QUEST = 60001
FLAG_QUEST_UPDATE = 60002

FETCH_QUEST_STATUS = 60010
FETCH_UPDATE_STATUS = 60011


# Item calls, the 610 group
FETCH_STAT = 61001
FETCH_STAT_BY_REGION = 61002

FETCH_ITEM_STAT = 61010
SET_ITEM_STAT = 61011

ACQUIRE_ITEM = 91020
LOSE_ITEM = 91021
UPGRADE_ITEM = 91022 # (?)


# Wave calls, the 900 group
SET_WAVE_PARAM = 90001
SET_WAVE_ALLOWANCE = 90002
SET_WAVE_REQUIREMENT = 90003
SET_WAVE_COUNTER = 90004  # I don't plan to use this, but I'm reserving it just in case...
SET_WAVE_LIMIT = 90005

NEW_WAVE = 90020

SHOW_WAVE_PROGRESS_CHART = 90030
REBUILD_WAVE_PROGRESS_CHART = 90031
HIDE_WAVE_PROGRESS_CHART = 90032

CREATE_TIMER = 90040
CLEAR_TIMER = 90041
INCREMENT_TIMER = 90042

# Special room dialog calls, the 910 group
PUZZLE_INTRO = 91001
PUZZLE_OUTRO = 91002

CHALLENGE_INTRO = 91010
CHALLENGE_OUTRO = 91011

WAVE_INTRO = 91020
WAVE_OUTRO = 91021


"""
REVERSE TRANSLATIONS, STRING TO CONSTANT INTEGER, PLUS OTHER DATA
"""

LOOKUP_TABLE = {

    "overlay": {
        "id": OVERLAY,
        "properties": [
			"map-name",
			"title"
        ],
        "label": """
            <label name = '' value = 'Overlay [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["map-name"]']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "camera-message": {
        "id": CAMERA_MESSAGE,
        "properties": [
			"message",
			"entity"
        ],
        "label": """
            <label name = '' value = 'Camera Message [%s] [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["message"], fields["entity"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "shout": {
        "id": SHOUT,
        "properties": [
			"position",
			"message"
        ],
        "label": """
            <label name = '' value = 'Shout [%s] "%s"' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["position"], fields["message"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "sleep": {
        "id": SLEEP,
        "properties": [
			"frames"
        ],
        "label": """
            <label name = '' value = 'Sleep(%s)' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["frames"],)']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "condition-if": {
        "id": CONDITION_IF,
        "properties": [
			"variable1",
			"variable2",
			"operator",
			"raw-value"
        ],
        "label": """
            <label name = '' value = 'If [%s] %s [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable1"], fields["operator"], s)']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "condition-then": {
        "id": CONDITION_THEN,
        "properties": [

        ],
        "label": """
            <label name = '' value = 'Then' x = '5' y = '0' />
        """,
        "hints": """
            []
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "condition-else": {
        "id": CONDITION_ELSE,
        "properties": [

        ],
        "label": """
            <label name = '' value = 'Else' x = '5' y = '0' />
        """,
        "hints": """
            []
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "condition-switch": {
        "id": CONDITION_SWITCH,
        "properties": [
			"variable"
        ],
        "label": """
            <label name = '' value = 'Switch' x = '5' y = '0' />
        """,
        "hints": """
            []
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "condition-when": {
        "id": CONDITION_WHEN,
        "properties": [
			"variable",
			"raw-value"
        ],
        "label": """
            <label name = '' value = 'When [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['s']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "vars-plus": {
        "id": VARS_PLUS,
        "properties": [
			"variable",
			"amount"
        ],
        "label": """
            <label name = '' value = '[%s] += %s' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["amount"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "vars-sum": {
        "id": VARS_SUM,
        "properties": [
			"variable1",
			"variable2",
			"variable3"
        ],
        "label": """
            <label name = '' value = '[%s] = [%s] + [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable3"], fields["variable1"], fields["variable2"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "vars-diff": {
        "id": VARS_DIFF,
        "properties": [
			"variable1",
			"variable2",
			"variable3"
        ],
        "label": """
            <label name = '' value = '[%s] = [%s] - [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable3"], fields["variable1"], fields["variable2"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "vars-set": {
        "id": VARS_SET,
        "properties": [
			"variable",
			"value"
        ],
        "label": """
            <label name = '' value = '[%s] = %s' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["value"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "vars-copy": {
        "id": VARS_COPY,
        "properties": [
			"variable1",
			"variable2"
        ],
        "label": """
            <label name = '' value = '[%s] = [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable2"], fields["variable1"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue": {
        "id": DIALOGUE,
        "properties": [
			"conversation",
			"entity"
        ],
        "label": """
            <label name = '' value = '[%s] iterate conversation [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["conversation"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue-response": {
        "id": DIALOGUE_RESPONSE,
        "properties": [
			"message",
			"selectable",
			"answer"
        ],
        "label": """
            <label name = '' value = 'Dialogue Response: [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["message"][0:50].replace("\'", "&apos;")']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue-shop": {
        "id": DIALOGUE_SHOP,
        "properties": [
			"conversation",
			"entity"
        ],
        "label": """
            <label name = '' value = '[%s] iterate conversation [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["conversation"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue-computer": {
        "id": DIALOGUE_COMPUTER,
        "properties": [
			"conversation",
			"entity"
        ],
        "label": """
            <label name = '' value = '[%s] iterate conversation [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["conversation"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue-fyi": {
        "id": DIALOGUE_FYI,
        "properties": [
			"conversation",
			"entity",
			"id"
        ],
        "label": """
            <label name = '' value = '[%s] fyi[id = %s] [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["id"], fields["conversation"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dismiss-fyi": {
        "id": DISMISS_FYI,
        "properties": [
			"id"
        ],
        "label": """
            <label name = '' value = 'dismiss fyi[id = %s]' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["id"]']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue-enable-lines-by-class": {
        "id": DIALOGUE_ENABLE_LINES_BY_CLASS,
        "properties": [
			"entity",
			"conversation",
			"class"
        ],
        "label": """
            <label name = '' value = '@%s enable ^%s.%s' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["conversation"], fields["class"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dialogue-disable-lines-by-class": {
        "id": DIALOGUE_DISABLE_LINES_BY_CLASS,
        "properties": [
			"entity",
			"conversation",
			"class"
        ],
        "label": """
            <label name = '' value = '@%s disable ^%s.%s' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["conversation"], fields["class"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "dig-tiles": {
        "id": DIG_TILE,
        "properties": [
			"plane",
			"target",
			"behavior"
        ],
        "label": """
            <label name = '' value = 'Dig Tiles in [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["target"]']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "set-map-status-message": {
        "id": SET_MAP_STATUS_MESSAGE,
        "properties": [
			"message"
        ],
        "label": """
            <label name = '' value = 'Set Map Status Msg:  %s' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["message"]']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "cutscene": {
        "id": CUTSCENE_CONTROL,
        "properties": [
			"behavior"
        ],
        "label": """
            <label name = '' value = 'Cutscene [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["behavior"]']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "call-script": {
        "id": CALL_SCRIPT,
        "properties": [
			"script"
        ],
        "label": """
            <label name = '' value = 'Call Script [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['fields["script"]']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "reload-map": {
        "id": RELOAD_MAP,
        "properties": [

        ],
        "label": """
            <label name = '' value = 'RELOAD MAP' x = '5' y = '0' />
        """,
        "hints": """
            []
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "load-map": {
        "id": LOAD_MAP,
        "properties": [
			"name",
			"spawn"
        ],
        "label": """
            <label name = '' value = 'Load map [%s] player @ [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["name"], fields["spawn"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "mark-map-as-completed": {
        "id": MARK_MAP_AS_COMPLETED,
        "properties": [

        ],
        "label": """
            <label name = '' value = 'Mark Map as COMPLETED' x = '5' y = '0' />
        """,
        "hints": """
            []
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "spawn-random-enemy": {
        "id": SPAWN_RANDOM_ENEMY,
        "properties": [
			"target",
			"disposable"
        ],
        "label": """
            <label name = '' value = 'Spawn Random Enemy in [%s]  Disposable: [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["target"], fields["disposable"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "planar-slide": {
        "id": PLANAR_SLIDE,
        "properties": [
			"plane",
			"slide",
			"speed",
			"target"
        ],
        "label": """
            <label name = '' value = 'Planar Slide  -  %s -> %s' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["plane"], fields["slide"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "planar-message": {
        "id": PLANAR_MESSAGE,
        "properties": [
			"plane",
			"param",
			"message"
        ],
        "label": """
            <label name = '' value = 'Tell Plane [%s] [%s]   [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["plane"], fields["message"], fields["param"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "planar-shift": {
        "id": PLANAR_SHIFT,
        "properties": [
			"plane",
			"target",
			"speed",
			"collides"
        ],
        "label": """
            <label name = '' value = 'Planar Shift  -  %s -> %s' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["plane"], fields["target"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "entity-message": {
        "id": ENTITY_MESSAGE,
        "properties": [
			"entity",
			"param",
			"target",
			"message"
        ],
        "label": """
            <label name = '' value = 'Tell [%s] [%s]   [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["message"], fields["target"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "lever-has-position": {
        "id": LEVER_HAS_POSITION,
        "properties": [
			"variable",
			"entity",
			"position"
        ],
        "label": """
            <label name = '' value = '[%s] = [%s] has position [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["entity"], fields["position"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "set-npc-indicator": {
        "id": SET_NPC_INDICATOR,
        "properties": [
			"entity",
			"key",
			"value"
        ],
        "label": """
            <label name = '' value = '@%s[%s = %s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["entity"], fields["key"], fields["value"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "trigger-contains": {
        "id": TRIGGER_CONTAINS,
        "properties": [
			"variable",
			"entity",
			"target"
        ],
        "label": """
            <label name = '' value = '[%s] = [%s] contains [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["target"], fields["entity"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "trigger-message": {
        "id": TRIGGER_MESSAGE,
        "properties": [
			"target",
			"entity",
			"message"
        ],
        "label": """
            <label name = '' value = 'Trigger [%s] %s [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["target"], fields["message"], fields["entity"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "flag-quest": {
        "id": FLAG_QUEST,
        "properties": [
			"quest",
			"flag"
        ],
        "label": """
            <label name = '' value = 'Flag Quest [%s] [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["quest"], fields["flag"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "flag-quest-update": {
        "id": FLAG_QUEST_UPDATE,
        "properties": [
			"quest",
			"update",
			"flag"
        ],
        "label": """
            <label name = '' value = 'Flag Update [%s] [%s] [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["quest"], fields["update"], fields["flag"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "fetch-quest-status": {
        "id": FETCH_QUEST_STATUS,
        "properties": [
			"quest",
			"variable",
			"format"
        ],
        "label": """
            <label name = '' value = '[%s] = Fetch Quest Status [%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["quest"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "fetch-update-status": {
        "id": FETCH_UPDATE_STATUS,
        "properties": [
			"quest",
			"variable",
			"update",
			"format"
        ],
        "label": """
            <label name = '' value = '[%s] = %s.UpdateStatus[%s]' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["quest"], fields["update"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "fetch-stat": {
        "id": FETCH_STAT,
        "properties": [
			"statistic",
			"variable",
			"entity"
        ],
        "label": """
            <label name = '' value = '[%s] = fetch-stat [%s] (%s)"' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["statistic"], fields["entity"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "fetch-stat-by-region": {
        "id": FETCH_STAT_BY_REGION,
        "properties": [
			"statistic",
			"variable",
			"entity",
			"target"
        ],
        "label": """
            <label name = '' value = '[%s] = %s.fetch-stat [%s] (%s)"' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["target"], fields["statistic"], fields["entity"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "fetch-item-stat": {
        "id": FETCH_ITEM_STAT,
        "properties": [
			"statistic",
			"variable",
			"item"
        ],
        "label": """
            <label name = '' value = '[%s] = fetch-item-stat [%s] (%s)"' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["variable"], fields["statistic"], fields["item"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    },


    "set-item-stat": {
        "id": SET_ITEM_STAT,
        "properties": [
			"statistic",
			"value",
			"item"
        ],
        "label": """
            <label name = '' value = 'item [%s] [%s] = [%s]"' x = '5' y = '0' />
        """,
        "hints": """
            ['(fields["item"], fields["statistic"], fields["value"])']
        """,
        "tooltip": """
            Do tooltips later, if necessary.
        """
    }
}

TRANSLATIONS = {
    "planar-shift": PLANAR_SHIFT,
    "dig-tiles": DIG_TILE,
    "purge-tile": PURGE_TILE,
    "cutscene-begin": CUTSCENE_BEGIN,
    "cutscene-end": CUTSCENE_END,    
    "debug": DEBUG,

    "condition-if": CONDITION_IF,
    "condition-then": CONDITION_THEN,
    "condition-else": CONDITION_ELSE,

    "condition-switch": CONDITION_SWITCH,
    "condition-when": CONDITION_WHEN,

    "dialogue": DIALOGUE,
    "dialogue-response": DIALOGUE_RESPONSE,
    "dialogue-fyi": DIALOGUE_FYI,
    "dialogue-shop": DIALOGUE_SHOP,
    "dialogue-computer": DIALOGUE_COMPUTER,

    "dismiss-fyi": DISMISS_FYI,

    "shop": SHOP,

    "puzzle-intro": PUZZLE_INTRO,
    "puzzle-outro": PUZZLE_OUTRO,

    "challenge-intro": CHALLENGE_INTRO,
    "challenge-outro": CHALLENGE_OUTRO,

    "entity-message": ENTITY_MESSAGE,

    "trigger-contains": TRIGGER_CONTAINS,
    "trigger-message": TRIGGER_MESSAGE,

    "cutscene": CUTSCENE_CONTROL,

    "call-script": CALL_SCRIPT,

    "set-map-param": SET_MAP_PARAM,
    "get-map-param": GET_MAP_PARAM,

    "vars-plus": VARS_PLUS,
    "vars-sum": VARS_SUM,
    "vars-diff": VARS_DIFF,
    "vars-set": VARS_SET,
    "vars-copy": VARS_COPY,

    "set-npc-indicator": SET_NPC_INDICATOR,

    "dialogue-enable-lines-by-class": DIALOGUE_ENABLE_LINES_BY_CLASS,
    "dialogue-disable-lines-by-class": DIALOGUE_DISABLE_LINES_BY_CLASS,

    "flag-quest": FLAG_QUEST,
    "flag-quest-update": FLAG_QUEST_UPDATE,

    "fetch-quest-status": FETCH_QUEST_STATUS,
    "fetch-update-status": FETCH_UPDATE_STATUS,

    "overlay": OVERLAY,

    "camera-message": CAMERA_MESSAGE,

    "reload-map": RELOAD_MAP,
    "mark-map-as-completed": MARK_MAP_AS_COMPLETED,
    "set-map-status-message": SET_MAP_STATUS_MESSAGE,

    "lever-has-position": LEVER_HAS_POSITION,

    "planar-slide": PLANAR_SLIDE,
    "planar-message": PLANAR_MESSAGE,

    "spawn-random-enemy": SPAWN_RANDOM_ENEMY,

    "load-map": LOAD_MAP,

    "dialogue-update-lines-and-responses": DIALOGUE_UPDATE_LINES_AND_RESPONSES,

    "shout": SHOUT,

    "fetch-stat": FETCH_STAT,
    "fetch-stat-by-region": FETCH_STAT_BY_REGION,
    "fetch-item-stat": FETCH_ITEM_STAT,
    "set-item-stat": SET_ITEM_STAT,

    "sleep": SLEEP,

    "set-wave-param": SET_WAVE_PARAM,
    "set-wave-allowance": SET_WAVE_ALLOWANCE,
    "set-wave-requirement": SET_WAVE_REQUIREMENT,
    "set-wave-counter": SET_WAVE_COUNTER,
    "set-wave-limit": SET_WAVE_LIMIT,

    "new-wave": NEW_WAVE,

    "wave-intro": WAVE_INTRO,
    "wave-outro": WAVE_OUTRO,

    "show-wave-progress-chart": SHOW_WAVE_PROGRESS_CHART,
    "rebuild-wave-progress-chart": REBUILD_WAVE_PROGRESS_CHART,
    "hide-wave-progress-chart": HIDE_WAVE_PROGRESS_CHART,

    "create-timer": CREATE_TIMER,
    "clear-timer": CLEAR_TIMER,
    "increment-timer": INCREMENT_TIMER,

    "remove-random-enemies": REMOVE_RANDOM_ENEMIES,

    "post-newsfeeder-item": POST_NEWSFEEDER_ITEM,

    "acquire-item": ACQUIRE_ITEM,
    "lose-item": LOSE_ITEM,
    "upgrade-item": UPGRADE_ITEM
}
