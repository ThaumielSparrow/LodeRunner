# Constants used for the waves system.


# Certain requirements / allowances / labels should never be rendered.
UNRENDERABLE_NAMES = ["survive"]


# Translate a given requirement key to something readable by players for the progress chart.
HUMAN_READABLE_REQUIREMENT_NAMES = {
    "survive": "Survive?", # I don't intend to ever render this?
    "gold": "Gold Collected",
    "digs": "Digs Required",
    "enemy-kills": "Kills",
    "enemy-kills:tile-fill": "Dig Kills",
    "enemy-kills:bomb": "Bomb Kills",
    "enemy-kills:deadly-tile": "Hazard Kills"
}

# Translate a given allowance key to something readable
HUMAN_READABLE_ALLOWANCE_NAMES = {
    "digs": "Digs Remaining",
    "bombs": "Bombs Remaining"
}

# Translate a given wave limit key to something readable
HUMAN_READABLE_LIMIT_NAMES = {
    "gold": "Gold Limit",
    "digs": "Dig Limit",
    "enemy-kills": "Kill Limit",
    "enemy-kills:tile-fill": "Dig Kill Limit",
    "enemy-kills:bomb": "Bomb Kill Limit",
    "enemy-kills:deadly-tile": "Hazard Kill Limit"
}
