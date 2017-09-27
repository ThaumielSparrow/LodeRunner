import sys

from code.tools.eventqueue import EventQueue

from code.utils.common import log, log2, logn

class TimerControllerEvent:

    def __init__(self, interval, uses, on_complete, params):

        # Has this timer expired?  When it expires, we get rid of it...
        self.expired = False


        # How long until the next event?
        self.interval = interval

        # How close are we to reaching the next firing time?
        self.countdown = self.interval

        # If repeating, will it have a cap?
        self.uses = uses

        # How many times has this event fired?
        self.use_count = 0


        # What to do at the event horizon?
        self.on_complete = on_complete

        # This timer event may have certain parameters, such as the title of a script that would execute.
        self.params = params


    # Expire the timer
    def expire(self):

        self.expired = True


    # Check expiration status
    def is_expired(self):

        return self.expired


    # Increment the time remaining
    def increment(self, interval):

        # Increase countdown time
        self.countdown += interval


    # Get time remaining, in seconds.  Precision determines how many decimal points to round to...
    def get_time_remaining_in_seconds(self, precision = 1):

        # Raw time remaining
        raw_seconds = self.countdown / 60.0 # hard-coded

        # Round
        return round(raw_seconds, precision)


    def process(self):

        # Events that result from timer ringing
        results = EventQueue()


        # Check countdown
        if (self.countdown > 0):

            # Count down!
            self.countdown -= 1


        # Time to fire the event
        else:

            # Fire an event?
            if (self.on_complete != ""):

                results.add(
                    action = self.on_complete,
                    params = self.params
                )

                log2( "Timer '%s' firing event '%s'" % (self.on_complete, self.on_complete) )


            # Count uses, if it matters
            if (self.uses >= 0):

                self.use_count += 1

                # Reached the limit?
                if (self.use_count >= self.uses):

                    # Kill timer
                    self.expire()

                # Otherwise, reset interval countdown...
                else:

                    # We have at least one more use left
                    self.countdown = self.interval


            # If we have infinite uses, just reset the countdown...
            elif (self.uses == -1):

                # Set up for another countdown
                self.countdown = self.interval


        # Return events
        return results


class TimerController:

    def __init__(self):

        # Track any event attached to this controller, hashed by timer name
        self.events = {}

        # We can choose to delay all timer processing by a given framecount
        self.delay_interval = 0


    # Basic configuration
    def configure(self, options):

        if ( "delay" in options ):
            self.delay_interval = int( options["delay"] )


        # For chaining
        return self


    # Enact a delay
    def delay(self, interval):

        self.delay_interval = interval


    # Check if a given timer id exists
    def has_timer_with_name(self, name):

        # Simple check
        return (name in self.events)


    # Remove a timer, by name
    def remove_timer_by_name(self, name):

        # Validate
        if (name in self.events):

            # Goodbye, my love!
            self.events.pop(name)


    # Fetch a timer with a given name
    def get_timer_by_name(self, name):

        # Exists?
        if (name in self.events):

            # Yep
            return self.events[name]

        # Nope
        else:

            return None


    # Get the names of all known timers
    def get_timer_names(self):

        return self.events.keys()


    # Convenience function
    def add_singular_event_with_name(self, name, interval = 0, on_complete = "", params = {}):

        # Let's just create a "repeating" event that fires one single time...
        self.add_repeating_event_with_name(name = name, interval = interval, uses = 1, on_complete = on_complete, params = params)


    # These events can fire any number of times (or -1 for infinitely)
    def add_repeating_event_with_name(self, name, interval = 0, uses = -1, on_complete = "", params = {}):

        # If we already have a timer by this id, we will remove it.
        if ( self.has_timer_with_name(name) ):

            # Remove that timer; there can only be one by this name
            self.remove_timer_by_name(name)


        log2( "Creating timer '%s' with interval '%d'" % (name, interval) )


        # Add a timer event that fires N times.  This can technically be used to create "singular" timers.
        # Hash by timer event name.
        self.events[name] = TimerControllerEvent(
            interval = interval,
            uses = uses,
            on_complete = on_complete,
            params = params
        )


    # Process all timed events.
    def process(self):

        logn( "timer", "process timer ", self )

        # Events that result from firing timers...
        results = EventQueue()


        # Skip / pause all timers during any delay period
        if (self.delay_interval > 0):

            # Tick, tock!
            self.delay_interval -= 1

        # Otherwise, process each timer normally
        else:

            # Loop through the keys of our events...
            timer_names = self.get_timer_names()
            logn( "timer", "timers:  ", timer_names )

            # Loop
            i = 0
            while ( i < len(timer_names) ):
                logn( "timer index", "i = %s" % i )

                # Process each timer object
                results.append(
                    self.events[ timer_names[i] ].process()
                )

                # If the timer has expired, we will remove it...
                if ( self.events[ timer_names[i] ].is_expired() ):

                    # We'll remove the given timer.  We won't alter the list we're iterating through currently, though; it's transient.
                    self.remove_timer_by_name( timer_names[i] ) # We can do this immediately because we're looping through the timer names, not the timer hash itself.


                # Loop
                i += 1


        # Return events
        return results
