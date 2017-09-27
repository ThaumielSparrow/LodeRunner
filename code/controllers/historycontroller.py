class HistoryController:

    def __init__(self):

        # Track history trace
        self.stack = []

        # Snapshots of widget states, tracked by id
        self.snapshots = {}


        # Lock count
        self.lock_count = 0


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


    # Add new history item
    def push(self, item):

        # Only if not locked
        if ( not self.is_locked() ):

            self.stack.append(item)


    # Remove top history item
    def pop(self):

        # Only if not locked
        if ( not self.is_locked() ):

            # Sanity
            if ( len(self.stack) > 0 ):

                return self.stack.pop()

        return None


    def save_snapshot_with_id(self, snapshot, snapshot_id):

        self.snapshots[snapshot_id] = snapshot

        #f = open( os.path.join("debug", "snapshots.txt"), "a" )
        #f.write( "%s\n%s\n\n\n" % (snapshot_id, snapshot.compile_xml_string() ) )
        #f.close()


    def load_snapshot_by_id(self, snapshot_id):

        if (snapshot_id in self.snapshots):

            return self.snapshots[snapshot_id]#.pop(snapshot_id)

        else:

            return None


    def clear_snapshots(self):

        self.snapshots.clear()


    # Retrieve history
    def get_trace(self):

        return self.stack


