from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, xml_encode, xml_decode

class IntervalController:

    def __init__(self, interval = 0.0, target = 1.0, speed_in = 0.045, speed_out = 0.065, integer_based = False):

        # Is this controller strictly integer based?
        self.integer_based = integer_based


        # Current alpha value
        self.interval = interval

        # Where we are fading to
        self.target = target


        # Fade in rate
        self.speed_in = speed_in

        # Fade out rate
        self.speed_out = speed_out


        # We can choose to enforce a delay before processing the interval/target
        self.interval_delay = 0


        # We can choose to lock the controller, preventing state changes
        self.lock_count = 0


        # Perhaps we'll set an accelerator of some sort for this interval controller.
        # By default, it will just return the default speeds.
        self.f_accelerator = lambda interval, dy: interval


        # Oncomplete events
        self.on_arrival = None
        self.on_dismissal = None

        self.on_complete = ""


    # Configuration
    def configure(self, options):

        if ( "interval" in options ):

            self.set_interval(
                self.parse_numeric_value( options["interval"] )
            )

        if ( "target" in options ):

            self.set_target(
                self.parse_numeric_value( options["target"] )
            )

        if ( "speed-in" in options ):

            self.set_speed_in(
                float( options["speed-in"] )
            )

        if ( "speed-out" in options ):

            self.set_speed_out(
                float( options["speed-out"] )
            )

        if ( "delay" in options ):

            self.delay(
                int( options["delay"] )
            )


        if ( "on-complete" in options ):

            self.on_complete = options["on-complete"]


        if ( "accelerator" in options ):

            self.f_accelerator = options["accelerator"]


        # For chaining
        return self


    # Convenience for parsing a string into a numeric value.
    # The return value can be a float or an integer (depending on which system this controller uses).
    def parse_numeric_value(self, value):

        # controllers that manage positional rendering (slides, etc.) will use an integer-based system (you can't render at pixel 1.5, after all ;)
        if (self.integer_based):

            return int(value)

        # Most other controllers (alpha, notably) will use floats
        else:

            return float(value)


    def get_state(self):

        # Set up a quick bare-bones node
        node = XMLParser().create_node_from_xml("""
            <interval-controller />
        """)

        # Track important widget state settings in the widget node
        node.get_first_node_by_tag("interval-controller").set_attributes({
            "lock-count": xml_encode( "%d" % self.lock_count ),
            "interval": xml_encode( "%s" % self.get_interval() ),
            "target": xml_encode( "%s" % self.get_target() ),
            "on-complete": xml_encode( self.on_complete if (self.on_complete != None) else "" )
        })

        return node.get_first_node_by_tag("interval-controller")


    def set_state(self, node):

        # Validate it's the node we need
        if (node.tag_type == "interval-controller"):

            # Update lock count
            self.lock_count = int( node.get_attribute("lock-count") )

            # Set interval and target for this format of controller
            self.interval = self.parse_numeric_value( node.get_attribute("interval") )
            self.target = self.parse_numeric_value( node.get_attribute("target") )

            # Restore on-complete event
            self.on_complete = node.get_attribute("on-complete")


    # Lock controller
    def lock(self):

        self.lock_count += 1


    # Unlock
    def unlock(self):

        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            self.lock_count = 0


    # Lock status
    def is_locked(self):

        return (self.lock_count > 0)


    def get_interval(self):

        return self.parse_numeric_value(self.interval)


    def set_interval(self, interval):

        if ( not self.is_locked() ):

            self.interval = interval


    def get_target(self):

        return self.target


    def set_target(self, target):

        if ( not self.is_locked() ):

            self.target = target


    def set_speed_in(self, speed_in):

        if ( not self.is_locked() ):

            self.speed_in = speed_in


    def get_speed_in(self):

        return self.speed_in


    def set_speed_out(self, speed_out):

        if ( not self.is_locked() ):

            self.speed_out = speed_out


    def get_speed_out(self):

        return self.speed_out


    # Specify a delay
    def delay(self, frames):

        if ( not self.is_locked() ):

            self.interval_delay = frames


    # Call it in
    def summon(self, target = 1.0, on_complete = ""):

        if ( not self.is_locked() ):

            # Update target
            self.set_target(target)

            # Track optional callback
            self.on_complete = on_complete


    # Goodbye
    def dismiss(self, target = 0.0, on_complete = ""):

        if ( not self.is_locked() ):

            # Update target
            self.set_target(target)

            # Track optional callback
            self.on_complete = on_complete


    # Instant goodbye
    def blackout(self, on_complete = ""):

        if ( not self.is_locked() ):

            # All the way gone
            self.set_interval(0)

            # Chain of command
            self.dismiss(
                on_complete = on_complete
            )


    # Is currently visible, at all?
    def is_visible(self):

        return ( self.get_interval() > 0 )


    # Process fade logic, events if/a
    def process(self):

        # Events that result from processing
        results = EventQueue()


        if ( not self.is_locked() ):

            # Adhere to delay
            if (self.interval_delay > 0):

                # Wait
                self.interval_delay -= 1

            else:

                # Process interval
                if (self.interval < self.target):

                    self.interval += self.f_accelerator(self.speed_in, dy = self.interval)

                    # Don't overshoot
                    if (self.interval > self.target):

                        self.interval = self.target

                        # Callback?
                        if ( (self.on_complete != None) and (self.on_complete != "") ):

                            results.add(
                                action = self.on_complete
                            )

                            # Reset tracker
                            self.on_complete = ""



                elif (self.interval > self.target):

                    self.interval -= self.f_accelerator(self.speed_out, dy = self.interval)

                    # Don't overshoot
                    if (self.interval < self.target):

                        self.interval = self.target

                        # Callback?
                        if ( (self.on_complete != None) and (self.on_complete != "") ):

                            results.add(
                                action = self.on_complete
                            )

                            # Reset tracker
                            self.on_complete = ""

                else:

                    if ( self.on_complete != "" ):

                        results.add(
                            action = self.on_complete
                        )

                        # Reset tracker
                        self.on_complete = ""


        # Return events
        return results
