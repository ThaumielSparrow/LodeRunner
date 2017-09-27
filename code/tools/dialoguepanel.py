import sys

from code.controllers.intervalcontroller import IntervalController

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser

from code.game.scripting.script import Script

from code.utils.common import log, log2, logn, xml_encode, xml_decode

from code.constants.common import PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_PROMPT_WIDTH, DIALOGUE_PANEL_WIDTH, DIALOGUE_PANEL_HEIGHT, DIALOGUE_PANEL_CONTENT_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_ACTIVATE, MIN_SPEAKER_HEIGHT, MIN_RESPONSE_HEIGHT, SPEAKER_X, SPEAKER_WIDTH, SPEAKER_HEIGHT, DIALOGUE_X, DIALOGUE_PANEL_X, DIALOGUE_RESPONSE_X, GENUS_PLAYER, CONVERSATION_X, SKILL_ICON_WIDTH, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, COMPUTER_SIMPLE_WIDTH

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY



class DialoguePanelFoundation(Menu):

    def __init__(self):#, line, universe, session, conversation, narrator):

        Menu.__init__(self)

        # Track a reference to the entity object which narrates this dialogue...
        self.narrator = None#narrator

        # Also remember which conversation (ID) this panel applies to...
        self.conversation_id = None#conversation


        # Will this dialogue redirect to another conversation branch?
        self.redirect = None#line.redirect

        # Keep a reference to the original line
        self.source_node = None#line


        # If the entire text cannot fit vertically on the screen,
        # we automatically divide it into 2 or more queued pages.
        self.queue = []


        self.comment_menu = None


        # Alpha control
        self.alpha_controller = IntervalController(
            interval = 0.0,
            target = 1.0,
            speed_in = 0.05,
            speed_out = 0.05
        )


    def configure(self, options):

        # Standard Menu configure
        Menu.__std_configure__(self, options)


        if ( "narrator" in options ):
            self.narrator = options["narrator"]

        if ( "conversation-id" in options ):
            self.conversation_id = options["conversation-id"]

        if ( "redirect" in options ):
            self.redirect = options["redirect"]

        if ( "source-node" in options ):
            self.source_node = options["source-node"]


        # For chaining
        return self


    def populate_node_with_line_responses(self, node, line, panel_variant, control_center, universe):

        # Inject this line's possible responses...
        self.inject_line_responses_into_node(
            node = node, #root.get_first_node_by_tag("template").get_node_by_id("ext.responses"),
            line = line,
            control_center = control_center,
            universe = universe,
            panel_variant = panel_variant # normal, shop, (other?); the response width will differ, requiring slightly different template versions
        )


    def inject_line_responses_into_node(self, node, line, panel_variant, control_center, universe):

        # Now we'll inject a new item for each response option
        for response in line.get_responses():

            # Scope
            phrase = None

            # Should we translate?  (Usually we should!)
            if (response.translate):

                # Translated response text
                phrase = universe.translate_session_variable_references(
                    control_center.get_localization_controller().translate(response.phrase),
                    control_center = None
                )

            # If not, we'll still replace session variable references
            else:

                # Untranslated response text
                phrase = universe.translate_session_variable_references(response.phrase, control_center = None)


            # Debug
            log( "Phrase Data:  ", (response.phrase, phrase) )


            # Calculate whether or not the user can select this response.  If not,
            # I'll technically leave the thing "enabled," but I will give it a
            # non-functioning "action."
            (active, error_phrase, special_phrase) = (True, "", "")


            # Too expensive?
            gold_available = int( universe.get_session_variable("core.gold.wallet").get_value() )

            if ( response.min_gold > gold_available ):

                (active, error_phrase) = (
                    False,
                    "You need %d more gold." % (response.min_gold - gold_available)
                )

            elif (response.min_gold > 0):

                special_phrase = "Cost:  %d gold" % response.min_gold


            # Not a good enough hacker?
            hacker_level = int( universe.get_session_variable("core.skills.hacking").get_value() )

            if ( response.min_hacking > hacker_level ):

                (active, error_phrase) = (
                    False,
                    "Requires Hacking Level %d" % response.min_hacking
                )

            elif (response.min_hacking > 0):

                special_phrase = "Hacking:  Level %d" % response.min_hacking


            # Not a good enough persuader?
            persuader_level = int( universe.get_session_variable("core.skills.persuasion").get_value() )

            log2( "persuade", (persuader_level, response.min_persuasion) )

            if ( response.min_persuasion > persuader_level ):

                (active, error_phrase) = (
                    False,
                    "Requires Persuasion Level %d" % response.min_persuasion
                )

            elif (response.min_persuasion > 0):

                special_phrase = "Persuasion:  Level %d" % response.min_persuasion


            # Prepare to generate item markup
            markup = ""

            # Which version should we grab?
            version = ""


            # Will it be an available option?
            if (active):

                version = "normal"

                if (special_phrase != ""):
                    version = "special"

            # Nope!
            else:
                version = "disabled"


            # Perhaps we need one of the variants (e.g. shop variant)
            if ( panel_variant != "" ):

                # Apply variant
                version = "%s:%s" % (version, panel_variant)


            log2( "version:", version )


            # Get response template
            template = self.fetch_xml_template( "dialogue.response", version = version ).add_parameters({
                "@response-id": xml_encode( response.id ),
                "@response-text": xml_encode( phrase ),
                "@response-error-phrase": xml_encode( error_phrase ),
                "@response-special-phrase": xml_encode( special_phrase )
            })


            # Compile iter node
            iter_node = template.compile_node_by_id("response")

            # Inject it into the response options
            node.add_node(iter_node)#.get_first_node_by_tag("template").get_nodes_by_tag("*") )


    # Take a given dialogue panel widget and remove potential
    # overflow text, potentially creating >= 2 pages.
    def pagewrap_widget(self, comment, widget, overflow_model, original_model, control_center, universe):

        # Track results
        queue = []


        # Handle
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


        widget.invalidate_cached_metrics()

        # Check to see if we've used up too much vertical screen estate.
        if ( widget.report_widget_height(text_renderer) > PAUSE_MENU_HEIGHT ):

            # Temporary copy of current comment text
            removed_text = ""
            inline = False

            # As we remove text from the beginning of the comment,
            # store it in a queue.
            queued_text = ""


            # Remove the first paragraph / sentence until we can fit
            # in the allotted screen region.
            while ( widget.report_widget_height(text_renderer) > PAUSE_MENU_HEIGHT ):

                # Divide by double space
                paragraphs = comment.split("\n\n")

                # If we have more than one paragraph, begin by removing that first paragraph.
                if ( len(paragraphs) > 1 ):

                    # Remove the first paragraph, then update the comment data.
                    (removed_text, comment) = (
                        "%s" % paragraphs[0],
                        "\n\n".join( paragraphs[1 : len(paragraphs)] )
                    )

                # If we have only one paragraph (which takes so much space as to overflow
                # the available space), then we're going to assume there's a period
                # in there somewhere that indicates a full stop of a sentence.  (Safe, right?!)
                else:

                    # Find the first acceptable punctuation mark
                    (pos1, pos2, pos3) = (
                        comment.find("."), comment.find("?"), comment.find("!")
                    )

                    # Assume
                    pos = -1

                    # Validate at least one match.
                    # Ignore 0 match because surely no sentence would "start" with a punctuation mark.
                    if (pos1 > 0 or pos2 > 0 or pos3 > 0):

                        # Find the earliest-in-sentence match (ignoring -1 which indicates not found)
                        pos = min( [ o for o in (pos1, pos2, pos3) if o > 0 ] )


                    # If we didn't find it, then we're just going to arbitrarily remove 100 characters.
                    if ( pos <= 0 ):

                        # Arbitrary 100 characters
                        if ( pos < 0 ):
                            pos = 100


                    # Remove the first sentence, then update the comment data
                    # with the rest of the text.
                    (removed_text, comment) = (
                        "%s" % comment[0 : pos + 1],
                        comment[pos + 1 : len(comment)]
                    )


                    # If we've previously removed from multiparagraph text
                    # and this is the first time we've removed an entire sentence,
                    # then we'll add a final double-space after the existing queued text.
                    if ( (not inline) and (queued_text != "") ):

                        # Final double-space
                        queued_text += "\n\n"


                    # Flag inline as true now
                    inline = True


                # Does the text queue have enough room to fit the removed text on one page?
                # To determine, we must build a widget based on the queue + removed text.
                potential_text = ( "%s" % removed_text if (queued_text == "") else ( "%s\n\n%s" % (queued_text, removed_text) if (not inline) else "%s%s" % (queued_text, removed_text) ) )

                # Add potential text to working root2
                overflow_model.set_data("translations", {
                    "@npc-name": xml_encode( self.narrator.nick ),
                    "@npc-comment": xml_encode( "%s" % potential_text ),
                    "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
                })

                # Create a throwaway widget
                t = widget_dispatcher.convert_node_to_widget(overflow_model, control_center, universe)
                t.invalidate_cached_metrics()

                # If the height exceeds the available screen estate, we must
                # begin a new queued page.
                if ( t.report_widget_height(text_renderer) > PAUSE_MENU_HEIGHT ):

                    # Use the previously queued text to create a queued page.
                    overflow_model.set_data("translations", {
                        "@npc-name": xml_encode( self.narrator.nick ),
                        "@npc-comment": xml_encode( queued_text.strip() ), # The added portion did not fit
                        "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
                    })

                    # Add a new page to the queue
                    w = widget_dispatcher.convert_node_to_widget(overflow_model, control_center, universe)
                    queue.extend(
                        self.pagewrap_widget(comment = queued_text.strip(), widget = w, overflow_model = overflow_model, original_model = overflow_model, control_center = control_center, universe = universe)
                    )

                    # Set the queued text to hold the portion that would not fit
                    queued_text = removed_text

                # If the added text will fit on the page-in-progress (to be queued),
                # then we can set the potential text as queued now.
                else:

                    # Update queue
                    queued_text = potential_text


                # Next, let's update the widget that initially had too much text.
                # At some point we will have removed enough text for it to fit on the screen.
                original_model.set_data("translations", {
                    "@npc-name": xml_encode( self.narrator.nick ),
                    "@npc-comment": xml_encode( comment ),
                    "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
                })

                # Recreate the dialogue widget
                widget = widget_dispatcher.convert_node_to_widget(original_model, control_center, universe)

                widget.set_id("dialogue-widget")

                widget.invalidate_cached_metrics()


            # Assuming we have some data left in the queued text string,
            # we should add one final queued page.
            if (queued_text != ""):

                if (1):

                    # Use the previously queued text to create a queued page.
                    overflow_model.set_data("translations", {
                        "@npc-name": xml_encode( self.narrator.nick ),
                        "@npc-comment": xml_encode( queued_text ), # The added portion did not fit
                        "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
                    })

                    # Create one final queued page
                    w = widget_dispatcher.convert_node_to_widget(overflow_model, control_center, universe)
                    queue.extend(
                        self.pagewrap_widget(comment = queued_text, widget = w, overflow_model = overflow_model, original_model = overflow_model, control_center = control_center, universe = universe)
                    )


        # Always add the final (potentially interactive) widget
        # to the end of the queue.
        queue.append(widget)


        # Add the same id for each queued page
        for widget in queue:

            # Always the same id
            widget.set_id("dialogue-widget")


        # Return results
        return queue


    # Process any pre-script data for the current (but not quite yet displayed) source node
    # For example, give an item to the player before saying "look at this!"
    def process_pre_script(self, control_center, universe):

        # Check for any post-script action
        if (self.source_node.pre_script):

            # Create a new, temporary event controller
            event_controller = control_center.create_event_controller()

            # Add the requisite events to the new event controller
            event_controller.load(
                Script(self.source_node.pre_script.innerText)
            )
            logn( "conversation prescript", "PS Pre:  %s" % self.source_node.pre_script.innerText )

            # Run for as long as we can
            event_controller.loop(control_center, universe)


        """
        logn( "conversation prescript", "Looming:  %s" % self.source_node.comment )
        for key in universe.session:
            logn( "conversation prescript session-dump", "SV[%s] = %s" % (key, universe.session[key].get_value()) )
        """


    # Process any post-script data on the current source node
    def process_post_script(self, control_center, universe):

        # Check for any post-script action
        if (self.source_node.post_script):

            # Do we want to queue this post script in the map's event controller?
            if ( self.source_node.post_script.get_attribute("queued") == "1" ):

                # Create a throwaway Script object
                universe.get_active_map().get_event_controller().load(
                    Script(self.source_node.post_script.innerText)
                )


            # If not, let's execute it in real-time...
            else:

                # Create a new, temporary event controller
                event_controller = control_center.create_event_controller()

                # Add the requisite events to the new event controller
                event_controller.load(
                    Script(self.source_node.post_script.innerText)
                )
                logn( "conversation postscript", "PS:  %s" % self.source_node.post_script.innerText )

                # Run for as long as we can
                event_controller.loop(control_center, universe)


    # Special processing for a dialogue panel
    def additional_processing(self, control_center, universe):

        # Events that result from this
        results = EventQueue()


        # Do we need to rebuild the response menu?
        if (universe.get_session_variable("app.rebuild-response-menu").get_value() == "1"):

            """
            Disabled - crashes game (UIKeyboard save state bug),
                       and unnecessary after removing persuasion/hacking skill tree category.
            # Refresh UI
            self.refresh_pages(control_center, universe)
            """


            # Disable flag
            universe.set_session_variable("app.rebuild-response-menu", "0")


        # Return events
        return results


    # Handle (forward) an event
    def handle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        action = event.get_action()

        log( action )


        # Alternate versions of the DialoguePanel (such as the shop panel) will overwrite
        # the .handle_build_event() method, but they will still use this simple build event...
        if ( action == "build" ):

            # All dialogue panels have the potential to find pre-script data.
            # They should all process that data before building, so I'm going to
            # sneak it in here ahead of the build event handler.
            self.process_pre_script(control_center, universe)

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        elif ( action == "next-page" ):

            results.append(
                self.handle_next_page_event(event, control_center, universe)
            )


        elif ( action == "finish:next-page" ):

            results.append(
                self.handle_finish_next_page_event(event, control_center, universe)
            )


        elif ( action == "respond" ):

            results.append(
                self.handle_respond_event(event, control_center, universe)
            )


        elif ( action == "finish:respond" ):

            results.append(
                self.handle_finish_respond_event(event, control_center, universe)
            )


        elif ( action == "continue" ):

            results.append(
                self.handle_continue_event(event, control_center, universe)
            )


        elif ( action == "continue:transition" ):

            pass
            """
            results.append(
                self.handle_continue_transition_event(event, control_center, universe)
            )
            """


        elif ( action == "submit:keyboard" ):

            results.append(
                self.handle_submit_keyboard_event(event, control_center, universe)
            )


        elif ( action == "resume-game" ):

            results.append(
                self.handle_resume_game_event(event, control_center, universe)
            )


        elif ( action == "finish:resume-game" ):

            results.append(
                self.handle_finish_resume_game_event(event, control_center, universe)
            )


        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    # Build the dialogue menu
    def handle_build_event(self, event, control_center, universe):

        # Inheriting classes will overwrite this function.  This
        # base version does nothing...
        return EventQueue() # No results to speak of!


    # Move to the next queued page
    def handle_next_page_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Validate that another page exists
        if ( len(self.queue) > 1 ):

            # Get the current dialogue page widget
            widget = self.get_widget_by_id("dialogue-widget")

            # Validate
            if (widget):

                # Fade out
                widget.hide(
                    on_complete = "finish:next-page"
                )

        # No more data exists (we should never reach this, but if we
        # do we'll "gracefully" return back to game.
        else:
            self.fire_event("resume-game")


        # Return events
        return results


    # Finish "next page" logic, getting the next page widget in the queue
    def handle_finish_next_page_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Remove first queued page
        self.queue.pop(0)


        # Remove the existing dialogue page from the widget stack
        self.remove_widget_by_id("dialogue-widget")

        # Add the next queued page (already built widget)
        self.add_widget_via_event( self.queue[0], event )


        # Return events
        return results


    # Respond to an NPC
    def handle_respond_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        log2( "Check post script for:  %s" % self.source_node.comment )
        # Before we process the response (i.e. continue to the next line), let's see if the current line has any post-script data.
        self.process_post_script(control_center, universe)


        # Validate that we have a handle to the entity that's talking
        if (self.narrator):

            if ( self.conversation_id in self.narrator.conversations ):

                logn( "conversation", self.narrator.conversations[ self.conversation_id ].branches )

                line = self.narrator.conversations[ self.conversation_id ].branches[ params["response-id"] ].get_next_line()

                if (line):

                    #self.create_dialogue_panel(line, universe, session, quests, conversation, entity, shop = (self.dialogue_panel.species == "shop"))
                    self.source_node = line


                    # If the next line does not have any text, and it does not
                    # redirect or transition elsewhere, then let's drop the lightbox effect.
                    if (
                        (not self.source_node.redirect) and
                        (self.source_node.get_attribute("transition") != "1")
                    ):

                        # Dismiss lightbox
                        self.lightbox_controller.set_target(0)


                    comment_menu = self.get_widget_by_id("dialogue-widget")

                    # Validate
                    if (comment_menu):

                        comment_menu.hide(
                            on_complete = "finish:respond"
                        )
                        log2( "DEBUG:  Received response '%s'" % params["response-id"] )


                # No "next" line... just close and resume game
                else:

                    # If the next line does not have any text, and it does not
                    # redirect or transition elsewhere, then let's drop the lightbox effect.
                    if (
                        (not self.source_node.redirect) and
                        (self.source_node.get_attribute("transition") != "1")
                    ):

                        # Dismiss lightbox
                        self.lightbox_controller.set_target(0)

                    self.fire_event("resume-game")

            # Invalid conversation id; resume game
            else:
                self.fire_event("resume-game")

        # No narrarator provided, so we can't check the next line anyway.  Resume game...
        else:
            self.fire_event("resume-game")


        # Return events
        return results


    # Finish up respond logic, moving on to the next line of conversation
    def handle_finish_respond_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        log( "REACT" )

        # Clear all widgets
        #while ( len(self.widgets) > 0 ):
        #self.widgets = []

        # Close menu, clearing all widgets
        self.close(control_center)

        # Rebuild the dialogue menu using the currently active dialogue line data
        self.fire_event("build")


        # Return events
        return results


    # Continue (?)
    def handle_continue_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Did we need to pagewrap?
        if ( len(self.queue) > 1 ):

            # Move to the next page
            self.fire_event("next-page")

        # Let's see if the current line has a redirect...
        elif (self.source_node.redirect):

            # Emulate an event to move to that branch
            self.fire_event_with_params(
                event = "respond",
                params = {
                    "response-id": self.source_node.redirect # Pretend that the next line is a "response ID" (i.e. next branch key)
                }
            )

        # If not, let's resume game...
        else:

            # Before we resume game, we should process any post script data.
            # If we have a response or a redirect, we handle it there.  Because we don't, we handle it here.
            self.process_post_script(control_center, universe)

            if ((self.source_node.get_attribute("transition") == "1")): # Unless we marked this explicitly as a transition line
                control_center.get_window_controller().set_param("dialogue-lock-count", "1")

            # If we're not transitioning to another lightboxed menu, then
            # let's drop the lightbox effect.
            else:

                # Dismiss lightbox
                self.lightbox_controller.set_target(0)

            # Resume game event
            self.fire_event("resume-game")


        # Return events
        return results


    # Handle a "submit keyboard" event (from an interrogative dialogue)
    def handle_submit_keyboard_event(self, event, control_center, universe):

        # Resultant events
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Find the keyboard widget in the current page
        keyboard = self.get_active_page().find_widget_by_id("keyboard")

        # Update session variable that tracks last input
        universe.get_session_variable("core.keyboard.value").set_value(
            keyboard.get_value()
        )


        # Disable pause-lock now that the user has submitted the keyboard.
        # (Maybe i should wait even longer, but for now this should work.)
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })


        # Resume game event
        self.fire_event("resume-game")


        # Return events
        return results


    # Resume game.  Hide then kill this dialogue menu; dismiss splash, resuming game when done.
    def handle_resume_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We might have a comment menu...
        comment_menu = self.get_widget_by_id("dialogue-widget")

        # Hide the comment menu
        if (comment_menu):

            comment_menu.hide(
                on_complete = "finish:resume-game"
            )

        # Empty comments never create a comment menu.  We thus have
        # nothing to hide; let's simply end the dialogue...
        else:
            self.fire_event("kill")


        # Assume
        count = 0

        # Check for existence of dialogue lock count param
        if ( control_center.get_window_controller().has_param("dialogue-lock-count") ):

            # Update
            count = int( control_center.get_window_controller().get_param("dialogue-lock-count") )


        # If we locked the dialogue panel, then we will decrease count by 1.
        if (count > 0):

            # Update variable
            count -= 1

            # Update lock count
            control_center.get_window_controller().set_param("dialogue-lock-count", "%s" % count)

        # Otherwise, we can resume the game
        else:

            # Fetch splash controller
            splash_controller = control_center.get_splash_controller()


            # Dismiss the splash controller, calling to resume game action once done...
            splash_controller.dismiss(
                on_complete = "game:unpause"
            )


        # Return events
        return results


    # Finish up resume game logic.  Resume this game, 
    def handle_finish_resume_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Not much to do here right now.  Let's fire off the kill event.
        self.fire_event("kill")


        # Return events
        return results


    # Kill the menu.
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Clear all widgets
        self.widgets = []

        # Done with the dialogue widget
        self.set_status(STATUS_INACTIVE)


        # Disable pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })


        # Return events
        return results


# A standard dialogue panel for conversing with ordinary NPCs.
class DialoguePanel(DialoguePanelFoundation):

    def __init__(self):#, line, universe, session, conversation, narrator, event_type):

        DialoguePanelFoundation.__init__(self)#, line, universe, session, conversation, narrator)


        # This is an ordinary dialogue panel
        self.species = "generic"

        self.event_type = "?????"#event_type


        self.fire_event("build")


    # Build standard dialogue panel
    def handle_build_event(self, event, control_center, universe):

        # Always pause lock on build
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })

        # "Dim" background music a bit
        control_center.get_sound_controller().set_background_ratio(0.4)


        # Grab the comment for this line...
        comment = universe.translate_session_variable_references(
            control_center.get_localization_controller().translate(self.source_node.comment),
            control_center
        )


        # Empty-comment "lines" will immediately disappear (I use them for certain pre/post scripting events only)
        if (0):#if (comment == ""):

            self.alpha_controller.dismiss()
            self.set_status(STATUS_INACTIVE)

            # (?)
            if (1):

                # Check for any post-script action
                if (self.source_node.post_script):

                    # Create a new, temporary event controller
                    event_controller = control_center.create_event_controller()

                    # Add the requisite events to the new event controller
                    event_controller.load_events_from_xml_packet( self.source_node.post_script )

                    # Run for as long as we can
                    event_controller.loop(control_center, universe)


                # Fire a "continue" event.  This allows us to forward "empty lines"
                # to another conversation / script event, if desired.  The event handler
                # will ultimately call "resume-game" if it doesn't find a redirect.
                self.fire_event("continue")


        else:

            # Fetch the widget dispatcher
            widget_dispatcher = control_center.get_widget_dispatcher()


            # Does this dialogue text have any response option?
            # (This matters when deciding which template to load...)
            has_responses = ( len( self.source_node.get_responses() ) > 0 )

            # Like so...
            template_version = ( "interactive" if (has_responses) else "noninteractive" )


            # If the dialogue has "responses" but the first (and, if scripted correctly, only) response has a value of "keyboard,"
            # then we should disable responses and use the "keyboard" dialogue template.
            if (has_responses):

                # If we have one or more "keyboard" responses, we immediate switch to displaying a UI keyboard.
                if (
                    len( self.source_node.get_responses_by_class("keyboard") ) > 0
                ):

                    # Switch template
                    template_version = "interrogative"

                    # Ignore any script response options
                    has_responses = False


                    # During this keyboard input period, we're going to prevent in-game pausing.
                    control_center.get_menu_controller().configure({
                        "pause-locked": True
                    })


            # Fetch the desired template for the NPC dialogue stuff
            template = self.fetch_xml_template( "dialogue.comment", version = template_version ).add_parameters({
                "@x": xml_encode( "%d" % (int( SCREEN_WIDTH / 2 )) ),
                "@y": xml_encode( "%d" % (int( (SCREEN_HEIGHT - PAUSE_MENU_HEIGHT) / 2 )) ),
                "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
                "@npc-name": xml_encode( self.narrator.nick ),
                "@npc-comment": xml_encode( comment ),
                "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
            })

            # Compile template
            root = template.compile_node_by_id("panel")

            # Add secondary translations
            #root.set_data("translations", {
            #})


            # Will we list a RowMenu of response options for this line of dialogue?
            if (has_responses):

                # Populate the response menu...
                self.populate_node_with_line_responses( root.find_node_by_id("ext.responses"), self.source_node, panel_variant = "", control_center = control_center, universe = universe )


            # Create the dialogue widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)
            widget.set_id("dialogue-widget")



            # Fetch the noninteractive (press return to continue) template for potential wrapping needs.
            template2 = self.fetch_xml_template( "dialogue.comment", version = "noninteractive" ).add_parameters({
                "@x": xml_encode( "%d" % (int( SCREEN_WIDTH / 2 )) ),
                "@y": xml_encode( "%d" % (int( (SCREEN_HEIGHT - PAUSE_MENU_HEIGHT) / 2 )) ),
                "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
            })

            # Compile that fallback template
            root2 = template2.compile_node_by_id("panel")


            # Create 1 or more pages in the queue
            self.queue = self.pagewrap_widget(comment = comment, widget = widget, overflow_model = root2, original_model = root, control_center = control_center, universe = universe)

            # Add the first available widget page
            self.add_widget_via_event( self.queue[0], event )


            # If we just created a blank overlay, then we'll immediately dismiss it with a "continue" event.
            if (comment == ""):

                if (not(self.source_node.get_attribute("transition") == "1")): # Unless we marked this explicitly as a transition line

                    # Fire a "continue" event.  This allows us to forward "empty lines"
                    # to another conversation / script event, if desired.  The event handler
                    # will ultimately call "resume-game" if it doesn't find a redirect.
                    self.fire_event("continue")
                    log2( "DEBUG:  Continue event" )

                else:
                    self.fire_event("continue")#:transition")


# This version of the DialoguePanel works just like an ordinary dialogue panel, except that it does
# not pause the game when created, and it loads from a different template.
class DialoguePanelFYI(DialoguePanelFoundation):

    def __init__(self):#, line, universe, session, conversation, narrator, event_type):

        DialoguePanelFoundation.__init__(self)#, line, universe, session, conversation, narrator)


        # FYI should not use the standard Menu lightbox effect
        self.lightbox_controller.configure({
            "interval": 0,
            "target": 0
        })


        # This is an ordinary dialogue panel
        self.species = "generic"

        # Fire build event
        self.fire_event("build")


    # Build FYI dialogue panel
    def handle_build_event(self, event, control_center, universe):

        # Grab the comment for this line...
        comment = universe.translate_session_variable_references(
            control_center.get_localization_controller().translate(self.source_node.comment),
            control_center
        )


        # Empty-comment "lines" will immediately disappear (I use them for certain pre/post scripting events only)
        if (comment == ""):

            self.alpha_controller.dismiss()
            self.set_status(STATUS_INACTIVE)

            # ** (?)
            log( 5/0 )

        else:

            # Fetch the widget dispatcher
            widget_dispatcher = control_center.get_widget_dispatcher()


            # Always use the FYI template
            template = self.fetch_xml_template( "dialogue.comment", version = "fyi" ).add_parameters({
                "@x": xml_encode( "%d" % (int( SCREEN_WIDTH / 2 )) ),
                "@y": xml_encode( "%d" % (int( (SCREEN_HEIGHT - PAUSE_MENU_HEIGHT) / 2 )) ),
                "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
            })

            # Compile template.
            # Note that we're searching by a slightly different node id.
            root = template.compile_node_by_id("panel.fyi")

            # Add secondary translations
            root.set_data("translations", {
                "@npc-name": xml_encode( self.narrator.nick ),
                "@npc-comment": xml_encode( comment ),
                "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
            })


            # Create the dialogue widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("dialogue-widget")

            # Add the widget page
            self.add_widget_via_event(widget, event)


    # Ordinarily, a dialogue panel will fire a game:unpause event in response to a
    # resume-game event.  An FYI panel is kind of static, though; it doesn't affect
    # the game in any way.  This is all to say, this is a total hack.
    # Resume game.  Hide then kill this dialogue menu; dismiss splash, resuming game when done.
    def handle_resume_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # We might have a comment menu...
        comment_menu = self.get_widget_by_id("dialogue-widget")

        # Hide the comment menu
        if (comment_menu):

            comment_menu.hide(
                on_complete = "kill"
            )

        # Empty comments never create a comment menu.  We thus have
        # nothing to hide; let's simply end the dialogue...
        else:
            self.fire_event("kill")


        # Return events
        return results


# This variation of the DialoguePanel renders everything in the right hand
# of an HPane.  The logic all works the same.
class DialoguePanelShop(DialoguePanelFoundation):

    def __init__(self):#, line, universe, session, conversation, narrator, event_type):

        DialoguePanelFoundation.__init__(self)#, line, universe, session, conversation, narrator)


        # This is a "shop" dialogue panel
        self.species = "shop"

        self.event_type = "?????"#event_type


        self.fire_event("build")


    # Build the "shop" dialogue menu.  It's an ordinary dialogue menu, but the formatting changes to match
    # the appearance of an honest-to-goodness ShopMenu object (for a consistent UI experience).
    def handle_build_event(self, event, control_center, universe):

        # Always pause lock on build
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })

        # "Dim" background music a bit
        control_center.get_sound_controller().set_background_ratio(0.4)


        # What will the NPC say?
        comment = universe.translate_session_variable_references(
            control_center.get_localization_controller().translate(self.source_node.comment),
            control_center
        )


        # Empty comments fade away (we only use them for invisible scripts)
        if (comment == ""):

            # We're inevitably going to trash this dialogue menu...
            self.set_status(STATUS_INACTIVE)

            log( "no comment, checking for transition..." )

            # Does this line simply transition to another conversation / shop menu / whatever?
            if ( self.source_node.get_attribute("transition") == "1" ):

                ##self.fire_event("resume-game-but-retain-splash")

                # Pessimistically, let's assume we don't reach our destination.
                # (As long as we do, the new menu will re-pause the universe...)
                universe.unpause()

                # Check for any post-script action
                if (self.source_node.post_script):

                    # Fetch the splash controller;
                    splash_controller = control_center.get_splash_controller()

                    # and the menu controller
                    menu_controller = control_center.get_menu_controller()


                    # Splash events work in a queue, so queue up a lock before running the transition script(s)
                    #splash_controller.get_event_queue().add(action = "lock")


                    # Create a new, temporary event controller
                    event_controller = control_center.create_event_controller()

                    # Add the requisite events to the new event controller
                    event_controller.load(
                        Script(self.source_node.post_script.innerText)
                    )

                    # Run for as long as we can
                    event_controller.loop(control_center, universe)


                    # If we did create a new menu, we should "max out" its lightbox (i.e. ensure a seamless transition to the new menu)
                    if ( menu_controller.count() > 0 ):

                        menu = menu_controller.get_active_wrapper().get_menu()

                        menu.lightbox_controller.set_interval(
                            menu.lightbox_controller.get_target()
                        )

                        control_center.get_splash_controller().get_greyscale_controller().set_interval(
                            control_center.get_splash_controller().get_greyscale_controller().get_target()
                        )

                        universe.pause()


                    # Lastly, queue up an unlock event for the splash controller
                    #splash_controller.get_event_queue().add(action = "unlock")

            # No; it's just a dead end
            else:

                self.fire_event("resume-game")

                # Because we're not transitioning to another lightboxed menu, then
                # let's drop the lightbox effect.
                self.lightbox_controller.set_target(0)

                # Check for any post-script action
                if (self.source_node.post_script):

                    # Create a new, temporary event controller
                    event_controller = control_center.create_event_controller()

                    # Add the requisite events to the new event controller
                    event_controller.load(
                        Script(self.source_node.post_script.innerText)
                    )

                    # Run for as long as we can
                    event_controller.loop(control_center, universe)


        else:

            # Fetch the widget dispatcher
            widget_dispatcher = control_center.get_widget_dispatcher()


            # Does this shop dialogue have responses, or is it "dictatorial?"
            has_responses = ( len( self.source_node.get_responses() ) > 0 )

            # Depending, which template?
            template_version = ( "interactive" if (has_responses) else "noninteractive" )

            # Assume (generally these are true!)
            per_row = 1
            panel_variant = "shop"


            # The source node can include an attribute that
            # uses a rare template version, "interactive:grid"
            if ( self.source_node.get_attribute("use-grid") == "yes" ):

                # Update template version
                template_version = "interactive:grid"

                # Update per_row variable
                per_row = self.source_node.get_attribute("per-row")

                # Use a custom panel variant
                panel_variant = "shop:grid"


            # Fetch the desired template for this shop dialogue panel
            template = self.fetch_xml_template( "dialogue.shop.comment", version = template_version ).add_parameters({
                "@x": xml_encode( "%d" % (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ) + PAUSE_MENU_WIDTH) ),#( SCREEN_WIDTH - int(PAUSE_MENU_WIDTH / 2) - 20 ),
                "@y": xml_encode( "%d" % (int( (SCREEN_HEIGHT - PAUSE_MENU_HEIGHT) / 2 )) ),
                "@width": xml_encode( "%d" % (int(PAUSE_MENU_WIDTH) / 2) ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
                "@per-row": xml_encode( "%s" % per_row )
            })

            # Compile template
            root = template.compile_node_by_id("panel")

            # Add secondary translations
            root.set_data("translations", {
                "@npc-name": xml_encode( self.narrator.nick ),
                "@npc-comment": xml_encode( comment ),
                "@some-key": xml_encode( "%s" % ( universe.get_session_variable("sys.input.keyboard.enter").get_value() if ( control_center.get_input_controller().get_last_used_device() == "keyboard" ) else universe.get_session_variable("sys.input.gamepad.enter").get_value() ) )
            })

            # Create a separate response menu that we'll render "on top" of the base RowMenu
            if (has_responses):

                # Populate the response menu...
                self.populate_node_with_line_responses( root.find_node_by_id("ext.responses"), self.source_node, panel_variant = panel_variant, control_center = control_center, universe = universe )


            # Create the widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)
            widget.set_id("dialogue-widget")


            # We'll need at least 1 copy of the noninteractive template
            template2 = self.fetch_xml_template( "dialogue.shop.comment", version = "noninteractive" ).add_parameters({
                "@x": xml_encode( "%d" % (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ) + PAUSE_MENU_WIDTH) ),#( SCREEN_WIDTH - int(PAUSE_MENU_WIDTH / 2) - 20 ),
                "@y": xml_encode( "%d" % (int( (SCREEN_HEIGHT - PAUSE_MENU_HEIGHT) / 2 )) ),
                "@width": xml_encode( "%d" % (int(PAUSE_MENU_WIDTH) / 2) ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
            })

            # Compile fallback template
            root2 = template2.compile_node_by_id("panel")


            # Create 1 or more pages in the queue
            self.queue = self.pagewrap_widget(comment = comment, widget = widget, overflow_model = root2, original_model = root, control_center = control_center, universe = universe)

            # Add the first available widget page
            self.add_widget_via_event( self.queue[0], event )

            # Add the new page
            #self.add_widget_via_event(widget, event)


# This variation of the DialoguePanel renders a MenuStack with a
# header on the top ("exit computer") and the responses / associated
# "details" (e.g. an e-mail's text) in an HPane below the header.
class DialoguePanelComputer(DialoguePanelFoundation):

    def __init__(self, line, universe, session, conversation, narrator, event_type):

        DialoguePanelFoundation.__init__(self, line, universe, session, conversation, narrator)


        # This is a "computer" dialogue panel
        self.species = "computer"

        # Track the original event type
        self.event_type = event_type


        # When this panel first appears, we will not have yet computed the necessary height
        # (which equals the greatest height of any individual "details" panel)
        self.configured = False

        # Unfortunately, we don't have access to text_renderer here, but we don't have access to universe/session
        # when rendering.  Thus, we'll hack together a quick "check" function for use on the first rendering pass.
        # A hacky approach deserves a hacky function name, too!
        self.calculate_greatest_response_details_pane_height_using_text_renderer = lambda text_renderer, a = self, b = universe, c = session: a.calculate_greatest_response_details_pane_height(text_renderer, b, c)


        # What will the NPC say?
        comment = universe.translate_session_variable_references(
            control_center.get_localization_controller().translate(line.comment),
            control_center = None
        )


        # Create the base MenuStack that holds everything
        self.menu_stack = MenuStack(width = DIALOGUE_PANEL_WIDTH, center_vertically = False)


        # Create a simple RowMenu for the header (e.g. [Exit Computer Dialogue] <---------> (header text)])
        row_menu_header = RowMenu(x = 0, y = 0, width = DIALOGUE_PANEL_WIDTH, height = 200)

        # Place focus on the responses HPane on wrap...
        row_menu_header.on_wrap_down = lambda widget, a = self, b = universe, c = session: a.focus_on_responses(b, c)#a.set_active_item_by_index(1)


        # Fetch the template for this type of header
        template = self.fetch_xml_template("dialogue.computer.header").add_parameters({
            "@back-button-text": xml_encode( self.ref_line.get_attribute("back-button-text") ),
            "@responses-header-text": xml_encode( self.ref_line.get_attribute("responses-header-text") ),
            "@header-text": xml_encode( "header text???" ),
            "@player-name": xml_encode( universe.get_session_variable("core.player1.name").get_value() )
        })

        # Compile template
        root = XMLParser().create_node_from_xml(markup)

        # Get the cell collection
        cell_collection = root.get_first_node_by_tag("template").get_nodes_by_tags("item, item-group")

        # Populate the header
        row_menu_header.populate_from_collection(universe.widget_dispatcher, cell_collection, universe, session)

        # Lastly, add the header to the MenuStack
        self.menu_stack.add_with_id(row_menu_header, item_id = "navbar")


        # We continue by creating a pair of RowMenu objects to display
        # the responses (on the left) and the details for the active
        # response (e.g. e-mail text) (on the right).
        (row_menu_responses, row_menu_details) = (
            RowMenu(x = 0, y = 0, width = 0, height = 200, global_frame = True),
            RowMenu(x = 0, y = 0, width = 0, height = 200, global_frame = True)
        )

        row_menu_responses.on_wrap_down = lambda widget, a = self, b = universe, c = session: a.focus_on_navbar(b, c)#a.set_active_item_by_index(0)
        row_menu_responses.onchange = lambda widget, a = self, b = universe, c = session: a.build_response_details(b, c, widget)


        # We're going to throw those RowMenus into an HPane
        log( "Sorry, no more HPane(), use widget dispatcher, event, etc..." )
        log( 5/0 )
        hpane = HPane(width = DIALOGUE_PANEL_WIDTH, item1 = row_menu_responses, item2 = row_menu_details, width1 = 0.35, width2 = 0.65)


        # Let's populate the responses now...
        self.populate_response_menu(row_menu_responses, self.ref_line, universe, session, template_version = "computer")

        # We won't populate the "details" here; we'll do that onchange (emulating the first one in a moment).
        # For now, we'll proceed by adding the HPane to the MenuStack...
        self.menu_stack.add_with_id(hpane, "responses")

        # Make sure to focus on the header by default
        #self.menu_stack.set_active_item_by_index(0)
        self.focus_on_navbar(universe, session)


    # Focus on the navbar (simply "Exit Computer")
    def focus_on_navbar(self, universe, session):

        # Grab a reference to that navbar
        row_menu = self.menu_stack.get_item_by_id("navbar").get_widget()

        # Place focus on index 0
        self.menu_stack.set_active_item_by_id("navbar")

        # Update the "details" pane to display default system status
        self.build_system_status(universe, session)


    # Focus on the responses
    def focus_on_responses(self, universe, session):

        # Grab a reference to the response RowMenu
        row_menu_responses = self.menu_stack.get_item_at_index(1).get_widget().item1

        # Place focus on menu stack index 1 (HPane)
        self.menu_stack.set_active_item_by_id("responses")

        # Emulate an onchange call for the currently highlighted response...
        row_menu_responses.onchange(row_menu_responses)


    def calculate_greatest_response_details_pane_height(self, text_renderer, universe, session):

        # Grab a reference to the "details" RowMenu
        row_menu_details = self.menu_stack.get_item_at_index(1).get_widget().item2

        max_height = 0

        for response in self.ref_line.get_responses():

            row_menu_temp = RowMenu(x = 0, y = 0, width = row_menu_details.width, height = SCREEN_HEIGHT)

            self.populate_response_details_rowmenu_from_response(row_menu_temp, response, universe, session)

            max_height = max(max_height, row_menu_temp.report_widget_height(text_renderer))

        return max_height


    # Populate the "details" RowMenu with a generic introductory message
    # (pending the highlighting of any given response)
    def build_system_status(self, universe, session):

        # Grab a reference to the "details" RowMenu
        row_menu_details = self.menu_stack.get_item_at_index(1).get_widget().item2

        # Reset that RowMenu
        row_menu_details.reset()


        # Get all "splash" responses (there should be one, but only one)
        responses = self.ref_line.get_responses_by_class("splash")

        # Did we find it?
        if ( len(responses) > 0 ):

            # Use the first one we found (it should be the only one)
            response = responses[0]

            # Use that "response" data to populate the "details" pane when we're on the navbar
            self.populate_response_details_rowmenu_from_response(row_menu_details, response, universe, session)


    # Populate (or repopulate) the "summary" RowMenu that displays the "details"
    # pertaining to the selected response (e.g. e-mail text).
    def build_response_details(self, universe, session, widget):

        # Only do this if the MenuStack is focused on the HPane
        if ( self.menu_stack.get_active_status_by_id("responses") == True ):

            # Grab a reference to the "details" RowMenu
            row_menu_details = self.menu_stack.get_item_at_index(1).get_widget().item2

            # Reset that RowMenu
            row_menu_details.reset()


            # Get a reference to the active RowMenuItem widget
            active_widget = widget.get_active_item().get_widget()

            # Get the response ID from that active widget's attributes
            response_id = active_widget.attributes["response-id"]

            # Use our stored reference to the current line of dialogue to find the response by that ID...
            response = self.ref_line.get_response_by_id(response_id)


            # Validate...
            if (response):

                self.populate_response_details_rowmenu_from_response(row_menu_details, response, universe, session)


    def populate_response_details_rowmenu_from_response(self, row_menu_details, response, universe, session):

        # The "details" are stored as unprocessed XML.  Let's compile the XML...
        root = XMLParser().create_node_from_xml( response.details )

        # Grab the paragraphs the comprise the details
        paragraph_collection = root.get_nodes_by_tag("p")


        # Before we loop through the paragraph collection, let's now grab the
        # template for the details RowMenu
        template = self.fetch_xml_template("dialogue.computer.details").add_parameters({
        })

        # Compile container
        root = XMLParser().create_node_from_xml(markup)


        # Loop
        for ref_paragraph in paragraph_collection:

            # Which version will we want?  It depends on whether or not we define an icon for this paragraph...
            version = "icon"

            # No icon index provided?
            if (not ref_paragraph.get_attribute("icon-index")):

                version = "no-icon"

            # Lastly, check for an explicit template version declaration...
            if (ref_paragraph.get_attribute("template-version")):

                version = ref_paragraph.get_attribute("template-version")


            # Fetch the appropriate template
            template = self.fetch_xml_template( "dialogue.computer.details.paragraph", version = version ).add_parameters({
                "@icon-index": xml_encode( "%d" % int( ref_paragraph.get_attribute("icon-index") ) ),
                "@paragraph-text": xml_encode( ref_paragraph.innerText )
            })

            # Compile template
            iter_node = XMLParser().create_node_from_xml(markup)

            # Inject the new node into the appropriate root...
            root.get_first_node_by_tag("template").get_node_by_id("ext.paragraphs").add_nodes( iter_node.get_first_node_by_tag("template").get_nodes_by_tag("*") )


        # Now grab the cell collection from the container
        cell_collection = root.get_first_node_by_tag("template").get_nodes_by_tags("item, item-group")

        # Finally, populate the details RowMenu!
        row_menu_details.populate_from_collection(universe.widget_dispatcher, cell_collection, universe, session)


    def process(self, user_input, universe, session):

        # Handle fade
        self.process_alpha()


        # Handle to the HPane, with RowMenus we'll want to process...
        hpane = self.menu_stack.get_item_by_id("responses").get_widget()

        # Grab RowMenu references
        (row_menu_responses, row_menu_details) = (
            hpane.item1,
            hpane.item2
        )


        # Check which MenuStack item has the focus
        index = self.menu_stack.get_active_item_index()


        # Header?
        if ( self.menu_stack.get_active_status_by_id("navbar") == True ):

            # Handle to the header
            row_menu_header = self.menu_stack.get_item_at_index(0).get_widget()

            # Process with user input
            row_menu_header.process(user_input, [], universe, session, save_controller = None)


            # Process the responses / details RowMenus without any input
            row_menu_responses.process([], [], universe, session, save_controller = None)
            row_menu_details.process([], [], universe, session, save_controller = None)


            # Use a generic check to dismiss the dialogue panel on enter ("exit computer" is the only option in the header)
            return self.check_for_generic_input(user_input, universe, session)

        # HPane
        elif ( self.menu_stack.get_active_status_by_id("responses") == True ):

            # Process details without input (just handle fading / scrolling / whatever)
            row_menu_details.process([], [], universe, session, save_controller = None)

            # Process responses with input
            return self.handle_response_menu_params(
                params = self.process_response_menu_and_get_params(row_menu_responses, user_input, universe, session),
                universe = universe,
                session = session
            )

        return None


    def render(self, text_renderer, additional_sprites, window_controller):

        # This is a workaround.  On the first frame, we calculate RowMenu heights...
        if (not self.configured):

            # We'll use the same height (a "global" height) for each RowMenu in the HPane
            global_height = self.calculate_greatest_response_details_pane_height_using_text_renderer(text_renderer)

            # Grab a reference to each of those 2 RowMenu objects
            (row_menu_responses, row_menu_details) = (
                self.menu_stack.get_item_at_index(1).get_widget().item1,
                self.menu_stack.get_item_at_index(1).get_widget().item2
            )

            # Set their heights accordingly
            row_menu_responses.height = global_height
            row_menu_details.height = global_height


            # Track that we have now fully configured this panel
            self.configured = True

            # Ultimately emulate a "wrap up" from the responses to ensure we have the correct visual
            # display ready to go (default splash screen)
            row_menu_responses.on_wrap_down(row_menu_responses)


        # Lightbox effect
        window_controller.get_geometry_controller().draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (25, 25, 25, (self.alpha_controller.get_interval() / 1.5)))

        # Render MenuStack
        self.menu_stack.draw(DIALOGUE_PANEL_X, PAUSE_MENU_Y, None, additional_sprites, text_renderer, self.alpha_controller.get_interval(), window_controller = window_controller, f_draw_worldmap = None)


# This "simple" version of the Computer dialogue panel simply
# shows a list of the various responses without any navbar, etc.
class DialoguePanelComputerSimple(DialoguePanelFoundation):

    def __init__(self, line, universe, session, conversation, narrator, event_type):

        DialoguePanelFoundation.__init__(self, line, universe, session, conversation, narrator)


        # This is a "computer:simple" dialogue panel
        self.species = "computer:simple"

        # Track the original event type
        self.event_type = event_type


        # What will the NPC say?
        comment = universe.translate_session_variable_references(
            control_center.get_localization_controller().translate(line.comment),
            control_center = None
        )


        # Calculate centered x coordinate
        x = int(SCREEN_WIDTH / 2) - int(COMPUTER_SIMPLE_WIDTH / 2)

        # Create a simple RowMenu for the options...
        self.row_menu = RowMenu(x = x, y = 0, width = COMPUTER_SIMPLE_WIDTH, height = SCREEN_HEIGHT, global_frame = False, shrinkwrap = True, center_vertically = True, cellspacing = 5)


        # Fetch the simple template
        template = self.fetch_xml_template("dialogue.computer.simple").add_parameters({
            "@back-button-text": xml_encode( self.ref_line.get_attribute("back-button-text") ),
            "@responses-header-text": xml_encode( self.ref_line.get_attribute("responses-header-text") ),
            "@header-text": xml_encode( "header text???" ),
            "@player-name": xml_encode( universe.get_session_variable("core.player1.name").get_value() )
        })

        # Compile template
        root = XMLParser().create_node_from_xml(markup)


        # Now we should add a button for each visible response
        self.inject_line_responses_into_node(
            node = root.get_first_node_by_tag("template").get_node_by_id("ext.responses"),
            line = line,
            control_center = control_center,
            universe = universe,
            session = session
        )

        # Get the RowMenu cell collection
        cell_collection = root.get_first_node_by_tag("template").get_nodes_by_tags("item, item-group")

        # Populate!
        self.row_menu.populate_from_collection(universe.widget_dispatcher, cell_collection, universe, session)


        self.row_menu.focus()
        return



        # Create the base MenuStack that holds everything
        self.menu_stack = MenuStack(width = DIALOGUE_PANEL_WIDTH, center_vertically = False)


        # Create a simple RowMenu for the header (e.g. [Exit Computer Dialogue] <---------> (header text)])
        row_menu_header = RowMenu(x = 0, y = 0, width = DIALOGUE_PANEL_WIDTH, height = 200)

        # Place focus on the responses HPane on wrap...
        row_menu_header.on_wrap_down = lambda widget, a = self, b = universe, c = session: a.focus_on_responses(b, c)#a.set_active_item_by_index(1)


        # Fetch the template for this type of header
        template = self.fetch_xml_template("dialogue.computer.header").add_parameters({
            "@back-button-text": xml_encode( self.ref_line.get_attribute("back-button-text") ),
            "@responses-header-text": xml_encode( self.ref_line.get_attribute("responses-header-text") ),
            "@header-text": xml_encode( "header text???" ),
            "@player-name": xml_encode( universe.get_session_variable("core.player1.name").get_value() )
        })

        # Compile template
        root = XMLParser().create_node_from_xml(markup)

        # Get the cell collection
        cell_collection = root.get_first_node_by_tag("template").get_nodes_by_tags("item, item-group")

        # Populate the header
        row_menu_header.populate_from_collection(universe.widget_dispatcher, cell_collection, universe, session)

        # Lastly, add the header to the MenuStack
        self.menu_stack.add_with_id(row_menu_header, item_id = "navbar")


        # We continue by creating a pair of RowMenu objects to display
        # the responses (on the left) and the details for the active
        # response (e.g. e-mail text) (on the right).
        (row_menu_responses, row_menu_details) = (
            RowMenu(x = 0, y = 0, width = 0, height = 200, global_frame = True),
            RowMenu(x = 0, y = 0, width = 0, height = 200, global_frame = True)
        )

        row_menu_responses.on_wrap_down = lambda widget, a = self, b = universe, c = session: a.focus_on_navbar(b, c)#a.set_active_item_by_index(0)
        row_menu_responses.onchange = lambda widget, a = self, b = universe, c = session: a.build_response_details(b, c, widget)


        # We're going to throw those RowMenus into an HPane
        hpane = HPane(width = DIALOGUE_PANEL_WIDTH, item1 = row_menu_responses, item2 = row_menu_details, width1 = 0.35, width2 = 0.65)


        # Let's populate the responses now...
        self.populate_response_menu(row_menu_responses, self.ref_line, universe, session, template_version = "computer")

        # We won't populate the "details" here; we'll do that onchange (emulating the first one in a moment).
        # For now, we'll proceed by adding the HPane to the MenuStack...
        self.menu_stack.add_with_id(hpane, "responses")

        # Make sure to focus on the header by default
        #self.menu_stack.set_active_item_by_index(0)
        self.focus_on_navbar(universe, session)


    # Focus on the navbar (simply "Exit Computer")
    def focus_on_navbar(self, universe, session):

        # Grab a reference to that navbar
        row_menu = self.menu_stack.get_item_by_id("navbar").get_widget()

        # Place focus on index 0
        self.menu_stack.set_active_item_by_id("navbar")

        # Update the "details" pane to display default system status
        self.build_system_status(universe, session)


    # Focus on the responses
    def focus_on_responses(self, universe, session):

        # Grab a reference to the response RowMenu
        row_menu_responses = self.menu_stack.get_item_at_index(1).get_widget().item1

        # Place focus on menu stack index 1 (HPane)
        self.menu_stack.set_active_item_by_id("responses")

        # Emulate an onchange call for the currently highlighted response...
        row_menu_responses.onchange(row_menu_responses)


    def calculate_greatest_response_details_pane_height(self, text_renderer, universe, session):

        # Grab a reference to the "details" RowMenu
        row_menu_details = self.menu_stack.get_item_at_index(1).get_widget().item2

        max_height = 0

        for response in self.ref_line.get_responses():

            row_menu_temp = RowMenu(x = 0, y = 0, width = row_menu_details.width, height = SCREEN_HEIGHT)

            self.populate_response_details_rowmenu_from_response(row_menu_temp, response, universe, session)

            max_height = max(max_height, row_menu_temp.report_widget_height(text_renderer))

        return max_height


    # Populate the "details" RowMenu with a generic introductory message
    # (pending the highlighting of any given response)
    def build_system_status(self, universe, session):

        # Grab a reference to the "details" RowMenu
        row_menu_details = self.menu_stack.get_item_at_index(1).get_widget().item2

        # Reset that RowMenu
        row_menu_details.reset()


        # Get all "splash" responses (there should be one, but only one)
        responses = self.ref_line.get_responses_by_class("splash")

        # Did we find it?
        if ( len(responses) > 0 ):

            # Use the first one we found (it should be the only one)
            response = responses[0]

            # Use that "response" data to populate the "details" pane when we're on the navbar
            self.populate_response_details_rowmenu_from_response(row_menu_details, response, universe, session)


    # Populate (or repopulate) the "summary" RowMenu that displays the "details"
    # pertaining to the selected response (e.g. e-mail text).
    def build_response_details(self, universe, session, widget):

        # Only do this if the MenuStack is focused on the HPane
        if ( self.menu_stack.get_active_status_by_id("responses") == True ):

            # Grab a reference to the "details" RowMenu
            row_menu_details = self.menu_stack.get_item_at_index(1).get_widget().item2

            # Reset that RowMenu
            row_menu_details.reset()


            # Get a reference to the active RowMenuItem widget
            active_widget = widget.get_active_item().get_widget()

            # Get the response ID from that active widget's attributes
            response_id = active_widget.attributes["response-id"]

            # Use our stored reference to the current line of dialogue to find the response by that ID...
            response = self.ref_line.get_response_by_id(response_id)


            # Validate...
            if (response):

                self.populate_response_details_rowmenu_from_response(row_menu_details, response, universe, session)


    def populate_response_details_rowmenu_from_response(self, row_menu_details, response, universe, session):

        # The "details" are stored as unprocessed XML.  Let's compile the XML...
        root = XMLParser().create_node_from_xml( response.details )

        # Grab the paragraphs the comprise the details
        paragraph_collection = root.get_nodes_by_tag("p")


        # Before we loop through the paragraph collection, let's now grab the
        # template for the details RowMenu
        template = self.fetch_xml_template("dialogue.computer.details").add_parameters({
        })

        # Compile container
        root = XMLParser().create_node_from_xml(markup)


        # Loop
        for ref_paragraph in paragraph_collection:

            # Which version will we want?  It depends on whether or not we define an icon for this paragraph...
            version = "icon"

            # No icon index provided?
            if (not ref_paragraph.get_attribute("icon-index")):

                version = "no-icon"

            # Lastly, check for an explicit template version declaration...
            if (ref_paragraph.get_attribute("template-version")):

                version = ref_paragraph.get_attribute("template-version")


            # Fetch the appropriate template
            template = self.fetch_xml_template( "dialogue.computer.details.paragraph", version = version ).add_parameters({
                "@icon-index": xml_encode( "%d" % int( ref_paragraph.get_attribute("icon-index") ) ),
                "@paragraph-text": xml_encode( ref_paragraph.innerText )
            })

            # Compile template
            iter_node = XMLParser().create_node_from_xml(markup)

            # Inject the new node into the appropriate root...
            root.get_first_node_by_tag("template").get_node_by_id("ext.paragraphs").add_nodes( iter_node.get_first_node_by_tag("template").get_nodes_by_tag("*") )


        # Now grab the cell collection from the container
        cell_collection = root.get_first_node_by_tag("template").get_nodes_by_tags("item, item-group")

        # Finally, populate the details RowMenu!
        row_menu_details.populate_from_collection(universe.widget_dispatcher, cell_collection, universe, session)


    def process(self, user_input, universe, session):

        # Handle fade
        self.process_alpha()


        # Process responses with input
        return self.handle_response_menu_params(
            params = self.process_response_menu_and_get_params(self.row_menu, user_input, universe, session),
            universe = universe,
            session = session
        )


        self.row_menu.process(user_input, [], universe, session, save_controller = None)
        return
        # Handle to the HPane, with RowMenus we'll want to process...
        hpane = self.menu_stack.get_item_by_id("responses").get_widget()

        # Grab RowMenu references
        (row_menu_responses, row_menu_details) = (
            hpane.item1,
            hpane.item2
        )


        # Check which MenuStack item has the focus
        index = self.menu_stack.get_active_item_index()


        # Header?
        if ( self.menu_stack.get_active_status_by_id("navbar") == True ):

            # Handle to the header
            row_menu_header = self.menu_stack.get_item_at_index(0).get_widget()

            # Process with user input
            row_menu_header.process(user_input, [], universe, session, save_controller = None)


            # Process the responses / details RowMenus without any input
            row_menu_responses.process([], [], universe, session, save_controller = None)
            row_menu_details.process([], [], universe, session, save_controller = None)


            # Use a generic check to dismiss the dialogue panel on enter ("exit computer" is the only option in the header)
            return self.check_for_generic_input(user_input, universe, session)

        # HPane
        elif ( self.menu_stack.get_active_status_by_id("responses") == True ):

            # Process details without input (just handle fading / scrolling / whatever)
            row_menu_details.process([], [], universe, session, save_controller = None)

            # Process responses with input
            return self.handle_response_menu_params(
                params = self.process_response_menu_and_get_params(row_menu_responses, user_input, universe, session),
                universe = universe,
                session = session
            )

        return None


    def render(self, text_renderer, additional_sprites, window_controller):

        # Lightbox effect
        window_controller.get_geometry_controller().draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (25, 25, 25, (self.alpha_controller.get_interval() / 1.5)))

        # Render RowMenu
        self.row_menu.draw(0, 0, None, additional_sprites, text_renderer, self.alpha_controller.get_interval(), window_controller = window_controller, f_draw_worldmap = None)
