#!/bin/bash
# BeerSmith MCP Server Test Script

echo "🍺 BeerSmith MCP Server Test"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check uv installation
echo "1. Checking uv installation..."
UV_PATH=$(which uv)
if [ -z "$UV_PATH" ]; then
    echo -e "${RED}✗ uv not found${NC}"
    echo "  Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
else
    echo -e "${GREEN}✓ uv found at: $UV_PATH${NC}"
fi

# Check Python version
echo ""
echo "2. Checking Python version..."
PYTHON_VERSION=$(/Users/john/.local/bin/uv run python --version 2>&1)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

# Check dependencies
echo ""
echo "3. Checking dependencies..."
cd "/Users/john/Development/BeerSmith MCP Server"
/Users/john/.local/bin/uv sync --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All dependencies installed${NC}"
else
    echo -e "${RED}✗ Dependency installation failed${NC}"
    exit 1
fi

# Check BeerSmith data
echo ""
echo "4. Checking BeerSmith 3 data..."
BEERSMITH_PATH="$HOME/Library/Application Support/BeerSmith3"
if [ -d "$BEERSMITH_PATH" ]; then
    echo -e "${GREEN}✓ BeerSmith data found at: $BEERSMITH_PATH${NC}"
    echo "  Files found:"
    ls -1 "$BEERSMITH_PATH"/*.bsmx 2>/dev/null | head -5 | sed 's/^/    /'
else
    echo -e "${RED}✗ BeerSmith 3 data not found${NC}"
    echo "  Expected at: $BEERSMITH_PATH"
fi

# Test parser
echo ""
echo "5. Testing parser..."
TEST_OUTPUT=$(/Users/john/.local/bin/uv run python -c "
from beersmith_mcp.parser import BeerSmithParser
p = BeerSmithParser()
print(f'Hops: {len(p.get_hops())}')
print(f'Grains: {len(p.get_grains())}')
print(f'Yeasts: {len(p.get_yeasts())}')
print(f'Styles: {len(p.get_styles())}')
print(f'Equipment: {len(p.get_equipment_profiles())}')
print(f'Recipes: {len(p.get_recipes())}')
" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Parser working${NC}"
    echo "$TEST_OUTPUT" | sed 's/^/    /'
else
    echo -e "${RED}✗ Parser failed${NC}"
    echo "$TEST_OUTPUT"
    exit 1
fi

# Test MCP server tools
echo ""
echo "6. Testing MCP server tools..."
TOOLS_OUTPUT=$(/Users/john/.local/bin/uv run python -c "
from beersmith_mcp.server import mcp
tools = list(mcp._tool_manager._tools.keys())
print(f'{len(tools)} tools registered')
" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ MCP server tools loaded${NC}"
    echo "    $TOOLS_OUTPUT"
else
    echo -e "${RED}✗ MCP server failed${NC}"
    echo "$TOOLS_OUTPUT"
    exit 1
fi

# Check Claude config
echo ""
echo "7. Checking Claude Desktop config..."
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CLAUDE_CONFIG" ]; then
    if grep -q "beersmith" "$CLAUDE_CONFIG"; then
        echo -e "${GREEN}✓ BeerSmith MCP configured in Claude Desktop${NC}"
        
        # Check if using full path
        if grep -q "\"command\": \"$UV_PATH\"" "$CLAUDE_CONFIG" || grep -q "\"command\": \"/.*uv\"" "$CLAUDE_CONFIG"; then
            echo -e "${GREEN}  ✓ Using full path to uv${NC}"
        else
            echo -e "${YELLOW}  ⚠ Warning: Not using full path to uv${NC}"
            echo "    Config should use: \"command\": \"$UV_PATH\""
        fi
    else
        echo -e "${YELLOW}⚠ BeerSmith not found in Claude config${NC}"
        echo "  Add to: $CLAUDE_CONFIG"
    fi
else
    echo -e "${YELLOW}⚠ Claude Desktop config not found${NC}"
fi

# Test server startup
echo ""
echo "8. Testing MCP server can be imported..."
TEST_IMPORT=$(/Users/john/.local/bin/uv run python -c "
import sys
from beersmith_mcp.server import main, mcp
print('Server imported successfully')
print(f'MCP server name: {mcp.name}')
" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ MCP server ready${NC}"
    echo "$TEST_IMPORT" | sed 's/^/    /'
else
    echo -e "${RED}✗ Server import failed${NC}"
    echo "$TEST_IMPORT"
    exit 1
fi

echo ""
echo "=============================="
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Desktop"
echo "  2. Ask Claude: 'List my brewing equipment'"
echo ""
echo "Logs: ~/Library/Logs/Claude/mcp-server-beersmith.log"
