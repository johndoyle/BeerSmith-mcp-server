#!/usr/bin/env python3
"""Debug equipment parsing."""

from lxml import etree

path = '/Users/john/Library/Application Support/BeerSmith3/Equipment.bsmx'
parser_xml = etree.XMLParser(recover=True, encoding='utf-8')
tree = etree.parse(path, parser_xml)
root = tree.getroot()

print("Root tag:", root.tag)
print("Root element count:", len(list(root.iter())))

# Find SS Brewtech equipment
for eq in root.iter('Equipment'):
    name_elem = eq.find('F_E_NAME')
    if name_elem is not None and 'SS Brewtech' in name_elem.text:
        print("\nFound:", name_elem.text)
        parent = eq.getparent()
        if parent is not None:
            print("  Parent tag:", parent.tag)
            print("  Parent is root:", parent is root)
        else:
            print("  Parent: None (this IS the root)")
        break
