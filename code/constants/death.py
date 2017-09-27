# Constants related to damage and death.


DEATH_BY_TILE_FILL = 1
DEATH_BY_ENEMY = 2
DEATH_BY_PLANAR_SHIFT = 3
DEATH_BY_OUT_OF_BOUNDS = 4
DEATH_BY_DEADLY_TILE = 5
DEATH_BY_BOMB = 6
DEATH_BY_VAPORIZATION = 7
DEATH_BY_SUICIDE = 8

# String-based lookups
DEATH_TYPE_LOOKUPS = {
    "tile-fill": DEATH_BY_TILE_FILL,
    "enemy": DEATH_BY_ENEMY,
    "planar-shift": DEATH_BY_PLANAR_SHIFT,
    "out-of-bounds": DEATH_BY_OUT_OF_BOUNDS,
    "deadly-tile": DEATH_BY_DEADLY_TILE,
    "bomb": DEATH_BY_BOMB,
    "vaporization": DEATH_BY_VAPORIZATION,
    "suicide": DEATH_BY_SUICIDE
}

# Reverse lookups
DEATH_TYPE_STRING_NAMES = {
    DEATH_BY_TILE_FILL: "tile-fill",
    DEATH_BY_ENEMY: "enemy",
    DEATH_BY_PLANAR_SHIFT: "planar-shift",
    DEATH_BY_OUT_OF_BOUNDS: "out-of-bounds",
    DEATH_BY_DEADLY_TILE: "deadly-tile",
    DEATH_BY_BOMB: "bomb",
    DEATH_BY_VAPORIZATION: "vaporization",
    DEATH_BY_SUICIDE: "suicide"
}

# This only matters for the personal-shield skill.  Without a shield,
# death is immediate in any of these cases...
DAMAGE_POINTS_BY_CAUSE = {
    DEATH_BY_TILE_FILL: 1000,       # Instant death no matter how strong the shield
    DEATH_BY_ENEMY: 1,
    DEATH_BY_PLANAR_SHIFT: 1000,    # Instant death
    DEATH_BY_OUT_OF_BOUNDS: 1000,   # Instant death
    DEATH_BY_DEADLY_TILE: 1,
    DEATH_BY_BOMB: 3,
    DEATH_BY_VAPORIZATION: 3,
    DEATH_BY_SUICIDE: 1000          # Instant death
}

# How long does the player have to hold down the suicide key?
SUICIDE_INTERVAL_MAX = 30#180
