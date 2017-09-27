class Trap:

    def __init__(self, timer = 0, delay = 0, occupants = 0, fill_pattern = 0):

        # Time left on trap
        self.timer = timer

        # Delay (?)
        self.delay = delay

        # Number of occupants (0 or 1)
        self.occupants = occupants

        # Fill pattern; we use randomized fill patterns to keep things from looking
        # weird and monotonous.
        self.fill_pattern = fill_pattern


    # Get timer
    def get_timer(self):

        return self.timer


    # Set timer
    def set_timer(self, timer):

        self.timer = timer


    # Increment timer
    def increment_timer(self, amount):

        self.timer += amount


    # Get delay (?)
    def get_delay(self):

        return self.delay


    # Set delay (?)
    def set_delay(self, delay):

        self.delay = delay


    # Increment delay (?)
    def increment_delay(self, amount):

        self.delay += amount


    # Get occupant count
    def get_occupants(self):

        return self.occupants


    # Set occupant count
    def set_occupants(self, occupants):

        self.occupants = occupants


    # Get fill pattern
    def get_fill_pattern(self):

        return self.fill_pattern
