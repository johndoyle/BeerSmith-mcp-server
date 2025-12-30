# BeerSmith MCP Server - Quick Start Guide

## Installation (2 minutes)

```bash
cd "/Users/USERNAME/Development/BeerSmith MCP Server"
uv sync
```

## Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "/Users/john/.local/bin/uv",
      "args": ["--directory", "/Users/john/Development/BeerSmith MCP Server", "run", "beersmith-mcp"]
    }
  }
}
```

💡 **Tip**: Find your `uv` path with `which uv` and use the full path.

**Restart Claude Desktop**

## Quick Commands

Try these with Claude:

### Basic
- "List all my brewing equipment"
- "Show me my recipes"
- "What hops do I have in BeerSmith?"

### Research
- "Tell me about Cascade hops"
- "What are the guidelines for American IPA?"
- "Find substitutes for Simcoe hops"

### Planning (with Grocy)
- "Check my brewing inventory in Grocy"
- "Match my Grocy ingredients to BeerSmith"
- "What recipes can I brew with my current stock?"

### Recipe Management
- "Show me the full recipe for [recipe name]"
- "Is my IPA within style guidelines?"
- "Export my recipe as BeerXML"

## Tool Quick Reference

| Tool | What It Does |
|------|-------------|
| `list_hops` | Browse 266 hop varieties |
| `list_grains` | Browse 182 grains/fermentables |
| `list_yeasts` | Browse 501 yeast strains |
| `list_styles` | Browse 202 BJCP styles |
| `list_recipes` | See your recipe collection |
| `get_recipe` | Full recipe details |
| `validate_recipe` | Check recipe vs style |
| `search_ingredients` | Search everything at once |
| `match_ingredients` | Match Grocy → BeerSmith |
| `suggest_recipes` | Find brewable recipes |

## Common Issues

**Server not showing in Claude?**
- Use full path to `uv` (run `which uv`)
- Check JSON syntax (no trailing commas!)
- Restart Claude Desktop completely
- Check logs: `~/Library/Logs/Claude/mcp-server-beersmith.log`
- Test manually: `cd "/Users/john/Development/BeerSmith MCP Server" && /Users/john/.local/bin/uv run beersmith-mcp`

**Recipe not found?**
- Names are case-sensitive
- Use `list_recipes` first

**Poor ingredient matching?**
- Names don't need to be exact
- Fuzzy matching handles variations
- Confidence scores show quality

## What's Loaded

- ✅ 266 hops
- ✅ 182 grains
- ✅ 501 yeasts
- ✅ 202 styles
- ✅ 20 equipment profiles
- ✅ 50+ water profiles
- ✅ All your recipes

## Next Steps

1. Ask Claude to list your equipment
2. Browse your recipe collection
3. Research ingredients for your next brew
4. Connect with Grocy for inventory-based recipe suggestions

Full documentation: [README.md](README.md)
