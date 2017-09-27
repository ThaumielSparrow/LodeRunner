from code.utils.common import log, log2, is_numeric

# The wave tracker holds general wave params, wave allowances, and wave requirements.
class WaveTracker:

    def __init__(self):

        # Whenever we change a counter variable, we'll flag the tracker's data as "dirty."
        # Some widget (i.e. the wave progress chart) should see this as a sign to rebuild its data.
        self.dirty = True # Default to dirty


        # General wave params
        self.wave_params = {
            "on-complete": "", # What script will we execute when the wave completes?  If we do not specify
                               # any script, then the game will NOT bother actively monitoring for wave completion.
                               # (The game will still track and enforce all other metrics, though.)

            "on-fail": "",     # What script will we execute if we fail the wave by reaching a wave limit?
                               # The script may kill the player, or summon the wave failure menu, or something else entirely?

            "active-timer": "", # If this wave uses some sort of timer, then we specify the id of that timer here.
            "active-timer-label": "", # We will render the timer with this label...

            "on-collect-gold": "", # Should we fire a script when the player collects a piece of gold?
            "on-enemy-collect-gold": "", # Should we fire a script when any enemy collects a piece of gold?

            "on-enemy-kill": "", # Should we fire a script when the player kills an enemy?

            "gold-rotation-size": 0, # Setting a positive value enables gold rotation, where picking up a piece of gold
                                     # triggers a new piece of gold to appear/reappear.  Set this number to the total gold pieces that should appear at any given moment.

            "digs-purge": 0, # Does digging a tile cause the tile to "purge" from the map for the entire duration of the wave?
            "on-dig": "", # What script will we execute if the player digs?

            "players-collect-gold": 1, # Can the player collect gold?

            "enemies-collect-gold": 1, # Do enemies pick up gold when they touch it?  (Usually, yes...)

            "bombs-free": 0 # When set to 1, the player's bomb inventory is not reduced when using a bomb, and the player can drop a bomb even if their overworld inventory is 0.
                            # When this is set, only the "bombs-used" parameter limits the number of bombs the player can use.
        }


        # Wave allowances (bombs given, digs allowed, etc.)
        self.wave_allowances = {
            "digs": -1, # -1 indicates unlimited digs (default, typical).  Non-negative values place a ceiling on the number of times the player can dig.
            "bombs": 0 # How many bombs can the player use on this wave?  -1 indicates infinite bombs allowed.
        }


        # Wave counters (digs committed, enemies killed, etc.)
        self.wave_counters = {
            "survive": 0, # We don't actively increment this counter.  If the wave requires survival for some time n,
                          # then the wave will set the "survive" requirement to 1.  We can never "complete" that requirement;
                          # the map's scripts must create a timer object that manually fires a "wave complete" event instead.

            "gold": 0, # How many pieces of gold has the player collected so far?
            "digs": 0, # How many times has the player made a dig?
            "bombs": 0, # How many bombs has the player placed so far?

            "enemy-kills": 0, # How many enemies has the player killed during the wave?
            "enemy-kills:tile-fill": 0, # Kill n enemies by trapping them
            "enemy-kills:planar-shift": 0, # Kill n enemies by squishing them
            "enemy-kills:out-of-bounds": 0, #               by making them fall off the level
            "enemy-kills:deadly-tile": 0, #                 by making them run into spikes, or a similarly deadly tile
            "enemy-kills:bomb": 0 #                         by bombing them
        }


        # Wave requirements (how much gold to get, how many enemies to kill, etc.)
        self.wave_requirements = {
            "survive": 0, # Must the player survive indefinitely?  (A timer should control when the player has survived for long enough...)

            "gold": -1, # How much gold does the player need to complete this wave?  Positive values indicate some minimum exists...
            "digs": -1, # How many digs must the player perform to complete this wave?  Positive values indicate some minimum exists...

            "enemy-kills": -1, # How many enemies does the player need to kill?  Positive values indicate a requirement of some sort.
            "enemy-kills:tile-fill": -1, # Kill n enemies by trapping them
            "enemy-kills:planar-shift": -1, # Kill n enemies by squishing them
            "enemy-kills:out-of-bounds": -1, #               by making them fall off the level
            "enemy-kills:deadly-tile": -1, #                 by making them run into spikes, or a similarly deadly tile
            "enemy-kills:bomb": -1 #                        by bombing them
        }


        # Wave limits (if you exceed a set limit, you fail the wave)
        self.wave_limits = {
            "survive": 100, # You cannot "exceed" this limit.  It doesn't apply as a limit...

            "gold": -1, # The most gold the player is allowed to collect.  Non-negative values indicate a limit exists.
            "digs": -1, # The most digs the player is allowed to perform.  Non-negative values indicate a limit exists.

            "enemy-kills": -1, # How many enemies is the player allowed to kill?  Non-negative... etc.
            "enemy-kills:tile-fill": -1, # Kill n enemies by trapping them
            "enemy-kills:planar-shift": -1, # Kill n enemies by squishing them
            "enemy-kills:out-of-bounds": -1, #               by making them fall off the level
            "enemy-kills:deadly-tile": -1, #                 by making them run into spikes, or a similarly deadly tile
            "enemy-kills:bomb": -1 #                        by bombing them
        }


        # Keep a "cached" list of which wave requirements actually have requirements (i.e. > 0)
        self.active_wave_requirement_names = []

        # A similar "cached" list of which wave allowances have been set
        self.active_wave_allowance_names = []

        # Also keep a "cached" list of which wave limits actually have a limit (i.e. > -1)
        self.active_wave_limit_names = []


        log2( "new wave" )


    # Set a given wave param
    def set_wave_param(self, param, value):

        # Validate
        if (param in self.wave_params):

            self.wave_params[param] = value

        else:

            log2( "Warning:  Wave param '%s' does not exist!" % param )


    # Set multiple params using a hash
    def set_wave_params(self, params):

        # Loop params
        for key in params:

            # Set param
            self.set_wave_param(key, params[key])


    # Get a wave param
    def get_wave_param(self, param):

        # Validate
        if (param in self.wave_params):

            return self.wave_params[param]

        else:

            log2( "Warning:  Wave param '%s' does not exist!" % param )
            return 0


    # Get the name of each wave param
    def get_wave_param_names(self):

        return self.wave_params.keys()


    # Set a wave allowance (e.g. bombs allowed)
    def set_wave_allowance(self, param, amount):

        # Validate
        if (param in self.wave_allowances):

            # Save
            self.wave_allowances[param] = int(amount)

            # Now let's build / rebuild the list of "active" allowance names
            self.active_wave_allowance_names = []

            # Loop
            for name in self.wave_allowances:

                # Special case:  I don't want to render bomb allowances.  I handle that in the
                # HUD at the top of the screen...
                if (name == "bombs"):

                    pass

                # Standard cases
                else:

                    # If we have a non-negative allowance, then we add it
                    if (self.wave_allowances[name] >= 0):

                        # Cache, of sorts
                        self.active_wave_allowance_names.append(name)

                    # Also, if we have "-1" bombs, then we have "infinite" bombs
                    elif ( (name == "bombs") and (self.wave_allowances[name] == -1) ):

                        # Special case, hack
                        self.active_wave_allowance_names.append(name)


    # Set multiple wave allowances simultaneously, using a hash
    def set_wave_allowances(self, params):

        # Loop params
        for key in params:

            # Set allowance
            self.set_wave_allowance(key, params[key])


    # Get a wave allowance (e.g. digs allowed)
    def get_wave_allowance(self, param):

        # Validate
        if (param in self.wave_allowances):

            return self.wave_allowances[param]

        else:

            log2( "Warning:  Wave allowance '%s' does not exist!" % param )
            return 0


    # Increment a given wave counter (numerics only)
    def increment_wave_counter(self, param, amount):

        # Validate
        if (param in self.wave_counters):

            # Go ahead and mark the tracker data as "dirty"
            self.dirty = True


            # Try to increment, assuming it's numeric
            try:
                self.wave_counters[param] += amount

            # Something went wrong...
            except:
                log2( "Warning:  Could not increment non-numeric wave counter '%s!'" % param )

        else:

            log2( "Warning: Wave counter '%s' does not exist!" % param )


    # Get the current value of a wave counter
    def get_wave_counter(self, param):

        # Validate
        if (param in self.wave_counters):

            return self.wave_counters[param]

        else:

            log2( "Warning:  Wave counter '%s' does not exist!" % param )
            return 0


    # Set a wave requirement
    def set_wave_requirement(self, param, amount):

        # Validate key
        if (param in self.wave_requirements):

            # Set now
            self.wave_requirements[param] = amount

            # At this point, let's regenerate our list of active wave requirements.  Kind of excessive ot do it all, maybe.
            self.active_wave_requirement_names = []

            # Loop
            for name in self.wave_requirements:

                # If we have a positive requirement, then we add it
                if (self.wave_requirements[name] > 0):

                    # CAche, of sorts
                    self.active_wave_requirement_names.append(name)


        else:
            log2( "Warning:  Wave requirement '%s' does not exist!" % param )


    # Set multiple wave requirements simultaneously, using a hash
    def set_wave_requirements(self, params):

        # Loop requirements
        for key in params:

            # Set requirement
            self.set_wave_requirement(key, params[key])


    # Get a wave requirement
    def get_wave_requirement(self, param):

        # Validate
        if (param in self.wave_requirements):

            return self.wave_requirements[param]

        else:

            log2( "Warning:  Wave requirement '%s' does not exist!" % param )
            return -1


    # Set a wave limit
    def set_wave_limit(self, param, amount):

        # Validate key
        if (param in self.wave_limits):

            # Set limit
            self.wave_limits[param] = amount

            # Track this in our list of active wave limits
            self.active_wave_limit_names = []

            # Loop
            for name in self.wave_limits:

                # If we have a non-negative limit, then the limit exists / is active
                if (self.wave_limits[name] >= 0):

                    # CAche
                    self.active_wave_limit_names.append(name)


        else:
            log2( "Warning:  Wave limit '%s' does not exist!" )


    # Set multiple wave limits simultaneously, using a hash
    def set_wave_limits(self, params):

        # Loop limits
        for key in params:

            # Set limit
            self.set_wave_limit(key, params[key])


    # Get a wave limit
    def get_wave_limit(self, param):

        # Validate
        if (param in self.wave_limits):

            return self.wave_limits[param]

        else:

            log2( "Warning:  Wave limit '%s' does not exist!" % param )
            return -1


    # Get the active wave requirements.  (Ignore those requirements that are 0 or negative.)
    def get_active_wave_requirement_names(self):

        return self.active_wave_requirement_names


    # Get all active wave allowances
    def get_active_wave_allowance_names(self):

        return self.active_wave_allowance_names


    # Get the active wave limits.
    def get_active_wave_limit_names(self):

        return self.active_wave_limit_names


    # According to current wave parameters, calculate how many "free" bombs the player has remaining...
    def count_free_bombs_remaining(self):

        # Currently I've decided to make bombs "free" on all puzzle/challenge maps,
        # but I must specify a wave allowance that indicates how many bombm (-1 for infinite) the player can use.
        """
        # If bombs aren't "free," then it's 0...
        if ( False and self.get_wave_param("bombs-free") != 1 ):

            # No free rides
            return 0

        # Otherwise, it depends on how many we're allowed to use on this map versus how many we've already used...
        else:
        """
        if (1):

            # If we can use infinite bombs, then we essentially have "infinite" free bombs remaining.
            if ( self.get_wave_allowance("bombs") == -1 ):

                # Arbitrary
                return 1000

            elif ( self.get_wave_allowance("bombs") == 0 ):

                return 0

            # Otherwise, it's a calculation of used versus allowed
            else:

                # Difference
                return ( self.get_wave_allowance("bombs") - self.get_wave_counter("bombs") )


    # Check to see if the current wave has been completed.
    def is_wave_complete(self):

        # We only check for wave completion if we have set some sort of requirement
        # for this wave.  Let's begin by fetching those requirements.
        names = self.get_active_wave_requirement_names()

        # Validate that we have some requirement...
        if ( len(names) > 0 ):

            # Let's check each requirement
            for name in names:

                # Compare the counter against the requirement.  If we haven't met the requirement,
                # then we haven't completed the wave.
                if ( self.get_wave_counter(name) < self.get_wave_requirement(name) ):

                    # Not done yet!
                    return False


            # If we have at least one requirement and we have met each requirement, then
            # we have completed the wave.
            return True


        # We cannot complete this wave because it does not have a single active requirement.
        else:

            return False


    # Check to see if we have failed a wave by exceeding a wave limit.
    def is_wave_failed(self):

        # We only check the limits that have a non-negative value.  Begin by fetching
        # the list of active limits.
        names = self.get_active_wave_limit_names()

        # Validate that some limit exists...
        if ( len(names) > 0 ):

            # Check each limit
            for name in names:

                #print "%s:  %d / %d" % (name, self.get_wave_counter(name), self.get_wave_limit(name))

                # If the counter exceeds the limit, then we fail the wave.
                if ( self.get_wave_counter(name) > self.get_wave_limit(name) ):

                    # Failure
                    return True


            # If we have not exceeded any active limit, then we have not failed this wave
            return False


        # If no limit exists, then we cannot fail a wave by exceeding a limit
        else:

            return False

