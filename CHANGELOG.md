# Changelog

All notable changes to the BeerSmith MCP Server will be documented in this file.

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

## Future Versions

### Planned for 1.1.0
- Recipe update/modification support
- Windows compatibility
- Real-time file watching

### Planned for 1.2.0
- Recipe comparison tools
- Batch brewing schedules
- Enhanced water chemistry calculations

### Under Consideration
- Linux support
- BeerSmith Cloud integration
- Recipe scaling and conversion tools
- Integration with brewing equipment (Tilt, iSpindel)
- Recipe cost calculator
- Ingredient inventory tracking

---

**Version Format**: [MAJOR.MINOR.PATCH]
- MAJOR: Breaking changes
- MINOR: New features, backwards compatible
- PATCH: Bug fixes, minor improvements
