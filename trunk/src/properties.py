#
# GOFoto 0.1.0 - a photo manager application
#
# Copyright (c) 2005-2005 Michal Nowikowski
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#



class Properties:
    def __save_elem(self, doc, xml, key, elem):
        node_key = doc.createElement(key)
        xml.appendChild(node_key)
        node_key.setAttribute("type", elem.__class__.__name__)
        node_key.setAttribute("value", str(elem))
        pass
    
    def save(self, doc, xml_base, name, attr_type=None):
        xml = doc.createElement(name)
        if attr_type:
            xml.setAttribute("type", attr_type)
            pass
        xml_base.appendChild(xml)
        
        for key in self.__dict__.keys():
            #print "%s = %s" % (str(key), str(self.__dict__[key]))
            el_type = self.__dict__[key].__class__
            if el_type == Properties:
                self.__dict__[key].save(doc, xml, key, "group")
                
            elif el_type in [int, str, unicode, bool]:
                self.__save_elem(doc, xml, key, self.__dict__[key])
                             
            elif el_type == list:
                list_node = doc.createElement(key)
                list_node.setAttribute("type", "list")
                xml.appendChild(list_node)

                table = self.__dict__[key]
                subtype = table[0].__class__
                if subtype == Properties:
                    for el in table:
                        el.save(doc, list_node, key, "group")
                        pass
                    pass
                elif subtype in [int, str, unicode, bool]:
                    for el in table:
                        self.__save_elem(doc, list_node, key, el)
                        pass
                    pass
                else:
                    print "unhandled type %s in list for field %s" % (subtype, key)
                    pass
                pass
            else:
                print "ERROR: unhandled type %s for field %s" % (el_type, key)
                pass
            pass
        pass

    def __get_value(self, el_type, node):
        if el_type == "int":
            return int(node.getAttribute("value"))
        elif el_type == "str":
            return str(node.getAttribute("value"))
        elif el_type == "unicode":
            return unicode(node.getAttribute("value"))
        elif el_type == "bool":
            val = node.getAttribute("value")
            if val == "False":
                return False
            else:
                return True
            pass
        pass

    def load(self, xml):
        for node in xml.childNodes:
            if node.nodeType != xml.ELEMENT_NODE:
                continue
            
            el_type = node.getAttribute("type")
            if el_type in ["int", "str", "unicode", "bool"]:
                self.__dict__[node.nodeName] = self.__get_value(el_type, node)
            
            elif el_type == "list":
                self.__dict__[node.nodeName] = []
                for subnode in node.childNodes:
                    if subnode.nodeType != xml.ELEMENT_NODE:
                        continue
                    sub_el_type = subnode.getAttribute("type")
                    if sub_el_type in ["int", "str", "unicode", "bool"]:
                        self.__dict__[node.nodeName].append(self.__get_value(sub_el_type, subnode))
                        
                    elif sub_el_type == "group":
                        p = Properties()
                        p.load(subnode)
                        self.__dict__[node.nodeName].append(p)
                        pass
                    else:
                        print "ERROR: unknown subtype %s" % sub_el_type
                        pass
                    pass
                pass
            elif el_type == "group":
                self.__dict__[node.nodeName] = Properties()
                self.__dict__[node.nodeName].load(node)
                    
            else:
                print "ERROR: Missing type"
                pass

            pass
        pass
    pass

# some unit test
if __name__ == "__main__":
    import xml.dom.minidom
    import sys

    # setting props
    prop = Properties()
    prop.int = 1
    prop.str = "aaa"
    prop.unicode = u"fff"
    prop.bool = True
    prop.list_int = [1, 2, 3]
    prop.list_str = ["aa", "bb", "cc"]
    prop.list_unicode = [u"aa", u"bb", u"cc"]
    prop.list_bool = [True, True, False]
    prop.subprop = Properties()
    prop.subprop.a = 1
    prop.listsubprop = [Properties(), Properties()]
    prop.listsubprop[0].x = 1
    prop.listsubprop[1].y = 1

    # saving props
    doc = xml.dom.minidom.Document()
    prop.save(doc, doc, "root")
    xml1 = doc.toprettyxml()
    print xml1
    f=open("1.xml", "w")
    f.write(xml1)
    f.close()

    # loading props
    root_xml = doc.getElementsByTagName("root")[0]
    prop2 = Properties()
    prop2.load(root_xml)

    # save 2nd time and compare
    doc2 = xml.dom.minidom.Document()
    prop2.save(doc2, doc2, "root")
    xml2 = doc2.toprettyxml()
    print xml2
    f=open("2.xml", "w")
    f.write(xml2)
    f.close()

    if xml1 == xml2:
        print "PASSED"
    else:
        print "FAILED"
        xml1_lines = xml1.splitlines()
        xml2_lines = xml2.splitlines()
        for i in range(0, len(xml1_lines)):
            if xml1_lines[i] != xml2_lines[i]:
                print "DIF[%d]:" % i
                #print xml1_lines[i]
                #print xml2_lines[i]
            else:
                print "OK[%d]:" % i
                pass
        pass  
