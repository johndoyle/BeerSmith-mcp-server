"""Parser for BeerSmith .bsmx XML files."""

import html
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from lxml import etree
from pydantic import BaseModel

from beersmith_mcp.models import (
    Equipment,
    Grain,
    Hop,
    MashProfile,
    MashStep,
    Misc,
    Recipe,
    RecipeGrain,
    RecipeHop,
    RecipeMisc,
    RecipeSummary,
    RecipeWater,
    RecipeYeast,
    Style,
    Water,
    Yeast,
)

T = TypeVar("T", bound=BaseModel)

# Default BeerSmith data path on macOS
DEFAULT_BEERSMITH_PATH = os.path.expanduser("~/Library/Application Support/BeerSmith3")

# HTML entities that need to be converted for XML parsing
HTML_ENTITIES = {
    '&ldquo;': '"',
    '&rdquo;': '"',
    '&lsquo;': "'",
    '&rsquo;': "'",
    '&ndash;': '-',
    '&mdash;': '--',
    '&nbsp;': ' ',
    '&auml;': 'ä',
    '&ouml;': 'ö',
    '&uuml;': 'ü',
    '&Auml;': 'Ä',
    '&Ouml;': 'Ö',
    '&Uuml;': 'Ü',
    '&szlig;': 'ß',
    '&eacute;': 'é',
    '&egrave;': 'è',
    '&aacute;': 'á',
    '&iacute;': 'í',
    '&oacute;': 'ó',
    '&uacute;': 'ú',
    '&ntilde;': 'ñ',
    '&copy;': '©',
    '&reg;': '®',
    '&trade;': '™',
    '&deg;': '°',
    '&plusmn;': '±',
    '&frac12;': '½',
    '&frac14;': '¼',
    '&frac34;': '¾',
    '&times;': '×',
    '&divide;': '÷',
    '&aring;': 'å',
    '&Aring;': 'Å',
    '&ordm;': 'º',
    '&shy;': '',  # Soft hyphen - remove
    '&hellip;': '...',
    '&bull;': '•',
    '&middot;': '·',
    '&cedil;': '¸',
    '&ccedil;': 'ç',
    '&Ccedil;': 'Ç',
}


class BeerSmithParser:
    """Parser for BeerSmith .bsmx files."""

    def __init__(self, beersmith_path: str | None = None):
        """Initialize parser with BeerSmith data path."""
        self.beersmith_path = Path(beersmith_path or DEFAULT_BEERSMITH_PATH)
        self.backup_path = self.beersmith_path / "mcp_backups"
        self._cache: dict[str, tuple[float, Any]] = {}  # filename -> (mtime, parsed_data)

    def _get_file_path(self, filename: str) -> Path:
        """Get full path to a BeerSmith file."""
        return self.beersmith_path / filename

    def _parse_xml_file(self, filename: str) -> etree._Element | None:
        """Parse a .bsmx XML file and return the root element."""
        filepath = self._get_file_path(filename)
        if not filepath.exists():
            return None

        # Check cache
        mtime = filepath.stat().st_mtime
        if filename in self._cache:
            cached_mtime, cached_data = self._cache[filename]
            if cached_mtime == mtime:
                return cached_data

        # BeerSmith files are not well-formed XML - they may have HTML entities
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Replace all known HTML entities with Unicode equivalents
        for entity, replacement in HTML_ENTITIES.items():
            content = content.replace(entity, replacement)
        
        # Handle numeric entities (&#39; etc.)
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)

        # Use lxml with recovery mode for better parsing
        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(content.encode('utf-8'), parser=parser)
            self._cache[filename] = (mtime, root)
            return root
        except etree.XMLSyntaxError as e:
            print(f"Error parsing {filename}: {e}")
            return None

    def _element_to_dict(self, element: etree._Element) -> dict[str, Any]:
        """Convert an XML element to a dictionary with lowercase keys."""
        result = {}
        for child in element:
            tag = child.tag.lower()
            if len(child) > 0:
                # Has children - recurse
                result[tag] = self._element_to_dict(child)
            else:
                # Leaf node - get text
                text = child.text or ""
                # Decode HTML entities
                text = html.unescape(text)
                # Try to convert to appropriate type
                result[tag] = self._convert_value(text)
        return result

    def _convert_value(self, text: str) -> Any:
        """Convert string value to appropriate Python type."""
        if not text:
            return ""

        # Try int
        try:
            if "." not in text:
                return int(text)
        except ValueError:
            pass

        # Try float
        try:
            return float(text)
        except ValueError:
            pass

        # Return as string
        return text

    def _parse_items(
        self, root: etree._Element, item_tag: str, model_class: type[T]
    ) -> list[T]:
        """Parse all items of a given type from an XML root."""
        items = []
        
        # Find all Data sections that contain items
        for data in root.iter("Data"):
            for item_elem in data.findall(item_tag):
                try:
                    item_dict = self._element_to_dict(item_elem)
                    item = model_class.model_validate(item_dict)
                    items.append(item)
                except Exception as e:
                    # Skip items that fail validation
                    name = (item_dict.get("f_h_name") or item_dict.get("f_g_name") or 
                           item_dict.get("f_y_name") or item_dict.get("f_e_name") or "unknown")
                    # Always print validation errors for debugging
                    import sys
                    print(f"Warning: Failed to parse {item_tag} '{name}': {e}", file=sys.stderr)

        return items

    # === Hop Methods ===

    def get_hops(self, search: str | None = None, hop_type: int | None = None) -> list[Hop]:
        """Get all hops, optionally filtered."""
        root = self._parse_xml_file("Hops.bsmx")
        if root is None:
            return []

        hops = self._parse_items(root, "Hops", Hop)

        # Filter by search term
        if search:
            search_lower = search.lower()
            hops = [h for h in hops if search_lower in h.name.lower() or search_lower in h.origin.lower()]

        # Filter by type
        if hop_type is not None:
            hops = [h for h in hops if h.type == hop_type]

        return sorted(hops, key=lambda h: h.name)

    def get_hop(self, name: str) -> Hop | None:
        """Get a specific hop by name."""
        hops = self.get_hops(search=name)
        for hop in hops:
            if hop.name.lower() == name.lower():
                return hop
        return hops[0] if hops else None

    # === Grain Methods ===

    def get_grains(self, search: str | None = None, grain_type: int | None = None) -> list[Grain]:
        """Get all grains/fermentables, optionally filtered."""
        root = self._parse_xml_file("Grain.bsmx")
        if root is None:
            return []

        grains = self._parse_items(root, "Grain", Grain)

        # Filter by search term
        if search:
            search_lower = search.lower()
            grains = [g for g in grains if search_lower in g.name.lower() or search_lower in g.origin.lower()]

        # Filter by type
        if grain_type is not None:
            grains = [g for g in grains if g.type == grain_type]

        return sorted(grains, key=lambda g: g.name)

    def get_grain(self, name: str) -> Grain | None:
        """Get a specific grain by name."""
        grains = self.get_grains(search=name)
        for grain in grains:
            if grain.name.lower() == name.lower():
                return grain
        return grains[0] if grains else None

    # === Yeast Methods ===

    def get_yeasts(self, search: str | None = None, lab: str | None = None) -> list[Yeast]:
        """Get all yeasts, optionally filtered."""
        root = self._parse_xml_file("Yeast.bsmx")
        if root is None:
            return []

        yeasts = self._parse_items(root, "Yeast", Yeast)

        # Filter by search term
        if search:
            search_lower = search.lower()
            yeasts = [y for y in yeasts if search_lower in y.name.lower() or 
                      search_lower in y.lab.lower() or 
                      search_lower in y.product_id.lower()]

        # Filter by lab
        if lab:
            lab_lower = lab.lower()
            yeasts = [y for y in yeasts if lab_lower in y.lab.lower()]

        return sorted(yeasts, key=lambda y: (y.lab, y.name))

    def get_yeast(self, name: str) -> Yeast | None:
        """Get a specific yeast by name or product ID."""
        yeasts = self.get_yeasts(search=name)
        for yeast in yeasts:
            if yeast.name.lower() == name.lower() or yeast.product_id.lower() == name.lower():
                return yeast
        return yeasts[0] if yeasts else None

    # === Water Methods ===

    def get_water_profiles(self, search: str | None = None) -> list[Water]:
        """Get all water profiles, optionally filtered."""
        root = self._parse_xml_file("Water.bsmx")
        if root is None:
            return []

        waters = self._parse_items(root, "Water", Water)

        # Filter by search term
        if search:
            search_lower = search.lower()
            waters = [w for w in waters if search_lower in w.name.lower()]

        return sorted(waters, key=lambda w: w.name)

    def get_water_profile(self, name: str) -> Water | None:
        """Get a specific water profile by name."""
        waters = self.get_water_profiles(search=name)
        for water in waters:
            if water.name.lower() == name.lower():
                return water
        return waters[0] if waters else None

    # === Style Methods ===

    def get_styles(self, search: str | None = None, category: str | None = None) -> list[Style]:
        """Get all beer styles, optionally filtered."""
        root = self._parse_xml_file("Style.bsmx")
        if root is None:
            return []

        styles = self._parse_items(root, "Style", Style)

        # Filter by search term
        if search:
            search_lower = search.lower()
            styles = [s for s in styles if search_lower in s.name.lower() or 
                      search_lower in s.category.lower()]

        # Filter by category
        if category:
            cat_lower = category.lower()
            styles = [s for s in styles if cat_lower in s.category.lower()]

        return sorted(styles, key=lambda s: (s.category, s.name))

    def get_style(self, name: str) -> Style | None:
        """Get a specific style by name."""
        styles = self.get_styles(search=name)
        for style in styles:
            if style.name.lower() == name.lower():
                return style
        return styles[0] if styles else None

    # === Equipment Methods ===

    def get_equipment_profiles(self) -> list[Equipment]:
        """Get all equipment profiles."""
        # Clear cache to ensure we get fresh data (equipment may be updated frequently)
        if "Equipment.bsmx" in self._cache:
            del self._cache["Equipment.bsmx"]
            
        root = self._parse_xml_file("Equipment.bsmx")
        if root is None:
            return []

        equipment = self._parse_items(root, "Equipment", Equipment)
        
        # BeerSmith's Equipment.bsmx sometimes has multiple root Equipment elements (invalid XML)
        # We need to parse these separately. Read the file and look for all Equipment elements
        try:
            file_path = self._get_file_path("Equipment.bsmx")
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Find all top-level <Equipment>...</Equipment> blocks after the first one
            import re
            # Split by </Equipment> to find multiple roots
            parts = content.split('</Equipment>')
            
            # Process parts after the first complete Equipment element
            for i, part in enumerate(parts[1:], 1):  # Skip first (main root)
                # Check if this part starts a new Equipment element
                if '<Equipment>' in part:
                    # Extract just this Equipment section
                    eq_start = part.find('<Equipment>')
                    eq_content = part[eq_start:]
                    # Add closing tag if not present
                    if '</Equipment>' not in eq_content:
                        eq_content += parts[i+1].split('<')[0] + '</Equipment>' if i+1 < len(parts) else '</Equipment>'
                    else:
                        eq_content = eq_content.split('</Equipment>')[0] + '</Equipment>'
                    
                    # Try to parse this Equipment element
                    try:
                        parser_xml = etree.XMLParser(recover=True, encoding='utf-8')
                        eq_root = etree.fromstring(eq_content.encode('utf-8'), parser=parser_xml)
                        
                        item_dict = self._element_to_dict(eq_root)
                        if "f_e_name" in item_dict:
                            item = Equipment.model_validate(item_dict)
                            # Avoid duplicates
                            if not any(e.name == item.name for e in equipment):
                                equipment.append(item)
                    except Exception as e:
                        continue  # Skip malformed extra equipment
        except Exception as e:
            print(f"Warning: Could not parse additional equipment elements: {e}")
        
        return sorted(equipment, key=lambda e: e.name)
        
        return sorted(equipment, key=lambda e: e.name)

    def get_equipment(self, name: str) -> Equipment | None:
        """Get a specific equipment profile by name."""
        equipment_list = self.get_equipment_profiles()
        for equipment in equipment_list:
            if equipment.name.lower() == name.lower():
                return equipment
        # Try partial match
        for equipment in equipment_list:
            if name.lower() in equipment.name.lower():
                return equipment
        return None

    # === Mash Methods ===

    def get_mash_profiles(self) -> list[MashProfile]:
        """Get all mash profiles."""
        root = self._parse_xml_file("Mash.bsmx")
        if root is None:
            return []

        profiles = []
        # Mash profiles have a more complex structure with nested steps
        for data in root.iter("Data"):
            for mash_elem in data.findall("MashProfile"):
                try:
                    mash_dict = self._element_to_dict(mash_elem)
                    mash = MashProfile.model_validate(mash_dict)
                    
                    # Parse steps
                    steps_elem = mash_elem.find("steps")
                    if steps_elem is not None:
                        steps_data = steps_elem.find("Data")
                        if steps_data is not None:
                            for step_elem in steps_data.findall("MashStep"):
                                step_dict = self._element_to_dict(step_elem)
                                step = MashStep.model_validate(step_dict)
                                mash.steps.append(step)
                    
                    profiles.append(mash)
                except Exception as e:
                    print(f"Warning: Failed to parse mash profile: {e}")

        return sorted(profiles, key=lambda m: m.name)

    def get_mash_profile(self, name: str) -> MashProfile | None:
        """Get a specific mash profile by name."""
        profiles = self.get_mash_profiles()
        for profile in profiles:
            if profile.name.lower() == name.lower():
                return profile
        # Try partial match
        for profile in profiles:
            if name.lower() in profile.name.lower():
                return profile
        return None

    # === Misc Methods ===

    def get_misc_ingredients(self, search: str | None = None) -> list[Misc]:
        """Get all miscellaneous ingredients."""
        root = self._parse_xml_file("Misc.bsmx")
        if root is None:
            return []

        miscs = self._parse_items(root, "Misc", Misc)

        if search:
            search_lower = search.lower()
            miscs = [m for m in miscs if search_lower in m.name.lower()]

        return sorted(miscs, key=lambda m: m.name)

    # === Recipe Methods ===

    def _parse_recipe_element(self, recipe_elem: etree._Element) -> Recipe | None:
        """Parse a single recipe element into a Recipe object."""
        try:
            recipe_dict = self._element_to_dict(recipe_elem)
            recipe = Recipe.model_validate(recipe_dict)

            # Parse embedded style
            style_elem = recipe_elem.find("F_R_STYLE")
            if style_elem is not None:
                style_dict = self._element_to_dict(style_elem)
                recipe.style = Style.model_validate(style_dict)

            # Parse embedded equipment
            equip_elem = recipe_elem.find("F_R_EQUIPMENT")
            if equip_elem is not None:
                equip_dict = self._element_to_dict(equip_elem)
                recipe.equipment = Equipment.model_validate(equip_dict)

            # Parse embedded mash
            mash_elem = recipe_elem.find("F_R_MASH")
            if mash_elem is not None:
                mash_dict = self._element_to_dict(mash_elem)
                recipe.mash = MashProfile.model_validate(mash_dict)
                
                # Parse mash steps
                steps_elem = mash_elem.find("steps")
                if steps_elem is not None:
                    steps_data = steps_elem.find("Data")
                    if steps_data is not None:
                        for step_elem in steps_data.findall("MashStep"):
                            step_dict = self._element_to_dict(step_elem)
                            step = MashStep.model_validate(step_dict)
                            recipe.mash.steps.append(step)

            # Parse ingredients
            ingredients_elem = recipe_elem.find("Ingredients")
            if ingredients_elem is not None:
                ingredients_data = ingredients_elem.find("Data")
                if ingredients_data is not None:
                    # Grains
                    for grain_elem in ingredients_data.findall("Grain"):
                        grain_dict = self._element_to_dict(grain_elem)
                        grain = RecipeGrain.model_validate(grain_dict)
                        recipe.grains.append(grain)

                    # Hops
                    for hop_elem in ingredients_data.findall("Hops"):
                        hop_dict = self._element_to_dict(hop_elem)
                        hop = RecipeHop.model_validate(hop_dict)
                        recipe.hops.append(hop)

                    # Yeasts
                    for yeast_elem in ingredients_data.findall("Yeast"):
                        yeast_dict = self._element_to_dict(yeast_elem)
                        yeast = RecipeYeast.model_validate(yeast_dict)
                        recipe.yeasts.append(yeast)

                    # Misc
                    for misc_elem in ingredients_data.findall("Misc"):
                        misc_dict = self._element_to_dict(misc_elem)
                        misc = RecipeMisc.model_validate(misc_dict)
                        recipe.miscs.append(misc)

                    # Water
                    for water_elem in ingredients_data.findall("Water"):
                        water_dict = self._element_to_dict(water_elem)
                        water = RecipeWater.model_validate(water_dict)
                        recipe.waters.append(water)

            return recipe
        except Exception as e:
            print(f"Warning: Failed to parse recipe: {e}")
            return None

    def _find_recipes_recursive(self, element: etree._Element, folder_path: str = "/") -> list[Recipe]:
        """Recursively find all recipes in folders."""
        recipes = []

        # Check for Table elements (folders)
        for table in element.findall("Table"):
            table_name = table.findtext("Name", "")
            folder_data = table.find("Data")
            if folder_data is not None:
                # Recurse into folder
                new_folder = f"{folder_path}{table_name}/"
                recipes.extend(self._find_recipes_recursive(folder_data, new_folder))

        # Check for Recipe elements directly (local recipes)
        for recipe_elem in element.findall("Recipe"):
            recipe = self._parse_recipe_element(recipe_elem)
            if recipe:
                if not recipe.folder or recipe.folder == "/":
                    recipe.folder = folder_path
                recipes.append(recipe)

        # Check for Cloud elements (cloud recipes)
        for cloud_elem in element.findall("Cloud"):
            # Cloud recipes have F_C_RECIPE sub-element with the actual recipe data
            recipe_data = cloud_elem.find("F_C_RECIPE")
            if recipe_data is not None:
                recipe = self._parse_recipe_element(recipe_data)
                if recipe:
                    if not recipe.folder or recipe.folder == "/":
                        recipe.folder = folder_path
                    recipes.append(recipe)

        # Check in Data elements
        for data in element.findall("Data"):
            recipes.extend(self._find_recipes_recursive(data, folder_path))

        return recipes

    def get_recipes(self, folder: str | None = None, search: str | None = None) -> list[RecipeSummary]:
        """Get all recipes as summaries from both local and cloud storage."""
        recipes = []
        
        # Load local recipes
        root = self._parse_xml_file("Recipe.bsmx")
        if root is not None:
            recipes.extend(self._find_recipes_recursive(root))
        
        # Load cloud recipes
        cloud_root = self._parse_xml_file("Cloud.bsmx")
        if cloud_root is not None:
            cloud_recipes = self._find_recipes_recursive(cloud_root, folder_path="/Cloud/")
            recipes.extend(cloud_recipes)

        # Filter by folder
        if folder:
            folder_lower = folder.lower()
            recipes = [r for r in recipes if folder_lower in r.folder.lower()]

        # Filter by search
        if search:
            search_lower = search.lower()
            recipes = [r for r in recipes if search_lower in r.name.lower()]

        # Convert to summaries
        summaries = []
        for r in recipes:
            summaries.append(
                RecipeSummary(
                    id=r.id,
                    name=r.name,
                    style=r.style.name if r.style else "",
                    og=r.og,
                    fg=r.fg,
                    ibu=r.ibu,
                    abv=r.abv,
                    color_srm=r.color_srm,
                    folder=r.folder,
                )
            )

        return sorted(summaries, key=lambda r: (r.folder, r.name))

    def get_recipe(self, name_or_id: str) -> Recipe | None:
        """Get a specific recipe by name or ID from both local and cloud storage."""
        recipes = []
        
        # Load local recipes
        root = self._parse_xml_file("Recipe.bsmx")
        if root is not None:
            recipes.extend(self._find_recipes_recursive(root))
        
        # Load cloud recipes
        cloud_root = self._parse_xml_file("Cloud.bsmx")
        if cloud_root is not None:
            recipes.extend(self._find_recipes_recursive(cloud_root, folder_path="/Cloud/"))
        
        # Try exact match by ID first
        for recipe in recipes:
            if recipe.id == name_or_id:
                return recipe
        
        # Try exact match by name
        name_lower = name_or_id.lower()
        for recipe in recipes:
            if recipe.name.lower() == name_lower:
                return recipe
        
        # Try partial match
        for recipe in recipes:
            if name_lower in recipe.name.lower():
                return recipe

        return None

    # === Write Operations ===

    def create_backup(self, filename: str) -> Path:
        """Create a backup of a file before modifying it."""
        source = self._get_file_path(filename)
        if not source.exists():
            raise FileNotFoundError(f"Cannot backup {filename}: file does not exist")

        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_dir = self.backup_path / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Copy file
        dest = backup_dir / filename
        shutil.copy2(source, dest)

        # Create manifest
        manifest = backup_dir / "manifest.json"
        import json
        manifest.write_text(json.dumps({
            "timestamp": timestamp,
            "files": [filename],
            "reason": "MCP server modification"
        }, indent=2))

        return dest

    def _generate_recipe_xml(self, recipe: Recipe) -> str:
        """Generate XML string for a recipe."""
        # This is a simplified implementation - a full implementation would
        # need to match BeerSmith's exact XML structure
        lines = [
            f"<Recipe><_PERMID_>{recipe.id}</_PERMID_>",
            f"<_MOD_>{datetime.now().strftime('%Y-%m-%d')}</_MOD_>",
            f"<F_R_NAME>{html.escape(recipe.name)}</F_R_NAME>",
            f"<F_R_BREWER>{html.escape(recipe.brewer)}</F_R_BREWER>",
            f"<F_R_DATE>{recipe.recipe_date or datetime.now().strftime('%Y-%m-%d')}</F_R_DATE>",
            f"<F_R_FOLDER_NAME>{html.escape(recipe.folder)}</F_R_FOLDER_NAME>",
            f"<F_R_OG>{recipe.og:.7f}</F_R_OG>",
            f"<F_R_FG>{recipe.fg:.7f}</F_R_FG>",
            f"<F_R_IBU>{recipe.ibu:.7f}</F_R_IBU>",
            f"<F_R_COLOR>{recipe.color_srm:.7f}</F_R_COLOR>",
            f"<F_R_ABV>{recipe.abv:.7f}</F_R_ABV>",
            f"<F_R_BOIL_TIME>{recipe.boil_time:.7f}</F_R_BOIL_TIME>",
            f"<F_R_NOTES>{html.escape(recipe.notes)}</F_R_NOTES>",
        ]

        # Add style if present
        if recipe.style:
            lines.append("<F_R_STYLE>")
            lines.append(f"<F_S_NAME>{html.escape(recipe.style.name)}</F_S_NAME>")
            lines.append(f"<F_S_CATEGORY>{html.escape(recipe.style.category)}</F_S_CATEGORY>")
            lines.append(f"<F_S_GUIDE>{html.escape(recipe.style.guide)}</F_S_GUIDE>")
            lines.append("</F_R_STYLE>")

        # Add ingredients section
        lines.append("<Ingredients>")
        lines.append("<Data>")

        # Add grains
        for grain in recipe.grains:
            lines.append("<Grain>")
            lines.append(f"<F_G_NAME>{html.escape(grain.name)}</F_G_NAME>")
            lines.append(f"<F_G_AMOUNT>{grain.amount_oz:.7f}</F_G_AMOUNT>")
            lines.append(f"<F_G_COLOR>{grain.color:.7f}</F_G_COLOR>")
            lines.append(f"<F_G_YIELD>{grain.yield_pct:.7f}</F_G_YIELD>")
            lines.append(f"<F_G_TYPE>{grain.type}</F_G_TYPE>")
            lines.append(f"<F_G_USE>{grain.use}</F_G_USE>")
            lines.append("</Grain>")

        # Add hops
        for hop in recipe.hops:
            lines.append("<Hops>")
            lines.append(f"<F_H_NAME>{html.escape(hop.name)}</F_H_NAME>")
            lines.append(f"<F_H_AMOUNT>{hop.amount_oz:.7f}</F_H_AMOUNT>")
            lines.append(f"<F_H_ALPHA>{hop.alpha:.7f}</F_H_ALPHA>")
            lines.append(f"<F_H_BOIL_TIME>{hop.boil_time:.7f}</F_H_BOIL_TIME>")
            lines.append(f"<F_H_USE>{hop.use}</F_H_USE>")
            lines.append(f"<F_H_TYPE>{hop.type}</F_H_TYPE>")
            lines.append("</Hops>")

        # Add yeasts
        for yeast in recipe.yeasts:
            lines.append("<Yeast>")
            lines.append(f"<F_Y_NAME>{html.escape(yeast.name)}</F_Y_NAME>")
            lines.append(f"<F_Y_LAB>{html.escape(yeast.lab)}</F_Y_LAB>")
            lines.append(f"<F_Y_PRODUCT_ID>{html.escape(yeast.product_id)}</F_Y_PRODUCT_ID>")
            lines.append(f"<F_Y_AMOUNT>{yeast.amount:.7f}</F_Y_AMOUNT>")
            lines.append(f"<F_Y_TYPE>{yeast.type}</F_Y_TYPE>")
            lines.append(f"<F_Y_FORM>{yeast.form}</F_Y_FORM>")
            lines.append("</Yeast>")

        lines.append("</Data>")
        lines.append("</Ingredients>")
        lines.append("</Recipe>")

        return "\n".join(lines)

    def save_recipe(self, recipe: Recipe) -> bool:
        """
        Save a recipe to the Recipe.bsmx file.
        
        Note: This is a simplified implementation. For full compatibility with BeerSmith,
        you may want to create recipes as .bsmx files that can be imported into BeerSmith
        rather than modifying the main Recipe.bsmx file directly.
        """
        # For safety, we'll create a separate importable .bsmx file instead of
        # modifying the main Recipe.bsmx file
        
        export_dir = self.beersmith_path / "MCP_Exports"
        export_dir.mkdir(exist_ok=True)
        
        filename = re.sub(r'[^\w\-_]', '_', recipe.name) + ".bsmx"
        filepath = export_dir / filename
        
        xml_content = self._generate_recipe_xml(recipe)
        
        # Wrap in proper container structure
        full_xml = f"""<Recipe><_PERMID_>0</_PERMID_>
<_MOD_>{datetime.now().strftime('%Y-%m-%d')}</_MOD_>
<Name>MCP Export</Name>
<Type>7372</Type>
<Dirty>1</Dirty>
<Owndata>1</Owndata>
<TID>7372</TID>
<Size>1</Size>
<_XName>Recipe</_XName>
<Allocinc>16</Allocinc>
<Data>{xml_content}
</Data></Recipe>"""

        filepath.write_text(full_xml, encoding="utf-8")
        return True

    def add_recipe_to_beersmith(self, recipe: Recipe) -> bool:
        """
        Add a recipe directly to BeerSmith's Recipe.bsmx file.
        
        This makes the recipe appear in BeerSmith without manual import.
        Creates a backup before modifying the file.
        """
        recipe_file = self.beersmith_path / "Recipe.bsmx"
        
        if not recipe_file.exists():
            raise FileNotFoundError(f"Recipe.bsmx not found at {recipe_file}")
        
        # Create backup
        self.backup_path.mkdir(exist_ok=True)
        backup_file = self.backup_path / f"Recipe_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bsmx"
        shutil.copy2(recipe_file, backup_file)
        
        # Read the current Recipe.bsmx file
        content = recipe_file.read_text(encoding="utf-8")
        
        # Find the /MCP Created/ folder or create it
        # We'll add the recipe to a special MCP folder
        folder_name = recipe.folder or "/MCP Created/"
        
        # Generate the recipe XML
        recipe_xml = self._generate_recipe_xml(recipe)
        
        # Find the best place to insert the recipe
        # Look for the Cloud folder or the end of the main Data section
        cloud_folder_pattern = r'(<Table><_PERMID_>[^<]+</_PERMID_>[^<]*<_MOD_>[^<]+</_MOD_>[^<]*<Name>Cloud</Name>.*?<Data>)'
        
        import re
        match = re.search(cloud_folder_pattern, content, re.DOTALL)
        
        if match:
            # Insert before the Cloud folder
            insert_pos = match.start()
            new_content = content[:insert_pos] + recipe_xml + content[insert_pos:]
        else:
            # Insert at the end of the main Data section, before </Data></Recipe>
            end_pattern = r'</Data></Recipe>\s*$'
            match = re.search(end_pattern, content)
            if match:
                insert_pos = match.start()
                new_content = content[:insert_pos] + recipe_xml + content[insert_pos:]
            else:
                raise ValueError("Could not find insertion point in Recipe.bsmx")
        
        # Write the modified content
        recipe_file.write_text(new_content, encoding="utf-8")
        
        # Clear cache
        self._cache.clear()
        
        return True

    def export_recipe_beerxml(self, recipe: Recipe) -> str:
        """Export a recipe in BeerXML format."""
        # BeerXML 1.0 format
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<RECIPES>',
            '  <RECIPE>',
            f'    <NAME>{html.escape(recipe.name)}</NAME>',
            '    <VERSION>1</VERSION>',
            '    <TYPE>All Grain</TYPE>',
            f'    <BREWER>{html.escape(recipe.brewer)}</BREWER>',
            f'    <BATCH_SIZE>{recipe.batch_size_liters:.2f}</BATCH_SIZE>',
            f'    <BOIL_SIZE>{recipe.batch_size_liters * 1.2:.2f}</BOIL_SIZE>',
            f'    <BOIL_TIME>{recipe.boil_time:.0f}</BOIL_TIME>',
            f'    <EFFICIENCY>{recipe.efficiency:.1f}</EFFICIENCY>',
        ]

        # Add hops
        lines.append('    <HOPS>')
        for hop in recipe.hops:
            lines.append('      <HOP>')
            lines.append(f'        <NAME>{html.escape(hop.name)}</NAME>')
            lines.append('        <VERSION>1</VERSION>')
            lines.append(f'        <ALPHA>{hop.alpha:.2f}</ALPHA>')
            lines.append(f'        <AMOUNT>{hop.amount_grams / 1000:.4f}</AMOUNT>')
            lines.append(f'        <USE>{hop.use_name}</USE>')
            lines.append(f'        <TIME>{hop.boil_time:.0f}</TIME>')
            lines.append('      </HOP>')
        lines.append('    </HOPS>')

        # Add fermentables
        lines.append('    <FERMENTABLES>')
        for grain in recipe.grains:
            lines.append('      <FERMENTABLE>')
            lines.append(f'        <NAME>{html.escape(grain.name)}</NAME>')
            lines.append('        <VERSION>1</VERSION>')
            lines.append(f'        <TYPE>{grain.type_name}</TYPE>')
            lines.append(f'        <AMOUNT>{grain.amount_kg:.4f}</AMOUNT>')
            lines.append(f'        <YIELD>{grain.yield_pct:.1f}</YIELD>')
            lines.append(f'        <COLOR>{grain.color:.1f}</COLOR>')
            lines.append('      </FERMENTABLE>')
        lines.append('    </FERMENTABLES>')

        # Add yeasts
        lines.append('    <YEASTS>')
        for yeast in recipe.yeasts:
            lines.append('      <YEAST>')
            lines.append(f'        <NAME>{html.escape(yeast.name)}</NAME>')
            lines.append('        <VERSION>1</VERSION>')
            lines.append(f'        <TYPE>{yeast.type_name}</TYPE>')
            lines.append(f'        <FORM>{yeast.form_name}</FORM>')
            lines.append(f'        <LABORATORY>{html.escape(yeast.lab)}</LABORATORY>')
            lines.append(f'        <PRODUCT_ID>{html.escape(yeast.product_id)}</PRODUCT_ID>')
            lines.append(f'        <MIN_TEMPERATURE>{yeast.min_temp_c:.1f}</MIN_TEMPERATURE>')
            lines.append(f'        <MAX_TEMPERATURE>{yeast.max_temp_c:.1f}</MAX_TEMPERATURE>')
            lines.append(f'        <ATTENUATION>{yeast.avg_attenuation:.1f}</ATTENUATION>')
            lines.append('      </YEAST>')
        lines.append('    </YEASTS>')

        # Add style if present
        if recipe.style:
            lines.append('    <STYLE>')
            lines.append(f'      <NAME>{html.escape(recipe.style.name)}</NAME>')
            lines.append('      <VERSION>1</VERSION>')
            lines.append(f'      <CATEGORY>{html.escape(recipe.style.category)}</CATEGORY>')
            lines.append(f'      <STYLE_GUIDE>{html.escape(recipe.style.guide)}</STYLE_GUIDE>')
            lines.append(f'      <OG_MIN>{recipe.style.min_og:.3f}</OG_MIN>')
            lines.append(f'      <OG_MAX>{recipe.style.max_og:.3f}</OG_MAX>')
            lines.append(f'      <FG_MIN>{recipe.style.min_fg:.3f}</FG_MIN>')
            lines.append(f'      <FG_MAX>{recipe.style.max_fg:.3f}</FG_MAX>')
            lines.append(f'      <IBU_MIN>{recipe.style.min_ibu:.1f}</IBU_MIN>')
            lines.append(f'      <IBU_MAX>{recipe.style.max_ibu:.1f}</IBU_MAX>')
            lines.append('    </STYLE>')

        lines.append('  </RECIPE>')
        lines.append('</RECIPES>')

        return '\n'.join(lines)
