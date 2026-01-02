# Changelog

All notable changes to the BeerSmith MCP Server will be documented in this file.

## [1.2.1] - 2026-01-01

### Fixed
- **CRITICAL: BeerSmith Price Storage Format Corrected**
  - BeerSmith stores ALL prices in **price per ounce ($/oz)**, not per pound!
  - This applies to grains, hops, and misc ingredients
  - Fixed 35x multiplier bug where prices displayed incorrectly
  - Updated all conversion logic to use oz as the storage unit
  - Price conversion now works correctly: £3.75/kg → £0.1063/oz → displays as £3.75/kg ✓
  
- **Price Unit and Currency Conversion**: Complete rewrite of price handling for international users
  - **Metric is now the default**: No need to convert to imperial manually
  - **Currency conversion support**: Handles GBP, USD, EUR, CAD, AUD with configurable exchange rates
  - **Automatic detection**: Uses `currency_config.json` for your preferred currency and units
  - `convert_ingredient_price` now handles BOTH unit AND currency conversion
  - Added price display to `get_grain`, `get_hop`, and `get_yeast` tools ($/lb, $/kg, $/oz formats)
  - Added inventory display showing current stock levels
  - Clear documentation that BeerSmith stores grains in price/lb and hops in price/oz internally

### Added
- **Currency Configuration File**: New `currency_config.json` for user preferences
  - Set your local currency (GBP, USD, EUR, etc.)
  - Set preferred unit system (kg for metric, lb for imperial)
  - Configure exchange rates for accurate conversions
  - Metric (kg) is the default setting
- **Improved Price Conversion Tool**: `convert_ingredient_price` redesigned
  - Defaults to metric units (kg) - no parameters needed for most users
  - Shows step-by-step: currency conversion → unit conversion → BeerSmith format
  - Provides ready-to-use JSON for `update_ingredient`
  - Validates exchange rates and warns if missing

### Changed
- Enhanced `get_grain`, `get_hop`, and `get_yeast` output to include pricing and inventory section
- Updated all documentation to use metric as the default example
- `convert_ingredient_price` signature changed to make all parameters except price and ingredient_type optional

## [1.2.0] - 2025-12-31

### Added
- **Bulk Price Sync from Grocy**: New `sync_prices_from_grocy` tool for batch updating BeerSmith ingredient prices
  - Accepts JSON array of Grocy products with names and prices
  - Uses fuzzy matching to map Grocy products to BeerSmith ingredients
  - Supports dry-run mode (default) to preview changes before applying
  - Configurable matching threshold (default 70%)
  - Optional `product_group` field to improve matching accuracy
  - Detailed report showing matched/unmatched items with confidence scores
  - Automatic backup before applying changes

## [1.1.0] - 2025-12-31

### Added
- **4 New Tools** for enhanced workflow:
  - `search_recipes_by_ingredient`: Search all recipes containing a specific ingredient with amounts
  - `list_recipes_with_ingredients`: List recipes with grain bills and hop schedules without full fetch
  - `export_recipe_to_grocy`: Export recipes in Grocy-compatible JSON format with ingredient grouping
  - `update_ingredient`: Modify ingredient properties including price, inventory, supplier, and technical specs
- **Inventory and Price Tracking**: All ingredient models now support price and inventory fields
  - Update costs per unit for grains, hops, yeast, and misc ingredients
  - Track current inventory levels for better brewing planning
  - Automatic backup creation before any database modifications
  - Fields: `price` (cost per unit) and `inventory` (quantity on hand)
- **Intelligent Ingredient Matching**: Fuzzy matching with suggestions when exact ingredient names don't match
  - Shows top 3 similar ingredients with confidence scores
  - Dramatically improves `create_recipe` user experience
  - Applied to both grains and hops lookups

### Fixed
- **Recipe Creation Now Adds to BeerSmith**: Recipes created via `create_recipe` now:
  - Automatically appear in BeerSmith's recipe list (no manual import needed)
  - Are placed in a `/MCP Created/` folder for easy organization
  - Create automatic backups before modifying Recipe.bsmx
  - Still save exportable `.bsmx` files for backup purposes
- **Equipment Profile Loading**: Fixed parser to handle BeerSmith's non-standard multi-root XML in Equipment.bsmx
  - Now loads all 21 equipment profiles (was missing 1 custom profile)
  - Uses text-based parsing to extract additional Equipment elements beyond first root
- **Recipe Display Precision**: Improved amount formatting for better accuracy
  - Grain amounts: 3 decimal places (3.875 kg instead of 3.88 kg)
  - Hop amounts: 1 decimal place for grams (15.1 g instead of 15 g)
  - Misc ingredients: 3 decimal places for precise measurements

### Changed
- Enhanced error messages with actionable suggestions
- Recipe creation backup strategy with dual-save approach
- Improved XML parsing robustness for malformed BeerSmith files

### Technical
- Added `add_recipe_to_beersmith()` method to parser for direct Recipe.bsmx modification
- Integrated rapidfuzz fuzzy matching into ingredient lookup flow
- Extended Equipment.bsmx parser to handle multiple root elements
- Enhanced enum support in models (added "Aging" to MiscUse, "Cryo" to HopForm)

## [1.0.0] - 2024-12-30

### Initial Release

#### Added
- **20 MCP Tools** for comprehensive BeerSmith 3 integration
- **Recipe Management**: List, view, create, validate, and export recipes
- **Ingredient Databases**: Full access to hops, grains, yeasts, water profiles, and styles
- **Equipment Profiles**: View and query brewing equipment specifications
- **Fuzzy Ingredient Matching**: Intelligent matching between Grocy inventory and BeerSmith
- **Recipe Suggestions**: AI-powered recipe recommendations based on available ingredients
- **Style Validation**: Automatic BJCP style compliance checking
- **BeerXML Export**: Export recipes in standard format

#### Features
- **266 hop varieties** with characteristics and substitutions
- **182 grains and fermentables** with detailed specifications
- **501 yeast strains** with attenuation and temperature data
- **202 BJCP style guidelines** with complete parameter ranges
- **50+ water chemistry profiles** for water treatment planning

#### Technical
- FastMCP server implementation
- Pydantic 2 data models with type safety
- lxml XML parser with recovery mode for BeerSmith's non-standard XML
- rapidfuzz for fuzzy string matching
- Comprehensive error handling and logging

#### Grocy Integration
- Ingredient name matching with confidence scores
- Recipe suggestions based on inventory
- Cross-system ingredient lookup

#### Documentation
- Complete README.md with all tools and usage examples
- QUICK_START.md for fast onboarding
- DESIGN.md with architecture documentation
- Inline code documentation

### Known Limitations
- macOS only (BeerSmith 3 data location)
- Read-only for existing recipes (can create new)
- Requires server restart to see BeerSmith changes

### Dependencies
- Python 3.11+
- FastMCP 1.25.0+
- Pydantic 2.12.5+
- lxml 6.0.2+
- rapidfuzz 3.14.3+

---

**Version Format**: [MAJOR.MINOR.PATCH]
- MAJOR: Breaking changes
- MINOR: New features, backwards compatible
- PATCH: Bug fixes, minor improvements
