#!/usr/bin/env python3
"""Debug equipment parsing with parser."""

from beersmith_mcp.parser import BeerSmithParser
from beersmith_mcp.models import Equipment

parser = BeerSmithParser()
root = parser._parse_xml_file('Equipment.bsmx')

print(f"Root: {root}")
print(f"Root tag: {root.tag}")

# Test the iter logic
for item_elem in root.iter("Equipment"):
    if item_elem is root:
        print("Skipping root (item_elem is root)")
        continue
    
    parent = item_elem.getparent()
    if parent is not None and parent.tag == "Data":
        continue
    
    item_dict = parser._element_to_dict(item_elem)
    name = item_dict.get("f_e_name", "(no name)")
    
    if "f_e_name" not in item_dict:
        continue
        
    print(f"\nFound equipment outside Data: {name}")
    print(f"  Parent: {parent.tag if parent else 'None'}")
    print(f"  Parent is root: {parent is root}")
    
    try:
        item = Equipment.model_validate(item_dict)
        print(f"  ✓ Validated successfully")
    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
