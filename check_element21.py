#!/usr/bin/env python3
from beersmith_mcp.parser import BeerSmithParser

parser = BeerSmithParser()
parser._cache.clear()
root = parser._parse_xml_file('Equipment.bsmx')

all_equipment = list(root.iter('Equipment'))
print(f"Total Equipment elements found: {len(all_equipment)}")

# Check element 21 (index 20, the last one)
if len(all_equipment) >= 21:
    eq21 = all_equipment[20]
    print(f"\nElement #21:")
    print(f"  Is root: {eq21 is root}")
    print(f"  Parent: {eq21.getparent().tag if eq21.getparent() else 'None'}")
    print(f"  Parent is root: {eq21.getparent() is root if eq21.getparent() else 'N/A'}")
    
    # Try to get its dict
    eq21_dict = parser._element_to_dict(eq21)
    print(f"  Has f_e_name: {'f_e_name' in eq21_dict}")
    if 'f_e_name' in eq21_dict:
        print(f"  Name: {eq21_dict['f_e_name']}")
else:
    print("Less than 21 elements found")
