from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, xml_encode, xml_decode, strip_alpha, strip_numbers

from code.constants.common import GENUS_NPC

# This class contains a number of common GUI population routines (populating dropdowns, mostly)
class GUIWidgetPopulationFunctions:

    def __init__(self):

        return


    def populate_treeview_from_xml_node(self, treeview, node, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        # Fetch UI responder
        ui_responder = control_center.get_ui_responder()

        child_collection = node.get_nodes_by_tag("event")

        for c in child_collection:

            param = "%s" % c.get_attribute("type")

            (fields, innerXML, tooltip) = ui_responder.get_gui_specs_by_event_type(param, c.attributes)

            if (fields != None):

                xml = "<dialog name = '' x = '0' y = '0' width = '100%' height = '-1' background-color = 'None' border-color = 'None'>" + innerXML + "</dialog>"

                node = XMLParser().create_node_from_xml(xml)

                dialog = self.create_gui_element_from_xml_node(node.get_nodes_by_tag("dialog")[0], treeview, control_center)

                index = treeview.add(dialog, fields, tooltip)

                self.populate_treeview_from_xml_node(treeview.rows[index]["children"], c, control_center, universe)


    def populate_dropdown_with_planes(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]


        rows = []

        for plane in m.planes:
            rows.append(plane.name)

        rows.sort()

        for row in rows:
            elem.add(row, row)


    def populate_dropdown_with_triggers(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

        rows = []

        for t in m.triggers:
            rows.append(t.name)

        rows.sort()

        for row in rows:
            elem.add(row, row)


    def populate_dropdown_with_session_variables(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()


        rows = []

        for key in universe.session:
            rows.append(key)

        rows.sort()

        for row in rows:
            elem.add(row, row)


    def populate_dropdown_with_entities(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

        rows = []

        for genus in m.master_plane.entities:

            for e in m.master_plane.entities[genus]:

                # For entities, I don't care about them if they have no name...
                if (e.name == ""):
                    pass

                # I also don't want to pollute the dropdown with gold1, gold2, etc.  If stripping numerical
                # characters from the string results in "gold," I'll ignore it...
                elif ( strip_numbers(e.name) == "gold" ):
                    pass

                # Okay, let's add this one...
                else:
                    rows.append(e.name)

        rows.sort()

        for row in rows:
            elem.add(row, row)


    def populate_dropdown_with_scripts(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()


        elem.clear()

        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

        rows = []

        for key in m.scripts:
            rows.append(key)

        rows.sort()

        for row in rows:
            elem.add(row, row)


    def populate_dropdown_with_packets_from_script(self, elem, script, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        m = universe.visible_maps[ editor_controller.active_layer ][ universe.active_map_name ]

        if (script in m.scripts):

            packets = m.scripts[script].get_nodes_by_tag("packet")

            for i in range(0, len(packets)):
                elem.add("Packet %d" % (i + 1), "%d" % i)


    def populate_dropdown_with_quest_names(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        rows = []

        for quest in universe.quests:
            rows.append(quest.name)

        rows.sort()

        for row in rows:
            elem.add(row, row)


    def populate_dropdown_with_quest_update_names(self, quest_name, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        quest = universe.get_quest_by_name(quest_name)

        if (quest):

            rows = []

            for update in quest.updates:
                rows.append(update.name)

            rows.sort()

            for row in rows:
                elem.add(row, row)


    def populate_dropdown_with_item_names(self, elem, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        rows = []

        for item in universe.items:
            rows.append( (item.title, item.name) )

        rows.sort()

        for (title, name) in rows:
            elem.add(title, name)


    def populate_dropdown_with_conversations_by_entity_name(self, elem, entity_name, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        entity = universe.get_active_map().get_entity_by_name(entity_name)

        log(  entity, entity_name )

        if (entity):

            rows = []

            # Only NPCs can have conversations
            if (entity.genus == GENUS_NPC):

                log(  entity.conversations )

                for key in entity.conversations:
                    rows.append(key)

                rows.sort()

                for row in rows:
                    elem.add(row, row)


    def populate_dropdown_with_conversation_lines_by_entity_name(self, elem, entity_name, conversation_id, control_center, universe):

        # Fetch level editor controller
        editor_controller = control_center.get_editor_controller()

        elem.clear()

        entity = universe.get_active_map().get_entity_by_name(entity_name)

        if (entity):

            rows = []

            for key in entity.conversations[conversation_id].branches:

                branch = entity.conversations[conversation_id].branches[key]

                for line in branch.linear_data:

                    if ( not (line.id in ("", "False")) ):
                        rows.append(line.id)

                for line in branch.nag_data:

                    if ( not (line.id in ("", "False")) ):
                        rows.append(line.id)

            rows.sort()

            for row in rows:
                elem.add(row, row)
