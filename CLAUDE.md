# CLAUDE.md - BeerSmith MCP Server

## Project Overview

BeerSmith MCP Server is a Model Context Protocol (MCP) server that integrates Claude Desktop with BeerSmith 3 brewing software. It enables Claude to query recipes, ingredients, equipment, and create new recipes programmatically.

**Version**: 1.1.0
**Platform**: macOS only
**Python**: 3.11+

## Quick Commands

```bash
# Install dependencies
uv sync

# Run tests
./test_server.sh

# Start server manually
uv run beersmith-mcp

# Test parser
uv run python -c "from beersmith_mcp.parser import BeerSmithParser; p = BeerSmithParser(); print(len(p.get_hops()), 'hops loaded')"
```

## Project Structure

```
src/beersmith_mcp/
├── __init__.py      # Package init, exports main()
├── server.py        # Main MCP server with 24 tools (entry point)
├── parser.py        # BeerSmith XML parsing (.bsmx files)
├── models.py        # Pydantic v2 data models
└── matching.py      # Fuzzy ingredient matching (rapidfuzz)
```

## Key Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server with all 24 tools, main entry point |
| `parser.py` | XML parsing with lxml recovery mode for malformed files |
| `models.py` | Pydantic models: Recipe, Hop, Grain, Yeast, Style, Equipment, Water |
| `matching.py` | IngredientMatcher with fuzzy matching algorithms |
| `pyproject.toml` | Project config, dependencies, build settings |
| `test_server.sh` | Comprehensive test script |

## Architecture

```
Claude Desktop → MCP Protocol → FastMCP Server
                                    ↓
                              BeerSmithParser (reads .bsmx XML)
                                    ↓
                              Pydantic Models (validation)
                                    ↓
                              IngredientMatcher (fuzzy matching)
```

## Dependencies

- `mcp>=1.0.0` - FastMCP for MCP protocol
- `pydantic>=2.0.0` - Data validation
- `lxml>=5.0.0` - XML parsing with recovery mode
- `rapidfuzz>=3.0.0` - Fuzzy string matching

## Data Locations

- **BeerSmith Data**: `~/Library/Application Support/BeerSmith3/`
- **Backups**: `~/Library/Application Support/BeerSmith3/mcp_backups/`
- **Claude Config**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Logs**: `~/Library/Logs/Claude/mcp-server-beersmith.log`

## BeerSmith Files (.bsmx)

| File | Contents |
|------|----------|
| `Hops.bsmx` | 266 hop varieties |
| `Grain.bsmx` | 182 grains/fermentables |
| `Yeast.bsmx` | 501 yeast strains |
| `Style.bsmx` | 202 BJCP styles |
| `Equipment.bsmx` | Equipment profiles |
| `Water.bsmx` | Water chemistry profiles |
| `Recipe.bsmx` | User recipes |

## MCP Tools (25 total)

### Recipe Management
- `list_recipes()` - List recipes with search/folder filtering
- `search_recipes_by_ingredient()` - Find recipes using ingredient
- `list_recipes_with_ingredients()` - Show recipes with grain bills & hops
- `get_recipe()` - Complete recipe details
- `create_recipe()` - Create new recipe (writes to Recipe.bsmx)

### Ingredients
- `list_hops()`, `get_hop()` - Hop management
- `list_grains()`, `get_grain()` - Grain management
- `list_yeasts()`, `get_yeast()` - Yeast management
- `search_ingredients()` - Cross-database fuzzy search
- `match_ingredients()` - Match Grocy items to BeerSmith
- `update_ingredient()` - Modify price, inventory, specs
- `sync_prices_from_grocy()` - Bulk sync prices from Grocy to BeerSmith

### Equipment & Water
- `list_equipment()`, `get_equipment()` - Equipment profiles
- `list_water_profiles()`, `get_water_profile()` - Water chemistry

### Styles & Export
- `list_styles()`, `get_style()` - BJCP style guidelines
- `validate_recipe()` - Check recipe vs style
- `export_recipe_beerxml()` - Export as BeerXML
- `export_recipe_to_grocy()` - Export for Grocy system
- `suggest_recipes()` - Recommend recipes from available ingredients

## Code Patterns

### Adding a New Tool
```python
@mcp.tool()
def my_new_tool(param: str) -> str:
    """Tool description for Claude.

    Args:
        param: Parameter description
    """
    # Implementation
    return result
```

### Parser Usage
```python
parser = BeerSmithParser()
hops = parser.get_hops()           # Returns list of Hop models
recipe = parser.get_recipe("name") # Returns Recipe model or None
```

### Fuzzy Matching
```python
matcher = IngredientMatcher(parser)
matches = matcher.match_ingredient("cascade", threshold=70)
```

## XML Parsing Notes

- BeerSmith uses `.bsmx` XML format with potential issues:
  - HTML entities (`&ldquo;`, `&eacute;`)
  - Non-ASCII characters (umlauts, accents)
  - Malformed XML (parser uses recovery mode)
  - Multiple root elements in Equipment.bsmx
- Parser has 81+ HTML entity mappings in `_replace_html_entities()`

## Unit Conversions

BeerSmith stores imperial units. Conversion helpers in parser:
- `oz_to_ml()`, `oz_to_liters()`, `oz_to_grams()`
- `f_to_c()`, `c_to_f()`

## Safety Mechanisms

- **Backups**: Auto-created before any write to `mcp_backups/`
- **Validation**: Pydantic models enforce type safety
- **Recovery Mode**: lxml handles malformed XML gracefully
- **Read-Heavy**: Most operations are read-only

## Testing

```bash
# Full test suite
./test_server.sh

# Test specific component
uv run python -c "from beersmith_mcp.parser import BeerSmithParser; p = BeerSmithParser(); print(p.get_recipe('recipe_name'))"
```

## Common Issues

1. **Server not connecting**: Check Claude Desktop config path and uv installation
2. **Missing ingredients**: Restart server after BeerSmith changes (no file watching)
3. **XML parse errors**: Check for malformed XML, parser has recovery mode
4. **Recipe not found**: Use exact name or search with partial match

## Linting

```bash
# Uses ruff with line-length=100, target py311
uv run ruff check src/
uv run ruff format src/
```
