#!/usr/bin/env python3
from lxml import etree

path = '/Users/john/Library/Application Support/BeerSmith3/Equipment.bsmx'
parser = etree.XMLParser(recover=True, encoding='utf-8')
tree = etree.parse(path, parser)
root = tree.getroot()

print("Searching for Brewtech equipment...")
found = False
for eq in root.iter('Equipment'):
    for name_elem in eq.iter('F_E_NAME'):
        text = name_elem.text or ""
        if 'Brewtech' in text or 'brewtech' in text or 'SS' in text:
            print(f'Found: |{text}|')
            found = True
            break

if not found:
    print("Not found in F_E_NAME elements")
    print("\nChecking if it exists in file at all...")
    with open(path, 'r') as f:
        content = f.read()
        if 'Brewtech' in content:
            print("YES - found 'Brewtech' in raw file content")
            # Show context
            import re
            matches = re.findall(r'.{0,50}Brewtech.{0,50}', content)
            for m in matches[:3]:
                print(f"  Context: {m}")
        else:
            print("NO - not in file at all")
