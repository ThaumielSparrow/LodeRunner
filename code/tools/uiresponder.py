import os
import sys

import copy
import random

from code.game.universe import Universe
from code.game.map import Map, Plane

from code.game.trigger import Trigger

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, logn

from code.constants.common import AI_BEHAVIOR_TRANSLATIONS, AI_BEHAVIOR_REVERSE_TRANSLATIONS, TILE_WIDTH, TILE_HEIGHT, GENUS_ENEMY, GENUS_NPC, GENUS_RESPAWN_ENEMY, GENUS_RESPAWN_PLAYER, GENUS_LEVER, GENUS_GOLD, LAYER_FOREGROUND, LAYER_BACKGROUND, MODE_GAME, MODE_EDITOR, BACKGROUND_MAP_SCALE, BACKGROUND_MAP_PARALLAX_SCALE, PARALLAX_BY_LAYER, SCALE_BY_LAYER
from code.constants.common import COLLISION_NONE, COLLISION_DIGGABLE, COLLISION_UNDIGGABLE, COLLISION_LADDER, COLLISION_MONKEYBAR, COLLISION_DEADLY, COLLISION_BRIDGE, COLLISION_SPIKES_LEFT, COLLISION_SPIKES_RIGHT
from code.constants.paths import UNIVERSES_PATH

from code.constants.newsfeeder import * # Why not all

class UIResponder:

    def __init__(self):
        return

    def handle_event(self, e, control_center, universe):

        # Events that result from handling this event
        results = EventQueue()


        log( e )

        # Fetch GUI manager;
        gui_manager = control_center.get_gui_manager()

        # and the level editor controller;
        editor_controller = control_center.get_editor_controller()

        # also grab a GUI text renderer
        gui_text_renderer = control_center.get_window_controller().get_text_controller_by_name("gui").get_text_renderer()


        # Convenience
        (action, params) = (
            e.get_action(),
            e.get_params()
        )

        logn( "ui-event", "action:  ", action )
        logn( "ui-event", "params:  ", params )

        if ( action == "dialog.close" ):

            dialog = gui_manager.get_widget_by_name( params["target"] )

            if (dialog):

                #dialog.configure_alpha_controller({
                #    "target": 0
                #})

                dialog.hide(animated = False)
                #dialog.hide(
                #    on_complete = "

            else:
                log2( "Warning:  Dialog '%s' does not exist!!" % params["target"] )


        elif ( action == "finish:dialog.close" ):

            dialog = gui_manager.get_widget_by_name( params["target"] )

            if (dialog):
                dialog.hide(animated = False)

            else:
                log2( "Warning:  Dialog '%s' does not exist!!" % params["target"] )


        elif ( action == "dialog.show" ):

            dialog = gui_manager.get_widget_by_name( params["target"] )

            if (dialog):

                #dialog.configure_alpha_controller({
                #    "interval": 0.0,
                #    "target": 1.0
                #})

                dialog.show()

                results.append(
                    dialog.raise_action("show")
                )

                logn( "ui-event show queue", dialog.raise_action("show").queue )
                logn( "ui-event dialog hooks", dialog.hooks )


        elif ( action == "dialog.dropdown" ):

            dialog = gui_manager.get_widget_by_name( params["target"] )

            if (dialog):

                # Dialog where we'll find the referring widget
                ref_dialog = gui_manager.get_widget_by_name( params["dialog"] )

                # Get referring widget
                ref_widget = ref_dialog.find_widget_by_name( params["widget"] )

                # Validate
                if (ref_widget):

                    # Set new dialog position
                    dialog.x = ref_widget.last_render_x
                    dialog.y = ref_widget.last_render_y + ref_widget.get_box_height(gui_text_renderer)

                    logn( "ui-event dialog last-render-x", ref_widget.last_render_x )

                dialog.blur()

                dialog.show()


        # "Activate" a given widget within a given widget (e.g. place focus on a text input field within a dialog)
        elif ( action == "widget:activate-child" ):

            # Find the parent widget
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find the widget we want to activate
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Activate widget
                    child.activate()


        # Reset a given widget within a given widget
        elif ( action == "widget:reset-child" ):

            # Find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find child widget
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Reset child widget
                    child.reset()


        # Set text for a given widget
        elif ( action == "widget:set-child-text" ):

            # Find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find child widget
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Reset child widget
                    child.set_text( params["text"], gui_text_renderer )


        # Check a widget (must be a checkbox)
        elif ( action == "widget:check-child" ):

            # Find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find child widget
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Make sure it's a checkbox
                    if (child.selector == "checkbox"):

                        # Check; raise check events
                        results.append(
                            child.check()
                        )


        # Uncheck a widget (must be a checkbox)
        elif ( action == "widget:uncheck-child" ):

            # Find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find child widget
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Make sure it's a checkbox
                    if (child.selector == "checkbox"):

                        # Check; raise check events
                        results.append(
                            child.uncheck()
                        )


        # Uncheck all of a widget's children (children that are checkboxes)
        elif ( action == "widget:uncheck-all-children" ):

            # Find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Loop all checkbox children
                for child in parent.find_widgets_by_selector("checkbox"):

                    # Check; raise check events
                    results.append(
                        child.uncheck()
                    )


        # Toggle a widget (must be a checkbox)
        elif ( action == "widget:toggle-child" ):

            # Find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find child widget
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Make sure it's a checkbox
                    if (child.selector == "checkbox"):

                        # Check; raise check events
                        results.append(
                            child.toggle()
                        )


        # Populate a given widget with the names of all maps on a given layer.
        # Widget must be a dropdown or a listbox.
        elif ( action == "widget:populate-child-with-map-names" ):

            # find parent
            parent = gui_manager.get_widget_by_name( params["widget"] )

            # Validate
            if (parent):

                # Find child
                child = parent.find_widget_by_name( params["child"] )

                # Validate
                if (child):

                    # Make sure ti's either a listbox or a dropdown
                    if ( child.selector in ("listbox", "dropdown") ):

                        # Empty the dropdown's contents
                        child.empty()

                        # Track new names
                        temp_names = []


                        # Assume active layer
                        layer = editor_controller.active_layer

                        # Check for explicitly specified layer
                        if ("layer" in params):

                            # Which layer do we want?
                            layer = LAYER_FOREGROUND if ( params["layer"] == "foreground" ) else LAYER_BACKGROUND


                        # Loop maps on the given layer
                        for name in universe.map_data[layer]:

                            # Track
                            temp_names.append(name)


                        # Sort maps alphabetically
                        temp_names.sort()

                        # Add options to widget
                        for name in temp_names:

                            # Add new option to the target widget
                            child.add(name, name)


        # Universe submenu
        elif ( action == "click:menu-bar.universe" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.universe")

            if (dialog):
                dialog.hide()


            # New universe
            if ( params["value"] == "menu-bar.universe/new" ):

                dialog = gui_manager.get_widget_by_name("menu-bar.universe.new")

                if (dialog):
                    #dialog.find_widget_by_name("error").set_text("", gui_text_renderer)
                    dialog.show()

            # Load universe
            elif ( params["value"] == "menu-bar.universe/load" ):

                dialog = gui_manager.get_widget_by_name("generic.error")
                dialog.show()

                """
                dialog = gui_manager.get_widget_by_name("menu-bar.universe.load")

                if (dialog):
                    dialog.show()

                    # Populate dropdown with existing universes
                    if (os.path.exists("universes")):

                        files = os.listdir("universes")

                        for f in files:

                            # Remove trailing xml extension.  Ignore invalidly short file names...
                            if (len(f) >= len(".xml")):

                                f = f[0 : len(f) - len(".xml")]
                                dialog.find_widget_by_name("name").add(f, f)
                """

            # Save universe
            elif ( params["value"] == "menu-bar.universe/save" ):

                for layer in (LAYER_BACKGROUND, LAYER_FOREGROUND):

                    universe.update_data_for_maps_on_layer(universe.visible_maps[layer], layer)

                universe.save()

            # Save universe as...
            elif ( params["value"] == "menu-bar.universe/save-as" ):

                dialog = gui_manager.get_widget_by_name("menu-bar.universe.save-as")

                if (dialog):
                    dialog.find_widget_by_name("error").set_text("", gui_text_renderer)
                    dialog.show()


            # Show foreground only
            elif ( params["value"] == "menu-bar.universe/show-foreground" ):

                # Show foreground, hide background
                editor_controller.layer_visibility[LAYER_FOREGROUND] = True
                editor_controller.layer_visibility[LAYER_BACKGROUND] = False

                # Active layer is foreground
                editor_controller.active_layer = LAYER_FOREGROUND


            # Show background only
            elif ( params["value"] == "menu-bar.universe/show-background" ):

                # Show background, hide foreground
                editor_controller.layer_visibility[LAYER_BACKGROUND] = True
                editor_controller.layer_visibility[LAYER_FOREGROUND] = False

                # Active layer is background
                editor_controller.active_layer = LAYER_BACKGROUND


            # Show both foreground and background
            elif ( params["value"] == "menu-bar.universe/show-all" ):

                # Show both
                editor_controller.layer_visibility[LAYER_FOREGROUND] = True
                editor_controller.layer_visibility[LAYER_BACKGROUND] = True

                # Foreground is active when rendering both layers
                editor_controller.active_layer = LAYER_FOREGROUND


            # Toggle zoom on background (zoom obeyed only when focused exclusively on background)
            elif ( params["value"] == "menu-bar.universe/toggle-background-zoom" ):

                # Toggle
                #editor_controller["zoom-background"] = (not editor_controller["zoom-background"])
                log2("**Not coded into editor controller")
                pass

        elif (0):
            logn( "ui-event", "Disable all other events" )
            pass


        # Toggle foreground visibility
        elif ( action == "universe:toggle-foreground" ):

            # Update in accordance with the checkbox setting
            editor_controller.layer_visibility[LAYER_FOREGROUND] = params["checked"]


        # Toggle background visibility
        elif ( action == "universe:toggle-background" ):

            # Update in accordance with the checkbox setting
            editor_controller.layer_visibility[LAYER_BACKGROUND] = params["checked"]


        # Use a given layer (by readable name)
        elif ( action == "universe:use-layer" ):

            # Convenience
            layer_name = params["layer"]

            # Check against readable name
            if (layer_name == "foreground"):

                # Set foreground as active
                editor_controller.active_layer = LAYER_FOREGROUND

            # Background?
            elif (layer_name == "background"):

                # Set background as active
                editor_controller.active_layer = LAYER_BACKGROUND


        # Set the zoom level for the editor
        elif ( action == "universe:set-zoom" ):

            # Easy
            editor_controller.zoom_controller.configure({
                "target": float( params["zoom"] )
            })


        # Maps submenu
        elif ( action == "click:menu-bar.maps" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps")

            if (dialog):
                dialog.hide()


            # New map
            if (params["value"] == "menu-bar.maps/new"):

                results.add(
                    action = "dialog.show",
                    params = {
                        "target": "menu-bar.maps.new"
                    }
                )
                #dialog = gui_manager.get_widget_by_name("menu-bar.maps.new")
                #if (dialog):
                #    dialog.show()

            # Import map
            elif (params["value"] == "menu-bar.maps/import"):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.import")

                if (dialog):
                    dialog.show()

                    # Populate dropdown with existing maps
                    if (os.path.exists("maps")):

                        files = os.listdir("maps")

                        for f in files:

                            # Remove trailing xml extension.  Ignore invalidly short file names...
                            if (len(f) >= len(".xml")):

                                f = f[0 : len(f) - len(".xml")]
                                dialog.find_widget_by_name("name").add(f, f)

            # Save map
            elif (params["value"] == "menu-bar.maps/save"):

                m = universe.get_active_map()

                if (m):

                    # Already saved?  Just use the same name...
                    if (m.saved == True):
                        m.save( os.path.join( universe.get_working_map_data_path(), "%s.xml" % m.name) )

                    # Nope... need to prompt for a name...
                    else:

                        dialog = gui_manager.get_widget_by_name("menu-bar.maps.save-as")

                        if (dialog):
                            dialog.show()


                    # Newsfeeder update
                    control_center.get_window_controller().get_newsfeeder().post({
                        "type": NEWS_GENERIC_ITEM,
                        "title": "Map Saved",
                        "content": m.name
                    })

            # Save map as...
            elif (params["value"] == "menu-bar.maps/save-as"):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.save-as")

                if (dialog):
                    dialog.show()

            # Import map into universe
            elif (params["value"] == "menu-bar.maps/import"):
                pass


            # Show the "map params" dialog
            elif ( params["value"] == "menu-bar.maps/params" ):

                # Forward a show dialog event
                results.add(
                    action = "dialog.show",
                    params = {
                        "target": "menu-bar.maps.params"
                    }
                )

                # Grab a reference to the dialog we're going to show
                dialog = gui_manager.get_widget_by_name("menu-bar.maps.params")

                # Validate
                if (dialog):

                    # Trigger on onchange of the dropdown to show the proper overlay
                    results.append(
                        dialog.find_widget_by_name("param").raise_action("change")
                    )


            # Map properties
            elif (params["value"] == "menu-bar.maps/properties"):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.properties")

                if (dialog):

                    temp_names = []

                    # Populate this universe's existing map names...
                    for key in universe.map_data[ editor_controller.active_layer ]:
                        temp_names.append(key)

                    temp_names.sort()

                    for name in temp_names:
                        dialog.find_widget_by_name("name").add(name, name)

                    dialog.find_widget_by_name("width").set_text("", gui_text_renderer)
                    dialog.find_widget_by_name("height").set_text("", gui_text_renderer)

                    if (universe.active_map_name != None):

                        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

                        dialog.find_widget_by_name("width").set_text("%d" % m.get_width(), gui_text_renderer)
                        dialog.find_widget_by_name("height").set_text("%d" % m.get_height(), gui_text_renderer)

                        # Change redline dropdown to "on" if necessar
                        if ( m.is_redlined() ):
                            dialog.find_widget_by_name("redline").select_by_value("on")

                        else:
                            dialog.find_widget_by_name("redline").select_by_value("off")

                        # Try to select the current map name
                        dialog.find_widget_by_name("name").select(universe.active_map_name)

                    dialog.show()


            # Goto map...
            elif (params["value"] == "menu-bar.maps/goto"):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.goto")

                if (dialog):

                    dialog.find_widget_by_name("name").clear()

                    temp_names = []

                    # Populate this universe's existing map names...
                    for key in universe.map_data[ editor_controller.active_layer ]:
                        temp_names.append(key)

                    temp_names.sort()

                    for name in temp_names:
                        dialog.find_widget_by_name("name").add(name, name)

                    dialog.show()


            # Select tile
            elif (params["value"] == "menu-bar.maps/select-tile"):
                editor_controller.selecting_tile = True


            # Create entity
            elif (params["value"] == "menu-bar.maps/select-entity"):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.entities.properties")

                if (dialog):

                    m = universe.get_active_map()

                    if (m == None):
                        return

                    else:

                        dialog.find_widget_by_name("do").set_value("create")

                        dialog.find_widget_by_name("tx").set_value("0")
                        dialog.find_widget_by_name("ty").set_value("0")

                        dialog.find_widget_by_name("entity-type").set_value("")
                        dialog.find_widget_by_name("entity-index").set_value(-1)

                        dialog.find_widget_by_name("name").set_text("", gui_text_renderer)
                        dialog.find_widget_by_name("type").select_by_value("enemy")
                        dialog.find_widget_by_name("ai-behavior").select_by_value(AI_BEHAVIOR_TRANSLATIONS["normal"])

                        # Emulate an onchange event to show the appropriate details subdialog
                        e = {
                            "event-info": {
                                "action": "maps.entities.properties:change-type"
                            }
                        }

                        dialog.show()


            # Move map to foreground
            elif (params["value"] == "menu-bar.maps/move-to-foreground"):

                # Get active map
                m = universe.get_active_map()

                # Update layer
                m.configure({
                    "x": int( int( (m.x * TILE_WIDTH) * BACKGROUND_MAP_SCALE ) / TILE_WIDTH ),
                    "y": int( int( (m.y * TILE_HEIGHT) * BACKGROUND_MAP_SCALE ) / TILE_HEIGHT ),
                    "layer": LAYER_FOREGROUND
                })


                for layer in universe.visible_maps:

                    universe.visible_maps[layer].clear()

                # Update map layer data on both layers
                universe.map_data[LAYER_FOREGROUND][m.name] = universe.map_data[LAYER_BACKGROUND].pop(m.name)

                # Switch active layer to follow map
                editor_controller.active_layer = LAYER_FOREGROUND


            # Move map to background
            elif (params["value"] == "menu-bar.maps/move-to-background"):

                # Get active map
                universe.map_data[LAYER_BACKGROUND][ universe.active_map_name ] = universe.map_data[LAYER_FOREGROUND].pop( universe.active_map_name )

                universe.visible_maps[LAYER_BACKGROUND][ universe.active_map_name ] = universe.visible_maps[LAYER_FOREGROUND].pop( universe.active_map_name )


                # Switch active layer to follow map
                editor_controller.active_layer = LAYER_BACKGROUND


                m = universe.get_active_map()


                log2( "before:", (m.x, m.y) )

                # Update layer
                m.configure({
                    "x": int( int( (m.x * TILE_WIDTH) / BACKGROUND_MAP_SCALE ) / TILE_WIDTH ),
                    "y": int( int( (m.y * TILE_HEIGHT) / BACKGROUND_MAP_SCALE ) / TILE_HEIGHT ),
                    "layer": LAYER_BACKGROUND
                })

                log2( "after:", (m.x, m.y) )



                # Update map layer data on both layers
                #universe.map_data[LAYER_BACKGROUND][m.name] = m


                if ( editor_controller.active_layer == LAYER_BACKGROUND and (editor_controller.layer_visibility[LAYER_FOREGROUND] == True) ):

                    #m = universe.get_active_map()
                    m.center_within_camera_using_parallax( universe.camera )

                else:

                    m.center_within_camera( universe.camera, scale = 2 )


        # Planes submenu
        elif ( action == "click:menu-bar.planes" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes")

            if (dialog):
                dialog.hide()


            # New plane
            if (params["value"] == "menu-bar.planes/new"):

                results.add(
                    action = "dialog.show",
                    params = {
                        "target": "menu-bar.planes.new"
                    }
                )

                """
                dialog = gui_manager.get_widget_by_name("menu-bar.planes.new")

                if (dialog):
                    dialog.find_widget_by_name("error").set_text("", gui_text_renderer)
                    dialog.show()
                """

            # Select plane
            elif (params["value"] == "menu-bar.planes/select-plane"):

                dialog = gui_manager.get_widget_by_name("menu-bar.planes.select-plane")

                if (dialog):

                    # Populate existing plane names with z-indices...
                    m = universe.visible_maps[editor_controller.active_layer][ universe.active_map_name ]

                    dialog.find_widget_by_name("name").clear()

                    # Add in current z-index order...
                    for z in range(0, len(m.planes)):

                        for plane in m.planes:

                            if (plane.z_index == z):
                                dialog.find_widget_by_name("name").add(plane.name, "%d" % z)

                    # Select the currently active plane...
                    dialog.find_widget_by_name("name").select_by_value(m.active_plane_z_index)

                    dialog.show()

            # Order planes
            elif (params["value"] == "menu-bar.planes/order-planes"):

                dialog = gui_manager.get_widget_by_name("menu-bar.planes.order-planes")

                if (dialog):

                    # Populate existing plane names with z-indices...
                    m = universe.visible_maps[editor_controller.active_layer][ universe.active_map_name ]

                    dialog.find_widget_by_name("order").clear()

                    # Add in current z-index order...
                    for z in range(0, len(m.planes)):

                        for plane in m.planes:

                            if (plane.z_index == z):
                                dialog.find_widget_by_name("order").add(plane.name, "%d" % z)

                    # Select the currently active plane...
                    dialog.find_widget_by_name("order").select_by_value(m.active_plane_z_index)

                    dialog.show()


            # Copy a random plane
            elif ( params["value"] == "menu-bar.planes/copy-random" ):

                # Get the active map
                m = universe.get_active_map()

                # Validate
                if (m):

                    # Gather candidates
                    pool = []

                    # Only "mold*" planes work
                    for plane in m.planes:

                        # mold*
                        if ( plane.name.startswith("mold") ):

                            # Add to pool
                            pool.append(plane)

                    # Does the map have at least one useable plane?
                    if ( len(pool) > 0 ):

                        # Select an index at random
                        pos = random.randint( 0, len(pool) - 1 )

                        # Copy the winning plane to the "clipboard"
                        editor_controller.clipboard.plane = copy.deepcopy( pool[pos] )

                        log2( "Copy successful" )


            # Copy a random plane from the LAST map, then paste it on the CURRENT map
            # (Hotkey only (?))
            elif ( params["value"] == "menu-bar.planes/copy-random-from-last-and-paste" ):

                # What's the last map we were on?
                last_map_name = editor_controller.last_map_name

                # Was there one?
                if (last_map_name):

                    # Raise a "go to last map" event
                    results.add(
                        action = "click:rk.offmap",
                        params = {
                            "value": "rk.offmap/goto-last",
                            "is-hotkey": "1"
                        }
                    )

                    # Now raise a "copy random plane" event
                    results.add(
                        action = "click:menu-bar.planes",
                        params = {
                            "value": "menu-bar.planes/copy-random"
                        }
                    )

                    # Next, return to the original map
                    results.add(
                        action = "click:rk.offmap",
                        params = {
                            "value": "rk.offmap/goto-last",
                            "is-hotkey": "1"
                        }
                    )

                    # Lastly, raise the "paste plane" event
                    results.add(
                        action = "click:rk.generic",
                        params = {
                            "value": "rk.generic/paste-plane"
                        }
                    )


            # Plane properties
            elif (params["value"] == "menu-bar.planes/properties"):

                dialog = gui_manager.get_widget_by_name("menu-bar.planes.properties")

                if (dialog):

                    # Get current map, plane
                    m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

                    plane = m.planes[ m.active_plane_z_index ]

                    dialog.find_widget_by_name("name").set_text("%s" % plane.name, gui_text_renderer)

                    ## Obselete... I just drag and drop planes to move them now.
                    ##dialog.find_widget_by_name("relative-x").set_text("%d" % plane.x, gui_text_renderer)
                    ##dialog.find_widget_by_name("relative-y").set_text("%d" % plane.y, gui_text_renderer)

                    dialog.find_widget_by_name("width").set_text("%d" % plane.get_width(), gui_text_renderer)
                    dialog.find_widget_by_name("height").set_text("%d" % plane.get_height(), gui_text_renderer)

                    results.add(
                        action = "dialog.show",
                        params = {
                            "target": "menu-bar.planes.properties"
                        }
                    )
                    #dialog.show()


        # Triggers submenu
        elif ( action == "click:menu-bar.triggers" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.triggers")

            if (dialog):
                dialog.hide()


            # New trigger
            if (params["value"] == "menu-bar.triggers/new"):

                dialog = gui_manager.get_widget_by_name("menu-bar.triggers.new")

                if (dialog):

                    dialog.find_widget_by_name("width").set_text("1", gui_text_renderer)
                    dialog.find_widget_by_name("height").set_text("1", gui_text_renderer)

                    dialog.find_widget_by_name("tx").set_value("0")
                    dialog.find_widget_by_name("ty").set_value("0")

                    dialog.find_widget_by_name("name").set_text("", gui_text_renderer)
                    dialog.find_widget_by_name("prompt").set_text("", gui_text_renderer)

                # Trigger show event
                results.add(
                    action = "dialog.show",
                    params = {
                       "target": "menu-bar.triggers.new"
                    }
                )
                #dialog.show()


        # Scripts submenu
        elif ( action == "click:menu-bar.scripts" ):

            # New script
            if (params["value"] == "menu-bar.scripts/new"):

                results.add(
                    action = "dialog.show",
                    params = {
                        "target": "menu-bar.scripts.new"
                    }
                )

                """
                dialog = gui_manager.get_widget_by_name("menu-bar.scripts.new")
                if (dialog):
                    dialog.show()
                """


            # New session variable dialog
            elif (params["value"] == "menu-bar.scripts/new-session-variable"):

                dialog = gui_manager.get_widget_by_name("new-session-variable")

                if (dialog):

                    results.add(
                        action = "dialog.show",
                        params = {
                            "target": "new-session-variable"
                        }
                    )


            # Manage session variables dialog
            elif (params["value"] == "menu-bar.scripts/manage-session-variables"):

                dialog = gui_manager.get_widget_by_name("manage-session-variables")

                if (dialog):

                    elem = dialog.find_widget_by_name("variable2")

                    if (elem):
                        gui_manager.populate_dropdown_with_session_variables(elem, control_center, universe)

                    #dialog.find_widget_by_name("error").set_text("", gui_text_renderer)

                    results.add(
                        action = "dialog.show",
                        params = {
                            "target": "manage-session-variables"
                        }
                    )
                    #dialog.show()

            # Script editor
            elif (params["value"] == "menu-bar.scripts/edit"):

                dialog = gui_manager.get_widget_by_name("menu-bar.scripts.script-editor")

                if (dialog):

                    elem = dialog.find_widget_by_name("script")

                    if (elem):
                        gui_manager.populate_dropdown_with_scripts(elem, control_center, universe)

                    dialog.show()

                    # Emulate an onchange event to populate the packets listbox
                    e = {
                        "event-info": {
                            "action": "script-editor:change-script"
                        }
                    }

                    results.append(
                        elem.raise_action("change")
                    )

                    #self.handle_event(e, control_center, universe)


        elif ( action == "preview-dialog" ):

            dialog = gui_manager.get_widget_by_name( e["parent"] )

            selected_dialog = gui_manager.get_widget_by_name( dialog.find_widget_by_name("name").get_value() )

            if (selected_dialog):

                for (alias, x) in p_app.gui_objects:
                    if (alias != "dialog-previewer"):
                        gui_manager.get_widget_by_name(alias).hide()

                selected_dialog.show()


        # Create a new universe
        elif ( action == "universe.new" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.universe.new")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_text()

                u = Universe(param, is_new = True)

                if (u.error):
                    dialog.find_widget_by_name("error").set_text(u.error, gui_text_renderer)

                else:

                    p_app.universe = u

                    p_app.universe.visible_maps[LAYER_FOREGROUND] = {}

                    dialog.hide()

        # Load a universe
        elif ( action == "universe.load" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.universe.load")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_value()

                u = Universe(param)
                p_app.universe = u

                dialog.hide()

        # Save universe as...
        elif ( action == "universe.save-as" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.universe.save-as")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_text()

                u = Universe(param, is_new = True)

                if (u.error):
                    dialog.find_widget_by_name("error").set_text(u.error, gui_text_renderer)

                else:

                    p_app.universe = u
                    p_app.universe.save()

                    dialog.hide()


        # Create new map
        elif ( action == "maps.new" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.new")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_text().strip()

                # Validate name
                if ( len(param) == 0 ):

                    log2( "Error:  Cannot create map with name '%s'" % param )

                # Make sure it doesn't already exist
                elif ( os.path.exists( os.path.join(UNIVERSES_PATH, universe.name, "%s.xml" % param) ) ):

                    log2( "Error:  Map '%s' already exists!" % param )

                else:

                    # Convenience
                    (cameraX, cameraY) = (
                        editor_controller.camera.x,
                        editor_controller.camera.y
                    )


                    # Create a new map objectt
                    m = Map(
                        name = param,
                        universe = universe,
                        options = {
                            "is-new": True
                        },
                        parent = universe
                    )


                    # Add a default plane to the map...
                    plane = Plane()

                    # Default plane dimensions
                    #plane.set_height(10)
                    #plane.set_width(10)
                    plane.set_height(16) # For main-menu maps
                    plane.set_width(17)  # For main-menu maps

                    m.planes.append(plane)

                    # Position the map in the northwest of the current camera view
                    (pad_x, pad_y) = (3, 3)


                    # Calculate default map coordinates
                    (x, y) = (
                        pad_x + int( (editor_controller.camera.x / 1) / TILE_WIDTH),
                        pad_y + int( (editor_controller.camera.y / 1) / TILE_HEIGHT)
                    )

                    # Scale to background if necessary
                    if ( editor_controller.active_layer == LAYER_BACKGROUND ):

                        """
                        # Adjust for map size scale
                        (x, y) = (
                            int(x / BACKGROUND_MAP_SCALE),
                            int(y / BACKGROUND_MAP_SCALE)
                        )

                        # Further, adjust for parallax movement
                        (x, y) = (
                            x + int( -editor_controller.camera.x / BACKGROUND_MAP_PARALLAX_SCALE ),
                            y + int( -editor_controller.camera.y / BACKGROUND_MAP_PARALLAX_SCALE )
                        )
                        """

                        # Get parallax ratio
                        parallax = PARALLAX_BY_LAYER[editor_controller.active_layer]

                        # Get scale ratio
                        scale = SCALE_BY_LAYER[editor_controller.active_layer]


                        # First we must adjusted for the size scale
                        (adjustedX, adjustedY) = (
                            (cameraX / scale),
                            (cameraY / scale)
                        )

                        # We must also factor in the parallax for the (adjusted) camera location
                        (px, py) = universe.camera.get_parallax_offsets_at_location( (cameraX / scale), (cameraY / scale), parallax = parallax)

                        # Adjust again
                        (adjustedX, adjustedY) = (
                            adjustedX - px,
                            adjustedY - py
                        )


                        # Now apply the final location calculation
                        #m.x = int(adjustedX / TILE_WIDTH)
                        #m.y = int(adjustedY / TILE_HEIGHT)

                        (x, y) = (
                            int(adjustedX / TILE_WIDTH),
                            int(adjustedY / TILE_HEIGHT)
                        )





                    log2(m, m.planes)
                    # Configure map position and layer
                    m.configure({
                        "x": x,
                        "y": y,
                        "layer": editor_controller.active_layer
                    })


                    log2(m, m.planes)
                    # Fit the plane...
                    m.update_dimensions()

                    # Try to add the map to the universe
                    result = universe.add_map_to_layer(m, editor_controller.active_layer, control_center)

                    if (result):

                        dialog.hide()

                        # Save the new map
                        #m.save( os.path.join( universe.get_working_map_data_path(), "%s.xml" % param) )

                        # Add the map to the universe's visible / unsaved maps on the active layer
                        universe.visible_maps[editor_controller.active_layer][m.name] = m


                        # Update universe's map data so that it knows this new map's location / dimensions...
                        for layer in (LAYER_BACKGROUND, LAYER_FOREGROUND):

                            universe.update_data_for_maps_on_layer(universe.visible_maps[layer], layer)


                        # Save the universe with the new map in it...
                        universe.save()

                    else:

                        dialog.find_widget_by_name("error").set_text("Duplicate Name", gui_text_renderer)


        # Import map to the universe
        elif ( action == "maps.import" ):
            pass


        # Save map as...
        elif ( action == "maps.save-as" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.save-as")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_text()

                # Prevent overwrites
                if (os.path.exists( os.path.join("maps", "%s.xml" % param) )):
                    dialog.find_widget_by_name("error").set_text("Already Exists", gui_text_renderer)

                else:
                    m = universe.visible_maps[editor_controller.active_layer][ universe.active_map_name ]
                    m.save( os.path.join( universe.get_working_map_data_path(), "%s.xml" % param ) )

                    dialog.hide()


        # Change dropdown selection in map params dialog
        elif ( action == "menu-bar.maps.params:change" ):

            # Fetch params dialog
            dialog = gui_manager.get_widget_by_name("menu-bar.maps.params")

            # Validate
            if (dialog):

                # Get current value
                value = dialog.find_widget_by_name("param").get_value()

                logn( "ui-event", "value = ", value )

                # Hide all secondary overlay containers
                for overlay in dialog.find_widget_by_name("overlays").get_widgets_by_selector("stack2"):

                    # Hide
                    overlay.hide()

                    logn( "ui-event", "hide:  ", overlay )


                # Next, find the overlay that corresponds with the current dropdown selection
                overlay = dialog.find_widget_by_name("overlays").get_widget_by_name(value)

                # Validate
                if (overlay):

                    # Show this particular overlay
                    overlay.show()


        # Update active map params according to map params dialog settings.
        # We call this event each time one of the overlay dropdowns (or text inputs) changes...
        elif ( action == "menu-bar.maps.params:update" ):

            # Grab the map params dialog
            dialog = gui_manager.get_widget_by_name("menu-bar.maps.params")

            # Validate
            if (dialog):

                # Fetch active map
                m = universe.get_active_map()

                # Loop through dropdowns
                for overlay in dialog.find_widget_by_name("overlays").find_widgets_by_selector("dropdown"):

                    # Update given map param
                    m.set_param(
                        overlay.name,
                        overlay.get_value()
                    )

                # Loop through text entry fields
                for overlay in dialog.find_widget_by_name("overlays").find_widgets_by_selector("input"):

                    # Update given map param
                    m.set_param(
                        overlay.name,
                        overlay.get_value()
                    )


        # Refresh map properties (onchange of dropdown)
        elif ( action == "menu-bar.maps.properties:refresh" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.properties")

            if (dialog):
                param = dialog.find_widget_by_name("name").get_value()

                layer = editor_controller.active_layer

                # I prefer to get fresh, current data from visible maps themselves...
                if (param in universe.visible_maps[layer]):

                    dialog.find_widget_by_name("universal-x").set_text("%d" % universe.visible_maps[layer][param].x, gui_text_renderer)
                    dialog.find_widget_by_name("universal-y").set_text("%d" % universe.visible_maps[layer][param].y, gui_text_renderer)

                    dialog.find_widget_by_name("width").set_text("%d" % universe.visible_maps[layer][param].get_width(), gui_text_renderer)
                    dialog.find_widget_by_name("height").set_text("%d" % universe.visible_maps[layer][param].get_height(), gui_text_renderer)

                else:

                    dialog.find_widget_by_name("universal-x").set_text("%d" % universe.map_data[layer][param].x, gui_text_renderer)
                    dialog.find_widget_by_name("universal-y").set_text("%d" % universe.map_data[layer][param].y, gui_text_renderer)

                    dialog.find_widget_by_name("width").set_text("%d" % universe.map_data[layer][param].get_width(), gui_text_renderer)
                    dialog.find_widget_by_name("height").set_text("%d" % universe.map_data[layer][param].get_height(), gui_text_renderer)

        # Save map properties
        elif ( action == "menu-bar.maps.properties:save" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.properties")

            if (dialog):

                m = universe.get_active_map()

                if (m):

                    m.set_param(
                        "redline",
                        "1" if ( dialog.find_widget_by_name("redline").get_value() == "on" ) else "0"
                    )

                dialog.hide()

        # Goto some map
        elif ( action == "menu-bar.maps.goto:go" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.goto")

            if (dialog):

                # Track current map as "last map"
                editor_controller.last_map_name = universe.get_active_map().name

                editor_controller.camera.last_x = universe.camera.x
                editor_controller.camera.last_y = universe.camera.y

                # Remember where the camera was, too
                #editor_controller["last-map-camera-x"] = editor_controller.camera.x
                #editor_controller["last-map-camera-y"] = editor_controller.camera.y

                map_name = dialog.find_widget_by_name("name").get_value()

                universe.activate_map_on_layer_by_name(map_name, editor_controller.active_layer, game_mode = MODE_EDITOR, control_center = control_center)

                m = universe.get_active_map()



                if ( editor_controller.active_layer == LAYER_BACKGROUND and editor_controller.layer_visibility[LAYER_FOREGROUND] == False ):

                    m.center_within_camera_using_parallax( universe.camera )

                else:

                    m.center_within_camera( universe.camera )


                dialog.hide()

        # Select entity
        elif ( action == "maps.select-entity" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.entities.properties")

            if (dialog):

                m = universe.get_active_map()

                if (m == None):
                    return


                entity = editor_controller.mouse.rightclick.object_reference

                index = m.get_entity_index(entity)

                if (index >= 0):

                    dialog.find_widget_by_name("do").set_value("create")

                    dialog.find_widget_by_name("entity-type").set_value(entity.genus)
                    dialog.find_widget_by_name("entity-index").set_value(index)

                    dialog.find_widget_by_name("name").set_text("", gui_text_renderer)
                    dialog.find_widget_by_name("type").select_by_value("enemy")
                    dialog.find_widget_by_name("ai-behavior").select_by_value(AI_BEHAVIOR_TRANSLATIONS["normal"])

                    # Emulate an onchange event to show the appropriate details subdialog
                    e = {
                        "event-info": {
                            "action": "maps.entities.properties:change-type"
                        }
                    }

                    self.handle_event(e, control_center, universe)

                    dialog.show()

        # Toggle subdialog depending on selected entity
        elif ( action == "maps.entities.properties:change-type" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.entities.properties")

            if (dialog):

                value = int( dialog.find_widget_by_name("type").get_value()[0] )

                # Lever-specific choices
                if (value == GENUS_LEVER):

                    dialog.find_widget_by_name("details.generic").hide()
                    dialog.find_widget_by_name("details.lever").show()

                # Generic information
                else:

                    dialog.find_widget_by_name("details.generic").show()
                    dialog.find_widget_by_name("details.lever").hide()

        # Save entity properties
        elif ( action == "maps.entities.properties:save" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.maps.entities.properties")

            if (dialog):

                m = universe.get_active_map()

                if (m):

                    command = dialog.find_widget_by_name("do").get_value()

                    if (command == "create"):

                        value = dialog.find_widget_by_name("type").get_value()

                        entity_type = 0
                        entity_species = ""

                        if ( int(value[0]) == GENUS_NPC ):

                            (genus, species) = value.split(":")

                            entity_type = int(genus)
                            entity_species = species

                        else:
                            entity_type = int( dialog.find_widget_by_name("type").get_value() )

                        entity_name = dialog.find_widget_by_name("name").get_text()

                        entity_ai_behavior = int( AI_BEHAVIOR_TRANSLATIONS[dialog.find_widget_by_name("ai-behavior").get_value()] )

                        entity = m.add_entity_by_type(entity_type, entity_species, entity_name, entity_ai_behavior)

                        if (entity):

                            entity.x = int( dialog.find_widget_by_name("tx").get_value() * TILE_WIDTH )
                            entity.y = int( dialog.find_widget_by_name("ty").get_value() * TILE_HEIGHT )

                            entity.ai_state.ai_behavior = entity_ai_behavior

                            entity.nick = dialog.find_widget_by_name("details.generic").find_widget_by_name("nick").get_text()
                            #entity.nick = "Bomb Vending Machine"
                            entity.title = dialog.find_widget_by_name("details.generic").find_widget_by_name("title").get_text()

                            #""" Debug - hack in class name, I'm placing bomb terminals """
                            #entity.class_name = "bomb-vending-machine"
                            #""" End Debug """


                            # Levers need a couple of additional details...
                            if (entity_type == GENUS_LEVER):

                                entity.mount = int( dialog.find_widget_by_name("details.lever").find_widget_by_name("mount").get_value() )
                                entity.position = int( dialog.find_widget_by_name("details.lever").find_widget_by_name("position").get_value() )

                    elif (command == "update"):

                        entity_type = int( dialog.find_widget_by_name("entity-type").get_value() )
                        entity_index = int( dialog.find_widget_by_name("entity-index").get_value() )

                        entity = m.get_entity_by_type_and_index(entity_type, entity_index)

                        entity.name = dialog.find_widget_by_name("name").get_text()
                        entity.ai_state.ai_behavior = int( AI_BEHAVIOR_TRANSLATIONS[dialog.find_widget_by_name("ai-behavior").get_value()] )

                        entity.nick = dialog.find_widget_by_name("details.generic").find_widget_by_name("nick").get_text()
                        entity.title = dialog.find_widget_by_name("details.generic").find_widget_by_name("title").get_text()

                        # Levers need a couple of additional details...
                        if (entity_type == GENUS_LEVER):

                            entity.mount = int( dialog.find_widget_by_name("details.lever").find_widget_by_name("mount").get_value() )
                            entity.position = int( dialog.find_widget_by_name("details.lever").find_widget_by_name("position").get_value() )

                dialog.hide()

        # Create a plane
        elif ( action == "planes.new:create" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.new")

            if (dialog):

                m = universe.get_active_map()

                if (m):

                    plane = Plane()
                    plane.name = dialog.find_widget_by_name("name").get_text()

                    # Default it to 5x5
                    plane.set_height(5)
                    plane.set_width(5)

                    # Add it to the top of the plane stack
                    for p in m.planes:

                        if (plane.z_index < p.z_index):
                            plane.z_index = p.z_index + 1

                    m.add_plane(plane)
                    m.update_plane_z_indices()

                    m.active_plane_z_index = len(m.planes) - 1

                dialog.hide()

        # Changed selection within plane selection
        elif ( action == "menu-bar.planes.select-plane:selection-changed" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.select-plane")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_value() # The z-index

                # I guess if we're looking at the map currently, we'll automatically switch to the various planes in real-time as the dropdown changes
                if ( universe.active_map_name in universe.visible_maps[ editor_controller.active_layer ] ):

                    # So hitting "select" doesn't really do anything, or it's redundant, anyway.
                    universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ].active_plane_z_index = int(param)

        # Select plane within map
        elif ( action == "planes.select-plane" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.select-plane")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_value() # The z-index

                # Validate that we're looking at the active map (and we're on its layer)
                if ( universe.active_map_name in universe.visible_maps[ editor_controller.active_layer ] ):

                    # Somewhat redundant (okay, completely redundant...)
                    universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ].active_plane_z_index = int(param)

                dialog.hide()

        # Save updated plane properties
        elif ( action == "planes.properties:save" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.properties")

            if (dialog):

                # Which z-index were we editing?
                z_index = int( dialog.find_widget_by_name("z-index").get_value() )

                m = universe.get_active_map()

                if (m):

                    # Find the appropriate plane
                    for plane in m.planes:

                        if (plane.z_index == z_index):

                            plane.name = "%s" % dialog.find_widget_by_name("name").get_text()

                            plane.x = int( dialog.find_widget_by_name("relative-x").get_text() )
                            plane.y = int( dialog.find_widget_by_name("relative-y").get_text() )

                            plane.set_height( int( dialog.find_widget_by_name("height").get_text() ) )
                            plane.set_width( int( dialog.find_widget_by_name("width").get_text() ) )

                dialog.hide()

        # Selected a plane in the order-planes listbox...
        elif ( action == "planes.order-planes:changed" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.order-planes")

            if (dialog):

                param = int( dialog.find_widget_by_name("order").get_value() ) # The z-index of the plane to adjust...

                # Make sure we're looking at the active map
                if ( universe.active_map_name in universe.visible_maps[ editor_controller.active_layer ] ):

                    universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ].active_plane_z_index = param

        # Move plane down
        elif ( action == "planes.order-planes:lower" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.order-planes")

            if (dialog):
                param = int( dialog.find_widget_by_name("order").get_value() ) # The z-index of the plane to adjust...

                # Flip it with the plane above it...
                if (param > 0):

                    plane_a = None
                    plane_b = None

                    # Make sure we're looking at the active map
                    if ( universe.active_map_name in universe.visible_maps[ editor_controller.active_layer ] ):

                        # Convenience
                        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

                        for plane in m.planes:
                            log( "%s:  %d" % (plane.name, plane.z_index) )

                        for plane in m.planes:

                            if (plane.z_index == (param - 1)):
                                plane_a = plane
                                break

                        for plane in m.planes:

                            if (plane.z_index == param):
                                plane_b = plane
                                break

                        if (plane_a != None and plane_b != None):

                            plane_a.z_index += 1
                            plane_b.z_index -= 1

                        # Update the currently active plane value...
                        m.active_plane_z_index = (param - 1)

                        log( "universe.visible_maps[ universe.active_map_name ].active_plane_z_index = ", m.active_plane_z_index )

                # Trigger a selection on the new z-index
                dialog.find_widget_by_name("order").select_by_value(param - 1)

        # Refresh plane order listing
        elif ( action == "menu-bar.planes.order-planes:refresh" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.order-planes")

            if (dialog):

                # Validate that we're looking at the active map
                if ( universe.active_map_name in universe.visible_maps[ editor_controller.active_layer ] ):

                    # Populate existing plane names with z-indices...
                    m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

                    dialog.find_widget_by_name("order").clear()

                    # Add in current z-index order...
                    for z in range(0, len(m.planes)):

                        for plane in m.planes:

                            if (plane.z_index == z):
                                dialog.find_widget_by_name("order").add(plane.name, "%d" % z)

                    # Select the currently active plane...
                    results.append(
                        dialog.find_widget_by_name("order").select_by_value( "%d" % m.active_plane_z_index )
                    )

                    dialog.show()


        # Commit pad plane
        elif ( action == "menu-bar.planes.pad:apply" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.planes.pad")

            if (dialog):

                plane = editor_controller.mouse.rightclick.object_reference

                plane.pad(x = int(dialog.find_widget_by_name("pad-left").get_text()), y = int(dialog.find_widget_by_name("pad-top").get_text()))

                dialog.hide()

        # New trigger
        elif ( action == "triggers.new" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.triggers.new")

            if (dialog):

                # Add a new trigger to the map
                universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ].triggers.append(
                    Trigger().configure({
                        "name": dialog.find_widget_by_name("name").get_text(),
                        "x": int( dialog.find_widget_by_name("tx").get_value() ),
                        "y": int( dialog.find_widget_by_name("ty").get_value() ),
                        "width": int( dialog.find_widget_by_name("width").get_text() ),
                        "height": int( dialog.find_widget_by_name("height").get_text() ),
                        "behavior": int( dialog.find_widget_by_name("behavior").get_value() ),
                        "prompt": dialog.find_widget_by_name("prompt").get_text()
                    })
                )

                dialog.hide()


        # Entities right-click menu
        elif ( action == "click:rk.entities" ):

            dialog = gui_manager.get_widget_by_name("rk.entities")

            if (dialog):
                dialog.hide()

            # Move entity
            if (params["value"] == "rk.entities/move"):

                entity = editor_controller.mouse.rightclick.object_reference

                editor_controller.drag.object_type = "entity"
                editor_controller.drag.object_reference = entity

            # Edit entity
            elif (params["value"] == "rk.entities/edit"):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.entities.properties")

                if (dialog):

                    m = universe.get_active_map()

                    if (m == None):
                        return


                    entity = editor_controller.mouse.rightclick.object_reference

                    index = m.get_entity_index(entity)

                    if (index >= 0):

                        dialog.find_widget_by_name("do").set_value("update")

                        dialog.find_widget_by_name("entity-type").set_value(entity.genus)
                        dialog.find_widget_by_name("entity-index").set_value(index)

                        dialog.find_widget_by_name("name").set_text(entity.name, gui_text_renderer)
                        dialog.find_widget_by_name("ai-behavior").select_by_value(AI_BEHAVIOR_REVERSE_TRANSLATIONS[entity.ai_state.ai_behavior])

                        dialog.find_widget_by_name("details.generic").find_widget_by_name("nick").set_text(entity.nick, gui_text_renderer)
                        dialog.find_widget_by_name("details.generic").find_widget_by_name("title").set_text(entity.title, gui_text_renderer)

                        # Levers provide a little bit of extra information
                        if (entity.genus == GENUS_LEVER):

                            dialog.find_widget_by_name("details.lever").find_widget_by_name("mount").select_by_value("%d" % entity.mount)
                            dialog.find_widget_by_name("details.lever").find_widget_by_name("position").select_by_value("%d" % entity.position)

                        #dialog.show()
                        results.add(
                            action = "dialog.show",
                            params = {
                                "target": "menu-bar.maps.entities.properties"
                            }
                        )


                        # Emulate an onchange event to show the appropriate details subdialog
                        """
                        e = {
                            "event-info": {
                                "action": "maps.entities.properties:change-type"
                            }
                        }
                        self.handle_event(e, control_center, universe)
                        """

                        results.add(
                            action = "maps.entities.properties:change-type"
                        )


        # Trigger right-click menu
        elif ( action == "click:rk.triggers" ):

            dialog = gui_manager.get_widget_by_name("rk.triggers")

            if (dialog):
                dialog.hide()


            # Move trigger
            if (params["value"] == "rk.triggers/move"):

                t = editor_controller.mouse.rightclick.object_reference

                editor_controller.drag.object_type = "trigger"
                editor_controller.drag.object_reference = t

            # Edit trigger
            elif (params["value"] == "rk.triggers/edit"):

                dialog = gui_manager.get_widget_by_name("menu-bar.triggers.properties")

                if (dialog):

                    m = universe.get_active_map()

                    if (m == None):
                        return


                    t = editor_controller.mouse.rightclick.object_reference

                    # Populate the 3 script dropdowns
                    for each in ("touch", "hover", "exit"):

                        elem = dialog.find_widget_by_name("scripts-wrapper").find_widget_by_name("%s.wrapper" % each).find_widget_by_name("%s.add" % each)
                        gui_manager.populate_dropdown_with_scripts(elem, control_center, universe)

                    # Populate each individual section's existing scripts...
                    for key in t.scripts:

                        elem = dialog.find_widget_by_name("scripts-wrapper").find_widget_by_name("%s.wrapper" % key).find_widget_by_name("%s.existing" % key)
                        t.populate_dropdown_with_scripts_by_type(elem, key)


                    # Populate general settings
                    wrapper = dialog.find_widget_by_name("properties-wrapper")

                    wrapper.find_widget_by_name("name").set_text("%s" % t.name, gui_text_renderer)
                    wrapper.find_widget_by_name("width").set_text("%d" % t.width, gui_text_renderer)
                    wrapper.find_widget_by_name("height").set_text("%d" % t.height, gui_text_renderer)
                    wrapper.find_widget_by_name("behavior").select_by_value("%d" % t.behavior)
                    wrapper.find_widget_by_name("prompt").set_text("%s" % t.prompt_text, gui_text_renderer)


                    dialog.find_widget_by_name("trigger-name").set_value(t.name)

                    #dialog.show()
                    results.add(
                        action = "dialog.show",
                        params = {
                            "target": "menu-bar.triggers.properties"
                        }
                    )


            # Delete trigger
            elif (params["value"] == "rk.triggers/delete"):

                dialog = gui_manager.get_widget_by_name("menu-bar.triggers.properties")

                if (dialog):
                    dialog.hide()


                m = universe.get_active_map()

                if (m):
                    t = editor_controller.mouse.rightclick.object_reference
                    m.delete_trigger_by_name(t.name)


        # Save trigger properties (on dialog close)
        elif ( action == "triggers.properties:save-properties" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.triggers.properties")

            if (dialog):

                wrapper = dialog.find_widget_by_name("properties-wrapper")

                m = universe.get_active_map()

                if (m):

                    # Get the trigger
                    t = m.get_trigger_by_name( dialog.find_widget_by_name("trigger-name").get_value() )

                    if (t):

                        # Update properties
                        t.name = wrapper.find_widget_by_name("name").get_text()
                        t.width = int( wrapper.find_widget_by_name("width").get_text() )
                        t.height = int( wrapper.find_widget_by_name("height").get_text() )
                        t.behavior = int( wrapper.find_widget_by_name("behavior").get_value() )
                        t.prompt = wrapper.find_widget_by_name("prompt").get_text()

        # Add new script event to a trigger
        elif ( action == "triggers.properties:add" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.triggers.properties")

            if (dialog):

                # Which kind of trigger event?  (e.g. touch, hover, exit)
                key = params["param"]


                # Which script to execute?
                source_elem = dialog.find_widget_by_name("scripts-wrapper").find_widget_by_name("%s.wrapper" % key).find_widget_by_name("%s.add" % key)

                # Where will we add it to in the end?
                target_elem = dialog.find_widget_by_name("scripts-wrapper").find_widget_by_name("%s.wrapper" % key).find_widget_by_name("%s.existing" % key)


                # Get the map
                m = universe.get_active_map()

                if (m):

                    # Get the trigger
                    t = m.get_trigger_by_name( dialog.find_widget_by_name("trigger-name").get_value() )

                    if (t):
                        t.add_script_by_type(source_elem.get_value(), key)

                        # Update listbox listing...
                        t.populate_dropdown_with_scripts_by_type(target_elem, key)

        # Remove a script event from a trigger
        elif ( action == "triggers.properties:delete-selected" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.triggers.properties")

            if (dialog):

                # Which kind of trigger event?  (e.g. touch, hover, exit)
                key = params["param"]


                # Where will we remove from?
                source_elem = dialog.find_widget_by_name("scripts-wrapper").find_widget_by_name("%s.wrapper" % key).find_widget_by_name("%s.existing" % key)


                # Get the map
                m = universe.get_active_map()

                if (m):

                    # Get the trigger
                    t = m.get_trigger_by_name( dialog.find_widget_by_name("trigger-name").get_value() )

                    if (t):
                        t.remove_script_by_type(source_elem.get_value(), key)

                        # Update the listbox
                        t.populate_dropdown_with_scripts_by_type(source_elem, key)

        # Entities right-click menu
        elif ( action == "click:rk.entities" ):

            dialog = gui_manager.get_widget_by_name("rk.entities")

            if (dialog):
                dialog.hide()


            # Move entity
            if (params["value"] == "rk.entities/move"):

                entity = editor_controller.mouse.rightclick.object_reference

                editor_controller.drag.object_type = "entity"
                editor_controller.drag.object_reference = entity


            # Edit entity


            # Delete entity


        # Planes right-click menu
        elif ( action == "click:rk.planes" ):

            dialog = gui_manager.get_widget_by_name("rk.planes")

            if (dialog):
                dialog.hide()


            # Move plane
            if (params["value"] == "rk.planes/move"):

                plane = editor_controller.mouse.rightclick.object_reference

                editor_controller.drag.object_type = "plane"
                editor_controller.drag.object_reference = plane


            # Edit plane
            elif (params["value"] == "rk.planes/edit"):

                dialog = gui_manager.get_widget_by_name("menu-bar.planes.properties")

                if (dialog):

                    # Get current map, plane
                    m = universe.get_active_map()

                    if (m):

                        # This option will force-select the plane...
                        plane = editor_controller.mouse.rightclick.object_reference

                        m.active_plane_z_index = plane.z_index

                        # Track the z-index so we know which plane to update when saving changes...
                        dialog.find_widget_by_name("z-index").set_value(plane.z_index)

                        dialog.find_widget_by_name("name").set_text("%s" % plane.name, gui_text_renderer)

                        dialog.find_widget_by_name("relative-x").set_text("%d" % plane.x, gui_text_renderer)
                        dialog.find_widget_by_name("relative-y").set_text("%d" % plane.y, gui_text_renderer)

                        dialog.find_widget_by_name("width").set_text("%d" % plane.get_width(), gui_text_renderer)
                        dialog.find_widget_by_name("height").set_text("%d" % plane.get_height(), gui_text_renderer)

                        dialog.show()


            # Select plane
            elif (params["value"] == "rk.planes/select"):

                m = universe.get_active_map()

                if (m):

                    plane = editor_controller.mouse.rightclick.object_reference
                    m.active_plane_z_index = plane.z_index

            # Pad plane...
            elif (params["value"] == "rk.planes/pad"):

                dialog = gui_manager.get_widget_by_name("menu-bar.planes.pad")

                if (dialog):

                    m = universe.get_active_map()

                    plane = editor_controller.mouse.rightclick.object_reference

                    dialog.find_widget_by_name("z-index").set_value(plane.z_index)

                    dialog.find_widget_by_name("label-title").set_text( "Pad %s" % plane.name, gui_text_renderer )

                    dialog.find_widget_by_name("pad-left").set_text("0", gui_text_renderer)
                    dialog.find_widget_by_name("pad-top").set_text("0", gui_text_renderer)

                    results.add(
                        action = "dialog.show",
                        params = {
                            "target": "menu-bar.planes.pad"
                        }
                    )
                    #dialog.show()


            # Copy plane
            elif ( params["value"] == "rk.planes/copy" ):

                m = universe.get_active_map()

                if (m):

                    plane = editor_controller.mouse.rightclick.object_reference

                    editor_controller.clipboard.plane = copy.deepcopy(plane)


            # Delete plane
            elif (params["value"] == "rk.planes/delete"):

                m = universe.get_active_map()

                if (m):

                    plane = editor_controller.mouse.rightclick.object_reference
                    z_index = plane.z_index

                    # Remove the plane
                    i = 0

                    for p in m.planes:

                        log( "plane '%s' z-index = %d" % (p.name, p.z_index) )

                    while (i < len(m.planes)):

                        if (m.planes[i].z_index == z_index):
                            m.planes.pop(i)

                        else:
                            i += 1

                    m.update_plane_z_indices()

        # Maps right-click menu
        elif ( action == "click:rk.maps" ):

            dialog = gui_manager.get_widget_by_name("rk.maps")

            if (dialog):
                dialog.hide()


            # Move map
            if (params["value"] == "rk.maps/move"):

                m = editor_controller.mouse.rightclick.object_reference

                editor_controller.drag.object_type = "map"
                editor_controller.drag.object_reference = m

                log2(m)


            # Select map
            elif (params["value"] == "rk.maps/select"):

                # Fetch current map
                m = universe.get_active_map()

                # Track current map as "last map"
                editor_controller.last_map_name = m.name

                # Also track current camera location
                #editor_controller["last-map-camera-x"] = editor_controller.camera.x
                #editor_controller["last-map-camera-y"] = editor_controller.camera.y

                # Grab the map we right-clicked on
                m = editor_controller.mouse.rightclick.object_reference

                # Just set the "active map name"
                universe.activate_map_on_layer_by_name(m.name, editor_controller.active_layer, game_mode = MODE_EDITOR, control_center = control_center) #???


            # Edit map (?)
            # pass


        # Offmap right-click menu
        elif ( action == "click:rk.offmap" ):

            dialog = gui_manager.get_widget_by_name("rk.offmap")

            if (dialog):
                dialog.hide()


            # Goto any map...
            if ( params["value"] == "rk.offmap/goto" ):

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.goto")

                if (dialog):

                    dialog.find_widget_by_name("name").clear()

                    temp_names = []

                    # Populate this universe's existing map names...
                    for key in universe.map_data[ editor_controller.active_layer ]:
                        temp_names.append(key)

                    temp_names.sort()

                    for name in temp_names:
                        dialog.find_widget_by_name("name").add(name, name)

                    dialog.show()


            # Flip back to last map
            elif ( params["value"] == "rk.offmap/goto-last" ):

                # What's the last map we were on?
                last_map_name = editor_controller.last_map_name

                # Was there one?
                if (last_map_name):

                    # Check both layers
                    for layer in (LAYER_BACKGROUND, LAYER_FOREGROUND):

                        # Does it exist on this layer?
                        if ( last_map_name in universe.map_data[layer] ):

                            # Fetch the current map first
                            m = universe.get_active_map()

                            # Save it as the "last map"
                            editor_controller.last_map_name = m.name

                            # Save these before we overwrite them
                            (tempX, tempY) = (
                                editor_controller.camera.last_x,
                                editor_controller.camera.last_y
                            )

                            editor_controller.camera.last_x = universe.camera.x
                            editor_controller.camera.last_y = universe.camera.y


                            # Activate the map on the foreground layer
                            universe.activate_map_on_layer_by_name(last_map_name, layer, game_mode = MODE_EDITOR, control_center = control_center)

                            # Show the foreground
                            editor_controller.layer_visibility[layer] = True

                            # Set foreground as active layer
                            editor_controller.active_layer = layer

                            # Fetch the newly activated map object
                            m = universe.get_active_map()

                            # Center on the map
                            if ( editor_controller.active_layer == LAYER_BACKGROUND and editor_controller.layer_visibility[LAYER_FOREGROUND] == False ):

                                m.center_within_camera_using_parallax( universe.camera )

                            else:

                                m.center_within_camera( universe.camera )


                            # Save those variables for a reason...
                            universe.camera.x = tempX
                            universe.camera.y = tempY


                            # Position the camera wherever it was on the previous map
                            if (0):# "is-hotkey" in e["params"] ):

                                (a, b) = (
                                    universe.camera.x,
                                    universe.camera.y
                                )

                                #universe.camera.x = editor_controller.["last-map-camera-x"]
                                #universe.camera.y = editor_controller["last-map-camera-y"]
                                #editor_controller["last-map-camera-x"] = a
                                #editor_controller["last-map-camera-y"] = b


            # (Hotkey only) Toggle visibility of a layer
            elif ( params["value"] == "rk.offmap/toggle-layer" ):

                # Which layer?
                layer = int( e["params"]["layer"] )

                # Toggle
                editor_controller.layer_visibility[layer] = (not editor_controller.layer_visibility[layer])


                ## Set active layer to background if it's visible and we toggled forgrou
                ##if ( layer == LAYER_FOREGROUND and (not editor_controller.layer_visibility[layer]) and (editor_controller.layer_visibility[LAYER_BACKGROUND] ):


        # Generic right-click menu
        elif ( action == "click:rk.generic" ):

            dialog = gui_manager.get_widget_by_name("rk.generic")

            if (dialog):
                dialog.hide()


            # Copy tile
            if (params["value"] == "rk.generic/copy"):

                (tx, ty) = (
                    editor_controller.mouse.rightclick.tx,
                    editor_controller.mouse.rightclick.ty
                )

                m = universe.get_active_map()

                if (m):

                    plane = m.get_active_plane()

                    if (plane):
                        (relX, relY) = (
                            tx - plane.x,
                            ty - plane.y
                        )

                        if (relY >= 0 and relY < plane.tiles.get_height()):

                            if (relX >= 0 and relX < plane.tiles.get_width()):

                                editor_controller.tile = plane.tiles.read(relX, relY)

                                # Disable randomizer
                                editor_controller.randomizer.enabled = False

            # Select a new tile
            elif (params["value"] == "rk.generic/select-tile"):
                editor_controller.selecting_tile = True

            # Place gold
            elif (params["value"] == "rk.generic/place-gold"):

                (tx, ty) = (
                    editor_controller.mouse.tx,
                    editor_controller.mouse.ty
                )

                m = universe.get_active_map()

                if (m):

                    # Instantly create the new gold entity...
                    entity_type = GENUS_GOLD
                    entity_species = ""

                    entity = m.add_entity_by_type(entity_type, entity_species, "", 0)

                    if (entity):

                        log( entity )

                        entity.x = tx * TILE_WIDTH
                        entity.y = ty * TILE_HEIGHT


            # HOTKEY ONLY - Place enemy, or place enemy respawn
            elif ( params["value"] in ("rk.generic/place-enemy", "rk.generic/place-enemy-respawn") ):

                # Get mouse's right-click tile coordinates
                (tx, ty) = (
                    editor_controller.mouse.tx,
                    editor_controller.mouse.ty
                )

                # Get active map
                m = universe.get_active_map()

                # Validate
                if (m):

                    # Create a new entity
                    entity = m.add_entity_by_type(
                        GENUS_ENEMY if (params["value"] == "rk.generic/place-enemy") else GENUS_RESPAWN_ENEMY,
                        "",          # species only applies to NPC entities
                        "",          # We don't usually need a name for enemies
                        AI_BEHAVIOR_TRANSLATIONS["normal"] # Will only apply to enemies, not the respawns...
                    )

                    # Validate entity creation
                    if (entity):

                        # Update entity position
                        entity.x = (tx * TILE_WIDTH)
                        entity.y = (ty * TILE_HEIGHT)


            # HOTKEY ONLY - Move an existing entity (instead of right click / move entity)
            elif ( params["value"] == "rk.generic/move-entity" ):

                # Grab active map
                m = universe.get_active_map()
                logn( "editor entity", "%s, %s (%s, %s)\n" % (editor_controller.mouse.tx, editor_controller.mouse.ty, editor_controller.mouse.x, editor_controller.mouse.y))


                # Loop entity types
                for genus in m.master_plane.entities:

                    # Loop entities
                    for entity in m.master_plane.entities[genus]:

                        # Check for match at current mouse position
                        if (
                            int(entity.get_x() / TILE_WIDTH) == editor_controller.mouse.tx and
                            int(entity.get_y() / TILE_HEIGHT) == editor_controller.mouse.ty
                        ):

                            # Set editor to drag "entity," and set
                            # that entity as editor's drag object reference
                            editor_controller.drag.object_type = "entity"
                            editor_controller.drag.object_reference = entity



            # Place new entity
            elif (params["value"] == "rk.generic/place-entity"):

                (tx, ty) = (
                    editor_controller.mouse.rightclick.tx,
                    editor_controller.mouse.rightclick.ty
                )

                dialog = gui_manager.get_widget_by_name("menu-bar.maps.entities.properties")

                if (dialog):

                    dialog.find_widget_by_name("tx").set_value(tx)
                    dialog.find_widget_by_name("ty").set_value(ty)

                    dialog.find_widget_by_name("do").set_value("create")

                    dialog.find_widget_by_name("name").set_text("", gui_text_renderer)

                    #dialog.show()
                    results.add(
                        action = "dialog.show",
                        params = {
                            "target": "menu-bar.maps.entities.properties"
                        }
                    )


                    # Emulate an onchange event to show the appropriate details subdialog
                    """
                    e = {
                        "event-info": {
                            "action": "maps.entities.properties:change-type"
                        }
                    }
                    self.handle_event(e, control_center, universe)
                    """

                    results.add(
                        action = "maps.entities.properties:change-type"
                    )

            # Place new trigger
            elif (params["value"] == "rk.generic/place-trigger"):

                (tx, ty) = (
                    editor_controller.mouse.rightclick.tx,
                    editor_controller.mouse.rightclick.ty
                )

                dialog = gui_manager.get_widget_by_name("menu-bar.triggers.new")

                if (dialog):

                    dialog.find_widget_by_name("width").set_text("1", gui_text_renderer)
                    dialog.find_widget_by_name("height").set_text("1", gui_text_renderer)

                    dialog.find_widget_by_name("tx").set_value(tx)
                    dialog.find_widget_by_name("ty").set_value(ty)

                    dialog.find_widget_by_name("name").set_text("bomb-machine", gui_text_renderer)
                    dialog.find_widget_by_name("prompt").set_text("Press @xxenterxx to buy bombs", gui_text_renderer)


                # Trigger dialog show event
                results.add(
                    action = "dialog.show",
                    params = {
                        "target": "menu-bar.triggers.new"
                    }
                )
                #dialog.show()


            # Paste a plane from the editor clipboard
            elif ( params["value"] == "rk.generic/paste-plane" ):

                (tx, ty) = (
                    editor_controller.mouse.rightclick.tx,
                    editor_controller.mouse.rightclick.ty
                )

                plane = editor_controller.clipboard.plane

                if (plane):

                    m = universe.get_active_map()

                    new_plane = copy.deepcopy(plane)
                    new_plane.x = tx
                    new_plane.y = ty

                    m.add_plane(new_plane)

                    m.update_plane_z_indices()

                    m.active_plane_z_index = len(m.planes) - 1

                    # We're dragging a plane (the new one)
                    editor_controller.drag.object_type = "plane"

                    # Track new plane
                    editor_controller.drag.object_reference = new_plane


            # Randomizer
            elif (params["value"] == "rk.generic/randomizer"):

                dialog = gui_manager.get_widget_by_name("rk.generic.randomizer")

                if (dialog):

                    (tx, ty) = (
                        editor_controller.mouse.rightclick.tx,
                        editor_controller.mouse.rightclick.ty
                    )

                    m = universe.get_active_map()

                    if (m):

                        plane = m.get_active_plane()

                        if (plane):
                            (relX, relY) = (
                                tx - plane.x,
                                ty - plane.y
                            )

                            if (relY >= 0 and relY < plane.tiles.get_height()):

                                if (relX >= 0 and relX < plane.tiles.get_width()):

                                    editor_controller.randomizer.tile = plane.tiles.read(relX, relY)

                    #dialog.find_widget_by_name("range").set_text("", gui_text_renderer)

                    dialog.show()

            # Automask (hotkey only!)
            elif ( params["value"] == "rk.generic/automask" ):

                # Active map
                m = universe.get_active_map()

                # Find base, mask planes
                (plane1, plane2) = (
                    m.get_plane_by_name("Untitled Plane"),
                    m.get_plane_by_name("mask")
                )

                # Create mask if necessary
                if (not plane2):

                    # Create plane
                    plane2 = Plane()
                    plane2.name = "mask"

                    # Equal mask width to main layer width
                    plane2.set_height(
                        plane1.get_height()
                    )
                    plane2.set_width(
                        plane1.get_width()
                    )

                    # Hack, guarantee it's on top (I guess?)
                    plane2.z_index = 1 + max( p.z_index for p in m.planes )

                    # mask layer is always modal
                    plane2.is_modal = True

                    # Add to map
                    m.add_plane(plane2)
                    m.update_plane_z_indices()


                # Define the tiles we will apply mask corners to
                level_tiles = []

                for r in (
                    range(96, 100),    # Snow filler
                    range(116, 120),   # Snow ground
                    range(160, 200),   # Mines filler / ground
                    range(200, 206),   # Jungle filler
                    range(220, 229),   # Jungle ground
                    range(303, 315),   # Town filler
                    range(323, 335),   # Town ground
                    range(17, 20)      # Spikes (???)
                ):

                    # Add in tile range
                    level_tiles.extend(r)

                # Make sure mask plane is at least as large as base plane.
                # Clear entire mask plane in the process, and also perform magic corner calculations.
                for y in range( 0, plane1.get_height() ):
                    for x in range( 0, plane1.get_width() ):

                        # Guarantee size
                        plane2.set_tile(x, y, 0)

                        # Check to see if we should check corner logic on this tile type
                        if ( plane1.get_tile(x, y) in level_tiles ):

                            # Lower island/peninsula?
                            if ( (not (plane1.get_tile(x - 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x + 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x, y + 1) in level_tiles)) ):

                                # Random value
                                r = random.random()

                                if ( r < 0.25 ):
                                    plane2.set_tile(x, y, 300)  # Lower-left

                                elif ( r < 0.50 ):
                                    plane2.set_tile(x, y, 302)  # Lower-right

                            # Lower-left corner?
                            if ( (not (plane1.get_tile(x - 1, y) in level_tiles)) and
                                 (    (plane1.get_tile(x + 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x, y + 1) in level_tiles)) ):

                                # Good chance
                                if ( random.random() < 0.75 ):
                                    plane2.set_tile(x, y, 300)

                            # Lower-right corner?
                            if ( (    (plane1.get_tile(x - 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x + 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x, y + 1) in level_tiles)) ):

                                # Good chance
                                if ( random.random() < 0.75 ):
                                    plane2.set_tile(x, y, 302)


            # Autodilapidate (hotkey only!)
            elif ( params["value"] == "rk.generic/autodilapidate" ):

                # Active map
                m = universe.get_active_map()

                # Find base, mask planes
                (plane1, plane2) = (
                    m.get_plane_by_name("Untitled Plane"),
                    m.get_plane_by_name("mask")
                )

                # Check for "mask1"
                if (not plane2):
                    plane2 = m.get_plane_by_name("mask1")


                # Create mask if necessary
                if (not plane2):

                    # Create plane
                    plane2 = Plane()
                    plane2.name = "mask"

                    # Equal mask width to main layer width
                    plane2.set_height(
                        plane1.get_height()
                    )
                    plane2.set_width(
                        plane1.get_width()
                    )

                    # Hack, guarantee it's on top (I guess?)
                    plane2.z_index = 1 + max( p.z_index for p in m.planes )

                    # mask layer is always modal
                    plane2.is_modal = True

                    # Add to map
                    m.add_plane(plane2)
                    m.update_plane_z_indices()


                # Define the tiles we can apply "top" dilapidation to
                top_eligible_tiles = []

                for r in (
                    range(116, 120),   # Snow ground
                    range(180, 200),   # Mines ground
                    range(220, 229),   # Jungle ground
                    range(323, 335),   # Town ground
                    range(253, 258)    # Town "aquaduct"
                ):

                    # Add in tile range
                    top_eligible_tiles.extend(r)


                # Define the tiles we can apply "bottom" dilapidation to
                bottom_eligible_tiles = []

                for r in (
                    range(96, 100),    # Snow filler
                    range(160, 180),   # Mines filler
                    range(200, 206),   # Jungle filler
                    range(303, 315),   # Town filler
                    range(17, 20)      # Spikes (???)
                ):

                    # Add in tile range
                    bottom_eligible_tiles.extend(r)


                # Define the list of collision types we're willing to ignore.
                # We'll only apply dilapidation where empty space (or ladder, monkey bar, etc.) appears on the other side...
                allowed_collision_types_top = (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR, COLLISION_BRIDGE)
                allowed_collision_types_bottom = (COLLISION_NONE, COLLISION_LADDER, COLLISION_MONKEYBAR, COLLISION_DEADLY)


                # Loop base layer plane
                for y in range( 0, plane1.get_height() ):
                    for x in range( 0, plane1.get_width() ):

                        # Validate mask layer covers this tile
                        if ( plane2.get_width() > x and plane2.get_height() > y ):

                            # Clear and existing dilapidation data
                            if ( plane2.get_tile(x, y) in range(340, 350) ):

                                # Clear
                                plane2.set_tile(x, y, 0)


                            # Scope
                            (top_eligible, bottom_eligible) = (False, False)


                            # Check to see if the tile above this tile is "empty" (non-colliding)
                            if (
                                (y != 0) and # Top row is always off-limits, too much hassle to check neighboring map...
                                ( plane1.check_collision(x, y - 1) in allowed_collision_types_top )
                            ):

                                # Validate base tile type
                                if ( plane1.get_tile(x, y) in top_eligible_tiles ):

                                    # Eligible
                                    top_eligible = True


                            # Check to see if the tile below this tile is "empty"
                            if (
                                (y != plane1.get_height() - 1) and # Bottom row is always off-limits, same hassle...
                                ( plane1.check_collision(x, y + 1) in allowed_collision_types_bottom )
                            ):

                                # Validate base tile type
                                if ( plane1.get_tile(x, y) in bottom_eligible_tiles ):

                                    # Eligible
                                    bottom_eligible = True


                            # Make sure this tile has no existing mask data (corner masks always win)
                            if ( plane2.get_tile(x, y) == 0 ):

                                # Roll the dice to see if we will apply dilapidation where possible
                                chance = random.random()

                                if ( chance < 0.49 ):

                                    # Top eligible?
                                    if (top_eligible):

                                        # Apply top dilapidation
                                        plane2.set_tile(x, y, 340 + random.randint(0, 5))
                                        logn( "dilapidation", "%s, %s is top dilapidated\n" % (x, y) )

                                    # Bottom eligible?
                                    elif (bottom_eligible):

                                        # Apply bottom dilapidation
                                        plane2.set_tile(x, y, 346 + random.randint(0, 3))
                                        logn( "dilapidation", "%s, %s is bottom dilapidated\n" % (x, y) )


        # Miscellaneous actions/commands (i.e. hotkey commands)
        elif ( action == "click:other" ):

            # Delete currently moused-over entity?
            if ( params["value"] == "delete-touched-entity" ):

                # Delete any entity at the given tile coords
                universe.get_active_map().delete_entities_at_tile_coords(
                    editor_controller.mouse.tx, editor_controller.mouse.ty
                )


            # Toggle trigger visibility.  They get in the way sometimes...
            elif ( params["value"] == "toggle-triggers" ):

                # Toggle both flags
                control_center.get_editor_controller().show_trigger_names = not control_center.get_editor_controller().show_trigger_names
                control_center.get_editor_controller().show_trigger_frames = not control_center.get_editor_controller().show_trigger_frames


        # Activate randomizer
        elif ( action == "rk.generic.randomizer:enable" ):

            dialog = gui_manager.get_widget_by_name("rk.generic.randomizer")

            if (dialog):

                # Get active map
                m = universe.get_active_map()

                # Validate
                if (m):

                    # Randomize this tile type (or any within the range) across the entire map
                    m.randomize_base_tile(
                        editor_controller.randomizer.tile,
                        int( dialog.find_widget_by_name("range").get_value() )
                    )

                dialog.hide()

        # New script
        # Create new map
        elif ( action == "scripts.new") :

            dialog = gui_manager.get_widget_by_name("menu-bar.scripts.new")

            if (dialog):

                param = dialog.find_widget_by_name("name").get_text()

                m = universe.visible_maps[editor_controller.active_layer][universe.active_map_name]

                if (param in m.scripts):
                    dialog.find_widget_by_name("error").set_text("Already exists", gui_text_renderer)

                else:

                    m.scripts[param] = ""
                    """
                    m.scripts[param].attributes["name"] = param
                    # Add a default packet
                    packet = XMLNode("packet")
                    m.scripts[param].nodes.append(packet)
                    """

                    dialog.hide()

        # Event maker's event type selection changed...
        elif ( action == "event-maker.type:change" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if ( not dialog ):
                logn( "ui-event error", "Aborting:  dialog does not exist!" )
                sys.exit()

            if (dialog):

                # First, hide all sub-dialogs
                dialogs = dialog.find_widget_by_name("overlays").get_widgets_by_selector("dialog")

                for d in dialogs:

                    d.alpha_controller.configure({
                        "interval": 0,
                        "target": 0
                    })


                # Now, which element did we select?
                param = dialog.find_widget_by_name("type").get_value()

                # The sub-dialog's name builds off of that value...
                sub_dialog = dialog.find_widget_by_name("overlays").find_widget_by_name("event-maker.%s" % param)

                if (sub_dialog):
                    sub_dialog.show()

                    # Check for common, generic auto-populated dropdown fields...
                    elem = sub_dialog.find_widget_by_name("plane")

                    if (elem):
                        gui_manager.populate_dropdown_with_planes(elem, control_center, universe)


                    elem = sub_dialog.find_widget_by_name("target")

                    if (elem):
                        gui_manager.populate_dropdown_with_triggers(elem, control_center, universe)


                    for key in ("variable", "variable1", "variable2", "variable3", "variable-description", "variable-status"):

                        elem = sub_dialog.find_widget_by_name(key)

                        if (elem):
                            gui_manager.populate_dropdown_with_session_variables(elem, control_center, universe)


                    elem = sub_dialog.find_widget_by_name("entity")

                    if (elem):
                        gui_manager.populate_dropdown_with_entities(elem, control_center, universe)


                    elem = sub_dialog.find_widget_by_name("script")

                    if (elem):
                        gui_manager.populate_dropdown_with_scripts(elem, control_center, universe)


                    elem = sub_dialog.find_widget_by_name("quest")

                    if (elem):
                        gui_manager.populate_dropdown_with_quest_names(elem, control_center, universe)


                    elem = sub_dialog.find_widget_by_name("item")

                    if (elem):
                        gui_manager.populate_dropdown_with_item_names(elem, control_center, universe)


                    # Clear all Entry fields
                    elems = sub_dialog.gui_manager.get_widgets_by_selector("input")

                    for elem in elems:
                        elem.set_text("", gui_text_renderer)


                    # Special emulation options
                    if (param == "flag-quest-update"):

                        # Emulate on onchange on the quest name to populate the updates for the default quest selection
                        results.add(
                            action = "event-maker.flag-quest-update:change-quest"
                        )


                    elif (param == "fetch-update-status"):

                        # Emulate on onchange on the quest name to populate the updates for the default quest selection
                        results.add(
                            action = "event-maker.fetch-update-status:change-quest"
                        )


                    elif (param == "dialogue"):

                        # Emulate on onchange event to populate the conversations belonging to this entity
                        results.add(
                            action = "event-maker.dialogue:change-entity"
                        )


                    elif (param == "dialogue-shop"):

                        # Emulate on onchange event to populate the conversations belonging to this entity
                        results.add(
                            action = "event-maker.dialogue-shop:change-entity"
                        )


                    elif (param == "dialogue-computer"):

                        # Emulate on onchange event to populate the conversations belonging to this entity
                        results.add(
                            action = "event-maker.dialogue-computer:change-entity"
                        )


                    elif (param == "dialogue-toggle-line"):

                        # Emulate on onchange event to populate the conversations belonging to this entity
                        results.add(
                            action = "event-maker.dialogue-toggle-line:change-entity"
                        )


                    elif (param == "enable-lines-by-class"):

                        # Emulate on onchange event to populate the conversations belonging to this entity
                        results.add(
                            action = "event-maker.enable-lines-by-class:change-entity"
                        )



        # Change quest in the flag-quest-update dialog
        elif ( action == "event-maker.flag-quest-update:change-quest" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.flag-quest-update")

                if (sub_dialog):

                    quest_name = sub_dialog.find_widget_by_name("quest").get_value()
                    update_elem = sub_dialog.find_widget_by_name("update")

                    gui_manager.populate_dropdown_with_quest_update_names(quest_name, update_elem, control_center, universe)

        # Change quest in the fetch-update-status dialog
        elif ( action == "event-maker.fetch-update-status:change-quest" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.fetch-update-status")

                if (sub_dialog):

                    quest_name = sub_dialog.find_widget_by_name("quest").get_value()
                    update_elem = sub_dialog.find_widget_by_name("update")

                    gui_manager.populate_dropdown_with_quest_update_names(quest_name, update_elem, control_center, universe)


        # Change entity in dialogue dialog...
        elif ( action == "event-maker.dialogue:change-entity" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.dialogue")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    update_elem = sub_dialog.find_widget_by_name("conversation")

                    gui_manager.populate_dropdown_with_conversations_by_entity_name(update_elem, entity_name, control_center, universe)


        # Change entity in dialogue (FYI) dialog...
        elif ( action == "event-maker.dialogue-fyi:change-entity" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.dialogue-fyi")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    update_elem = sub_dialog.find_widget_by_name("conversation")

                    gui_manager.populate_dropdown_with_conversations_by_entity_name(update_elem, entity_name, control_center, universe)


        # Change entity in dialogue (shop) dialog...
        elif ( action == "event-maker.dialogue-shop:change-entity" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.dialogue-shop")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    update_elem = sub_dialog.find_widget_by_name("conversation")

                    gui_manager.populate_dropdown_with_conversations_by_entity_name(update_elem, entity_name, control_center, universe)


        # Change entity in dialogue (computer) dialog...
        elif ( action == "event-maker.dialogue-computer:change-entity" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.dialogue-computer")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    update_elem = sub_dialog.find_widget_by_name("conversation")

                    gui_manager.populate_dropdown_with_conversations_by_entity_name(update_elem, entity_name, control_center, universe)


        # Change entity in dialogue "toggle line" dialog...
        elif ( action == "event-maker.dialogue-toggle-line:change-entity" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.dialogue-toggle-line")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    update_elem = sub_dialog.find_widget_by_name("conversation")

                    gui_manager.populate_dropdown_with_conversations_by_entity_name(update_elem, entity_name, control_center, universe)


        # Change entity in enable lines by class dialog
        elif ( action == "event-maker.enable-lines-by-class:change-entity" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.enable-lines-by-class")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    update_elem = sub_dialog.find_widget_by_name("conversation")

                    gui_manager.populate_dropdown_with_conversations_by_entity_name(update_elem, entity_name, control_center, universe)


        # Change conversation in dialogue "toggle line" dialog...
        elif ( action == "event-maker.dialogue-toggle-line:change-conversation" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            if (dialog):

                sub_dialog = dialog.find_widget_by_name("event-maker.dialogue-toggle-line")

                if (sub_dialog):

                    entity_name = sub_dialog.find_widget_by_name("entity").get_value()
                    conversation_id = sub_dialog.find_widget_by_name("conversation").get_value()

                    update_elem = sub_dialog.find_widget_by_name("line")

                    gui_manager.populate_dropdown_with_conversation_lines_by_entity_name(update_elem, entity_name, conversation_id, control_center, universe)

        # Right-click on an arbitrary treeview
        elif ( action == "fire-tree-rk" ):

            dialog = gui_manager.get_widget_by_name("rk.script-tree")

            if (dialog):

                (x, y) = (
                    editor_controller.mouse.x,
                    editor_controller.mouse.y
                )

                editor_controller.last_rk_tree = params["tree"]
                editor_controller.last_rk_tree_row_index = params["row-index"]

                dialog.x = x
                dialog.y = y

                dialog.alpha_controller.configure({
                    "interval": 0,
                    "target": 1
                })

                dialog.focus()

                dialog.show()

        # Change dropdown selection of existing session variable
        elif ( action == "manage-session-variables:refresh" ):

            dialog = gui_manager.get_widget_by_name("manage-session-variables")

            if (dialog):

                existing_name = dialog.find_widget_by_name("variable2").get_value()
                dialog.find_widget_by_name("existing-default").set_text(universe.session[existing_name]["default"], gui_text_renderer)

        # Create new session variable
        elif ( action == "new-session-variable:finish" ):

            dialog = gui_manager.get_widget_by_name("new-session-variable")

            if (dialog):

                new_name = dialog.find_widget_by_name("new-name").get_text().strip().replace(" ", "-")
                new_default = dialog.find_widget_by_name("new-default").get_text().strip()

                if (new_name != ""):

                    new_name = "session.%s" % new_name

                    if (not (new_name in universe.session)):
                        universe.session[new_name] = { "default": new_default, "value": new_default }
                        dialog.hide()

                    else:
                        dialog.find_widget_by_name("error").set_text("Already Exists", gui_text_renderer)

                else:
                    dialog.find_widget_by_name("error").set_text("Name Required", gui_text_renderer)

        elif ( action == "manage-session-variables:update" ):

            dialog = gui_manager.get_widget_by_name("manage-session-variables")

            if (dialog):

                existing_name = dialog.find_widget_by_name("variable2").get_value()
                new_default = dialog.find_widget_by_name("existing-default").get_text().strip()

                log( existing_name, new_default )

                if (existing_name in universe.session):
                    universe.session[existing_name]["default"] = new_default
                    universe.session[existing_name]["value"] = new_default

        # Add new event
        elif ( action == "script-editor:add-event" ):

            dialog = gui_manager.get_widget_by_name("event-maker")

            logn( "ui-event", "ADD NEW EVENT", ("param" in params) )

            if (dialog):

                dialog.show()

                # First, hide all sub-pages
                dialogs = dialog.find_widget_by_name("overlays").get_widgets_by_selector("dialog")

                for d in dialogs:

                    d.alpha_controller.configure({
                        "interval": 0,
                        "target": 0
                    })



                # If we clicked the generic add event button, we want to make sure
                # to add it as a top-level branch
                if ( (not ("param" in params) ) or ( params["param"] != "from-right-click" ) ):
                    editor_controller.last_rk_tree = None

                elem = dialog.find_widget_by_name("type")

                if (elem):

                    # Default to planar shift
                    elem.select_by_value("planar-shift")

                    # Update visible overlay within event creator
                    results.append(
                        elem.raise_action("change")
                    )


        # Script tree right-click
        elif ( action == "click:rk.script-tree" ):

            dialog = gui_manager.get_widget_by_name("rk.script-tree")

            if (dialog):

                param = dialog.find_widget_by_name("choice").get_value()

                if (param == "insert"):

                    results.add(
                        action = "script-editor:add-event",
                        params = {
                            "param": "from-right-click"
                        }
                    )

                    """
                    e = {
                        "event-info": {
                            "action": "script-editor:add-event",
                            "param": "from-right-click"
                        }
                    }

                    # Emulate an "add event" ... event
                    self.handle_event(e, control_center, universe)
                    """


                # Hide the right-click menu
                dialog.hide()


        # Change current script
        elif ( action == "script-editor:change-script" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.scripts.script-editor")

            if (dialog):

                # Get current script value
                param = dialog.find_widget_by_name("script").get_value()

                # Update packets
                packet_wrapper = dialog.find_widget_by_name("left-panel").find_widget_by_name("packet")

                gui_manager.populate_dropdown_with_packets_from_script(packet_wrapper, param, control_center, universe)


                 # Emulate a change packet event to load the first packet into the treeview
                """
                e = {
                    "event-info": {
                        "action": "script-editor:change-packet"
                    }
                }

                self.handle_event(e, control_center, universe)
                """

                results.add(
                    action = "script-editor:change-packet"
                )


        # Change packet
        elif ( action == "script-editor:change-packet" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.scripts.script-editor")

            if (dialog):

                # Get current script
                script = dialog.find_widget_by_name("script").get_value()

                # No current script?
                if (script == ""):

                    # Go ahead and reset the treeview, anyway...
                    tree = dialog.find_widget_by_name("right-panel").find_widget_by_name("tree-wrapper").find_widget_by_name("event-tree")
                    tree.clear()

                    # Now we're done
                    return

                else:

                    # Get the current packet index
                    index = int( dialog.find_widget_by_name("left-panel").find_widget_by_name("packet").get_value() )

                    # Get the packet node from the map
                    m = universe.visible_maps[LAYER_FOREGROUND][ universe.active_map_name ]

                    node = m.get_packet_node(script, index)

                    if (node):

                        tree = dialog.find_widget_by_name("right-panel").find_widget_by_name("tree-wrapper").find_widget_by_name("event-tree")

                        tree.clear()

                        gui_manager.populate_treeview_from_xml_node(tree, node, control_center, universe)

        # New packet for current script
        elif ( action == "script-editor:new-packet" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.scripts.script-editor")

            if (dialog):

                # First, emulate a save event on the current packet
                index = int( dialog.find_widget_by_name("left-panel").find_widget_by_name("packet").get_value() )

                # Get current script
                script = dialog.find_widget_by_name("script").get_value()

                # Get the map
                m = universe.get_active_map()

                if (m):

                    # Create a new, empty packet
                    node = XMLNode("packet")

                    # Add the new packet to that script...
                    m.scripts[script].nodes.append(node)

                    # Update the packet list
                    packet_wrapper = dialog.find_widget_by_name("left-panel").find_widget_by_name("packet")

                    packet_wrapper.add("Packet %d" % (len(m.scripts[script].nodes)), "%d" % (len(m.scripts[script].nodes) - 1))
                    #populate_dropdown_with_packets_from_script(packet_wrapper, script, update = True)


                    # Restore the active selection in the packet listbox...
                    dialog.find_widget_by_name("left-panel").find_widget_by_name("packet").select_by_value("%d" % index)

        # Save script
        elif ( action == "script-editor:save-script" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.scripts.script-editor")

            if (dialog):

                # Get current script
                script = ""

                # Get the current packet
                #packet_index = 0


                script = dialog.find_widget_by_name("script").get_value()

                if (script == ""):
                    return

                packet_index = int( dialog.find_widget_by_name("left-panel").find_widget_by_name("packet").get_value() )

                # Get the tree
                elem = dialog.find_widget_by_name("right-panel").find_widget_by_name("tree-wrapper").find_widget_by_name("event-tree")

                # Compile tree as XML
                xml = elem.compile_xml_string()

                # Create a fresh packet
                node = XMLNode("packet")

                if (xml != ""):
                    XMLParser().parse_xml(xml, node)

                # Update the packet
                m = universe.visible_maps[LAYER_FOREGROUND][ universe.active_map_name ]

                if (script in m.scripts):

                    if (packet_index < len(m.scripts[script].get_nodes_by_tag("packet"))):

                        m.scripts[script].nodes[packet_index] = node

        # Receive new event
        elif ( action == "script-editor:receive-event" ):

            dialog = gui_manager.get_widget_by_name("menu-bar.scripts.script-editor")

            if (dialog):

                em = gui_manager.get_widget_by_name("event-maker")

                if (em):

                    param = em.find_widget_by_name("type").get_value()

                    fields = None

                    innerXML = ""
                    tooltip = ""

                    em_details = em.find_widget_by_name("event-maker.%s" % param)

                    if (em_details):

                        attributes = {}

                        #ui_inputs = em_details.gui_manager.get_widgets()#em_details.get_widget_by_names_with_aliases_by_type("*")

                        # Find all input-ish widgets
                        for selector in ("input", "dropdown", "listbox"):

                            # Loop widgets of the given selector
                            for widget in em_details.find_widgets_by_selector(selector):

                                if (selector == "input"):
                                    attributes[ widget.name ] = widget.get_text()

                                elif (selector in ("dropdown", "listbox")):
                                    attributes[ widget.name ] = widget.get_value()

                        (fields, innerXML, tooltip) = self.get_gui_specs_by_event_type(param, attributes)

                        if (fields != None):

                            xml = "<dialog name = '' x = '0' y = '0' width = '100%' height = '-1' background-color = 'None' border-color = 'None'>" + innerXML + "</dialog>"

                            node = XMLNode("xml-root")
                            XMLParser().parse_xml(xml, node)

                            tree = editor_controller.last_rk_tree
                            elem = gui_manager.create_gui_element_from_xml_node(node.get_nodes_by_tag("dialog")[0], dialog, control_center)

                            logn( "ui-event tree-with-elem", tree, elem )

                            if (tree == None):
                                tree = dialog.find_widget_by_name("right-panel").find_widget_by_name("tree-wrapper").find_widget_by_name("event-tree")
                                index = tree.add(elem, fields, tooltip)

                                # Automatically add then/else tags to if statements...
                                if (param == "condition-if"):

                                    # then statement
                                    (fields, innerXML, tooltip) = self.get_gui_specs_by_event_type("condition-then", {})

                                    xml = "<dialog name = '' x = '0' y = '0' width = '100%' height = '-1' background-color = 'None' border-color = 'None'>" + innerXML + "</dialog>"

                                    node = XMLNode("xml-root")
                                    XMLParser().parse_xml(xml, node)

                                    elem = gui_manager.create_gui_element_from_xml_node(node.get_nodes_by_tag("dialog")[0], dialog, control_center)

                                    tree.rows[index]["children"].add(elem, fields, tooltip)

                                    # else statement
                                    (fields, innerXML, tooltip) = self.get_gui_specs_by_event_type("condition-else", {})

                                    xml = "<dialog name = '' x = '0' y = '0' width = '100%' height = '-1' background-color = 'None' border-color = 'None'>" + innerXML + "</dialog>"

                                    node = XMLNode("xml-root")
                                    XMLParser().parse_xml(xml, node)

                                    elem = gui_manager.create_gui_element_from_xml_node(node.get_nodes_by_tag("dialog")[0], dialog, control_center)

                                    tree.rows[index]["children"].add(elem, fields, tooltip)


                                    # Auto-expand the branch
                                    tree.rows[index]["toggled"] = True

                            else:

                                row_index = editor_controller.last_rk_tree_row_index

                                logn( "ui-event tree-with-row-index", tree, row_index )

                                tree.rows[row_index]["toggled"] = True
                                index = tree.rows[row_index]["children"].add(elem, fields, tooltip)

                                tree.rows[row_index]["children"].focus()

                                logn( "ui-event tree-row-count", "**COUNT:  ", tree.rows[row_index]["children"].count() )

                                # Hack
                                parent_widget = tree.rows[row_index]["children"].parent
                                while (parent_widget):
                                    parent_widget.focus()
                                    parent_widget.invalidate_cached_metrics()
                                    parent_widget = parent_widget.parent

                                logn( "ui-event", "\n**index = %d" % index )

                                # Automatically add then/else tags to if statements...
                                if (param == "condition-if"):

                                    # then statement
                                    (fields, innerXML, tooltip) = self.get_gui_specs_by_event_type("condition-then", {})

                                    xml = "<dialog name = '' x = '0' y = '0' width = '100%' height = '-1' background-color = 'None' border-color = 'None'>" + innerXML + "</dialog>"

                                    node = XMLNode("xml-root")
                                    XMLParser().parse_xml(xml, node)

                                    elem = gui_manager.create_gui_element_from_xml_node(node.get_nodes_by_tag("dialog")[0], dialog, control_center)

                                    tree.rows[row_index]["children"].rows[index]["children"].add(elem, fields, tooltip)

                                    # else statement
                                    (fields, innerXML, tooltip) = self.get_gui_specs_by_event_type("condition-else", {})

                                    xml = "<dialog name = '' x = '0' y = '0' width = '100%' height = '-1' background-color = 'None' border-color = 'None'>" + innerXML + "</dialog>"

                                    node = XMLNode("xml-root")
                                    XMLParser().parse_xml(xml, node)

                                    elem = gui_manager.create_gui_element_from_xml_node(node.get_nodes_by_tag("dialog")[0], dialog, control_center)

                                    tree.rows[row_index]["children"].rows[index]["children"].add(elem, fields, tooltip)


                                    # Auto-expand the branch
                                    tree.rows[row_index]["children"].rows[index]["toggled"] = True

                    em.hide()

                # Raise a save-script event to make the changes live on the map
                results.add(
                    action = "script-editor:save-script"
                )

        # Return resultant events
        return results


    def get_gui_specs_by_event_type(self, param, attributes):

        fields = None
        innerXML = ""
        tooltip = ""

        if (param == "planar-shift"):

            fields = {
                "type": "planar-shift",
                "plane": attributes["plane"],
                "target": attributes["target"],
                "speed": attributes["speed"],
                "collides": attributes["collides"]
            }


            innerXML = """
                <label name = '' value = 'Planar Shift  -  %s -> %s' x = '5' y = '0' />
            """ % (fields["plane"], fields["target"])

            tooltip = "Planar Shift\n\nPlane:  %s\nTarget Trigger:  %s\n\nSpeed:  %s\nCollides with other planes:  %s" % (fields["plane"], fields["target"], fields["speed"], fields["collides"])

        elif (param == "planar-slide"):

            fields = {
                "type": "planar-slide",
                "plane": attributes["plane"],
                "slide": attributes["slide"],
                "speed": attributes["speed"],
                "target": attributes["target"]
            }


            innerXML = """
                <label name = '' value = 'Planar Slide  -  %s -> %s' x = '5' y = '0' />
            """ % (fields["plane"], fields["slide"])

            tooltip = "Planar Slide\n\nPlane:  %s\nSlide Type:  %s\n\nSpeed:  %s\n" % (fields["plane"], fields["slide"], fields["speed"])

        elif (param == "planar-message"):

            fields = {
                "type": "planar-message",
                "plane": attributes["plane"],
                "param": attributes["param"],
                "message": attributes["message"]
            }

            innerXML = """
                <label name = '' value = 'Tell Plane [%s] [%s]   [%s]' x = '5' y = '0' />
            """ % (fields["plane"], fields["message"], fields["param"])

            tooltip = "Planar Message\n\nPlane:  %s\n\Message:  %s\nParam:  %s" % (fields["plane"], fields["message"], fields["param"])

        elif (param == "dig-tiles"):

            fields = {
                "type": "dig-tiles",
                "plane": attributes["plane"],
                "target": attributes["target"],
                "behavior": attributes["behavior"]
            }

            innerXML = """
                <label name = '' value = 'Dig Tiles in [%s]' x = '5' y = '0' />
            """ % fields["target"]

            tooltip = "Dig Tiles\n\nTarget:  %s\n\nAll tiles in the targeted trigger region will be dug away.\n\nBehavior:  %s" % (fields["target"], fields["behavior"])


        elif (param == "screen-shake"):


            fields = {
                "type": "screen-shake",
                "behavior": attributes["behavior"],
                "intensity": attributes["intensity"]
            }

            innerXML = """
                <label name = '' value = 'Screen Shake [%s] [%s]' x = '5' y = '0' />
            """ % (fields["behavior"], fields["intensity"])

            tooltip = "Screen Shake\n\nBehavior:  %s\nIntensity:  %s" % (fields["behavior"], fields["intensity"])

        elif (param == "cutscene"):

            fields = {
                "type": "cutscene",
                "behavior": attributes["behavior"]
            }

            innerXML = """
                <label name = '' value = 'Cutscene [%s]' x = '5' y = '0' />
            """ % fields["behavior"]

            tooltip = "Cutscene Control\n\nBehavior:  %s\n\nUser Input and Enemy AI processing halts during cutscenes." % fields["behavior"]

        elif (param == "planar-toggle"):

            fields = {
                "type": "planar-toggle",
                "plane": attributes["plane"],
                "behavior": attributes["behavior"],
                "speed": attributes["speed"]
            }

            innerXML = """
                <label name = '' value = 'Planar Toggle [%s] [%s]' x = '5' y = '0' />
            """ % (fields["plane"], fields["behavior"])

            tooltip = "Planar Toggle\n\nPlane:  %s\n\nBehavior:  %s\nSpeed:  %s" % (fields["plane"], fields["behavior"], fields["speed"])

        elif (param == "entity-toggle"):

            fields = {
                "type": "entity-toggle",
                "entity": attributes["entity"],
                "behavior": attributes["behavior"],
                "speed": attributes["speed"]
            }

            innerXML = """
                <label name = '' value = 'Entity Toggle [%s] [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["behavior"])

            tooltip = "Entity Toggle\n\nEntity:  %s\n\nBehavior:  %s\nSpeed:  %s" % (fields["entity"], fields["behavior"], fields["speed"])

        elif (param == "entity-move"):

            fields = {
                "type": "entity-move",
                "entity": attributes["entity"],
                "behavior": attributes["behavior"],
                "target": attributes["target"]
            }

            innerXML = """
                <label name = '' value = 'Entity Move [%s] [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["target"])

            tooltip = "Entity Move\n\nEntity:  %s\n\nBehavior:  %s\nTarget:  %s" % (fields["entity"], fields["behavior"], fields["target"])

        elif (param == "entity-message"):

            fields = {
                "type": "entity-message",
                "entity": attributes["entity"],
                "param": attributes["param"],
                "target": attributes["target"],
                "message": attributes["message"]
            }

            innerXML = """
                <label name = '' value = 'Tell [%s] [%s]   [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["message"], fields["target"])

            tooltip = "Entity Message\n\nEntity:  %s\n\Message:  %s\nTarget:  %s\nParam:  %s" % (fields["entity"], fields["message"], fields["target"], fields["param"])

        elif (param == "trigger-message"):

            fields = {
                "type": "trigger-message",
                "target": attributes["target"],
                "entity": attributes["entity"],
                "message": attributes["message"],
            }

            if ("param" in attributes):
                fields["param"] = attributes["param"]

            else:
                fields["param"] = ""

            innerXML = """
                <label name = '' value = 'Trigger [%s] %s [%s]' x = '5' y = '0' />
            """ % (fields["target"], fields["message"], fields["entity"])

            tooltip = "Trigger Message\n\nEntity:  %s\n\Message:  %s\nTrigger:  %s" % (fields["entity"], fields["message"], fields["target"])

        elif (param == "call-script"):

            fields = {
                "type": "call-script",
                "script": attributes["script"]
            }

            innerXML = """
                <label name = '' value = 'Call Script [%s]' x = '5' y = '0' />
            """ % fields["script"]

            tooltip = "Call Script\n\nScript Name:  %s" % fields["script"]

        elif (param == "packet-time-limit"):

            fields = {
                "type": "packet-time-limit",
                "limit": attributes["limit"]
            }

            innerXML = """
                <label name = '' value = 'Packet Time Limit [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["behavior"])

            tooltip = "Packet Time Limit\n\nA packet will last no longer* than this length of time.\n\n* - Packet will not conclude while a planar shift remains in motion."

        elif (param == "spawn-random-enemy"):

            fields = {
                "type": "spawn-random-enemy",
                "target": attributes["target"],
                "disposable": attributes["disposable"]
            }

            innerXML = """
                <label name = '' value = 'Spawn Random Enemy in [%s]  Disposable: [%s]' x = '5' y = '0' />
            """ % (fields["target"], fields["disposable"])

            tooltip = "Spawn Random Enemy\n\nTarget:  %s\n\Dispoable:  %s\n\nParam:  %s" % (fields["target"], fields["disposable"], "n/a")

        elif (param == "dialogue"):

            fields = {
                "type": "dialogue",
                "conversation": attributes["conversation"],
                "entity": attributes["entity"]
            }

            innerXML = """
                <label name = '' value = '[%s] iterate conversation [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["conversation"])

            tooltip = "Dialogue\n\nNarrating Entity:  %s\nConversation:  %s\n\nThis will typically appear as an NPC dialogue text.  It can also narrate cutscenes." % (fields["entity"], fields["conversation"])

        elif (param == "dialogue-fyi"):

            fields = {
                "type": "dialogue-fyi",
                "conversation": attributes["conversation"],
                "entity": attributes["entity"],
                "id": attributes["id"]
            }

            innerXML = """
                <label name = '' value = '[%s] fyi[id = %s] [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["id"], fields["conversation"])

            tooltip = "Dialogue FYI\n\nNarrating Entity:  %s\nConversation:  %s\n\nThis will typically appear as an NPC dialogue text.  It can also narrate cutscenes." % (fields["entity"], fields["conversation"])

        elif (param == "dismiss-fyi"):

            fields = {
                "type": "dismiss-fyi",
                "id": attributes["id"]
            }

            innerXML = """
                <label name = '' value = 'dismiss fyi[id = %s]' x = '5' y = '0' />
            """ % fields["id"]

            tooltip = "Dismiss FYI\n\FYI Widget ID:  %s\n\n:  Dismiss an FYI dialogue by a given widget ID.  You assigned the widget ID when you iterated the first FYI line.\n\nDoes nothing if the ID does not exist." % fields["id"]

        elif (param == "dialogue-shop"):

            fields = {
                "type": "dialogue-shop",
                "conversation": attributes["conversation"],
                "entity": attributes["entity"]
            }

            innerXML = """
                <label name = '' value = '[%s] iterate conversation [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["conversation"])

            tooltip = "Dialogue SHOP\n\nNarrating Entity:  %s\nConversation:  %s\n\nThis will typically appear as an NPC dialogue text.  It can also narrate cutscenes." % (fields["entity"], fields["conversation"])

        elif (param == "dialogue-computer"):

            fields = {
                "type": "dialogue-computer",
                "conversation": attributes["conversation"],
                "entity": attributes["entity"]
            }

            innerXML = """
                <label name = '' value = '[%s] iterate conversation [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["conversation"])

            tooltip = "Dialogue COMPUTER\n\nNarrating Entity:  %s\nConversation:  %s\n\nThis will typically appear as an NPC dialogue text.  It can also narrate cutscenes." % (fields["entity"], fields["conversation"])

        elif (param == "dialogue-toggle-line"):

            fields = {
                "type": "dialogue-toggle-line",
                "conversation": attributes["conversation"],
                "entity": attributes["entity"],
                "line": attributes["line"],
                "status": attributes["status"]
            }

            innerXML = """
                <label name = '' value = '[%s] conversation [%s] line [%s] [%s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["conversation"], fields["line"], fields["status"])

            tooltip = "Dialogue\n\nNarrating Entity:  %s\nConversation:  %s\n\nLine ID:  %s\nStatus:  %s" % (fields["entity"], fields["conversation"], fields["line"], fields["status"])

        elif (param == "dialogue-response"):

            fields = {
                "type": "dialogue-response",
                "message": attributes["message"],
                "selectable": attributes["selectable"],
                "answer": attributes["answer"]
            }

            innerXML = """
                <label name = '' value = 'Dialogue Response: [%s]' x = '5' y = '0' />
            """ % fields["message"][0:50].replace("'", "&apos;")

            tooltip = "Dialogue Response\n\nAnswer:\n%s\n\nFull Text:\n\n%s\n\nAdding responses to Dialogue events allows the player to select a reaction to a certain dialogue prompt.\n\nThe player's decision always assigns to the core.generic.dialogue-response Session Variable." % (fields["answer"], fields["message"])

        elif (param == "condition-if"):

            fields = {
                "type": "condition-if",
                "variable1": attributes["variable1"],
                "variable2": attributes["variable2"],
                "operator": attributes["operator"],
                "raw-value": attributes["raw-value"]
            }

            s = fields["variable2"]
            if (fields["raw-value"] != ""):
                s = fields["raw-value"]

            innerXML = """
                <label name = '' value = 'If [%s] %s [%s]' x = '5' y = '0' />
            """ % (fields["variable1"], fields["operator"], s)

            tooltip = "If Comparison\n\nSession Variable Left:  %s\n\nComparison Operator:  %s\nSession Variable Right:  %s\n\n-or-\n\nRaw Value Right:  %s\n\nIf provided, the raw value takes priority." % (fields["variable1"], fields["operator"], fields["variable2"], fields["raw-value"])

        elif (param == "condition-then"):


            fields = {
                "type": "condition-then"
            }

            innerXML = """
                <label name = '' value = 'Then' x = '5' y = '0' />
            """

            tooltip = "Children of this branch will execute only when the parent IF test evaluates to True."

        elif (param == "condition-else"):

            fields = {
                "type": "condition-else"
            }

            innerXML = """
                <label name = '' value = 'Else' x = '5' y = '0' />
            """

            tooltip = "Children of this branch will execute only when the parent IF test does not evaluate to True."

        elif (param == "condition-switch"):

            fields = {
                "type": "condition-switch",
                "variable": attributes["variable"]
            }

            innerXML = """
                <label name = '' value = 'Switch' x = '5' y = '0' />
            """

            tooltip = "Evaluate multiple possible values quicly.  Add WHEN events to do so."

        elif (param == "condition-when"):

            fields = {
                "type": "condition-when",
                "variable": attributes["variable"],
                "raw-value": attributes["raw-value"]
            }

            s = fields["variable"]
            if (fields["raw-value"] != ""):
                s = fields["raw-value"]

            innerXML = """
                <label name = '' value = 'When [%s]' x = '5' y = '0' />
            """ % s

            tooltip = "When the Switched variable equals this value..."

        elif (param == "trigger-contains"):

            fields = {
                "type": "trigger-contains",
                "variable": attributes["variable"],
                "entity": attributes["entity"],
                "target": attributes["target"]
            }

            innerXML = """
                <label name = '' value = '[%s] = [%s] contains [%s]' x = '5' y = '0' />
            """ % (fields["variable"], fields["target"], fields["entity"])

            tooltip = "Trigger Contains...\n\nEntity:  %s\nTarget Trigger:  %s\n\nResultant Session Variable:  %s" % (fields["target"], fields["entity"], fields["variable"])

        elif (param == "lever-has-position"):

            fields = {
                "type": "lever-has-position",
                "variable": attributes["variable"],
                "entity": attributes["entity"],
                "position": attributes["position"]
            }

            innerXML = """
                <label name = '' value = '[%s] = [%s] has position [%s]' x = '5' y = '0' />
            """ % (fields["variable"], fields["entity"], fields["position"])

            tooltip = "Lever has position...\n\nLever Entity:  %s\nPosition:  %s\n\nResultant Session Variable:  %s" % (fields["entity"], fields["position"], fields["variable"])

        elif (param == "vars-sum"):

            fields = {
                "type": "vars-sum",
                "variable1": attributes["variable1"],
                "variable2": attributes["variable2"],
                "variable3": attributes["variable3"]
            }

            innerXML = """
                <label name = '' value = '[%s] = [%s] + [%s]' x = '5' y = '0' />
            """ % (fields["variable3"], fields["variable1"], fields["variable2"])

            tooltip = "Sum 2 Session Variables into another Session Variable."

        elif (param == "vars-diff"):

            fields = {
                "type": "vars-diff",
                "variable1": attributes["variable1"],
                "variable2": attributes["variable2"],
                "variable3": attributes["variable3"]
            }

            innerXML = """
                <label name = '' value = '[%s] = [%s] - [%s]' x = '5' y = '0' />
            """ % (fields["variable3"], fields["variable1"], fields["variable2"])

            tooltip = "Set a Session Variable to the difference between two other Session Variables."

        elif (param == "vars-plus"):

            fields = {
                "type": "vars-plus",
                "variable": attributes["variable"],
                "amount": attributes["amount"]
            }

            innerXML = """
                <label name = '' value = '[%s] += %s' x = '5' y = '0' />
            """ % (fields["variable"], fields["amount"])

            tooltip = "Increase (or, via negative number, decrease) the value of a Session Variable."

        elif (param == "vars-set"):

            fields = {
                "type": "vars-set",
                "variable": attributes["variable"],
                "value": attributes["value"]
            }

            innerXML = """
                <label name = '' value = '[%s] = %s' x = '5' y = '0' />
            """ % (fields["variable"], fields["value"])

            tooltip = "Assign a value to a Session Variable."

        elif (param == "vars-copy"):

            fields = {
                "type": "vars-copy",
                "variable1": attributes["variable1"],
                "variable2": attributes["variable2"]
            }

            innerXML = """
                <label name = '' value = '[%s] = [%s]' x = '5' y = '0' />
            """ % (fields["variable2"], fields["variable1"])

            tooltip = "Assign the value of one Session Variable to another Session Variable."

        elif (param == "set-npc-indicator"):

            fields = {
                "type": "set-npc-indicator",
                "entity": attributes["entity"],
                "key": attributes["key"],
                "value": attributes["value"]
            }

            innerXML = """
                <label name = '' value = '@%s[%s = %s]' x = '5' y = '0' />
            """ % (fields["entity"], fields["key"], fields["value"])

            tooltip = "Set NPC Indicator\n\NPC:  %s\n\nIndicator:  %s\nValue:  %s" % (fields["entity"], fields["key"], fields["value"])

        elif (param == "enable-lines-by-class"):

            fields = {
                "type": "enable-lines-by-class",
                "entity": attributes["entity"],
                "conversation": attributes["conversation"],
                "class": attributes["class"]
            }

            innerXML = """
                <label name = '' value = '@%s enable ^%s.%s' x = '5' y = '0' />
            """ % (fields["entity"], fields["conversation"], fields["class"])

            tooltip = "No tooltip"#Set NPC Indicator\n\NPC:  %s\n\nIndicator:  %s\nValue:  %s" % (fields["entity"], fields["key"], fields["value"])

        elif (param == "disable-lines-by-class"):

            fields = {
                "type": "disable-lines-by-class",
                "entity": attributes["entity"],
                "conversation": attributes["conversation"],
                "class": attributes["class"]
            }

            innerXML = """
                <label name = '' value = '@%s disable ^%s.%s' x = '5' y = '0' />
            """ % (fields["entity"], fields["conversation"], fields["class"])

            tooltip = "No tooltip"#Set NPC Indicator\n\NPC:  %s\n\nIndicator:  %s\nValue:  %s" % (fields["entity"], fields["key"], fields["value"])

        elif (param == "flag-quest"):

            fields = {
                "type": "flag-quest",
                "quest": attributes["quest"],
                "flag": attributes["flag"]
            }

            innerXML = """
                <label name = '' value = 'Flag Quest [%s] [%s]' x = '5' y = '0' />
            """ % (fields["quest"], fields["flag"])

            tooltip = "Flag Quest\n\nQuest Name:  %s\n\nFlag:  %s" % (fields["quest"], fields["flag"])

        elif (param == "flag-quest-update"):

            fields = {
                "type": "flag-quest-update",
                "quest": attributes["quest"],
                "update": attributes["update"],
                "flag": attributes["flag"]
            }

            innerXML = """
                <label name = '' value = 'Flag Update [%s] [%s] [%s]' x = '5' y = '0' />
            """ % (fields["quest"], fields["update"], fields["flag"])

            tooltip = "Flag Quest Update\n\nQuest Name:  %s\nUpdate Name:  %s\n\nFlag:  %s" % (fields["quest"], fields["update"], fields["flag"])

        elif (param == "fetch-quest-status"):

            fields = {
                "type": "fetch-quest-status",
                "quest": attributes["quest"],
                "variable": attributes["variable"],
                "format": attributes["format"]
            }

            innerXML = """
                <label name = '' value = '[%s] = Fetch Quest Status [%s]' x = '5' y = '0' />
            """ % (fields["variable"], fields["quest"])

            tooltip = "\n\nQuest Name:  %s\n\nSession Variable Target:  %s\nFormat:  %s" % (fields["quest"], fields["variable"], fields["format"])

        elif (param == "fetch-update-status"):

            fields = {
                "type": "fetch-update-status",
                "quest": attributes["quest"],
                "variable": attributes["variable"],
                "update": attributes["update"],
                "format": attributes["format"]
            }

            innerXML = """
                <label name = '' value = '[%s] = %s.UpdateStatus[%s]' x = '5' y = '0' />
            """ % (fields["variable"], fields["quest"], fields["update"])

            tooltip = "\n\nQuest Name:  %s\n\nSession Variable Target:  %s\nFormat:  %s" % (fields["quest"], fields["variable"], fields["format"])

        elif (param == "overlay"):

            fields = {
                "type": "overlay",
                "map-name": attributes["map-name"],
                "title": attributes["title"]
            }

            innerXML = """
                <label name = '' value = 'Overlay [%s]' x = '5' y = '0' />
            """ % fields["map-name"]

            tooltip = "Show Map Overlay\n\nMap Name:  %s\nOverlay Title:  %s" % (fields["map-name"], fields["title"])

        elif (param == "camera-message"):

            fields = {
                "type": "camera-message",
                "message": attributes["message"],
                "entity": attributes["entity"]
            }

            innerXML = """
                <label name = '' value = 'Camera Message [%s] [%s]' x = '5' y = '0' />
            """ % (fields["message"], fields["entity"])

            tooltip = "Camera Message\n\nMessage:  %s\nEntity:  %s" % (fields["message"], fields["entity"])

        elif (param == "reload-map"):

            fields = {
                "type": "reload-map"
            }

            innerXML = """
                <label name = '' value = 'RELOAD MAP' x = '5' y = '0' />
            """

            tooltip = "Reload Map\n\nThis will reload the map entirely.  Be careful!"

        elif (param == "mark-map-as-completed"):

            fields = {
                "type": "mark-map-as-completed"
            }

            innerXML = """
                <label name = '' value = 'Mark Map as COMPLETED' x = '5' y = '0' />
            """

            tooltip = "Mark the current map as COMPLETED."

        elif (param == "load-map"):

            fields = {
                "type": "load-map",
                "name": attributes["name"],
                "spawn": attributes["spawn"]
            }

            innerXML = """
                <label name = '' value = 'Load map [%s] player @ [%s]' x = '5' y = '0' />
            """ % (fields["name"], fields["spawn"])

            tooltip = "Load Map\n\nMap Name:  %s\nPlayer Spawn Waypoint:  %s\n\nLoad a new map and place the player at a waypoint." % (fields["name"], fields["spawn"])

        elif (param == "set-map-status-message"):

            fields = {
                "type": "set-map-status-message",
                "message": attributes["message"]
            }

            innerXML = """
                <label name = '' value = 'Set Map Status Msg:  %s' x = '5' y = '0' />
            """ % fields["message"]

            tooltip = "Set Map Status Message\n\Message:  %s" % fields["message"]

        elif (param == "shout"):

            fields = {
                "type": "shout",
                "position": attributes["position"],
                "message": attributes["message"]
            }

            innerXML = """
                <label name = '' value = 'Shout [%s] "%s"' x = '5' y = '0' />
            """ % (fields["position"], fields["message"])

            tooltip = "Letterbox Shout\n\nPosition:  %s\nMessage:  %s" % (fields["position"], fields["message"])

        elif (param == "fetch-stat"):

            fields = {
                "type": "fetch-stat",
                "statistic": attributes["statistic"],
                "variable": attributes["variable"],
                "entity": attributes["entity"]
            }

            innerXML = """
                <label name = '' value = '[%s] = fetch-stat [%s] (%s)"' x = '5' y = '0' />
            """ % (fields["variable"], fields["statistic"], fields["entity"])

            tooltip = "Tooltip..."

        elif (param == "fetch-stat-by-region"):

            fields = {
                "type": "fetch-stat-by-region",
                "statistic": attributes["statistic"],
                "variable": attributes["variable"],
                "entity": attributes["entity"],
                "target": attributes["target"]
            }

            innerXML = """
                <label name = '' value = '[%s] = %s.fetch-stat [%s] (%s)"' x = '5' y = '0' />
            """ % (fields["variable"], fields["target"], fields["statistic"], fields["entity"])

            tooltip = "Tooltip..."

        elif (param == "fetch-item-stat"):

            fields = {
                "type": "fetch-item-stat",
                "statistic": attributes["statistic"],
                "variable": attributes["variable"],
                "item": attributes["item"]
            }

            innerXML = """
                <label name = '' value = '[%s] = fetch-item-stat [%s] (%s)"' x = '5' y = '0' />
            """ % (fields["variable"], fields["statistic"], fields["item"])

            tooltip = "Tooltip..."

        elif (param == "set-item-stat"):

            fields = {
                "type": "set-item-stat",
                "statistic": attributes["statistic"],
                "value": attributes["value"],
                "item": attributes["item"]
            }

            innerXML = """
                <label name = '' value = 'item [%s] [%s] = [%s]"' x = '5' y = '0' />
            """ % (fields["item"], fields["statistic"], fields["value"])

            tooltip = "Tooltip..."

        elif (param == "sleep"):

            fields = {
                "type": "sleep",
                "frames": attributes["frames"]
            }

            innerXML = """
                <label name = '' value = 'Sleep(%s)' x = '5' y = '0' />
            """ % (fields["frames"],)

            tooltip = "Tooltip..."

        return (fields, innerXML, tooltip)
