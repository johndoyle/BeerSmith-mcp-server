#!/usr/bin/env python3
"""Compare parser XML vs direct lxml."""

from lxml import etree
from beersmith_mcp.parser import BeerSmithParser

# Direct lxml
path = '/Users/john/Library/Application Support/BeerSmith3/Equipment.bsmx'
parser_xml = etree.XMLParser(recover=True, encoding='utf-8')
tree = etree.parse(path, parser_xml)
root_direct = tree.getroot()

# Via parser
parser = BeerSmithParser()
parser._cache.clear()
root_parser = parser._parse_xml_file('Equipment.bsmx')

print("Direct lxml:")
print(f"  Root tag: {root_direct.tag}")
print(f"  Total Equipment elements: {len(list(root_direct.iter('Equipment')))}")

print("\nVia parser:")
print(f"  Root tag: {root_parser.tag}")
print(f"  Total Equipment elements: {len(list(root_parser.iter('Equipment')))}")

# Count SS Brewtech
direct_ss = sum(1 for eq in root_direct.iter('Equipment') 
                if eq.find('.//F_E_NAME') is not None 
                and 'SS Brewtech' in eq.find('.//F_E_NAME').text)
parser_ss = sum(1 for eq in root_parser.iter('Equipment')
                if eq.find('.//F_E_NAME') is not None
                and 'SS Brewtech' in eq.find('.//F_E_NAME').text)

print(f"\nDirect lxml SS Brewtech count: {direct_ss}")
print(f"Via parser SS Brewtech count: {parser_ss}")
