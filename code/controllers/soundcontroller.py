import os
import sys

import pygame

import random

from code.tools.mixer import BGMixer

from code.controllers.intervalcontroller import IntervalController

from code.constants.sound import *


# load_sound just quickly loads a sound file and returns it.
def load_sound(path):

    class NoneSound:
        def play(self): pass

    if ( ( not pygame.mixer ) or ( not pygame.mixer.get_init() ) ):

        log(  "Failed to load sound" )
        return NoneSound()

    sound = None

    try:

        sound = pygame.mixer.Sound(path)

    except pygame.error, message:

        log(  'Cannot load sound:', path )
        raise SystemExit, message

    return sound


class SoundController:

    def __init__(self):

        # Track background music volume
        self.background_volume = 0.75

        # Track background music percentage (music
        # can fade during dialogue, etc.).
        # Defaults to 100%.
        self.background_ratio_controller = IntervalController(
            interval = 1.0,
            target = 1.0,
            speed_in = 0.010,
            speed_out = 0.0075
        )


        # Track sound effect volume
        self.sfx_volume = 0.75


        # Create a background track mixer
        self.mixer = BGMixer(
            self.get_background_volume()
        )


        # Load sound effects
        self.sound_effects = {
            SFX_MENU_CURSOR: [ load_sound( os.path.join("sound", "sfx", "tick%d.wav" % o) ) for o in (1, 2, 3, 4) ],
            SFX_MENU_SELECT: [ load_sound( os.path.join("sound", "sfx", "beep%d.wav" % o) ) for o in (2,) ],
            #SFX_PLAYER_DIG: load_sound("dig3.wav"),
            #SFX_PLAYER_BOMB: load_sound("dig1.wav"),
            #SFX_BOMB_EXPLODE: load_sound("bomb1.wav"),
            #SFX_BOMB_TICK: load_sound("bomb_tick.wav"),
            SFX_PLAYER_GRAB_GOLD: [ load_sound( os.path.join("sound", "sfx", "gold%d.wav" % o) ) for o in (1, 2, 3, 4, 5) ],
            SFX_PLAYER_WALK: [ load_sound( os.path.join("sound", "sfx", "steps%d.wav" % o) ) for o in (1, 2) ],
            SFX_PLAYER_DIG: [ load_sound( os.path.join("sound", "sfx", "dig%d.wav" % o) ) for o in (1, 2, 3, 4) ],

            SFX_NEWS: [ load_sound( os.path.join("sound", "sfx", "news1.wav") ) ],
            SFX_CONFIRM: [ load_sound( os.path.join("sound", "sfx", "query1.wav") ) ],

            SFX_PLACE_BOMB: [ load_sound( os.path.join("sound", "sfx", "placebomb%d.wav" % o) ) for o in (1, 2) ],
            SFX_BOMB_EXPLODE: [ load_sound( os.path.join("sound", "sfx", "explode%d.wav" % o) ) for o in (1, 2) ]
        }


        # Keep a list of queued sound effect types
        self.sfx_queue = []


    # Set background volume
    def set_background_volume(self, volume, permanent = True):

        # Set permanently?
        if (permanent):
            self.background_volume = volume

        # Update the mixer
        self.mixer.set_volume(volume)


    # Set background maximum percentage
    def set_background_ratio(self, ratio):

        # Set new interval target
        self.background_ratio_controller.set_target(ratio)


    # Set sound effects volume
    def set_sfx_volume(self, volume):

        # Set
        self.sfx_volume = volume


    # Get background volume
    def get_background_volume(self):

        # Return
        return self.background_volume


    # Get sound effects volume
    def get_sfx_volume(self):

        # Return
        return self.sfx_volume


    # Queue a sound effect
    def queue_sound(self, index):

        # Add to the queue
        self.sfx_queue.append(index)


    # Process sound-related stuff
    def process(self, universe):

        """ Debug """
        #self.sfx_queue = []
        #return
        """ End Debug """

        # Check to see if the current background track has ended
        if ( not self.mixer.is_playing() ):

            # Loop to next track
            self.mixer.load_next_track()


        # Check to see if the background music ratio has changed
        if ( self.background_ratio_controller.get_interval() != self.background_ratio_controller.get_target() ):

            # Set raw background volume level
            self.set_background_volume(
                self.background_ratio_controller.get_interval() * self.get_background_volume(),
                permanent = False
            )

        # Process background music ratio controller
        self.background_ratio_controller.process()


        # Check for queued sound effects
        while ( len(self.sfx_queue) > 0 ):

            index = self.sfx_queue.pop(0)

            if (index in self.sound_effects):

                sounds = self.sound_effects[index]

                sound = sounds[ random.randint(0, len(sounds) - 1) ]

                # Set volume level for the sound
                sound.set_volume(
                    self.get_sfx_volume()
                )

                sound.play()
                #each.queued_sound = None
