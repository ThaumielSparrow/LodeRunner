from xmllist import XMLParser, XMLNode

def xml_decode(s):
    return s.replace("&apos;", "'")

f = open("sed.xml", "r")
xml = f.read()
f.close()

root = XMLParser().create_node_from_xml(xml)

category_collection = root.get_first_node_by_tag("skilltrees").get_first_node_by_tag("categories").get_nodes_by_tag("*")

nodes_by_skill = {}

for ref_category in category_collection:

    skill_collection = ref_category.get_nodes_by_tag("*")

    for ref_skill in skill_collection:

        data_collection = ref_skill.get_nodes_by_tag("data")

        print ref_skill.get_first_node_by_tag("*").compile_xml_string()

        skill_root = XMLNode(ref_skill.tag_type)

        for level in (-1, 0, 1, 2, 3):

            ref_data = ref_skill.get_first_node_by_tag("data", {"level": "%d" % level})

            tier = "locked"

            if (level in (0, 1, 2)):
                tier = "%d" % (level + 1)
            elif (level == 3):
                tier = "max"

            data_node = skill_root.add_node(
                XMLNode("data")
            )

            data_node.set_attribute("tier", tier)

            # add text data
            texts_node = data_node.add_node( XMLNode("texts") )

            t = texts_node.add_node( XMLNode("overview") )
            t.innerText = xml_decode( ref_data.get_first_node_by_tag("billboard").get_first_node_by_tag("item-group").get_nodes_by_tag("item")[1].get_first_node_by_tag("label").get_attribute("value") )

            # reserved
            t = texts_node.add_node( XMLNode("specs") )

            # reserved
            t = texts_node.add_node( XMLNode("manual") )

            t = texts_node.add_node( XMLNode("gif-source") )
            t.innerText = ref_data.get_first_node_by_tag("options-panel").get_nodes_by_tag("item")[-1].get_first_node_by_tag("gif").get_attribute("map")


            inserts_node = texts_node.add_node( XMLNode("inserts") )

            ref_injections = ref_data.get_first_node_by_tag("injections")
            if (ref_injections):

                injection_collection = ref_injections.get_nodes_by_tag("injection")

                for ref_injection in injection_collection:

                    (template, target) = (
                        ref_injection.get_attribute("template"),
                        ref_injection.get_attribute("target")
                    )

                    folder = template.split(".")[-1]
                    region = target.split(".")[-1]

                    t = inserts_node.get_first_node_by_tag(folder)
                    if (t == None):
                        t = inserts_node.add_node( XMLNode(folder) )

                    t = t.add_node( XMLNode(region) )
                    t.innerText = xml_decode( ref_injection.get_first_node_by_tag("item").get_first_node_by_tag("label").get_attribute("value") )

            attributes_node = data_node.add_node( XMLNode("attributes") )

        nodes_by_skill[ref_skill.tag_type] = skill_root


# Get metrics
f = open("x.xml", "r")
xml = f.read()
f.close()

root = XMLParser().create_node_from_xml(xml)

category_collection = root.get_first_node_by_tag("*").get_first_node_by_tag("categories").get_nodes_by_tag("*")

for ref_category in category_collection:

    skill_collection = ref_category.get_nodes_by_tag("*")

    for ref_skill in skill_collection:

        stats_collection = ref_skill.get_nodes_by_tag("stats")

        for level in (1, 2, 3):

            ref_data = ref_skill.get_first_node_by_tag("stats", {"level": "%d" % level})

            ref_target = nodes_by_skill[ref_skill.tag_type].get_first_node_by_tag("data", {"tier": "%d" % level}).get_first_node_by_tag("attributes")

            for x in ("duration", "recharge", "modifiers"):

                ref_target.add_node(
                    ref_data.get_first_node_by_tag(x)
                )

            ref_target = nodes_by_skill[ref_skill.tag_type].get_first_node_by_tag("data", {"tier": "%d" % level}).get_first_node_by_tag("texts")

            ref_target.get_first_node_by_tag("specs").innerText = ref_data.get_first_node_by_tag("description").innerText

            if ( ref_data.get_first_node_by_tag("manual") ):
                ref_target.get_first_node_by_tag("manual").innerText = ref_data.get_first_node_by_tag("manual").innerText



for skill in nodes_by_skill:

    f = open("tmp/%s.xml" % skill, "w")
    f.write( nodes_by_skill[skill].compile_xml_string() )
    f.close()





"""
<sprint>
    <data tier = '1' min-character-level = '2' max-upgrade-level = '3'>
        <texts>
            <overview>Sprint increases your [color=title]lateral movement speed[/color], allowing for quicker travel and easier enemy evasion.</overview>
            <specs>[color=title]20%[/color] speed bonus for [color=title]3s[/color]
Recharges in [color=title]10 seconds[/color]</specs>
            <manual>Activate Sprint to increase your speed by [color=title]20%[/color] for [color=title]3s[/color].</manual>
            <gif-source>gifs.movement.sprint</gif-source>
            <inserts>
                <confirm>
                    <header>If you unlock [color=title]Sprint[/color], you will lose access to the [color=title]Matrix[/color] skill.</header>
                    <header>Higher levels of [color=title]Sprint[/color] offer small [color=title]speed increases[/color] while incrementally decreasing the base [color=title]recharge time[/color].</header>
                </confirm>
                <receipt>
                    <footer>You will no longer have access to the [color=title]Matrix[/color] skill.</footer>
                </receipt>
            </inserts>
        </texts>
        <attributes>
			<duration measure = 'seconds'>3.0</duration>
			<recharge measure = 'seconds'>10.0</recharge>
			<modifiers>
                <modifier name = 'kill-all-enemies' value = '1' />
                <modifier name = 'sprint-power-factor' value = '1.2' />
            </modifiers>
        </attributes>
    </data>
    <data tier = 'locked'>
    </data>
    <data tier = 'max'>
    </data>
</sprint>
"""
