import time

class NetworkRegisteredMessage:

    def __init__(self, message):

        # Contents of the packet
        self.message = message


        # Remember the last time (be it the first attempt or a subsequent retry) that we attempted to send this registered message
        self.last_send_time = time.time() # timeout base


        # How long will we wait before retrying?  (In seconds.)
        self.timeout = 5.0 # In seconds

        # How many retries will we allow before dropping the connection (timeout)?
        self.retries = 0


        # What kind of lock, if any, will we set on the network controller?
        # The game logic loop will check this to help determine how much, if any, game logic to run while the message is pending.
        self.net_lock_type = None # None, local, or global.


    def configure(self, options):

        if ( "message" in options ):
            self.message = options["message"]

        if ( "timeout" in options ):
            self.timeout = float( options["timeout"] )

        if ( "retries" in options ):
            self.retries = int( options["retries"] )

        if ( "net-lock-type" in options ):
            self.net_lock_type = options["net-lock-type"]


        # For chaining
        return self


    # Get the original message we sent
    def get_message(self):

        return self.message


    # Get the type of net lock we applied to this registered message
    def get_net_lock_type(self):

        return self.net_lock_type


    # Check to see if we've exhausted the waiting period
    def is_expired(self):

        return ( (time.time() - self.last_send_time) >= self.timeout )


    # Set the timer back to "now" as we presumably prepare to retry this message
    def reset_last_send_time(self):

        self.last_send_time = time.time()


    # Check to see if we have a retry available
    def can_retry(self):

        # Can we?
        if (self.retries > 0):

            # At least one more time...
            self.retries -= 1

            # Say yes
            return True

        # NOpe...
        else:

            # We'll have to drop this unresponsive player
            return False
