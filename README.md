# BeerSmith MCP Server

A MCP (Model Context Protocol) server that gives Claude Desktop direct access to your BeerSmith 3 brewing software data. Query recipes, search ingredient databases, validate recipes against BJCP style guidelines, and get intelligent recipe suggestions based on your available ingredients.

Beersmith 3 desktop, Apple Mac using Claude Desktop.   I also have Grocy MCP server for inventory management and so if that's needed then ping me.

## Features

### 🍺 Recipe Management
- **Read/Write Recipes**: List, view, create, and export recipes in BeerXML format
- **Style Validation**: Automatically validate recipes against BJCP style guidelines
- **Full Recipe Details**: Access fermentables, hops, yeast, mash profiles, and brewing notes

### 📚 Comprehensive Ingredient Databases
- **266 Hop Varieties**: Alpha acids, origins, substitutes, aroma profiles
- **182 Grains & Fermentables**: Color, yield, diastatic power, usage recommendations
- **501 Yeast Strains**: Attenuation ranges, temperature profiles, flocculation
- **202 BJCP Styles**: Complete style guidelines with OG/FG/IBU/SRM ranges
- **50+ Water Profiles**: Famous brewing water chemistry profiles

### 🔧 Equipment Profiles
- **Batch Size & Efficiency**: Access equipment settings for recipe scaling
- **Loss Calculations**: Trub, fermenter, and boil-off rates

### 🤖 Smart Features
- **Fuzzy Ingredient Matching**: Automatically match Grocy inventory to BeerSmith ingredients
- **Recipe Suggestions**: Get brewable recipes based on your available ingredients
- **Hop Substitutions**: Find alternative hops when your first choice isn't available
- **Cross-Database Search**: Search across all ingredient types simultaneously

## Installation

### Prerequisites

- **BeerSmith 3**: Must be installed on macOS at default location
- **Python 3.11+**: Required for running the server
- **uv**: Python package manager (recommended) - [Install uv](https://github.com/astral-sh/uv)

### Install with uv (Recommended)

```bash
cd "/Users/USERNAME/Development/BeerSmith MCP Server"
uv sync
```

This will:
- Create a virtual environment
- Install all dependencies (FastMCP, Pydantic, lxml, rapidfuzz)
- Make the `beersmith-mcp` command available

### Alternative: Install with pip

```bash
pip install -e .
```

## Claude Desktop Configuration

Add the BeerSmith MCP server to your Claude Desktop configuration:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "/Users/USERNAME/.local/bin/uv",
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

**Note**: Use the full path to `uv` (check with `which uv`). Claude Desktop doesn't inherit your shell's PATH.

### With Grocy Integration

If you also have the Grocy MCP server, combine them:

```json
{
  "mcpServers": {
    "grocy": {
      "command": "ssh",
      "args": ["USERNAME@SERVERIP", "docker", "exec", "-i", "grocy-mcp-server", "node", "build/index.js"]
    },
    "beersmith": {
      "command": "/Users/USERNAME/.local/bin/uv",
      "args": ["--directory", "/Users/USERNAME/Development/BeerSmith MCP Server", "run", "beersmith-mcp"]
    }
  }
}
```

**Replace**:
- `USERNAME` with your actual username
- `SERVERIP` with your Grocy server IP

**Important**: Restart Claude Desktop after updating the configuration.

### Verify Installation

Ask Claude: "List my brewing equipment" or "What hops are in my BeerSmith database?"

## Available Tools

### 📋 Recipe Tools

#### `list_recipes(search?)`
List all recipes with optional search filter.

**Example**: "Show me all my IPA recipes"

**Returns**: Recipe list with OG, FG, IBU, ABV, SRM for each recipe

---

#### `get_recipe(name)`
Get complete recipe details including fermentables, hops, yeast, mash profile, and notes.

**Parameters**:
- `name`: Recipe name (exact match)

**Example**: "Show me the full recipe for my American IPA"

**Returns**: Full recipe with:
- Style information and target parameters
- Complete fermentable bill with percentages
- Hop schedule with timing and IBU contributions
- Yeast details with attenuation and temperature ranges
- Mash profile with step-by-step instructions
- Brewing notes

---

#### `create_recipe(recipe_json)`
Create a new recipe in BeerSmith.

**Parameters**:
- `recipe_json`: JSON object with recipe details

**Example JSON**:
```json
{
  "name": "My Pale Ale",
  "style": "American Pale Ale",
  "batch_size_liters": 19,
  "boil_time": 60,
  "og": 1.052,
  "fg": 1.012,
  "ibu": 40,
  "grains": [
    {"name": "Pale Malt (2 Row) US", "amount_kg": 4.5},
    {"name": "Crystal 60", "amount_kg": 0.3}
  ],
  "hops": [
    {"name": "Cascade", "amount_g": 28, "time_min": 60},
    {"name": "Centennial", "amount_g": 28, "time_min": 10}
  ],
  "yeast": {"name": "Safale American", "amount": "1 pkg"}
}
```

---

#### `validate_recipe(recipe_name)`
Validate a recipe against its target BJCP style guidelines.

**Parameters**:
- `recipe_name`: Name of recipe to validate

**Example**: "Check if my IPA is within style"

**Returns**: Validation report showing:
- ✅ Parameters within style guidelines
- ❌ Out-of-style parameters with target ranges
- ⚠️ Borderline parameters

---

#### `export_recipe_beerxml(recipe_name)`
Export recipe in BeerXML format for sharing or importing into other software.

**Parameters**:
- `recipe_name`: Recipe name

**Returns**: Complete BeerXML document

---

### 🍀 Hop Tools

#### `list_hops(search?)`
List hop varieties with optional search.

**Parameters**:
- `search` (optional): Filter by name, origin, or characteristics

**Example**: "Show me all Cascade hops" or "List American hops"

**Returns**: Table with:
- Name, Origin, Alpha %, Type (Bittering/Aroma), Form (Pellet/Leaf/Extract)

---

#### `get_hop(name)`
Get detailed hop information including substitutes and aroma profile.

**Parameters**:
- `name`: Hop name

**Example**: "Tell me about Citra hops"

**Returns**:
- Alpha/Beta acid percentages
- HSI (Hop Storage Index)
- Usage recommendations
- Aroma characteristics
- Possible substitutes

---

### 🌾 Grain Tools

#### `list_grains(search?)`
List grains and fermentables with optional search.

**Parameters**:
- `search` (optional): Filter by name, type, or origin

**Example**: "Show me all Munich malts" or "List base malts"

**Returns**: Table with:
- Name, Origin, Color (°L), Yield %, Type

---

#### `get_grain(name)`
Get detailed grain information.

**Parameters**:
- `name`: Grain name

**Example**: "What are the specs for Pilsner malt?"

**Returns**:
- Color, yield, moisture, protein content
- Diastatic power (for base malts)
- Maximum recommended percentage in grain bill
- Requires mash? Yes/No
- Usage notes

---

### 🧫 Yeast Tools

#### `list_yeasts(search?)`
List yeast strains with optional search.

**Parameters**:
- `search` (optional): Filter by name, lab, or ID

**Example**: "Show me Wyeast strains" or "List lager yeasts"

**Returns**: Table with:
- Name, Lab, Product ID, Type, Attenuation Range, Temp Range

---

#### `get_yeast(name)`
Get detailed yeast information.

**Parameters**:
- `name`: Yeast name

**Example**: "Tell me about US-05"

**Returns**:
- Lab and product ID
- Type (Ale/Lager/etc), Form (Liquid/Dry)
- Flocculation level
- Attenuation range
- Temperature range (F and C)
- Alcohol tolerance
- Best for styles
- Usage notes

---

### 🎨 Style Tools

#### `list_styles(search?)`
List BJCP beer styles with optional search.

**Parameters**:
- `search` (optional): Filter by name or category

**Example**: "Show me all IPAs" or "List Belgian styles"

**Returns**: Table with:
- Style name, Code, OG range, FG range, IBU range, SRM range, ABV range

---

#### `get_style(name)`
Get complete BJCP style guidelines.

**Parameters**:
- `name`: Style name

**Example**: "What are the guidelines for American IPA?"

**Returns**:
- Category, Guide (BJCP year), Code
- Complete parameter ranges (OG, FG, ABV, IBU, SRM, Carbonation)
- Description and characteristics
- Recommended ingredients
- Example commercial beers

---

### ⚙️ Equipment Tools

#### `list_equipment()`
List all equipment profiles.

**Returns**: Table with:
- Name, Type, Batch Size, Efficiency, Hop Utilization

---

#### `get_equipment(name)`
Get detailed equipment profile.

**Parameters**:
- `name`: Equipment profile name

**Example**: "Show me my 5 gallon setup"

**Returns**:
- Type, batch size, boil size
- Efficiency and hop utilization
- Loss calculations (trub, fermenter, boil-off rate)

---

### 💧 Water Tools

#### `list_water_profiles(search?)`
List water chemistry profiles.

**Parameters**:
- `search` (optional): Filter by name or location

**Example**: "Show me Burton water profile"

**Returns**: Table with:
- Name, Ca, Mg, Na, SO4, Cl, HCO3, pH

---

#### `get_water_profile(name)`
Get detailed water profile.

**Parameters**:
- `name`: Water profile name

**Returns**:
- Complete ion concentrations
- pH level
- Usage recommendations for beer styles

---

### 🔍 Utility Tools

#### `search_ingredients(query, types?)`
Search across all ingredient databases.

**Parameters**:
- `query`: Search term
- `types` (optional): Comma-separated list: "hop,grain,yeast,misc"

**Example**: "Search for anything with 'cascade'" or "Find all Simcoe ingredients"

**Returns**: Results grouped by ingredient type

---

#### `match_ingredients(ingredients_json)`
Match ingredient names to BeerSmith database using fuzzy matching.

**Parameters**:
- `ingredients_json`: JSON array of ingredient names

**Example**:
```json
["Pale Ale Malt", "Cascade hops 2024", "Safale US-05"]
```

**Returns**: Top 3 matches for each ingredient with confidence scores:
- ✅ High confidence (≥80%)
- ⚠️ Medium confidence (60-80%)
- ❓ Low confidence (<60%)

**Use Case**: Match Grocy inventory items to BeerSmith ingredients

---

#### `suggest_recipes(available_ingredients_json)`
Suggest recipes based on available ingredients.

**Parameters**:
- `available_ingredients_json`: JSON object with available ingredients

**Example**:
```json
{
  "grains": ["Pale Malt", "Crystal 60", "Munich"],
  "hops": ["Cascade", "Centennial"],
  "yeasts": ["US-05", "S-04"]
}
```

**Returns**: Recipes ranked by:
- Match percentage (how many ingredients you have)
- Missing ingredients list
- Recipe details (style, OG, IBU, etc.)

**Minimum**: Requires 50% ingredient match to suggest a recipe

## Usage Examples

### Basic Queries

```
You: "List all my brewing equipment"
Claude: [Uses list_equipment tool to show your equipment profiles]

You: "What are the characteristics of Cascade hops?"
Claude: [Uses get_hop tool to show alpha acids, origin, aroma profile, substitutes]

You: "Show me American IPA style guidelines"
Claude: [Uses get_style tool to display BJCP parameters]
```

### Recipe Management

```
You: "Show me all my recipes"
Claude: [Uses list_recipes to display recipe collection]

You: "Get the full recipe for my Pale Ale"
Claude: [Uses get_recipe to show complete recipe with fermentables, hops, yeast, mash]

You: "Is my IPA within style for American IPA?"
Claude: [Uses validate_recipe to check against BJCP guidelines]
```

### Ingredient Research

```
You: "What yeasts work well for a saison?"
Claude: [Searches yeast database and provides recommendations]

You: "Find me a substitute for Simcoe hops"
Claude: [Uses get_hop to show possible substitutes like Amarillo, Citra]

You: "Compare Munich malt and Vienna malt"
Claude: [Gets grain details for both and compares characteristics]
```

### Grocy Integration

The real power comes from combining BeerSmith with Grocy:

```
You: "Check what brewing ingredients I have in stock"
Claude: [Queries Grocy inventory for brewing supplies]

You: "Match my Grocy ingredients to BeerSmith"
Claude: [Uses match_ingredients with fuzzy matching]
Result:
- "Cascade Hops 2024 Harvest" → Cascade (98% confidence)
- "2-Row Pale Malt" → Pale Malt (2 Row) US (95% confidence)
- "Safale American Yeast" → Safale American (100% confidence)

You: "What recipes can I brew with my current inventory?"
Claude: [Uses suggest_recipes with your Grocy stock]
Result: 
- "American Pale Ale" (85% match, missing: Crystal 60)
- "English Bitter" (75% match, missing: East Kent Goldings, British Ale yeast)
```

### Recipe Planning

```
You: "I want to brew an American IPA. What do I need?"
Claude: 
1. Shows BJCP style guidelines
2. Suggests appropriate base malts (Pale, Pilsner)
3. Recommends hops (Cascade, Centennial, Citra, etc.)
4. Suggests yeast (Safale US-05, WLP001)
5. Can check your Grocy inventory for what you already have

You: "Create a recipe based on these ingredients..."
Claude: [Uses create_recipe tool to build a new recipe in BeerSmith]
```

### Batch Planning

```
You: "I have 4kg of Pale Malt. What size batch can I brew?"
Claude: [Calculates based on equipment efficiency and typical grain bill]

You: "Scale this recipe to my 10 gallon equipment"
Claude: [Adjusts recipe quantities based on equipment profile]
```

## Data Sources

### BeerSmith Data Location

The MCP server reads data from your BeerSmith 3 installation:

**macOS**: `~/Library/Application Support/BeerSmith3/`

### Files Accessed

- `Hops.bsmx` - Hop varieties database
- `Grain.bsmx` - Grains and fermentables database
- `Yeast.bsmx` - Yeast strains database
- `Water.bsmx` - Water chemistry profiles
- `Style.bsmx` - BJCP style guidelines
- `Equipment.bsmx` - Equipment profiles
- `*.bsmx` (in recipe folders) - Individual recipes

### Data Loaded at Startup

- **266 hop varieties**
- **182 grains and fermentables**
- **501 yeast strains**
- **202 BJCP styles**
- **20 equipment profiles**
- **50+ water profiles**
- **All recipes** from your BeerSmith library

## Architecture

### Components

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│  FastMCP Server │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  BeerSmith      │────▶│  XML Parser      │
│  Parser         │     │  (lxml + recover)│
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Pydantic Models│────▶│  Fuzzy Matcher   │
│  (Type Safety)  │     │  (rapidfuzz)     │
└─────────────────┘     └──────────────────┘
```

### Key Technologies

- **FastMCP**: MCP protocol implementation
- **Pydantic 2**: Data validation and type safety
- **lxml**: XML parsing with recovery mode (handles BeerSmith's HTML entities)
- **rapidfuzz**: Fuzzy string matching for ingredient matching

### XML Parsing

BeerSmith files use XML with HTML entities (e.g., `&ldquo;`, `&rsquo;`). The parser:
1. Loads XML with `lxml` in recovery mode
2. Replaces common HTML entities
3. Validates against Pydantic models
4. Handles malformed XML gracefully

### Error Handling

- Malformed XML files are logged but don't crash the server
- Invalid data is skipped with warnings
- Missing fields use sensible defaults
- Type coercion for common issues (e.g., int → string for IDs)

## Development

### Project Structure

```
BeerSmith MCP Server/
├── src/
│   └── beersmith_mcp/
│       ├── __init__.py
│       ├── models.py       # Pydantic data models
│       ├── parser.py       # BeerSmith XML parser
│       ├── matching.py     # Fuzzy ingredient matching
│       └── server.py       # MCP server with all tools
├── pyproject.toml          # Project config and dependencies
├── README.md               # This file
└── DESIGN.md              # Architecture document
```

### Running Tests

```bash
# Test parser
uv run python -c "from beersmith_mcp.parser import BeerSmithParser; p = BeerSmithParser(); print(len(p.get_hops()))"

# Test individual tool
uv run python -c "from beersmith_mcp.server import list_hops; print(list_hops('cascade'))"

# Run server manually
uv run beersmith-mcp
```

### Adding New Tools

1. Add tool function in `server.py`
2. Decorate with `@mcp.tool()`
3. Add docstring with parameter descriptions
4. Test with Claude Desktop

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

### Server Not Appearing in Claude

1. Check config file path: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Verify JSON is valid (no trailing commas, proper quotes)
3. **Use full path to `uv`**: Run `which uv` and use that path in config (e.g., `/Users/USERNAME/.local/bin/uv`)
4. Restart Claude Desktop completely
5. Check logs: `~/Library/Logs/Claude/mcp-server-beersmith.log`

**Common Error**: "Failed to spawn process: No such file or directory"
- Solution: Use full path to `uv` command in config (Claude doesn't inherit your shell PATH)

### Parser Errors

If you see parsing errors:
- BeerSmith may have updated file format
- Check `~/Library/Application Support/BeerSmith3/` for file corruption
- Look for unusual characters in ingredient names

### Fuzzy Matching Issues

If ingredient matching is poor:
- Lower the `threshold` parameter (default: 0.8)
- Add more alternate names in `matching.py`
- Check ingredient names in Grocy vs BeerSmith

### Recipe Not Found

- Recipe names must match exactly (case-sensitive)
- Check recipe folder location in BeerSmith
- Try `list_recipes()` to see available names

## Safety & Data Integrity

### Read-Only by Default

Most operations are read-only. Write operations (create_recipe) create new files without modifying existing data.

### No Data Loss Risk

- Your BeerSmith files are only read, never modified
- New recipes are saved as separate `.bsmx` files
- Original recipes remain untouched

### Concurrent Access

BeerSmith and the MCP server can run simultaneously without conflicts.

## Performance

- **Startup**: ~1-2 seconds to load all databases
- **Queries**: <10ms for most operations
- **Fuzzy Matching**: <50ms for typical queries
- **Memory**: ~50MB for loaded databases

## Known Limitations

1. **Read-Only for Existing Recipes**: Cannot modify existing recipes (only create new ones)
2. **macOS Only**: Currently only supports macOS BeerSmith installations
3. **BeerSmith 3**: Tested with BeerSmith 3 format
4. **No Real-Time Sync**: Changes in BeerSmith require server restart to reflect

## Future Enhancements

- [ ] Recipe update/delete functionality
- [ ] Windows support
- [ ] Real-time file watching for BeerSmith changes
- [ ] Recipe comparison tools
- [ ] Batch brewing schedule planning
- [ ] Integration with brewing equipment (temperature monitoring, etc.)

## Credits

Built for integration between:
- **BeerSmith 3** by Brad Smith
- **Grocy** inventory management
- **Claude Desktop** by Anthropic
- **Model Context Protocol (MCP)** by Anthropic

## License

MIT License - See LICENSE file for details

---

**Made with 🍺 for homebrewers**
