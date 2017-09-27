import os
import sys

import pygame.mixer

from code.tools.xml import XMLParser

from code.utils.common import log, log2

from code.constants.sound import CHANNEL_MUSIC


class BGMixer:

    def __init__(self, volume = 1.0):

        self.ready = False


        # Volume level
        self.volume = volume


        # List of track filepaths
        self.tracks = []

        # Load tracklist
        self.load_tracklist()


        self.current_track = 0
        self.channel = pygame.mixer.Channel(CHANNEL_MUSIC)


        # This way, the first track (tracks[0]) will play if load_next_track is ever called)
        self.current_track = -1


    # Set volume level
    def set_volume(self, volume):

        # Set
        self.volume = volume

        # Immediately update pygame.mixer.music volume level
        pygame.mixer.music.set_volume(self.volume * 0.5)


    # Stop playback
    def stop_playback(self):

        # Stop!
        pygame.mixer.music.stop()


    # Load the game's tracklist from an xml file
    def load_tracklist(self):

        """ Debug - Skip loading tracklist if -B flag present """
        if ( "-B" in sys.argv ):
            return
        """ End debug """


        # Check for tracklist file
        if (os.path.exists( os.path.join("sound", "tracklist.xml") )):

            # Load xml into a node
            node = XMLParser().create_node_from_file( os.path.join("sound", "tracklist.xml") ).find_node_by_tag("tracks")

            # Loop track filenames
            for ref_track in node.get_nodes_by_tag("track"):

                # Check for filename tag
                ref_filename = ref_track.find_node_by_tag("filename")

                # Validate
                if (ref_filename):

                    # Get relative path
                    path = os.path.join("sound", ref_filename.innerText)

                    # Validate path
                    if ( os.path.exists(path) ):

                        # Add to tracklist
                        self.tracks.append(path)


    # Check to see if the current background track is still playing
    def is_playing(self):

        # Query busy status
        return pygame.mixer.music.get_busy()


    # Load the next available track (if one exists)
    def load_next_track(self):

        pygame.mixer.music.stop()

        # Validate that we have at least one track
        if ( len(self.tracks) > 0 ):

            # Advance to next track
            self.current_track += 1

            # Check for loop
            if ( self.current_track >= len(self.tracks) ):

                # Back to first track
                self.current_track = 0


            # Load next track file
            pygame.mixer.music.load( self.tracks[self.current_track] )

            # Make sure to explicitly set volume after loading new music
            pygame.mixer.music.set_volume(self.volume * 0.5)

            # Play!
            pygame.mixer.music.play()

