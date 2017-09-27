import sys

from code.utils.common import logn

class EventQueueIter:

    def __init__(self, action, params = {}):

        # What is the event?  (e.g. "do-something")
        self.action = action

        # The event may or may not have any parameter...
        self.params = params


    def get_action(self):

        return self.action


    # Get one specific param
    def get_param(self, param):

        # Validate
        if (param in self.params):

            return self.params[param]

        # Sorry
        else:

            return ""


    # Get all params
    def get_params(self):

        return self.params


    # Set a param
    def set_param(self, param, value):

        self.params[param] = value


    # Set multiple params
    def set_params(self, params_hash):

        for key in params_hash:

            self.set_param(key, params_hash[key])


class EventQueue:

    def __init__(self):

        # Get in line
        self.queue = []


    # Intended as a private method for appending one queue's events to another's
    def _get_queue(self):

        return self.queue


    def has_events(self):

        return ( self.count() > 0 )


    def count(self):

        return len(self.queue)


    # Debug
    def dump(self, minimum = 0):

        for o in self.queue:
            logn( "event dump", "\tAction:  %s" % o.get_action() )

        #if ( self.count() < minimum ):
        #    logn( "error", "invalid count, aborting!" )
        #    sys.exit()


    # Add a single event to the queue
    def add(self, action, params = {}):

        if (action == None):
            logn( "events warning", "no action given" )
            return

        # Add it to the queue
        self.queue.append(
            EventQueueIter(action = action, params = params)
        )


    # Append all of one queue's events to this queue
    def append(self, event_queue):

        if (event_queue):

            self.queue.extend(
                event_queue._get_queue()
            )


    # Alias.
    # Unclear why I previously chose the term "inject" for this.
    def add_event(self, e):

        # Add to list
        self.queue.append(e)

    # Inject a previously-created EventQueueIter into the queue
    def inject_event(self, item):

        self.queue.append(item)


    # Inject given params into each event in the queue
    def inject_params(self, params, overwrite = True):

        # Affect each event
        for event in self.queue:

            # Inject each param, checking for overwrite....
            for key in params:

                # Free slot?
                if ( not ( key in event.get_params() ) ):

                    # Add it
                    event.set_param(key, params[key])

                # We can still go ahead if overwrite is flagged...
                elif (overwrite):

                    # Overwrite it
                    event.set_param(key, params[key])


        # For chaining
        return self


    def fetch(self):

        # Do we have any event in the queue?
        if ( len(self.queue) > 0 ):

            # Return the first in line
            return self.queue.pop(0)

        # Nope!
        else:

            return None


    # Perhaps we only care about a certain kind of event
    def fetch_by_action(self, action):

        i = 0

        while ( i < len(self.queue) ):

            logn( "events", "Action:  %s" % self.queue[i].action )

            if ( self.queue[i].action == action ):

                # Remove this event and return it to the caller
                return self.queue.pop(i)

            else:
                i += 1


        # Couldn't find it, huh?
        return None


    # Clear the entire queue (!)
    def clear(self):

        # Goodbye
        self.queue = []


    # Clear only a certain type of event (possibly useful for preventing duplicates)
    def clear_by_action(self, action):

        i = 0

        while ( i < len(self.queue) ):

            if ( self.queue[i].action == action ):

                # Later, bro
                self.queue.pop(i)

            else:
                i += 1
