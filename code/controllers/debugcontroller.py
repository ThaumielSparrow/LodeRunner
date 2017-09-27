from code.tools.xml import XMLNode

from code.utils.common import xml_encode, xml_decode

class DebugController:

    def __init__(self):

        return


    def save_object(self, o):

        info = self.tell_all(o)

        node = XMLNode("xml")

        self.save_object_info_to_node(info, node)


        f = open( os.path.join("debug", "debug.object.xml"), "w" )
        f.write( node.compile_xml_string() )
        f.close()


    def save_object_info_to_node(self, info, node):

        for key in ("title", "type", "address", "eval"):

            node2 = node.add_node(
                XMLNode(key)
            )

            node2.innerText = "%s" % self.stringify( info[key] ).replace("<", "&lt;").replace(">", "&gt;")

        if ( len( info["descendants"] ) > 0 ):

            node2 = node.add_node(
                XMLNode("descendants")
            )

            for (attr, info2) in info["descendants"]:

                node3 = node2.add_node(
                    XMLNode(attr)
                )

                self.save_object_info_to_node(info2, node3)


    def tell(self, o, recursive = False, prefix = "", title = ""):

        info = {
            "title": "-",
            "type": "",
            "address": "",
            "eval": "",
            "descendants": []
        }

        try:

            info["title"] = title
            info["type"] = type(o)
            info["address"] = o
            info["eval"] = eval(o)
            #f.write( "%s%s\n%s%s\n%s%s:  %s\n\n" % ( prefix, title, prefix, type(o), prefix, o, stringify( eval(o) ) ) )

        except:

            info["title"] = title
            info["type"] = type(o)
            info["address"] = o
            info["eval"] = ""
            #f.write( "%s%s\n%s%s\n%s%s\n\n" % ( prefix, title, prefix, type(o), prefix, o ) )

        try:

            for attr in o.__dict__:

                info["descendants"].append((
                    attr,
                    self.tell( o.__dict__[attr], recursive = recursive, prefix = "\t%s" % prefix, title = attr )
                ))

        except:

            if ( type(o) == type([]) ):

                for i in range( 0, len(o) ):

                    info["descendants"].append((
                        "%d" % i,
                        self.tell( o[i], recursive = recursive, title = "List Index %d" % i )
                    ))

        return info


    def tell_all(self, o):

        return self.tell(o, recursive = True)


    def stringify(self, o):

        output = ""

        try:
            output = "%s" % o

        except:

            # Maybe it's an annoying tuple
            try:
                output = "%s" % ",".join( x for x in o )

            except:
                pass

        return output
