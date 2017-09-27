import random

class TextBlaster:

    def __init__(self, text, delay_max = 1, fade_speed = 0.05, max_width = -1, letters_per = 1, align = "left", effect = None, duration = None, lag = None, repeat_threshold = None):

        self.text = text.decode("utf-8")

        self.lines = []

        self.max_width = max_width

        self.align = align


        # Track the fade-in value of each letter
        self.letter_fade_values = []
        self.letter_fade_delays = []

        for i in range(0, len(text)):

            self.letter_fade_values.append(0.0)
            self.letter_fade_delays.append(0)


        # Put a collection together of all possible list indices.
        # We'll randomly draw from this collection to start a new
        # letter fade-in.
        self.remaining_letters = []

        for i in range(0, len(text)):
            self.remaining_letters.append(i)


        # Track the delay between each letter's fade-in
        self.delay = delay_max

        # We'll wait this long between each letter...
        self.delay_max = delay_max


        # What kind of effect will we use?
        self.effect = effect


        # How many letters per delay?
        self.letters_per = letters_per


        # How quickly will letters fade in?
        self.fade_speed = fade_speed

        if (duration):

            self.fade_speed = float(1) / float(duration)


        # How quickly will they fade out?
        self.fade_speed_out = self.fade_speed * 4


        # How long will each batch of letters "lag behind" before starting to fade in as well?
        self.lag = lag


        # For longer lines, we might want to "hurry up" the thing, while preserving the original "letters_per"
        # on reasonably-lengthed lines.  This will define that threshold of repeats...
        self.repeat_threshold = repeat_threshold


        # Line-by-line effects typically travel one line at a time.  Sometimes, though, we'll want to start on the
        # second line before we finish processing the first line...
        self.line_overlap_ratio = 0.5


        # What's the fade direction?
        self.behavior = "fade-in"

    # Query for effect completion
    def is_complete(self):

        result = True

        if (self.behavior == "fade-in"):

            # All letters must have concluded their fade-in...
            for i in range(0, len(self.letter_fade_values)):

                if (self.letter_fade_values[i] < 1.0):
                    result = False

        elif (self.behavior == "fade-out"):

            # All letters must have faded out...
            for i in range(0, len(self.letter_fade_values)):

                if (self.letter_fade_values[i] > 0.0):
                    result = False

        return result

    def set_behavior(self, behavior):

        self.behavior = behavior


        # Irregardless of new behavior, always reset letter pool...
        self.remaining_letters = []

        for i in range(0, len(self.text)):
            self.remaining_letters.append(i)


        # Reset delay
        self.delay = self.delay_max


        # Reset all fade values...
        if (behavior == "fade-in"):

            #for i in range(0, len(self.letter_fade_values)):
            #    self.letter_fade_values
            pass

    def get_letter_fade_values(self):

        return self.letter_fade_values

    def setup_initial_fade_values(self, text_renderer):

        # Get the wordwrapped lines for this text blaster
        self.lines = text_renderer.wordwrap_text(self.text, 0, 0, (225, 225, 225), self.max_width)

        self.activate()

    def activate(self):

        self.behavior = "fade-in"

        if (self.effect == "blaster:line-by-line"):

            # The entirety of the first line should appear before the second line begins appearing, 2 before 3, and so on...
            initial_fade = 0

            # For line overlap calculations, I'll want to keep a trailing record of the previous line's
            # initial fade value...
            previous_initial_fade = 0


            for i in range(0, len(self.lines)):

                # Check for trailing record and apply line overlap, if applicable...
                if (i > 0):

                    # Difference
                    df = (previous_initial_fade - initial_fade)

                    # Increase current initial fade by the appropriate factor, so that line n+1 begins appears before line n fully appears...
                    initial_fade += (self.line_overlap_ratio * df)

                    #print (self.line_overlap_ratio * df)

                # Update trailing record
                previous_initial_fade = initial_fade


                # Get the range of characters on this line of text...
                (a, b) = (self.lines[i]["begin"], self.lines[i]["end"])

                # Place all of the indexes for that range in a list; we'll take 1 * self.letters_per indexes
                # out at random to define the fade-in effect for this line.
                line_letter_indexes = range(a, b)

                # Will we apply a multiple to the "letters_per" rule based on a repeat threshold?
                letters_per_multiple = 1

                if (self.repeat_threshold):

                    letters_per_multiple = max(1, int((b - a) / self.repeat_threshold))


                # For however many characters should appear at a time, find that many characters at random
                # in this line and mark them to start at the currently calculated initial_fade value.
                while ( len(line_letter_indexes) > 0 ):

                    j = 0
                    while ( (j < (letters_per_multiple * self.letters_per)) and ( len(line_letter_indexes) > 0 ) ):

                        # Select a winner!
                        pos = random.randint(0, len(line_letter_indexes) - 1)

                        # Grab that character index
                        index = line_letter_indexes.pop(pos)

                        # If we're reactivating a partially-complete fade, we should ignore already-showing letters...
                        if (self.letter_fade_values[index] < 1):

                            # Mark the fade value for that character accordingly...
                            self.letter_fade_values[index] = initial_fade

                            # Looping variable
                            j += 1

                    # We have set "letters_per" characters to fade in first.  The next batch of characters
                    # must wait for "lag" frames before beginning to fade in as well...
                    initial_fade -= (self.lag * self.fade_speed)


        elif (effect == "blaster"):

            pass


    # Dismiss however many letters are currently showing (from 0 to all)
    def dismiss(self):

        # Set the thing to fade out
        self.behavior = "fade-out"


        if (self.effect == "blaster:line-by-line"):

            if ( len(self.letter_fade_values) > 0 ):

                # If none of the letters has reached full visibility, we an easily reverse the process
                if ( max(self.letter_fade_values) < 1.0 ):

                    # Make sure none of the fades employs any delay
                    for i in range(0, len(self.letter_fade_values)):
                        self.letter_fade_delays[i] = 0


                # If the effect has partially or fully completed, we need to basically do a reverse calculation...
                else:

                    # The entirety of the first line should disappear before the second line begins disappearing, 2 before 3, and so on...
                    initial_delay = 0

                    # For line overlap calculations, I'll want to keep a trailing record of the previous line's
                    # initial delay value...
                    previous_initial_delay = 0


                    for i in range(0, len(self.lines)):

                        # Check for trailing record and apply line overlap, if applicable...
                        if (i > 0):

                            # Difference
                            df = (initial_delay - previous_initial_delay) # Reversed

                            # Increase current initial fade by the appropriate factor, so that line n+1 begins appears before line n fully appears...
                            initial_delay -= (self.line_overlap_ratio * df)

                            #print (self.line_overlap_ratio * df)

                        # Update trailing record
                        previous_initial_delay = initial_delay


                        # Get the range of characters on this line of text...
                        (a, b) = (self.lines[i]["begin"], self.lines[i]["end"])

                        # Place all of the indexes for that range in a list; we'll take 1 * self.letters_per indexes
                        # out at random to define the fade-in effect for this line.
                        line_letter_indexes = range(a, b)

                        # Will we apply a multiple to the "letters_per" rule based on a repeat threshold?
                        letters_per_multiple = 1

                        if (self.repeat_threshold):

                            letters_per_multiple = max(1, int((b - a) / self.repeat_threshold))


                        # For however many characters should disappear at a time, find that many characters at random
                        # in this line and mark them to start at the currently calculated initial_fade value.
                        while ( len(line_letter_indexes) > 0 ):

                            j = 0
                            while ( (j < (letters_per_multiple * self.letters_per)) and ( len(line_letter_indexes) > 0 ) ):

                                # Select a winner!
                                pos = random.randint(0, len(line_letter_indexes) - 1)

                                # Grab that character index
                                index = line_letter_indexes.pop(pos)

                                # Now, here's the thing . If this letter is already faded away, we don't care about it.  Let's keep looking...
                                if (self.letter_fade_values[index] > 0):

                                    # Mark the fade value for that character accordingly...
                                    self.letter_fade_delays[index] = initial_delay

                                    # Looping variable
                                    j += 1

                            # We have set "letters_per" characters to fade in first.  The next batch of characters
                            # must wait for "lag" frames before beginning to fade out as well...
                            initial_delay += (self.lag * self.fade_speed_out)


    def linger(self):

        #self.process()

        return ( max(self.letter_fade_values) > 0 )


    def reset(self):

        if (self.behavior == "fade-in"):

            if (self.effect == "blaster:line-by-line"):

                for i in range(0, len(self.letter_fade_values)):

                    self.letter_fade_values[i] = 0

                self.activate()


    def process(self):

        # Always continue the fade-in on letters that are showing
        if (self.behavior == "fade-in"):

            if (self.effect == "blaster:line-by-line"):

                for i in range(0, len(self.letter_fade_values)):

                    if (self.letter_fade_values[i] < 1):

                        self.letter_fade_values[i] += self.fade_speed

                        # 1.0 is the limit... 100%
                        if (self.letter_fade_values[i] > 1.0):
                            self.letter_fade_values[i] = 1.0

        # Fade away instead?
        elif (self.behavior == "fade-out"):

            if (self.effect == "blaster:line-by-line"):

                for i in range(0, len(self.letter_fade_values)):

                    if (self.letter_fade_values[i] > 0):

                        if (self.letter_fade_delays[i] > 0):
                            self.letter_fade_delays[i] -= self.fade_speed_out

                        else:
                            self.letter_fade_values[i] -= self.fade_speed_out

                            # Don't overshoot
                            if (self.letter_fade_values[i] < 0):
                                self.letter_fade_values[i] = 0

    def process2(self):

        # If we're delaying, don't pick any new letter...
        if (self.delay > 0):

            self.delay -= 1

            if (self.delay <= 0):

                # Reset delay
                self.delay = self.delay_max

                # Start a new letter, if any remains...
                for i in range(0, self.letters_per):

                    if (len(self.remaining_letters) > 0):

                        index = random.randint(0, len(self.remaining_letters) - 1)


                        # Start the fade on the appropriate letter... don't affect letters that have already started a fade-in...
                        if (self.behavior == "fade-in"):
                            self.letter_fade_values[ self.remaining_letters[index] ] = max(0.01, self.letter_fade_values[ self.remaining_letters[index] ])

                        elif (self.behavior == "fade-out"):
                            self.letter_fade_values[ self.remaining_letters[index] ] = min( (0.99), self.letter_fade_values[ self.remaining_letters[index] ])


                        # Remove that letter's index from the pool of remaining unshown letters
                        self.remaining_letters.pop(index)

        # Always continue the fade-in on letters that are showing
        if (self.behavior == "fade-in"):

            for i in range(0, len(self.letter_fade_values)):

                # Has the fade started?  If so, we'll continue it...
                if (self.letter_fade_values[i] > 0):

                    self.letter_fade_values[i] += self.fade_speed

                    # 1.0 is the limit... 100%
                    if (self.letter_fade_values[i] > 1.0):
                        self.letter_fade_values[i] = 1.0

        elif (self.behavior == "fade-out"):

            for i in range(0, len(self.letter_fade_values)):

                if (self.letter_fade_values[i] < 1.0):

                    self.letter_fade_values[i] -= self.fade_speed

                    # Don't overshoot
                    if (self.letter_fade_values[i] < 0):
                        self.letter_fade_values[i] = 0

    def render(self, text_renderer, x, y, color):

        self.process()

        height_used = text_renderer.render_with_wrap(self.text, x, y, color, max_width = self.max_width, align = self.align, letter_fade_percentages = self.letter_fade_values)
        #text_renderer.render(self.text, x, y, color, p_max_width = self.max_width, auto_wrap = True, letter_fade_percentages = self.letter_fade_values)

        return height_used
