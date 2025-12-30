# BeerSmith MCP Server - Design Document

## Overview

This MCP (Model Context Protocol) server provides Claude Desktop with the ability to read and write BeerSmith 3 recipe data, as well as access ingredient databases (Hops, Grains, Yeast, Water Profiles, Styles) and Equipment profiles.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────────┐     ┌─────────────────────────┐
│   Claude Desktop    │◄───►│   BeerSmith MCP Server       │◄───►│  BeerSmith 3 Files      │
│                     │     │   (Python + FastMCP)         │     │  (.bsmx XML format)     │
└─────────────────────┘     └──────────────────────────────┘     └─────────────────────────┘
                                        │
                                        │ (Claude orchestration)
                                        ▼
                            ┌──────────────────────────────┐
                            │   Grocy MCP Server           │
                            │   (Your existing - via SSH)  │
                            └──────────────────────────────┘
```

## BeerSmith File Locations

| File | Purpose | Location |
|------|---------|----------|
| Recipe.bsmx | User recipes | ~/Library/Application Support/BeerSmith3/ |
| Hops.bsmx | Hop database | ~/Library/Application Support/BeerSmith3/ |
| Grain.bsmx | Grain/fermentables database | ~/Library/Application Support/BeerSmith3/ |
| Yeast.bsmx | Yeast strains database | ~/Library/Application Support/BeerSmith3/ |
| Water.bsmx | Water profiles | ~/Library/Application Support/BeerSmith3/ |
| Style.bsmx | BJCP style guidelines | ~/Library/Application Support/BeerSmith3/ |
| Equipment.bsmx | Equipment profiles | ~/Library/Application Support/BeerSmith3/ |
| Mash.bsmx | Mash profiles | ~/Library/Application Support/BeerSmith3/ |
| Misc.bsmx | Miscellaneous ingredients | ~/Library/Application Support/BeerSmith3/ |

## MCP Tools

### Recipe Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_recipes` | List all recipes with basic info (name, style, OG, FG, IBU) | `folder` (optional) |
| `get_recipe` | Get full recipe details including all ingredients | `recipe_name` or `recipe_id` |
| `create_recipe` | Create a new recipe | `recipe_data` (JSON) |
| `update_recipe` | Modify an existing recipe | `recipe_id`, `updates` (JSON) |
| `delete_recipe` | Delete a recipe | `recipe_id` |
| `export_recipe` | Export recipe in BeerXML format | `recipe_id` |

### Ingredient Databases (Read-Only)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_hops` | List available hops with AA%, type, origin | `search` (optional), `type` (optional: Bittering/Aroma/Both) |
| `get_hop` | Get detailed hop information | `hop_name` |
| `list_grains` | List available grains/fermentables | `search` (optional), `type` (optional) |
| `get_grain` | Get detailed grain information | `grain_name` |
| `list_yeasts` | List yeast strains with attenuation, temp ranges | `search` (optional), `lab` (optional) |
| `get_yeast` | Get detailed yeast information | `yeast_name` or `product_id` |
| `list_water_profiles` | List water profiles | `search` (optional) |
| `get_water_profile` | Get detailed water profile | `profile_name` |
| `list_styles` | List beer styles (BJCP) | `category` (optional) |
| `get_style` | Get detailed style information | `style_name` |
| `list_misc` | List miscellaneous ingredients | `search` (optional) |

### Equipment & Profiles (Read-Only)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_equipment` | List equipment profiles | None |
| `get_equipment` | Get equipment details (batch size, efficiency, hop util) | `equipment_name` |
| `list_mash_profiles` | List mash profiles | None |
| `get_mash_profile` | Get mash profile details | `mash_name` |

### Utility Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_ingredients` | Fuzzy search across all ingredient types | `query`, `types` (optional list) |
| `match_ingredients` | Match Grocy product names to BeerSmith ingredients | `grocy_items` (list of names) |
| `suggest_recipes_from_inventory` | Suggest possible recipes based on available ingredients | `available_ingredients` (JSON) |
| `validate_recipe` | Validate a recipe against style guidelines | `recipe_id` or `recipe_data` |

## Data Models

### Recipe
```python
@dataclass
class Recipe:
    id: str                     # _PERMID_
    name: str                   # F_R_NAME
    brewer: str                 # F_R_BREWER
    date: str                   # F_R_DATE
    style: Style                # F_R_STYLE (embedded)
    equipment: Equipment        # F_R_EQUIPMENT (embedded)
    batch_size_ml: float        # Calculated from equipment
    
    # Calculated values (from BeerSmith)
    og: float                   # F_R_OG
    fg: float                   # F_R_FG
    ibu: float                  # F_R_IBU
    srm: float                  # F_R_COLOR
    abv: float                  # F_R_ABV
    
    # Ingredients
    grains: List[RecipeGrain]
    hops: List[RecipeHop]
    yeasts: List[RecipeYeast]
    miscs: List[RecipeMisc]
    waters: List[RecipeWater]
    
    # Process
    mash: MashProfile
    boil_time: float            # F_R_BOIL_TIME
    notes: str                  # F_R_NOTES
```

### Hop
```python
@dataclass
class Hop:
    id: str                     # _PERMID_
    name: str                   # F_H_NAME
    origin: str                 # F_H_ORIGIN
    alpha: float                # F_H_ALPHA (AA%)
    beta: float                 # F_H_BETA
    type: HopType               # F_H_TYPE (0=Bittering, 1=Aroma, 2=Both)
    form: HopForm               # F_H_FORM (0=Pellet, 1=Plug, 2=Leaf)
    hsi: float                  # F_H_HSI (Hop Storage Index)
    notes: str                  # F_H_NOTES
```

### Grain/Fermentable
```python
@dataclass
class Grain:
    id: str                     # _PERMID_
    name: str                   # F_G_NAME
    origin: str                 # F_G_ORIGIN
    supplier: str               # F_G_SUPPLIER
    type: GrainType             # F_G_TYPE
    color: float                # F_G_COLOR (Lovibond)
    yield_pct: float            # F_G_YIELD
    moisture: float             # F_G_MOISTURE
    diastatic_power: float      # F_G_DIASTATIC_POWER
    protein: float              # F_G_PROTEIN
    max_in_batch: float         # F_G_MAX_IN_BATCH
    recommend_mash: bool        # F_G_RECOMMEND_MASH
    notes: str                  # F_G_NOTES
```

### Yeast
```python
@dataclass
class Yeast:
    id: str                     # _PERMID_
    name: str                   # F_Y_NAME
    lab: str                    # F_Y_LAB
    product_id: str             # F_Y_PRODUCT_ID
    type: YeastType             # F_Y_TYPE (0=Ale, 1=Lager, 2=Wine, etc.)
    form: YeastForm             # F_Y_FORM (0=Liquid, 1=Dry)
    flocculation: int           # F_Y_FLOCCULATION
    min_attenuation: float      # F_Y_MIN_ATTENUATION
    max_attenuation: float      # F_Y_MAX_ATTENUATION
    min_temp: float             # F_Y_MIN_TEMP (°F)
    max_temp: float             # F_Y_MAX_TEMP (°F)
    tolerance: float            # F_Y_TOLERANCE (ABV%)
    best_for: str               # F_Y_BEST_FOR
    notes: str                  # F_Y_NOTES
```

### Style
```python
@dataclass
class Style:
    id: str                     # _PERMID_
    name: str                   # F_S_NAME
    category: str               # F_S_CATEGORY
    guide: str                  # F_S_GUIDE (e.g., "BJCP 2015")
    number: str                 # F_S_NUMBER
    letter: str                 # F_S_LETTER
    type: StyleType             # F_S_TYPE
    min_og: float               # F_S_MIN_OG
    max_og: float               # F_S_MAX_OG
    min_fg: float               # F_S_MIN_FG
    max_fg: float               # F_S_MAX_FG
    min_ibu: float              # F_S_MIN_IBU
    max_ibu: float              # F_S_MAX_IBU
    min_color: float            # F_S_MIN_COLOR (SRM)
    max_color: float            # F_S_MAX_COLOR (SRM)
    min_abv: float              # F_S_MIN_ABV
    max_abv: float              # F_S_MAX_ABV
    description: str            # F_S_DESCRIPTION
    profile: str                # F_S_PROFILE
    ingredients: str            # F_S_INGREDIENTS
    examples: str               # F_S_EXAMPLES
```

### Equipment
```python
@dataclass
class Equipment:
    id: str                     # _PERMID_
    name: str                   # F_E_NAME
    type: EquipmentType         # F_E_TYPE
    batch_vol_ml: float         # F_E_BATCH_VOL (in BeerSmith units: oz)
    boil_time: float            # F_E_BOIL_TIME (minutes)
    boil_vol_ml: float          # F_E_BOIL_VOL
    efficiency: float           # F_E_EFFICIENCY (%)
    hop_utilization: float      # F_E_HOP_UTIL (%)
    trub_loss_ml: float         # F_E_TRUB_LOSS
    fermenter_loss_ml: float    # F_E_FERMENTER_LOSS
    notes: str                  # F_E_NOTES
```

## Unit Conversions

BeerSmith stores volumes in fluid ounces (US). Key conversions:
- 1 gallon = 128 fl oz
- 1 liter = 33.814 fl oz
- Weights in ounces (F_G_AMOUNT, F_H_AMOUNT)
- Temperatures in Fahrenheit

The MCP server will expose data in **metric units** with optional imperial.

## Fuzzy Ingredient Matching

For Grocy integration, we implement fuzzy matching:

```python
def match_ingredient(grocy_name: str, beersmith_ingredients: List[str]) -> List[Match]:
    """
    Match a Grocy product name to BeerSmith ingredient names.
    
    Strategies:
    1. Exact match (case-insensitive)
    2. Token-based matching (all words present)
    3. Fuzzy matching (Levenshtein distance)
    4. Keyword extraction (e.g., "Pilsner" matches any Pilsner malt)
    
    Examples:
    - "Crisp Pilsner Malt" → "Pilsner Malt" (keyword match)
    - "Cascade Hops (2023)" → "Cascade" (token match)
    - "US-05 Safale" → "Safale American" (fuzzy match)
    """
```

## Recipe Suggestion Algorithm

```python
def suggest_recipes(available_ingredients: Dict[str, float]) -> List[RecipeSuggestion]:
    """
    Given available inventory, suggest recipes that can be made.
    
    Steps:
    1. Match Grocy inventory to BeerSmith ingredients
    2. For each recipe, calculate ingredient coverage
    3. Score recipes by:
       - Percentage of required ingredients available
       - Freshness (hops AA% decay, yeast viability)
       - Style match with available base malts
    4. Return ranked suggestions with:
       - Missing ingredients
       - Substitute suggestions
       - Scaled quantities
    """
```

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **File corruption on write** | HIGH | Create timestamped backups before any write operation. Validate XML before saving. |
| **BeerSmith running during edit** | MEDIUM | Check for lock files. Warn user to close BeerSmith. Implement file locking. |
| **BSMX format changes** | MEDIUM | Version detection in XML. Defensive parsing with fallbacks. |
| **Ingredient name mismatch** | MEDIUM | Multiple matching strategies. User confirmation for ambiguous matches. Allow manual mapping storage. |
| **Large file performance** | LOW | Lazy loading. Cache parsed data with modification time checks. |
| **Unit conversion errors** | LOW | Comprehensive unit tests. Store original units alongside converted. |
| **Concurrent access** | LOW | File-based locking mechanism. |

## Implementation Notes

### Backup Strategy
```
~/Library/Application Support/BeerSmith3/
    └── backups/                    # Created by MCP server
        └── 2024-12-30T15-30-00/
            ├── Recipe.bsmx
            └── manifest.json       # What was changed
```

### Configuration
```json
{
  "beersmith_path": "~/Library/Application Support/BeerSmith3",
  "backup_enabled": true,
  "backup_count": 10,
  "units": "metric",
  "fuzzy_match_threshold": 0.7
}
```

## Claude Desktop Integration

### Config Location
`~/Library/Application Support/Claude/claude_desktop_config.json`

### MCP Server Entry
```json
{
  "mcpServers": {
    "beersmith": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/USERNAME/Development/BeerSmith MCP Server",
        "run",
        "beersmith-mcp"
      ]
    }
  }
}
```

## Workflow Examples

### 1. Check What You Can Brew
```
User: "What beers can I make with my current Grocy inventory?"

Claude:
1. Calls Grocy MCP → get_inventory(category="brewing")
2. Calls BeerSmith MCP → match_ingredients(grocy_items)
3. Calls BeerSmith MCP → suggest_recipes_from_inventory(matched_ingredients)
4. Returns: "Based on your inventory, you could make:
   - American Pale Ale (100% ingredients available)
   - Irish Stout (missing: Roasted Barley - 0.5kg)
   - Hefeweizen (missing: WB-06 yeast)"
```

### 2. Create Recipe from Suggestion
```
User: "Create an American Pale Ale recipe using my equipment"

Claude:
1. Calls BeerSmith MCP → get_style("American Pale Ale")
2. Calls BeerSmith MCP → list_equipment()
3. Asks user which equipment profile to use
4. Calls BeerSmith MCP → create_recipe(recipe_data)
5. Returns: "Created 'American Pale Ale v1' - OG: 1.052, IBU: 38"
```

### 3. Validate Recipe Against Style
```
User: "Does my IPA recipe fit BJCP guidelines?"

Claude:
1. Calls BeerSmith MCP → get_recipe("My IPA")
2. Calls BeerSmith MCP → validate_recipe(recipe)
3. Returns: "Your IPA is within style for OG (1.065) and IBU (62), 
   but SRM (8) is slightly below minimum (10). Consider adding 
   Crystal 60L or adjusting specialty malt ratio."
```
