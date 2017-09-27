import os

from code.tools.xml import XMLParser

from code.ui.common import Action, KeyListener, GamepadListener, Label, Rect, AnimatedRect, VolumeRect, Hidden, Icon, Gif, Worldmap, Graphic
from code.ui.keyboard import Keyboard

from code.ui.containers.rowmenu.rowmenu import RowMenu
from code.ui.containers.stack import Stack
from code.ui.containers.hmenu import HMenu
from code.ui.containers.hpane import HPane
from code.ui.containers.box import Box
from code.ui.containers.tooltip import Tooltip

from code.ui.popups import TriggerTooltip, RowMenuTooltip

#from code.menu.menu import OverworldDeathMenu, ShopMenu, PuzzlePauseMenu, PuzzleDeathMenu, PuzzleVictoryMenu, GameMenu2, NetLobby, IdleMenu

# Import menu screens
from code.menu.screens.gamemenu import GameMenu

from code.menu.screens.pausemenu import PauseMenu

from code.menu.screens.puzzleintromenu import PuzzleIntroMenu
from code.menu.screens.puzzlevictorymenu import PuzzleVictoryMenu
from code.menu.screens.puzzlepausemenu import PuzzlePauseMenu
from code.menu.screens.puzzledeathmenu import PuzzleDeathMenu

from code.menu.screens.waveintromenu import WaveIntroMenu
from code.menu.screens.wavepausemenu import WavePauseMenu
from code.menu.screens.wavedeathmenu import WaveDeathMenu

from code.menu.screens.linearpausemenu import LinearPauseMenu
from code.menu.screens.lineardeathmenu import LinearDeathMenu

from code.menu.screens.overworlddeathmenu import OverworldDeathMenu

from code.menu.screens.shopmenu import ShopMenu

from code.menu.screens.netsessionsetup import NetSessionSetup
from code.menu.screens.netsessionbrowsermenu import NetSessionBrowser
from code.menu.screens.netlobby import NetLobby
from code.menu.screens.netpausemenu import NetPauseMenu
from code.menu.screens.netnoplayersmenu import NetNoPlayersMenu

from code.menu.screens.idlemenu import IdleMenu
from code.menu.screens.progressmenu import ProgressMenu

from code.menu.screens.waveprogresschart import WaveProgressChart

from code.tools.dialoguepanel import DialoguePanel, DialoguePanelFYI, DialoguePanelShop

from code.utils.common import log, log2, logn

from code.constants.common import SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT

class WidgetDispatcher:

    def __init__(self):

        return

    # Create a widget container to hold an assembly of widgets
    def create_widget_container(self):

        return Box()


    # Create a tooltip widget (basically a Box with fades)
    def create_tooltip(self):

        return Tooltip()


    # Create a Label
    def create_label(self):

        return Label()


    # Create an "Action" widget
    def create_action(self):

        return Action()


    # Create keypress listener
    def create_key_listener(self):

        return KeyListener()


    # Create gamepad press listener
    def create_gamepad_listener(self):

        return GamepadListener()


    # Create gfx rectangle
    def create_rect(self):

        return Rect()


    # Create an "animated" rectangle (i.e. progress bar)
    def create_animated_rect(self):

        return AnimatedRect()


    # Create a "volume" rectangle (renders little rectangles to indicate volume level)
    def create_volume_rect(self):

        return VolumeRect()


    # Create a "hidden" widget (used only for storing data)
    def create_hidden(self):

        return Hidden()


    # Create icon
    def create_icon(self):

        return Icon()


    # Create GIF
    def create_gif(self):

        return Gif()


    # Create Worldmap
    def create_worldmap(self):

        return Worldmap()


    # Create graphic from disk
    def create_graphic(self):

        return Graphic()


    # Create a RowMenu
    def create_row_menu(self):

        return RowMenu()


    # Create an item group (usually for row menus)
    def create_item_group(self):

        return RowMenuItemGroup()


    # Create a WidgetStack
    def create_widget_stack(self):

        return Stack()


    # Create an HMenu
    def create_hmenu(self):

        return HMenu()


    # Create an HPane
    def create_hpane(self):

        return HPane()


    # Create a Keyboard (for entering save game name, etc.)
    def create_keyboard(self):

        return Keyboard()


    # Create a trigger tooltip (for entering doors, talking to people, etc... "Press RETURN to enter")
    def create_trigger_tooltip(self):

        return TriggerTooltip()


    # Create the story mode pause menu (default pause menu)
    def create_pause_menu(self):

        return PauseMenu()


    # Create a generic (default) dialogue panel
    def create_generic_dialogue_panel(self):

        return DialoguePanel()


    # Create an "FYI" dialogue panel (used for narrating cutscenes, providing instructions in real-time, etc.)
    def create_fyi_dialogue_panel(self):

        return DialoguePanelFYI().configure({
            "id": "panel.fyi"
        })


    # Create a "shopping" dialogue panel (minor formatting differences, mostly)
    def create_shopping_dialogue_panel(self):

        return DialoguePanelShop()


    # Create a shop menu (for buying items).  This works somewhat differently
    # than the "shopping dialogue panel," although they look fairly similar.
    def create_shop_menu(self):

        return ShopMenu()


    # Create the puzzle intro menu
    def create_puzzle_intro_menu(self):

        return PuzzleIntroMenu()


    # Create puzzle pause menu
    def create_puzzle_pause_menu(self):

        return PuzzlePauseMenu()


    # Create puzzle death / game over menu
    def create_puzzle_death_menu(self):

        return PuzzleDeathMenu()


    # Create the puzzle victory menu
    def create_puzzle_victory_menu(self):

        return PuzzleVictoryMenu()


    # (?) Create a wave intro menu
    def create_wave_intro_menu(self):

        return WaveIntroMenu()


    # Create a wave pause menu
    def create_wave_pause_menu(self):

        return WavePauseMenu()


    # (?) Create a wave death menu
    def create_wave_death_menu(self):

        return WaveDeathMenu()


    # Create a linear level pause menu
    def create_linear_pause_menu(self):

        return LinearPauseMenu()


    # Create a linear level death menu
    def create_linear_death_menu(self):

        return LinearDeathMenu()


    # Create an overworld death / game over menu
    def create_overworld_death_menu(self):

        return OverworldDeathMenu()


    # Create the main game menu
    def create_main_menu(self):

        return GameMenu()


    # Create an idle menu
    def create_idle_menu(self):

        return IdleMenu()


    # Create a progress menu (e.g. download completion progress)
    def create_progress_menu(self):

        return ProgressMenu()


    # Create a wave progress chart
    def create_wave_progress_chart(self):

        return WaveProgressChart()


    # Create a net session setup screen (for hosting games)
    def create_net_session_setup(self):

        return NetSessionSetup()


    # Create a net session browser (for joining games)
    def create_net_session_browser(self):

        return NetSessionBrowser()


    # Create a netplay lobby menu
    def create_net_lobby(self):

        return NetLobby()


    # Create the co-op mode's pause menu
    def create_net_pause_menu(self):

        return NetPauseMenu()


    # Create an "all clients disconnected" menu
    def create_net_no_players_menu(self):

        return NetNoPlayersMenu()


    # Convert an xml node into a widget object
    def convert_node_to_widget(self, node, control_center, universe):

        """
        i = 1
        while ( os.path.exists( os.path.join("conversions", "conversion%d.txt" % i ) ) ):
            i += 1

        f = open( os.path.join("conversions", "conversion%d.txt" % i), "w" )
        f.write(
            node.compile_xml_string()
        )
        f.close()
        """


        # Run conversion function
        widget = self.parse_node_as_widget(node, control_center, universe)

        # Validate widget
        if (widget):

            # Check the source node for a namespace.
            # If it has one, then we'll set that namespace on the new widget.
            if ( node.get_namespace() != None ):

                # Update widget's namespace
                widget.set_namespace(
                    node.get_namespace()
                )
                logn( "widget namespace", "Set namespace:  %s" % node.get_namespace() )


            # Check the source node for translation data (in hidden data)
            if ( node.has_data("translations") ):

                # Apply hidden / secondary translations to widget
                widget.translate( node.get_data("translations") )

                # **Hack to attempt to force max-height recalculations
                parent = widget.get_top_parent()
                if (parent):
                    parent.invalidate_cached_metrics()
                    parent.on_resize( control_center.get_window_controller().get_default_text_controller().get_text_renderer() )


        # Return new widget
        return widget


    # Parse a given node into a widget
    def parse_node_as_widget(self, node, control_center, universe):

        """
        # Before we begin, handle any miscellaneous data attributes...
        for attribute in node.attributes:

            if (attribute.startswith("-")):

                self.attributes[attribute] = node.attributes[attribute]


        # Now let's create the appropriate object...
        if (node.tag_type == "action"):

            for attribute in node.attributes:

                self.attributes[attribute] = node.attributes[attribute]

        elif (node.tag_type == "attributes"):

            for attribute in node.attributes:

                self.attributes[attribute] = node.attributes[attribute]
        """

        # A "languages" node should find the contained node
        # that matches the current language.  (Should only contain one!)
        if (node.tag_type == "languages"):

            # Try to find node matching current language
            ref = node.find_node_by_tag( control_center.get_localization_controller().get_language() )

            # Validate
            if (ref):

                # Return translation of first child
                return self.parse_node_as_widget(
                    ref.get_first_node_by_tag("*"),
                    control_center,
                    universe
                )

            # Fall back to potential default option
            else:

                # Try to find "else" node
                ref = node.find_node_by_tag("else")

                # Validate
                if (ref):

                    # Return translation of first child
                    return self.parse_node_as_widget(
                        ref.get_first_node_by_tag("*"),
                        control_center,
                        universe
                    )


        # Similarly, a "layouts" node should find the contained
        # node that matches the current language's layout type.  (Will only match one.)
        elif (node.tag_type == "layouts"):

            # Try to find node matching current layout
            ref = node.find_node_by_tag( control_center.get_localization_controller().get_layout() )

            # Validate
            if (ref):

                # Return first match
                return self.parse_node_as_widget(
                    ref.get_first_node_by_tag("*"),
                    control_center,
                    universe
                )

            # Fall back to potential default
            else:

                # Try to find "else" node
                ref = node.find_node_by_tag("else")

                # Validate
                if (ref):

                    # Return first node
                    return self.parse_node_as_widget(
                        ref.get_first_node_by_tag("*"),
                        control_center,
                        universe
                    )


        elif (node.tag_type == "action"):

            action = self.create_action().configure(
                node.get_attributes()
            )

            action.__std_update_css__(control_center, universe)

            return action

        elif (node.tag_type == "listener"):

            listener = self.create_key_listener().configure(
                node.get_attributes()
            )

            listener.__std_update_css__(control_center, universe)

            return listener

        elif (node.tag_type == "gamepad-listener"):

            gamepad_listener = self.create_gamepad_listener().configure(
                node.get_attributes()
            )

            gamepad_listener.__std_update_css__(control_center, universe)

            return gamepad_listener

        elif (node.tag_type == "label"):

            label = self.create_label().configure(
                node.set_attributes({
                    "xwidth": 0
                }).get_attributes()
            )


            # Get localization controller
            localization_controller = control_center.get_localization_controller()

            # Reconfigure text
            label.configure({
                "value": localization_controller.translate( label.get_text() )
            })


            label.__std_update_css__(control_center, universe)

            return label

        elif (node.tag_type == "rect"):

            rect = self.create_rect().configure(
                node.set_attributes({
                    "xwidth": 0
                }).get_attributes()
            )

            rect.__std_update_css__(control_center, universe)

            return rect

        elif (node.tag_type == "animated-rect"):

            animated_rect = self.create_animated_rect().configure(
                node.get_attributes()
            )

            animated_rect.__std_update_css__(control_center, universe)

            return animated_rect

        elif (node.tag_type == "volume-rect"):

            volume_rect = self.create_volume_rect().configure(
                node.get_attributes()
            )

            volume_rect.__std_update_css__(control_center, universe)

            return volume_rect

        elif (node.tag_type == "hidden"):

            hidden = self.create_hidden().configure(
                node.get_attributes()
            )

            # No CSS for hidden elements
            return hidden

        elif (node.tag_type == "icon"):

            icon = self.create_icon().configure(
                node.set_attributes({
                    "xwidth": 0
                }).get_attributes()
            )

            icon.__std_update_css__(control_center, universe)

            return icon

        elif (node.tag_type == "gif"):

            # Default GIF size
            (w, h) = (
                SKILL_PREVIEW_WIDTH,
                SKILL_PREVIEW_HEIGHT
            )

            # Explicit overwrites?
            if ( node.get_attribute("width") ):
                w = int( node.get_attribute("width") )

            if ( node.get_attribute("height") ):
                h = int( node.get_attribute("height") )

            # Return GIF widget
            gif = self.create_gif().configure(
                node.set_attributes({
                    "width": w,
                    "height": h
                }).get_attributes()
            )

            gif.__std_update_css__(control_center, universe)

            return gif

        elif (node.tag_type == "graphic"):

            graphic = self.create_graphic().configure(
                node.set_attributes({
                    "xwidth": 0,
                    "xheight": 0
                }).get_attributes()
            )

            graphic.__std_update_css__(control_center, universe)

            return graphic

        elif (node.tag_type == "rowmenu"):

            # Create a RowMenu and configure it
            row_menu = self.create_row_menu().configure(
                node.set_attributes({
                    "xwidth": 0,
                    "xheight": -1
                }).get_attributes()
            )

            row_menu.__std_update_css__(control_center, universe)

            # Now we need to configure this nested RowMenu
            if ( node.get_attribute("uses-scroll") == False ):

                row_menu.configure({
                    "uses-scroll": False
                })

            if ( node.get_attribute("uses-focus") == False ):

                row_menu.configure({
                    "uses-focus": False
                })

            # Lastly, populate the RowMenu
            cell_collection = node.get_nodes_by_tags("item, item-group")

            row_menu.populate_from_collection(cell_collection, control_center, universe)

            # Return widget
            return row_menu


        elif ( node.tag_type in ("item", "box") ):

            # Create a widget container, configure, and return...
            container = self.create_widget_container().configure(
                node.get_attributes()
            )

            container.__std_update_css__(control_center, universe)


            # Declare this variable here to keep scope
            elem_collection = None

            # Does this item separate contents into its own container?
            ref_contents = node.get_first_node_by_tag("contents")
            ref_tooltip = node.get_first_node_by_tag("tooltip")


            if (ref_contents):

                elem_collection = ref_contents.get_nodes_by_tag("*")

            else:

                # Populate the container (labels, etc.)
                elem_collection = node.get_nodes_by_tag("*")


            container.populate_from_collection(elem_collection, control_center, universe)


            # Check for tooltip data
            if (ref_tooltip):

                # Create tooltip Widget
                tooltip_widget = self.convert_node_to_widget(ref_tooltip, control_center, universe).configure(
                    ref_tooltip.get_attributes()
                )

                # Specify tooltip widget's parent
                tooltip_widget.configure({
                    "parent": container
                })

                # Set bloodline on the tooltip
                tooltip_widget.css({
                    "bloodline": container.get_bloodline()
                })

                # Update css for the new tooltip
                tooltip_widget.__std_update_css__(control_center, universe)


                # Set the new tooltip Widget as the Box's tooltip
                container.tooltip = tooltip_widget


            return container


        elif (node.tag_type == "tooltip"):

            # Create Tooltip
            tooltip = self.create_tooltip().configure(
                node.get_attributes()
            )

            # Update css
            tooltip.__std_update_css__(control_center, universe)

            # Populate with child widgets
            tooltip.populate_from_collection(
                node.get_nodes_by_tag("*"),
                control_center,
                universe
            )

            # Return new Tooltip
            return tooltip


        elif (node.tag_type == "stack"):

            # Get the default text renderer
            text_renderer = control_center.get_window_controller().get_default_text_controller().get_text_renderer()


            # Create the Widgetstack and configure it
            widget_stack = self.create_widget_stack().configure(
                node.get_attributes()
            )

            widget_stack.__std_update_css__(control_center, universe)

            # Get the widgets that belong to the stack
            collection = node.get_nodes_by_tag("*")

            # Populate the stack
            for node in collection:

                widget = widget_stack.add_widget(
                    self.convert_node_to_widget(node, control_center, universe),
                    text_renderer
                )

                if (widget):

                    widget.__std_update_css__(control_center, universe)


            # Return widget
            return widget_stack


        elif (node.tag_type == "hmenu"):

            # Create an Hmenu, configure
            hmenu = self.create_hmenu().configure(
                node.get_attributes()
            )

            hmenu.__std_update_css__(control_center, universe)

            # Find members of the hmenu
            collection = node.get_nodes_by_tag("*")

            # Add each to the hmenu
            hmenu.populate_from_collection(collection, control_center, universe)
            """
            for node in collection:

                hmenu.add_widget(
                    self.convert_node_to_widget(node, control_center, universe)
                )
            """

            # Return widget
            return hmenu


        elif (node.tag_type == "hpane"):

            # Create, configure
            hpane = self.create_hpane().configure(
                node.get_attributes()
            )

            hpane.__std_update_css__(control_center, universe)

            # Check for left/right panes
            (left, right) = (
                node.get_first_node_by_tag("left"),
                node.get_first_node_by_tag("right")
            )

            # Add left pane?
            if (left):

                pane = left.get_first_node_by_tag("*")

                if (pane):

                    hpane.configure({
                        "item1": self.convert_node_to_widget(pane, control_center, universe)
                    })

            # Add right pane?
            if (right):

                pane = right.get_first_node_by_tag("*")

                if (pane):

                    hpane.configure({
                        "item2": self.convert_node_to_widget(pane, control_center, universe)
                    })


            # Hack
            hpane.on_resize( control_center.get_window_controller().get_default_text_controller().get_text_renderer() )


            # Return widget
            return hpane


        elif (node.tag_type == "map"):

            worldmap = self.create_worldmap().configure(
                node.get_attributes()
            )

            worldmap.__std_update_css__(control_center, universe)

            return worldmap


        elif (node.tag_type == "keyboard"):

            keyboard = self.create_keyboard().configure(
                node.get_attributes()
            )

            keyboard.__std_update_css__(control_center, universe)

            return keyboard
