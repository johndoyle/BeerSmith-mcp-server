"""BeerSmith MCP Server - Main server implementation."""

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from beersmith_mcp.matching import IngredientMatcher, get_hop_substitutes
from beersmith_mcp.models import (
    IngredientMatch,
    Recipe,
    RecipeGrain,
    RecipeHop,
    RecipeSuggestion,
    RecipeYeast,
    grams_to_oz,
    liters_to_oz,
)
from beersmith_mcp.parser import BeerSmithParser, DEFAULT_BEERSMITH_PATH

# Initialize the MCP server
mcp = FastMCP("BeerSmith")

# Initialize parser and matcher
parser = BeerSmithParser()
matcher = IngredientMatcher(parser)


# === Recipe Tools ===


@mcp.tool()
def list_recipes(folder: str | None = None, search: str | None = None) -> str:
    """
    List all recipes in BeerSmith.

    Args:
        folder: Optional folder path to filter recipes (e.g., "/My Recipes/")
        search: Optional search term to filter by recipe name

    Returns:
        Formatted list of recipes with basic info (name, style, OG, IBU, ABV)
    """
    recipes = parser.get_recipes(folder=folder, search=search)

    if not recipes:
        return "No recipes found."

    lines = ["# Recipes\n"]
    current_folder = ""

    for r in recipes:
        if r.folder != current_folder:
            current_folder = r.folder
            lines.append(f"\n## {current_folder}\n")

        lines.append(
            f"- **{r.name}** ({r.style or 'No style'})\n"
            f"  OG: {r.og:.3f} | FG: {r.fg:.3f} | IBU: {r.ibu:.0f} | "
            f"ABV: {r.abv:.1f}% | SRM: {r.color_srm:.0f}"
        )

    return "\n".join(lines)


@mcp.tool()
def search_recipes_by_ingredient(
    ingredient_name: str,
    ingredient_type: str = "any",
) -> str:
    """
    Search for all recipes containing a specific ingredient.

    Args:
        ingredient_name: Name of the ingredient to search for (partial match supported)
        ingredient_type: Type of ingredient - "grain", "hop", "yeast", "misc", or "any" (default)

    Returns:
        List of recipes using the specified ingredient with amounts
    """
    # Get all full recipes (need to parse them for ingredients)
    all_summaries = parser.get_recipes()
    matches = []

    ingredient_lower = ingredient_name.lower()

    for summary in all_summaries:
        recipe = parser.get_recipe(summary.name)
        if not recipe:
            continue

        found_ingredients = []

        # Check grains
        if ingredient_type in ("any", "grain"):
            for grain in recipe.grains:
                if ingredient_lower in grain.name.lower():
                    found_ingredients.append(
                        f"Grain: {grain.amount_kg:.3f} kg {grain.name}"
                    )

        # Check hops
        if ingredient_type in ("any", "hop"):
            for hop in recipe.hops:
                if ingredient_lower in hop.name.lower():
                    found_ingredients.append(
                        f"Hop: {hop.amount_grams:.1f} g {hop.name} @ {hop.boil_time:.0f} min"
                    )

        # Check yeasts
        if ingredient_type in ("any", "yeast"):
            for yeast in recipe.yeasts:
                if ingredient_lower in yeast.name.lower() or ingredient_lower in yeast.product_id.lower():
                    found_ingredients.append(f"Yeast: {yeast.name} ({yeast.product_id})")

        # Check misc
        if ingredient_type in ("any", "misc"):
            for misc in recipe.miscs:
                if ingredient_lower in misc.name.lower():
                    found_ingredients.append(f"Misc: {misc.amount:.3f} {misc.name}")

        if found_ingredients:
            matches.append({
                "recipe": recipe.name,
                "style": recipe.style.name if recipe.style else "No style",
                "folder": recipe.folder,
                "ingredients": found_ingredients,
            })

    if not matches:
        return f"No recipes found containing '{ingredient_name}' (type: {ingredient_type})."

    lines = [f"# Recipes containing '{ingredient_name}'\n"]
    lines.append(f"Found {len(matches)} recipes:\n")

    for match in sorted(matches, key=lambda m: m["recipe"]):
        lines.append(f"## {match['recipe']}")
        lines.append(f"*{match['style']}* | {match['folder']}")
        for ing in match["ingredients"]:
            lines.append(f"- {ing}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def list_recipes_with_ingredients(
    folder: str | None = None,
    search: str | None = None,
) -> str:
    """
    List recipes with their grain bill and hop schedule included.

    This provides more detail than list_recipes without fetching full recipes.

    Args:
        folder: Optional folder path to filter recipes
        search: Optional search term to filter by recipe name

    Returns:
        Recipes with grain bills and hop schedules summarized
    """
    summaries = parser.get_recipes(folder=folder, search=search)

    if not summaries:
        return "No recipes found."

    lines = ["# Recipes with Ingredients\n"]

    for summary in summaries:
        recipe = parser.get_recipe(summary.name)
        if not recipe:
            continue

        lines.append(f"## {recipe.name}")
        lines.append(
            f"*{recipe.style.name if recipe.style else 'No style'}* | "
            f"OG: {recipe.og:.3f} | IBU: {recipe.ibu:.0f} | ABV: {recipe.abv:.1f}%"
        )

        # Grain bill summary
        if recipe.grains:
            lines.append("**Grains:**")
            for grain in sorted(recipe.grains, key=lambda g: g.percent, reverse=True):
                lines.append(f"  - {grain.amount_kg:.3f} kg ({grain.percent:.0f}%) {grain.name}")

        # Hop schedule summary
        if recipe.hops:
            lines.append("**Hops:**")
            for hop in sorted(recipe.hops, key=lambda h: h.boil_time, reverse=True):
                if hop.use == 1:  # Dry hop
                    timing = f"Dry {hop.dry_hop_time:.0f}d"
                else:
                    timing = f"{hop.boil_time:.0f}m"
                lines.append(f"  - {hop.amount_grams:.1f} g {hop.name} @ {timing}")

        # Yeast (just name)
        if recipe.yeasts:
            yeast_names = ", ".join(y.name for y in recipe.yeasts)
            lines.append(f"**Yeast:** {yeast_names}")

        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def export_recipe_to_grocy(recipe_name: str) -> str:
    """
    Export a recipe in Grocy-compatible JSON format.

    Returns structured JSON that can be used to create a recipe in Grocy,
    with ingredients mapped to common Grocy product naming conventions.

    Args:
        recipe_name: Name or ID of the recipe to export

    Returns:
        JSON object with recipe data structured for Grocy import
    """
    recipe = parser.get_recipe(recipe_name)

    if not recipe:
        return f"Recipe '{recipe_name}' not found."

    # Build Grocy-compatible recipe structure
    grocy_recipe = {
        "name": recipe.name,
        "description": recipe.notes or "",
        "base_servings": 1,  # One batch
        "desired_servings": 1,
        "picture_file_name": None,
        "product_group": "Beer",
        "type": "normal",
        # Custom fields for brewing
        "userfields": {
            "style": recipe.style.name if recipe.style else "",
            "og": round(recipe.og, 3),
            "fg": round(recipe.fg, 3),
            "ibu": round(recipe.ibu, 1),
            "abv": round(recipe.abv, 1),
            "color_srm": round(recipe.color_srm, 1),
            "batch_size_liters": round(recipe.batch_size_liters, 1),
            "boil_time_minutes": round(recipe.boil_time, 0),
        },
        "ingredients": [],
    }

    # Add grains as ingredients
    for grain in recipe.grains:
        grocy_recipe["ingredients"].append({
            "product_name": grain.name,
            "ingredient_group": "Grains",
            "amount": round(grain.amount_kg * 1000, 1),  # Convert to grams
            "quantity_unit": "g",
            "note": f"{grain.percent:.0f}% of grain bill, {grain.color:.0f}°L",
            # Suggested Grocy product matching fields
            "beersmith_name": grain.name,
            "search_terms": [
                grain.name,
                grain.name.replace(" Malt", ""),
                grain.name.split()[0] if grain.name else "",
            ],
        })

    # Add hops as ingredients
    for hop in recipe.hops:
        if hop.use == 1:  # Dry hop
            timing = f"Dry hop {hop.dry_hop_time:.0f} days"
        elif hop.use == 3:  # First wort
            timing = "First Wort"
        elif hop.use == 4:  # Whirlpool
            timing = f"Whirlpool {hop.boil_time:.0f} min"
        else:
            timing = f"Boil {hop.boil_time:.0f} min"

        grocy_recipe["ingredients"].append({
            "product_name": hop.name,
            "ingredient_group": "Hops",
            "amount": round(hop.amount_grams, 1),
            "quantity_unit": "g",
            "note": f"{hop.alpha:.1f}% AA, {timing}",
            "beersmith_name": hop.name,
            "search_terms": [hop.name, f"{hop.name} Hops"],
        })

    # Add yeast as ingredient
    for yeast in recipe.yeasts:
        grocy_recipe["ingredients"].append({
            "product_name": f"{yeast.lab} {yeast.product_id}",
            "ingredient_group": "Yeast",
            "amount": 1,
            "quantity_unit": "pack",
            "note": f"{yeast.name}, {yeast.type_name}, {yeast.min_attenuation:.0f}-{yeast.max_attenuation:.0f}% attenuation",
            "beersmith_name": yeast.name,
            "search_terms": [
                yeast.name,
                yeast.product_id,
                f"{yeast.lab} {yeast.product_id}",
            ],
        })

    # Add misc ingredients
    for misc in recipe.miscs:
        grocy_recipe["ingredients"].append({
            "product_name": misc.name,
            "ingredient_group": "Misc",
            "amount": round(misc.amount, 3),
            "quantity_unit": misc.type_name.lower(),  # Approximate unit
            "note": f"Use: {misc.use_name}",
            "beersmith_name": misc.name,
            "search_terms": [misc.name],
        })

    return json.dumps(grocy_recipe, indent=2)


@mcp.tool()
def get_recipe(recipe_name: str) -> str:
    """
    Get full details of a specific recipe.

    Args:
        recipe_name: Name or ID of the recipe to retrieve

    Returns:
        Complete recipe details including ingredients, process, and targets
    """
    recipe = parser.get_recipe(recipe_name)

    if not recipe:
        return f"Recipe '{recipe_name}' not found."

    lines = [f"# {recipe.name}\n"]
    lines.append(f"**Brewer:** {recipe.brewer or 'Not specified'}")
    lines.append(f"**Date:** {recipe.recipe_date or 'Not specified'}")
    lines.append(f"**Folder:** {recipe.folder}")

    if recipe.style:
        lines.append(f"\n## Style: {recipe.style.name}")
        lines.append(f"Category: {recipe.style.category}")
        lines.append(f"Guide: {recipe.style.guide} {recipe.style.style_code}")

    lines.append("\n## Targets")
    lines.append(f"- **OG:** {recipe.og:.3f}")
    lines.append(f"- **FG:** {recipe.fg:.3f}")
    lines.append(f"- **ABV:** {recipe.abv:.1f}%")
    lines.append(f"- **IBU:** {recipe.ibu:.0f}")
    lines.append(f"- **SRM:** {recipe.color_srm:.0f}")
    lines.append(f"- **Batch Size:** {recipe.batch_size_liters:.1f} L")
    lines.append(f"- **Boil Time:** {recipe.boil_time:.0f} min")

    if recipe.equipment:
        lines.append(f"\n## Equipment: {recipe.equipment.name}")
        lines.append(f"- Type: {recipe.equipment.type_name}")
        lines.append(f"- Efficiency: {recipe.equipment.efficiency:.0f}%")
        lines.append(f"- Hop Utilization: {recipe.equipment.hop_utilization:.0f}%")

    # Fermentables
    if recipe.grains:
        lines.append("\n## Fermentables")
        total_weight = sum(g.amount_kg for g in recipe.grains)
        for grain in sorted(recipe.grains, key=lambda g: g.percent, reverse=True):
            lines.append(
                f"- {grain.amount_kg:.3f} kg ({grain.percent:.1f}%) **{grain.name}** "
                f"[{grain.color:.0f}°L, {grain.type_name}]"
            )
        lines.append(f"- **Total:** {total_weight:.3f} kg")

    # Hops
    if recipe.hops:
        lines.append("\n## Hops")
        for hop in sorted(recipe.hops, key=lambda h: h.boil_time, reverse=True):
            if hop.use == 1:  # Dry hop
                timing = f"Dry Hop {hop.dry_hop_time:.0f} days"
            else:
                timing = f"{hop.boil_time:.0f} min"
            lines.append(
                f"- {hop.amount_grams:.1f} g **{hop.name}** ({hop.alpha:.1f}% AA) "
                f"@ {timing} [{hop.use_name}]"
            )

    # Yeast
    if recipe.yeasts:
        lines.append("\n## Yeast")
        for yeast in recipe.yeasts:
            lines.append(
                f"- **{yeast.name}** ({yeast.lab} {yeast.product_id})\n"
                f"  {yeast.type_name} | {yeast.form_name} | "
                f"Attenuation: {yeast.min_attenuation:.0f}-{yeast.max_attenuation:.0f}% | "
                f"Temp: {yeast.min_temp_c:.0f}-{yeast.max_temp_c:.0f}°C"
            )

    # Mash
    if recipe.mash and recipe.mash.steps:
        lines.append(f"\n## Mash Profile: {recipe.mash.name}")
        for step in recipe.mash.steps:
            lines.append(
                f"- **{step.name}**: {step.step_temp_c:.0f}°C for {step.step_time:.0f} min "
                f"[{step.type_name}]"
            )

    # Misc
    if recipe.miscs:
        lines.append("\n## Other Ingredients")
        for misc in recipe.miscs:
            lines.append(f"- {misc.amount:.3f} {misc.name} @ {misc.use_name}")

    # Notes
    if recipe.notes:
        lines.append(f"\n## Notes\n{recipe.notes}")

    return "\n".join(lines)


@mcp.tool()
def create_recipe(
    name: str,
    style_name: str,
    equipment_name: str,
    grains_json: str,
    hops_json: str,
    yeast_name: str,
    boil_time: float = 60.0,
    brewer: str = "",
    notes: str = "",
) -> str:
    """
    Create a new recipe in BeerSmith.

    The recipe will be saved as a .bsmx file that can be imported into BeerSmith.

    Args:
        name: Recipe name
        style_name: Target beer style (e.g., "American IPA")
        equipment_name: Equipment profile to use
        grains_json: JSON array of grains: [{"name": "Pale Malt", "amount_kg": 5.0}, ...]
        hops_json: JSON array of hops: [{"name": "Cascade", "amount_g": 50, "time": 60, "use": "boil"}, ...]
        yeast_name: Yeast strain name or product ID
        boil_time: Boil time in minutes (default 60)
        brewer: Brewer name (optional)
        notes: Recipe notes (optional)

    Returns:
        Confirmation message with file path
    """
    # Parse inputs
    try:
        grains_data = json.loads(grains_json)
        hops_data = json.loads(hops_json)
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"

    # Get style
    style = parser.get_style(style_name)
    if not style:
        return f"Style '{style_name}' not found. Use list_styles to see available styles."

    # Get equipment
    equipment = parser.get_equipment(equipment_name)
    if not equipment:
        return f"Equipment '{equipment_name}' not found. Use list_equipment to see available profiles."

    # Get yeast
    yeast = parser.get_yeast(yeast_name)
    if not yeast:
        return f"Yeast '{yeast_name}' not found. Use list_yeasts to see available strains."

    # Build recipe
    recipe = Recipe(
        id="0",
        name=name,
        brewer=brewer,
        notes=notes,
        boil_time=boil_time,
        style=style,
        equipment=equipment,
        folder="/MCP Created/",
    )

    # Add grains
    for grain_data in grains_data:
        grain = parser.get_grain(grain_data["name"])
        if grain:
            amount_kg = grain_data.get("amount_kg", 0)
            recipe_grain = RecipeGrain(
                id=grain.id,
                name=grain.name,
                amount_oz=grams_to_oz(amount_kg * 1000),
                color=grain.color,
                yield_pct=grain.yield_pct,
                type=grain.type,
                origin=grain.origin,
                notes=grain.notes,
            )
            recipe.grains.append(recipe_grain)
        else:
            # Try to find similar grains
            from rapidfuzz import process, fuzz
            all_grains = parser.get_grains()
            grain_names = [g.name for g in all_grains]
            matches = process.extract(
                grain_data["name"], 
                grain_names, 
                scorer=fuzz.ratio,
                limit=3
            )
            suggestions = "\n".join([f"  - {match[0]} (confidence: {match[1]:.0f}%)" for match in matches if match[1] > 60])
            if suggestions:
                return f"Grain '{grain_data['name']}' not found.\n\nDid you mean one of these?\n{suggestions}"
            else:
                return f"Grain '{grain_data['name']}' not found. Use list_grains to see available grains."

    # Add hops
    for hop_data in hops_data:
        hop = parser.get_hop(hop_data["name"])
        if hop:
            use_map = {"boil": 0, "dry hop": 1, "mash": 2, "first wort": 3, "whirlpool": 4}
            recipe_hop = RecipeHop(
                id=hop.id,
                name=hop.name,
                amount_oz=grams_to_oz(hop_data.get("amount_g", 0)),
                alpha=hop.alpha,
                boil_time=hop_data.get("time", 60),
                use=use_map.get(hop_data.get("use", "boil").lower(), 0),
                type=hop.type,
                origin=hop.origin,
                notes=hop.notes,
            )
            recipe.hops.append(recipe_hop)
        else:
            # Try to find similar hops
            from rapidfuzz import process, fuzz
            all_hops = parser.get_hops()
            hop_names = [h.name for h in all_hops]
            matches = process.extract(
                hop_data["name"], 
                hop_names, 
                scorer=fuzz.ratio,
                limit=3
            )
            suggestions = "\n".join([f"  - {match[0]} (confidence: {match[1]:.0f}%)" for match in matches if match[1] > 60])
            if suggestions:
                return f"Hop '{hop_data['name']}' not found.\n\nDid you mean one of these?\n{suggestions}"
            else:
                return f"Hop '{hop_data['name']}' not found. Use list_hops to see available hops."

    # Add yeast
    recipe_yeast = RecipeYeast(
        id=yeast.id,
        name=yeast.name,
        lab=yeast.lab,
        product_id=yeast.product_id,
        type=yeast.type,
        form=yeast.form,
        min_attenuation=yeast.min_attenuation,
        max_attenuation=yeast.max_attenuation,
        min_temp_f=yeast.min_temp_f,
        max_temp_f=yeast.max_temp_f,
        amount=1,
    )
    recipe.yeasts.append(recipe_yeast)

    # Save recipe
    try:
        # Add recipe directly to BeerSmith's Recipe.bsmx
        parser.add_recipe_to_beersmith(recipe)
        
        # Also save as exportable file for backup
        parser.save_recipe(recipe)
        export_path = parser.beersmith_path / "MCP_Exports"
        
        return (
            f"✅ Recipe '{name}' created successfully!\n\n"
            f"The recipe has been added to BeerSmith and should appear in your recipe list.\n"
            f"Look for it in the '/MCP Created/' folder.\n\n"
            f"A backup copy was also saved to: {export_path}\n\n"
            f"**Note:** You may need to restart BeerSmith to see the new recipe."
        )
    except Exception as e:
        return f"Error saving recipe: {e}"


@mcp.tool()
def export_recipe_beerxml(recipe_name: str) -> str:
    """
    Export a recipe in BeerXML format for use with other brewing software.

    Args:
        recipe_name: Name of the recipe to export

    Returns:
        BeerXML formatted string
    """
    recipe = parser.get_recipe(recipe_name)
    if not recipe:
        return f"Recipe '{recipe_name}' not found."

    return parser.export_recipe_beerxml(recipe)


# === Ingredient Database Tools ===


@mcp.tool()
def list_hops(
    search: str | None = None,
    hop_type: str | None = None,
) -> str:
    """
    List available hop varieties.

    Args:
        search: Optional search term to filter by name or origin
        hop_type: Optional filter: "bittering", "aroma", or "both"

    Returns:
        Formatted list of hops with alpha acid percentages
    """
    type_map = {"bittering": 0, "aroma": 1, "both": 2}
    type_filter = type_map.get(hop_type.lower()) if hop_type else None

    hops = parser.get_hops(search=search, hop_type=type_filter)

    if not hops:
        return "No hops found."

    lines = ["# Hops\n"]
    lines.append("| Name | Origin | Alpha | Type | Form |")
    lines.append("|------|--------|-------|------|------|")

    for hop in hops:
        lines.append(
            f"| {hop.name} | {hop.origin} | {hop.alpha:.1f}% | "
            f"{hop.type_name} | {hop.form_name} |"
        )

    return "\n".join(lines)


@mcp.tool()
def get_hop(hop_name: str) -> str:
    """
    Get detailed information about a specific hop variety.

    Args:
        hop_name: Name of the hop to look up

    Returns:
        Detailed hop information including usage notes and substitutes
    """
    hop = parser.get_hop(hop_name)

    if not hop:
        return f"Hop '{hop_name}' not found."

    substitutes = get_hop_substitutes(hop.name)

    lines = [
        f"# {hop.name}\n",
        f"**Origin:** {hop.origin}",
        f"**Type:** {hop.type_name}",
        f"**Form:** {hop.form_name}",
        f"\n## Characteristics",
        f"- **Alpha Acid:** {hop.alpha:.1f}%",
        f"- **Beta Acid:** {hop.beta:.1f}%",
        f"- **HSI (Storage):** {hop.hsi:.0f}%",
    ]

    if hop.notes:
        lines.append(f"\n## Notes\n{hop.notes}")

    if substitutes:
        lines.append(f"\n## Possible Substitutes")
        for sub in substitutes:
            lines.append(f"- {sub}")

    return "\n".join(lines)


@mcp.tool()
def list_grains(
    search: str | None = None,
    grain_type: str | None = None,
) -> str:
    """
    List available grains and fermentables.

    Args:
        search: Optional search term to filter by name
        grain_type: Optional filter: "grain", "extract", "sugar", "adjunct", "fruit", "honey"

    Returns:
        Formatted list of grains with color and yield
    """
    type_map = {
        "grain": 0, "extract": 1, "sugar": 2, "adjunct": 3,
        "dry extract": 4, "fruit": 5, "juice": 6, "honey": 7
    }
    type_filter = type_map.get(grain_type.lower()) if grain_type else None

    grains = parser.get_grains(search=search, grain_type=type_filter)

    if not grains:
        return "No grains found."

    lines = ["# Grains & Fermentables\n"]
    lines.append("| Name | Origin | Color (°L) | Yield | Type |")
    lines.append("|------|--------|------------|-------|------|")

    for grain in grains[:50]:  # Limit to first 50
        lines.append(
            f"| {grain.name} | {grain.origin} | {grain.color:.1f} | "
            f"{grain.yield_pct:.0f}% | {grain.type_name} |"
        )

    if len(grains) > 50:
        lines.append(f"\n*...and {len(grains) - 50} more. Use search to narrow results.*")

    return "\n".join(lines)


@mcp.tool()
def get_grain(grain_name: str) -> str:
    """
    Get detailed information about a specific grain or fermentable.

    Args:
        grain_name: Name of the grain to look up

    Returns:
        Detailed grain information including characteristics
    """
    grain = parser.get_grain(grain_name)

    if not grain:
        return f"Grain '{grain_name}' not found."

    lines = [
        f"# {grain.name}\n",
        f"**Origin:** {grain.origin}",
        f"**Supplier:** {grain.supplier or 'Not specified'}",
        f"**Type:** {grain.type_name}",
        f"\n## Characteristics",
        f"- **Color:** {grain.color:.1f}°L",
        f"- **Yield:** {grain.yield_pct:.0f}%",
        f"- **Moisture:** {grain.moisture:.1f}%",
        f"- **Protein:** {grain.protein:.1f}%",
        f"- **Diastatic Power:** {grain.diastatic_power:.0f}°L",
        f"- **Max in Batch:** {grain.max_in_batch:.0f}%",
        f"- **Recommend Mash:** {'Yes' if grain.recommend_mash else 'No'}",
    ]

    if grain.notes:
        lines.append(f"\n## Notes\n{grain.notes}")

    return "\n".join(lines)


@mcp.tool()
def list_yeasts(
    search: str | None = None,
    lab: str | None = None,
) -> str:
    """
    List available yeast strains.

    Args:
        search: Optional search term to filter by name or product ID
        lab: Optional filter by lab (e.g., "Wyeast", "White Labs", "Fermentis")

    Returns:
        Formatted list of yeast strains with key characteristics
    """
    yeasts = parser.get_yeasts(search=search, lab=lab)

    if not yeasts:
        return "No yeasts found."

    lines = ["# Yeast Strains\n"]
    lines.append("| Name | Lab | ID | Type | Attenuation | Temp Range |")
    lines.append("|------|-----|----|----|-------------|------------|")

    for yeast in yeasts[:50]:  # Limit to first 50
        lines.append(
            f"| {yeast.name} | {yeast.lab} | {yeast.product_id} | "
            f"{yeast.type_name} | {yeast.min_attenuation:.0f}-{yeast.max_attenuation:.0f}% | "
            f"{yeast.min_temp_c:.0f}-{yeast.max_temp_c:.0f}°C |"
        )

    if len(yeasts) > 50:
        lines.append(f"\n*...and {len(yeasts) - 50} more. Use search or lab filter to narrow results.*")

    return "\n".join(lines)


@mcp.tool()
def get_yeast(yeast_name: str) -> str:
    """
    Get detailed information about a specific yeast strain.

    Args:
        yeast_name: Name or product ID of the yeast (e.g., "US-05" or "American Ale")

    Returns:
        Detailed yeast information including fermentation characteristics
    """
    yeast = parser.get_yeast(yeast_name)

    if not yeast:
        return f"Yeast '{yeast_name}' not found."

    lines = [
        f"# {yeast.name}\n",
        f"**Lab:** {yeast.lab}",
        f"**Product ID:** {yeast.product_id}",
        f"**Type:** {yeast.type_name}",
        f"**Form:** {yeast.form_name}",
        f"\n## Fermentation Characteristics",
        f"- **Attenuation:** {yeast.min_attenuation:.0f}-{yeast.max_attenuation:.0f}%",
        f"- **Temperature Range:** {yeast.min_temp_c:.0f}-{yeast.max_temp_c:.0f}°C "
        f"({yeast.min_temp_f:.0f}-{yeast.max_temp_f:.0f}°F)",
        f"- **Alcohol Tolerance:** {yeast.tolerance:.0f}% ABV",
        f"- **Flocculation:** {yeast.flocculation_name}",
    ]

    if yeast.best_for:
        lines.append(f"\n## Best For\n{yeast.best_for}")

    if yeast.notes:
        lines.append(f"\n## Notes\n{yeast.notes}")

    return "\n".join(lines)


@mcp.tool()
def list_water_profiles(search: str | None = None) -> str:
    """
    List available water profiles.

    Args:
        search: Optional search term to filter by name

    Returns:
        Formatted list of water profiles with mineral content
    """
    waters = parser.get_water_profiles(search=search)

    if not waters:
        return "No water profiles found."

    lines = ["# Water Profiles\n"]
    lines.append("| Name | Ca | Mg | Na | SO4 | Cl | HCO3 | pH |")
    lines.append("|------|----|----|----|----|----|----|-----|")

    for water in waters:
        lines.append(
            f"| {water.name} | {water.calcium:.0f} | {water.magnesium:.0f} | "
            f"{water.sodium:.0f} | {water.sulfate:.0f} | {water.chloride:.0f} | "
            f"{water.bicarbonate:.0f} | {water.ph:.1f} |"
        )

    return "\n".join(lines)


@mcp.tool()
def get_water_profile(profile_name: str) -> str:
    """
    Get detailed information about a specific water profile.

    Args:
        profile_name: Name of the water profile

    Returns:
        Detailed water chemistry information
    """
    water = parser.get_water_profile(profile_name)

    if not water:
        return f"Water profile '{profile_name}' not found."

    # Determine character based on SO4:Cl ratio
    if water.chloride > 0:
        ratio = water.sulfate / water.chloride
        if ratio > 2:
            character = "Very Hoppy/Bitter"
        elif ratio > 1:
            character = "Balanced-Hoppy"
        elif ratio > 0.5:
            character = "Balanced-Malty"
        else:
            character = "Very Malty/Full"
    else:
        character = "Hoppy (no chloride)"

    lines = [
        f"# {water.name}\n",
        f"**pH:** {water.ph:.1f}",
        f"**Character:** {character} (SO4:Cl ratio: {water.sulfate_chloride_ratio:.1f})",
        f"\n## Mineral Content (ppm)",
        f"- **Calcium (Ca):** {water.calcium:.0f}",
        f"- **Magnesium (Mg):** {water.magnesium:.0f}",
        f"- **Sodium (Na):** {water.sodium:.0f}",
        f"- **Sulfate (SO4):** {water.sulfate:.0f}",
        f"- **Chloride (Cl):** {water.chloride:.0f}",
        f"- **Bicarbonate (HCO3):** {water.bicarbonate:.0f}",
    ]

    if water.notes:
        lines.append(f"\n## Notes\n{water.notes}")

    return "\n".join(lines)


@mcp.tool()
def list_styles(search: str | None = None, category: str | None = None) -> str:
    """
    List beer styles (BJCP guidelines).

    Args:
        search: Optional search term to filter by name
        category: Optional category filter (e.g., "IPA", "Stout", "Belgian")

    Returns:
        Formatted list of styles with key parameters
    """
    styles = parser.get_styles(search=search, category=category)

    if not styles:
        return "No styles found."

    lines = ["# Beer Styles\n"]

    current_category = ""
    for style in styles:
        if style.category != current_category:
            current_category = style.category
            lines.append(f"\n## {current_category}\n")
            lines.append("| Style | Code | OG | IBU | ABV | SRM |")
            lines.append("|-------|------|-----|-----|-----|-----|")

        lines.append(
            f"| {style.name} | {style.style_code} | "
            f"{style.min_og:.3f}-{style.max_og:.3f} | "
            f"{style.min_ibu:.0f}-{style.max_ibu:.0f} | "
            f"{style.min_abv:.1f}-{style.max_abv:.1f}% | "
            f"{style.min_color:.0f}-{style.max_color:.0f} |"
        )

    return "\n".join(lines)


@mcp.tool()
def get_style(style_name: str) -> str:
    """
    Get detailed information about a specific beer style.

    Args:
        style_name: Name of the style (e.g., "American IPA")

    Returns:
        Detailed style information including parameters and description
    """
    style = parser.get_style(style_name)

    if not style:
        return f"Style '{style_name}' not found."

    lines = [
        f"# {style.name}\n",
        f"**Category:** {style.category}",
        f"**Guide:** {style.guide}",
        f"**Code:** {style.style_code}",
        f"**Type:** {style.type_name}",
        f"\n## Parameters",
        f"- **OG:** {style.min_og:.3f} - {style.max_og:.3f}",
        f"- **FG:** {style.min_fg:.3f} - {style.max_fg:.3f}",
        f"- **ABV:** {style.min_abv:.1f}% - {style.max_abv:.1f}%",
        f"- **IBU:** {style.min_ibu:.0f} - {style.max_ibu:.0f}",
        f"- **SRM:** {style.min_color:.0f} - {style.max_color:.0f}",
        f"- **Carbonation:** {style.min_carb:.1f} - {style.max_carb:.1f} vols",
    ]

    if style.description:
        lines.append(f"\n## Description\n{style.description}")

    if style.profile:
        lines.append(f"\n## Profile\n{style.profile}")

    if style.ingredients:
        lines.append(f"\n## Ingredients\n{style.ingredients}")

    if style.examples:
        lines.append(f"\n## Commercial Examples\n{style.examples}")

    return "\n".join(lines)


# === Equipment Tools ===


@mcp.tool()
def list_equipment() -> str:
    """
    List available equipment profiles.

    Returns:
        Formatted list of equipment with batch size and efficiency
    """
    equipment = parser.get_equipment_profiles()

    if not equipment:
        return "No equipment profiles found."

    lines = ["# Equipment Profiles\n"]
    lines.append("| Name | Type | Batch Size | Efficiency | Hop Util |")
    lines.append("|------|------|------------|------------|----------|")

    for equip in equipment:
        lines.append(
            f"| {equip.name} | {equip.type_name} | "
            f"{equip.batch_size_liters:.1f} L ({equip.batch_size_gallons:.1f} gal) | "
            f"{equip.efficiency:.0f}% | {equip.hop_utilization:.0f}% |"
        )

    return "\n".join(lines)


@mcp.tool()
def get_equipment(equipment_name: str) -> str:
    """
    Get detailed information about a specific equipment profile.

    Args:
        equipment_name: Name of the equipment profile

    Returns:
        Detailed equipment information including volumes and losses
    """
    equip = parser.get_equipment(equipment_name)

    if not equip:
        return f"Equipment '{equipment_name}' not found."

    lines = [
        f"# {equip.name}\n",
        f"**Type:** {equip.type_name}",
        f"\n## Volumes",
        f"- **Batch Size:** {equip.batch_size_liters:.1f} L ({equip.batch_size_gallons:.1f} gal)",
        f"- **Boil Size:** {equip.boil_size_liters:.1f} L",
        f"- **Boil Time:** {equip.boil_time:.0f} min",
        f"- **Boil Off Rate:** {oz_to_liters(equip.boil_off_oz):.1f} L/hr",
        f"\n## Efficiency",
        f"- **Brewhouse Efficiency:** {equip.efficiency:.0f}%",
        f"- **Hop Utilization:** {equip.hop_utilization:.0f}%",
        f"\n## Losses",
        f"- **Trub Loss:** {oz_to_liters(equip.trub_loss_oz):.2f} L",
        f"- **Fermenter Loss:** {oz_to_liters(equip.fermenter_loss_oz):.2f} L",
    ]

    if equip.notes:
        lines.append(f"\n## Notes\n{equip.notes}")

    return "\n".join(lines)


# === Utility Tools ===


@mcp.tool()
def search_ingredients(
    query: str,
    types: str | None = None,
) -> str:
    """
    Search across all ingredient types (hops, grains, yeasts, misc).

    Args:
        query: Search term
        types: Optional comma-separated list of types to search: "hop,grain,yeast,misc"

    Returns:
        Search results grouped by ingredient type
    """
    type_list = types.split(",") if types else ["hop", "grain", "yeast", "misc"]
    type_list = [t.strip().lower() for t in type_list]

    lines = [f"# Search Results for '{query}'\n"]

    if "hop" in type_list:
        hops = parser.get_hops(search=query)
        if hops:
            lines.append("\n## Hops")
            for hop in hops[:10]:
                lines.append(f"- **{hop.name}** ({hop.origin}) - {hop.alpha:.1f}% AA")

    if "grain" in type_list:
        grains = parser.get_grains(search=query)
        if grains:
            lines.append("\n## Grains")
            for grain in grains[:10]:
                lines.append(f"- **{grain.name}** ({grain.origin}) - {grain.color:.0f}°L")

    if "yeast" in type_list:
        yeasts = parser.get_yeasts(search=query)
        if yeasts:
            lines.append("\n## Yeasts")
            for yeast in yeasts[:10]:
                lines.append(f"- **{yeast.name}** ({yeast.lab} {yeast.product_id})")

    if "misc" in type_list:
        miscs = parser.get_misc_ingredients(search=query)
        if miscs:
            lines.append("\n## Miscellaneous")
            for misc in miscs[:10]:
                lines.append(f"- **{misc.name}** ({misc.type_name})")

    if len(lines) == 1:
        return f"No ingredients found matching '{query}'."

    return "\n".join(lines)


@mcp.tool()
def match_ingredients(grocy_items_json: str, threshold: float = 0.5) -> str:
    """
    Match Grocy product names to BeerSmith ingredients.

    This is useful for inventory integration - it finds the best BeerSmith
    ingredient match for each Grocy product name.

    Args:
        grocy_items_json: JSON array of Grocy product names to match
            Example: ["Crisp Pilsner Malt", "Cascade Hops 2023", "US-05"]
        threshold: Minimum confidence score (0.0 to 1.0, default 0.5)

    Returns:
        Match results showing the best BeerSmith match for each item
    """
    try:
        grocy_items = json.loads(grocy_items_json)
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"

    if not isinstance(grocy_items, list):
        return "Error: grocy_items_json must be a JSON array of strings."

    results = matcher.match_ingredients_batch(grocy_items, threshold=threshold)

    lines = ["# Ingredient Matching Results\n"]

    for query, matches in results.items():
        lines.append(f"\n## {query}")
        if matches:
            for match in matches[:3]:
                confidence_pct = match.confidence * 100
                emoji = "✅" if match.confidence >= 0.8 else "⚠️" if match.confidence >= 0.6 else "❓"
                lines.append(
                    f"- {emoji} **{match.matched_name}** ({match.matched_type}) "
                    f"- {confidence_pct:.0f}% confidence"
                )
        else:
            lines.append("- ❌ No matches found")

    return "\n".join(lines)


@mcp.tool()
def suggest_recipes(available_ingredients_json: str) -> str:
    """
    Suggest recipes that can be brewed with available ingredients.

    Args:
        available_ingredients_json: JSON object with available ingredients
            Example: {
                "grains": ["Pilsner Malt", "Munich Malt"],
                "hops": ["Cascade", "Centennial"],
                "yeasts": ["US-05"]
            }

    Returns:
        List of suggested recipes ranked by ingredient availability
    """
    try:
        available = json.loads(available_ingredients_json)
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"

    # Get available ingredient names (matched to BeerSmith)
    available_grains = set()
    for g in available.get("grains", []):
        matches = matcher.match_ingredient(g, ingredient_types=["grain"], threshold=0.6, limit=1)
        if matches:
            available_grains.add(matches[0].matched_name.lower())

    available_hops = set()
    for h in available.get("hops", []):
        matches = matcher.match_ingredient(h, ingredient_types=["hop"], threshold=0.6, limit=1)
        if matches:
            available_hops.add(matches[0].matched_name.lower())

    available_yeasts = set()
    for y in available.get("yeasts", []):
        matches = matcher.match_ingredient(y, ingredient_types=["yeast"], threshold=0.6, limit=1)
        if matches:
            available_yeasts.add(matches[0].matched_name.lower())

    # Score each recipe
    recipes = parser.get_recipes()
    suggestions: list[RecipeSuggestion] = []

    for recipe_summary in recipes:
        recipe = parser.get_recipe(recipe_summary.id)
        if not recipe:
            continue

        # Calculate match percentage
        recipe_grains = {g.name.lower() for g in recipe.grains}
        recipe_hops = {h.name.lower() for h in recipe.hops}
        recipe_yeasts = {y.name.lower() for y in recipe.yeasts}

        matched_grains = recipe_grains & available_grains
        matched_hops = recipe_hops & available_hops
        matched_yeasts = recipe_yeasts & available_yeasts

        total_ingredients = len(recipe_grains) + len(recipe_hops) + len(recipe_yeasts)
        matched_ingredients = len(matched_grains) + len(matched_hops) + len(matched_yeasts)

        if total_ingredients == 0:
            continue

        match_pct = (matched_ingredients / total_ingredients) * 100

        if match_pct >= 50:  # Only suggest if at least 50% ingredients available
            missing = []
            missing.extend(recipe_grains - available_grains)
            missing.extend(recipe_hops - available_hops)
            missing.extend(recipe_yeasts - available_yeasts)

            suggestions.append(
                RecipeSuggestion(
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                    style=recipe.style.name if recipe.style else "",
                    match_percentage=match_pct,
                    available_ingredients=list(matched_grains | matched_hops | matched_yeasts),
                    missing_ingredients=missing,
                )
            )

    # Sort by match percentage
    suggestions.sort(key=lambda s: s.match_percentage, reverse=True)

    if not suggestions:
        return "No recipes found that match your available ingredients (minimum 50% match required)."

    lines = ["# Recipe Suggestions\n"]
    lines.append("Based on your available ingredients:\n")

    for sugg in suggestions[:10]:
        emoji = "🍺" if sugg.match_percentage >= 90 else "🍻" if sugg.match_percentage >= 75 else "🔸"
        lines.append(f"\n## {emoji} {sugg.recipe_name}")
        lines.append(f"**Style:** {sugg.style}")
        lines.append(f"**Match:** {sugg.match_percentage:.0f}%")

        if sugg.missing_ingredients:
            lines.append(f"\n**Missing ({len(sugg.missing_ingredients)}):**")
            for missing in sugg.missing_ingredients[:5]:
                # Suggest substitutes for hops
                subs = get_hop_substitutes(missing)
                sub_text = f" (try: {', '.join(subs[:2])})" if subs else ""
                lines.append(f"- {missing}{sub_text}")
            if len(sugg.missing_ingredients) > 5:
                lines.append(f"- *...and {len(sugg.missing_ingredients) - 5} more*")

    return "\n".join(lines)


@mcp.tool()
def validate_recipe(recipe_name: str) -> str:
    """
    Validate a recipe against its target style guidelines.

    Args:
        recipe_name: Name of the recipe to validate

    Returns:
        Validation results showing style compliance
    """
    recipe = parser.get_recipe(recipe_name)

    if not recipe:
        return f"Recipe '{recipe_name}' not found."

    if not recipe.style:
        return f"Recipe '{recipe_name}' has no style set."

    style = recipe.style
    issues = []
    warnings = []
    passed = []

    # Check OG
    if recipe.og < style.min_og:
        issues.append(f"OG too low: {recipe.og:.3f} (min: {style.min_og:.3f})")
    elif recipe.og > style.max_og:
        issues.append(f"OG too high: {recipe.og:.3f} (max: {style.max_og:.3f})")
    else:
        passed.append(f"OG: {recipe.og:.3f} ✓")

    # Check FG
    if recipe.fg < style.min_fg:
        warnings.append(f"FG low: {recipe.fg:.3f} (min: {style.min_fg:.3f})")
    elif recipe.fg > style.max_fg:
        issues.append(f"FG too high: {recipe.fg:.3f} (max: {style.max_fg:.3f})")
    else:
        passed.append(f"FG: {recipe.fg:.3f} ✓")

    # Check ABV
    if recipe.abv < style.min_abv:
        issues.append(f"ABV too low: {recipe.abv:.1f}% (min: {style.min_abv:.1f}%)")
    elif recipe.abv > style.max_abv:
        issues.append(f"ABV too high: {recipe.abv:.1f}% (max: {style.max_abv:.1f}%)")
    else:
        passed.append(f"ABV: {recipe.abv:.1f}% ✓")

    # Check IBU
    if recipe.ibu < style.min_ibu:
        issues.append(f"IBU too low: {recipe.ibu:.0f} (min: {style.min_ibu:.0f})")
    elif recipe.ibu > style.max_ibu:
        issues.append(f"IBU too high: {recipe.ibu:.0f} (max: {style.max_ibu:.0f})")
    else:
        passed.append(f"IBU: {recipe.ibu:.0f} ✓")

    # Check Color
    if recipe.color_srm < style.min_color:
        issues.append(f"Color too light: {recipe.color_srm:.0f} SRM (min: {style.min_color:.0f})")
    elif recipe.color_srm > style.max_color:
        issues.append(f"Color too dark: {recipe.color_srm:.0f} SRM (max: {style.max_color:.0f})")
    else:
        passed.append(f"SRM: {recipe.color_srm:.0f} ✓")

    # Build result
    lines = [
        f"# Style Validation: {recipe.name}\n",
        f"**Target Style:** {style.name} ({style.guide} {style.style_code})",
    ]

    if not issues and not warnings:
        lines.append("\n## ✅ All parameters within style guidelines!")
    else:
        if issues:
            lines.append("\n## ❌ Out of Style")
            for issue in issues:
                lines.append(f"- {issue}")
        if warnings:
            lines.append("\n## ⚠️ Warnings")
            for warning in warnings:
                lines.append(f"- {warning}")

    lines.append("\n## ✅ Passed")
    for p in passed:
        lines.append(f"- {p}")

    return "\n".join(lines)


def oz_to_liters(oz: float) -> float:
    """Convert fluid ounces to liters."""
    return oz * 0.0295735


def main():
    """Run the BeerSmith MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
