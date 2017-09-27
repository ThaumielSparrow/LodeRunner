from code.render.glfunctions import draw_rounded_rect

from code.extensions.common import UITemplateLoaderExt

from code.controllers.intervalcontroller import IntervalController

from code.tools.xml import XMLParser

from code.utils.common import log, log2, xml_encode, xml_decode

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, DIR_RIGHT
from code.constants.newsfeeder import *

from code.constants.sound import SFX_NEWS # Only sound we need for a Newsfeeder object


class NewsfeederItemEscapeEvent:

    def __init__(self, node):

        # A newsfeeder might have an associated event that should fire if the user
        # hits ESCAPE while it's visible...
        self.event = ""

        # Also, an escape event may have some number of parameters.
        self.params = {}


        self.load(node)


    def load(self, node):

        # Get event type
        self.event = node.get_attribute("on-escape")

        # Check for other parameters to grab...
        for key in node.attributes:

            if (key.startswith("-")):
                self.params[key] = node.get_attribute(key)


    def get_event(self):

        return self.event


    def get_param(self, key):

        # Validate
        if (key in self.params):

            return self.params[key]

        else:
            return None


class Newsfeeder(UITemplateLoaderExt):

    def __init__(self):

        UITemplateLoaderExt.__init__(self)


        # A queue of newsfeeder items (to render)
        self.widgets = []

        # Post queue (configurations waiting to be compiled into widgets)
        self.queue = []


        # Timer that tracks how long to show the current newsfeed item
        self.timer = 0


        # We can optionally delay processing on the newsfeeder for a set number of frames
        self.delay_interval = 0


    # Delay processing
    def delay(self, interval):

        # Add to any existing delay
        self.delay_interval += interval


    # Post a new configuration to the queue
    def post(self, options):

        self.queue.append(options)


    # Compile a given configuration
    def build(self, options, control_center, universe):

        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Totally generic item
        if ( options["type"] == NEWS_GENERIC_ITEM ):

            # Obviously we'll use the generic item ;)
            return self.build_generic_item(options, control_center, universe)

        # Quest updates all use the same template
        elif ( options["type"] in (NEWS_QUEST_NEW, NEWS_QUEST_UPDATE, NEWS_QUEST_FAILED, NEWS_QUEST_COMPLETE) ):

            # Fetch template
            template = self.fetch_xml_template("newsfeeder.quest.new").add_parameters({
                "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
                "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
                "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@title": xml_encode( "%s" % options["title"] ),
                "@quest-name": xml_encode( "%s" % options["quest"].get_name() ),
                "@quest-title": xml_encode( "%s" % options["quest"].get_title() )
            })

            # Compile template
            root = template.compile_node_by_id("feed")

            # Return widget
            return widget_dispatcher.convert_node_to_widget(root, control_center, universe)


        # Saved controls
        elif ( options["type"] == NEWS_GAME_CONTROLS_SAVED ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Saved game
        elif ( options["type"] == NEWS_GAME_SAVE_COMPLETE ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Loaded game
        elif ( options["type"] == NEWS_GAME_LOAD_COMPLETE ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Found a new gamepad (probably just on the first ever launch of the game)
        elif ( options["type"] == NEWS_GAME_GAMEPAD_NEW ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Found the last-used gamepad, by name
        elif ( options["type"] == NEWS_GAME_GAMEPAD_REMEMBERED ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Could not find last-used gamepad, but found an alternative
        elif ( options["type"] == NEWS_GAME_GAMEPAD_DEFAULT ):

            # Build a special newsfeeder item
            return self.build_gamepad_default_item(options, control_center, universe)


        # Could neither find the last-used gamepad nor any alternative
        elif ( options["type"] == NEWS_GAME_GAMEPAD_NOT_FOUND ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Chose a new gamepad to use
        elif ( options["type"] == NEWS_GAME_GAMEPAD_SELECTED ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Reset gamepad controls to default
        elif ( options["type"] == NEWS_GAME_GAMEPAD_RESET ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Reset keyboard controls to default
        elif ( options["type"] == NEWS_GAME_KEYBOARD_RESET ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Note that a new player has joined this game
        elif ( options["type"] == NEWS_NET_PLAYER_CONNECTED ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Note that a player left the game
        elif ( options["type"] == NEWS_NET_PLAYER_DISCONNECTED ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Note that a player timed out
        elif ( options["type"] == NEWS_NET_PLAYER_TIMED_OUT ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Local player has successfully joined a net game
        elif ( options["type"] == NEWS_NET_CLIENT_ONLINE ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Co-op level complete
        elif ( options["type"] == NEWS_NET_LEVEL_COMPLETE ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Co-op level failed
        elif ( options["type"] == NEWS_NET_LEVEL_FAILED ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Character levels up
        elif ( options["type"] == NEWS_CHARACTER_LEVEL_UP ):

            # Build level up notice
            return self.build_character_level_up_item(options, control_center, universe)


        # Item acquired
        elif ( options["type"] == NEWS_ITEM_NEW ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Item lost / given away
        elif ( options["type"] == NEWS_ITEM_LOST ):

            # Build a generic newsfeeder item
            return self.build_generic_item(options, control_center, universe)


        # Item upgraded
        elif ( options["type"] == NEWS_ITEM_UPGRADE ):

            # Build a special newsfeeder item
            return self.build_item_upgrade_item(options, control_center, universe)


        # New skill unlocked
        elif ( options["type"] == NEWS_SKILL_UNLOCKED ):

            # Build a special newsfeeder item
            return self.build_skill_unlocked_item(options, control_center, universe)


        # Skill upgraded
        elif ( options["type"] == NEWS_SKILL_UPGRADED ):

            # Build a special newsfeeder item
            return self.build_skill_upgraded_item(options, control_center, universe)



        # Unknown newsfeeder item type; do nothing...
        else:

            log( "Warning:  Unknown newsfeeder item type:  ", options["type"] )
            return None


    # Build a generic template.  Contains @title and @content.
    def build_generic_item(self, options, control_center, universe):

        # Fetch template
        template = self.fetch_xml_template("newsfeeder.generic").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
            "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
            "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@title": xml_encode( "%s" % options["title"] ),
            "@content": xml_encode( "%s" % options["content"] )
        })

        # Compile template
        root = template.compile_node_by_id("feed")

        # Return widget
        return control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)


    # Build a "character level up" update
    def build_character_level_up_item(self, options, control_center, universe):

        # Fetch template
        template = self.fetch_xml_template("newsfeeder.levelup").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
            "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
            "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@character-level": xml_encode( "%s" % options["character-level"] ),
            "@skill-points": xml_encode( "%s" % options["skill-points"] )
        })

        # Compile template
        root = template.compile_node_by_id("feed")

        # Return widget
        return control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)


    # Build an "item upgrade" update
    def build_item_upgrade_item(self, options, control_center, universe):

        # Fetch template
        template = self.fetch_xml_template("newsfeeder.item.upgrade").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
            "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
            "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@item-title": xml_encode( "%s" % options["item-title"] ),
            "@upgrade-title": xml_encode( "%s" % options["upgrade-title"] )
        })

        # Compile template
        root = template.compile_node_by_id("feed")

        # Return widget
        return control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)


    # Build a "skill unlocked " update
    def build_skill_unlocked_item(self, options, control_center, universe):

        # Fetch template
        template = self.fetch_xml_template("newsfeeder.skill.unlocked").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
            "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
            "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@skill-title": xml_encode( "%s" % options["skill-title"] ),
            "@skill-level": xml_encode( "%s" % options["skill-level"] ),
            "@skill-points-remaining": xml_encode( "%s" % options["skill-points-remaining"] )
        })

        # Compile template
        root = template.compile_node_by_id("feed")

        # Return widget
        return control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)


    # Build a "skill upgraded" update
    def build_skill_upgraded_item(self, options, control_center, universe):

        # Fetch template
        template = self.fetch_xml_template("newsfeeder.skill.upgraded").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
            "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
            "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@skill-title": xml_encode( "%s" % options["skill-title"] ),
            "@skill-level": xml_encode( "%s" % options["skill-level"] ),
            "@skill-points-remaining": xml_encode( "%s" % options["skill-points-remaining"] )
        })

        # Compile template
        root = template.compile_node_by_id("feed")

        # Return widget
        return control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)


    # Build a "using a default gamepad because I couldn't find the last one you used" item
    def build_gamepad_default_item(self, options, control_center, universe):

        # Fetch template
        template = self.fetch_xml_template("newsfeeder.gamepad.default").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - NEWSFEEDER_MARGIN) ),
            "@y": xml_encode( "%d" % NEWSFEEDER_ITEM_Y ),
            "@width": xml_encode( "%d" % NEWSFEEDER_ITEM_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@current-device": xml_encode( "%s" % options["current-device"] ),
            "@last-device": xml_encode( "%s" % options["last-device"] )
        })

        # Compile template
        root = template.compile_node_by_id("feed")

        # Return widget
        return control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)



    def get_escape_event(self):

        if (len(self.queue) > 0):

            return self.queue[0].get_escape_event()

        else:

            return None


    def process(self, control_center, universe):

        # Don't process while a delay is in effect
        if (self.delay_interval > 0):

            # Wait...
            self.delay_interval -= 1

        # No delay exists
        else:

            # Check the post queue for new news feed items
            while ( len(self.queue) > 0 ):

                # Create new widget for news feed
                widget = self.build(
                    self.queue.pop(0),
                    control_center,
                    universe
                )

                # Validate
                if (widget):

                    # Position new item to slide in from the right
                    widget.slide(DIR_RIGHT, percent = 1.0, animated = False)

                    # Now set it to slide into position
                    widget.slide(None)


                    # Track in the stack!
                    self.widgets.append(widget)


                    # If this is the only news item (brand new), then let's reset the overall timer
                    # to allow it to show for however long.  Otherwise, we'll get to it later...
                    if ( len(self.widgets) == 1 ):

                        # However long
                        self.timer = NEWSFEEDER_ITEM_LIFESPAN

                        # Play sound effect that accompanies a news update
                        control_center.get_sound_controller().queue_sound(SFX_NEWS)


            # Do we have an active item to display?
            if ( len(self.widgets) > 0 ):

                # Process the first widget in line
                self.widgets[0].process(control_center, universe)


                # Decrease timer, if/a
                if (self.timer > 0):

                    # Tick, tock
                    self.timer -= 1

                    # Out of time?
                    if (self.timer <= 0):

                        # Hide the widget.  We'll check to see when it's fully gone, at which point we'll clear it out
                        self.widgets[0].hide()

                        # Slide the widget away
                        self.widgets[0].slide(DIR_RIGHT, percent = 1.0)

                # If the timer expired already, then let's see if the "active" widget finished fading away
                else:

                    # Check alpha
                    if ( self.widgets[0].alpha_controller.get_interval() == 0 ):

                        # Remove the widget from our stack
                        self.widgets.pop(0)


                        # If we have another widget waiting in the wings, then we should
                        # reset the timer and call .show on the next news item widget...
                        if ( len(self.widgets) > 0 ):

                            # Show
                            self.widgets[-1].show()


                            # Reset timer; show each item for the full lifespan
                            self.timer = NEWSFEEDER_ITEM_LIFESPAN

                            # Play sound effect that accompanies a news update
                            control_center.get_sound_controller().queue_sound(SFX_NEWS)


    def draw(self, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        if (len(self.widgets) > 0):

            #self.widgets[0].render(tilesheet_sprite, additional_sprites, text_renderer, window_controller, f_draw_worldmap)
            self.widgets[0].draw(0, 0, tilesheet_sprite, additional_sprites, text_renderer, window_controller)
