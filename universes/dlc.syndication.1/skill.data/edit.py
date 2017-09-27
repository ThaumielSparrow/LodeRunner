import os

from xmllist import XMLParser, XMLNode

f = open("skill_definitions.xml", "r")
xml = f.read()
f.close()

min_levels = []

cats = XMLParser().create_node_from_xml(xml).get_first_node_by_tag("*").get_first_node_by_tag("*")

for ref_cat in cats.get_nodes_by_tag("*"):

    for ref_skill in ref_cat.get_nodes_by_tag("*"):

        source = ref_skill.get_nodes_by_tag("stats")

        for ref_stats in source:

            (level, min_char) = (
                ref_stats.get_attribute("level"),
                ref_stats.get_attribute("min-character-level")
            )

            min_levels.append( (ref_skill.tag_type, level, min_char) )



for (skill, level, min_char) in min_levels:

    f = open("%s.xml" % skill, "r")
    xml = f.read()
    f.close()

    root = XMLParser().create_node_from_xml(xml).get_first_node_by_tag("*")

    ref_stats = root.get_first_node_by_tag("data", {"tier": level})

    print ref_stats.set_attribute("min-character-level", "%s" % min_char)

    print root.compile_xml_string()

    f = open("%s.xml" % skill, "w")
    f.write( root.compile_xml_string() )
    f.close()
