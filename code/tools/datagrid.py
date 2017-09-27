import sys

from code.utils.common import logn

class DataGrid:

    def __init__(self, width = 0, height = 0):
        self.debug = False

        # Track data in a 2d array
        self.data = []

        # Set width, height
        self.resize(width, height)


    # Get grid width
    def get_width(self):

        # No data?
        if ( len(self.data) == 0 ):

            # No width
            return 0

        else:

            # All rows have equal width at all times
            return len(self.data[0])


    # Get grid height
    def get_height(self):

        return len(self.data)


    # Add a new row.
    # -1 indicates to append at the end (default).
    def add_row(self, default_value, pos = -1):

        # No row previously exists?
        if ( len(self.data) == 0 ):

            # Add a row with no column data
            self.data.append([])

            # Return the empty row
            return self.data[-1]

        else:

            # Create array of equal width
            row = []

            for i in range( 0, len(self.data[0]) ):

                # Use given default value
                row.append(default_value)


            # Add row to end?
            if (pos < 0):

                self.data.append(row)

            # No; insert it somewhere, probably at the start...
            else:
                self.data.insert(pos, row)


            # Return new row
            return self.data[pos]


    # Clear the grid
    def clear(self):

        # Just a convenience function, really...
        self.resize(0, 0)


    # Resize the grid
    def resize(self, width, height, default_value = 0):

        # Shorter?
        if ( height < self.get_height() ):

            # Remove excess
            while ( self.get_height() > height ):

                # Trim
                self.data.pop()

        # Taller?
        elif ( height > self.get_height() ):

            # Add new rows
            while ( self.get_height() < height ):

                # Add
                self.add_row(default_value)


        # Thinner?
        if ( width < self.get_width() ):

            # Loop rows
            for y in range( 0, self.get_height() ):

                # Remove excess
                while ( len(self.data[y]) > width ):

                    # Trim
                    self.data[y].pop()

        # Wider?
        elif ( width > self.get_width() ):

            # Loop rows
            for y in range( 0, self.get_height() ):

                # Add columns
                while ( len(self.data[y]) < width ):

                    # Add new column
                    self.data[y].append(default_value)


    # "Pad" columns or rows into the grid
    def pad(self, px, py, default_value = 0):

        # Add rows first
        for i in range(0, py):

            # Insert new row at the top
            self.add_row(default_value, pos = 0)


        # Add new columns
        for y in range( 0, self.get_height() ):

            # Insert new data
            for j in range(0, px):

                self.data[y].insert(0, default_value)


    def read2(self, x, y):
        return self.data[y][x]


    # Get recorded value at a given position on the grid
    def read(self, x, y, default_value = 0):

        # Sanity
        if ( (x >= 0) and (y >= 0) ):

            # Validate
            if ( (x < self.get_width()) and (y < self.get_height()) ):

                # Return value
                return self.data[y][x]

            else:

                return default_value

        else:

            return default_value


    # Set recorded value at a given position on the grid.
    # We will use default_value when resizing grid (if we write "out of bounds").
    def write(self, x, y, value, default_value = 0):

        # Sanity
        if (x >= 0 and y >= 0):

            # Should we add more rows?
            if ( y >= self.get_height() ):

                # Fit to height
                self.resize( self.get_width(), y + 1, default_value )


            # Do we need to add columns?
            if ( x >= self.get_width() ):

                # Fit to width
                self.resize( x + 1, self.get_height(), default_value )


            # Write to 2d array
            self.data[y][x] = value


        if (self.debug):
            for qy in range( 0, self.get_height() ):
                for qx in range( 0, self.get_width() ):
                    if ( self.data[qy][qx] == 0 ):
                        logn( "datagrid", "Set %d, %d = %s" % (x, y, value) )
                        logn( "datagrid", "Aborting.  Unsure why, previous debug code..." )
                        sys.exit()


    # Get an entire row of data
    def get_row_at_index(self, index):

        # Sanity
        if ( index < len(self.data) ):

            return self.data[index]

        return []

