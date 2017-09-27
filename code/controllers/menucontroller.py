from code.tools.eventqueue import EventQueue

from code.utils.common import log, log2

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE

"""
properties / methods -

    n/a - index - just use list order

    alpha controller?  or just use widget-built-ins?

    lock - whenever adding a new one, lock the lower one
        unlock lower one after dismissing highest (if/a)

    count - so I know whether or not to lock gameplay input during map processing (menu_controller.count() > 0???)

    add - add a new uimenu type thing, draw it, etc.

    process - handle alpha if necessary, do input for the highest one, yeah just lock and loop, don't do z - 1 / z with/without input, etc., easy..

        call .process on each ITEM, and the item is locked if it's covered, so that'll cover it!

    draw - draw all, alpha control, whatever
"""


class UIMenuWrapper:

    def __init__(self, menu):

        # Track the UIMenu (or inheriting) object
        self.menu = menu

        # Input access
        self.lock_count = 0

        # Optional delay
        self.delay_interval = 0


    # Lock input access
    def lock(self):

        self.lock_count += 1


    # Unlock (grant input access)
    def unlock(self):

        self.lock_count -= 1

        # Don't go negative
        if (self.lock_count < 0):

            self.lock_count = 0


    # Is locked?
    def is_locked(self):

        return ( self.lock_count > 0 )


    # We can choose to delay processing (e.g. delaying the fade in at times)
    def delay(self, amount):

        self.delay_interval = amount


    def get_menu(self):

        return self.menu


    def process(self, control_center, universe):

        # Resultant events
        results = EventQueue()


        # Do absolutely nothing until any delay expires
        if (self.delay_interval > 0):

            self.delay_interval -= 1

        # Ready!
        else:

            # Should we ignore user input?
            if ( self.is_locked() ):

                # Fetch input controller
                input_controller = control_center.get_input_controller()

                # Lock input
                input_controller.lock_all_input()

                # Process UIMenu
                self.menu.process(control_center, universe)

                # Unlock input
                input_controller.unlock_all_input()

            # Nope; provide all input access
            else:

                # Just process
                results.append(
                    self.menu.process(control_center, universe)
                )


        # Return events
        return results


    def draw(self, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        self.menu.draw(tilesheet_sprite, additional_sprites, text_renderer, window_controller)


class MenuController:

    def __init__(self):

        # A stack of UIMenuWrapper objects (or objects that inherit from UIMenu)
        self.menu_wrappers = []

        # When "pause locked," the player won't be able to activate pause-type menus
        # Each pause menu should check this value before adding the menu.
        self.pause_locked = False


    # Configure
    def configure(self, options):

        if ( "pause-locked" in options ):
            self.pause_locked = ( int( options["pause-locked"] ) == 1 )


        # For chaining
        return self


    # Get pause lock status
    def is_pause_locked(self):

        return self.pause_locked


    # Add a new UiMenu to the item collection
    def add(self, menu):

        # Lock access to any lower-level menu
        for item in self.menu_wrappers:

            # Lock!
            item.lock()


        # Add the new menu
        self.menu_wrappers.append(
            UIMenuWrapper(menu)
        )


        # For chaining
        return self.menu_wrappers[-1]


    # Remove the top-most item
    def pop(self):

        # Validate
        if ( len(self.menu_wrappers) > 0 ):

            # Goodbye...
            self.menu_wrappers.pop()

            # Now, unlock the highest menu item (if/a)
            if ( len(self.menu_wrappers) > 0 ):

                # Top-most gets to respond to input again...
                self.menu_wrappers[-1].unlock()


    # Remove a menu with a given id
    def remove_menu_by_id(self, menu_id):

        # Loop
        i = 0
        while ( i < len(self.menu_wrappers) ):

            # Check the menu's id...
            if ( self.menu_wrappers[i].get_menu().get_id() == menu_id ):

                # Later, menu...
                self.menu_wrappers.pop(i)

            # Loop all menus...
            else:
                i += 1


    # Clear all menus
    def clear(self):

        # Delete all widgets
        self.menu_wrappers = []

        # Disable pause lock
        self.configure({
            "pause-locked": False
        })


    # Return the number of active menus
    def count(self):

        return len(self.menu_wrappers)


    # Get a raw menu by its id
    def get_menu_by_id(self, menu_id):

        # Loop wrappers
        for wrapper in self.menu_wrappers:

            # Check the menu object
            if ( wrapper.get_menu().get_id() == menu_id ):

                # Found it!
                return wrapper.get_menu()


        # 404
        return None


    # Get the active menu wrapper, if one exists
    def get_active_wrapper(self):

        if ( self.count() > 0 ):

            return self.menu_wrappers[-1]

        else:

            return None


    # Get the active menu, if one exists
    def get_active_menu(self):

        if ( self.count() > 0 ):

            return self.menu_wrappers[-1].get_menu()

        else:

            return None


    def process(self, control_center, universe):

        # Events from active menu
        results = EventQueue()


        # Loop
        for item in self.menu_wrappers:

            results.append(
                item.process(control_center, universe)
            )


        # If we have at least one menu...
        if ( len(self.menu_wrappers) > 0 ):

            # ... then let's remove any inactive menu item, from the top moving down...
            i = 0
            while ( i < len(self.menu_wrappers) ):

                if ( self.menu_wrappers[i].get_menu().get_status() == STATUS_INACTIVE ):

                    # Get out of here!
                    self.menu_wrappers.pop(i)

                    # Unlock the now-highest menu, if/a
                    if ( len(self.menu_wrappers) > 0 ):

                        # Restore input access
                        self.menu_wrappers[-1].unlock()

                else:
                    i += 1


        # Return events
        return results


    def draw(self, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Loop
        for item in self.menu_wrappers:

            item.draw(tilesheet_sprite, additional_sprites, text_renderer, window_controller)

