# Example: Updating Ingredient Prices from Grocy (Metric, GBP)

This guide shows how to update ingredient prices using **metric units** and **GBP currency** as defaults.

## Critical Information

**BeerSmith stores ALL prices in price per OUNCE ($/oz or £/oz)**

This includes:
- ✓ Grains: £/oz (NOT £/lb!)
- ✓ Hops: £/oz
- ✓ Misc: £/oz
- ✓ Yeast: £/package

When BeerSmith displays prices in metric (£/kg), it multiplies the stored £/oz value by 35.274.

**Example**: 
- Stored: £0.1063/oz
- Displayed: £0.1063 × 35.274 = £3.75/kg ✓

## Setup (One-time)

1. Edit `src/beersmith_mcp/currency_config.json`:
```json
{
  "user_currency": "GBP",
  "user_default_unit": "kg",
  "beersmith_currency": "GBP",
  "exchange_rates": {
    "USD_to_GBP": 0.79,
    "GBP_to_USD": 1.27,
    "EUR_to_GBP": 0.86,
    "GBP_to_EUR": 1.16
  }
}
```

2. Restart Claude Desktop

## Example 1: Simple Grain Price Update

**Scenario**: Grocy shows "Barke Pilsner - Weyermann" costs £3.75/kg

### Step 1: Check Current Price
```
get_grain("Pilsner (2 Row) Ger")
```

**Result:**
```markdown
# Pilsner (2 Row) Ger

**Origin:** Germany
**Supplier:** Weyermann
**Type:** Base Malt

## Pricing & Inventory
- **Price ($/lb):** $0.08
- **Price ($/kg):** $0.18
- **Price ($/oz):** $0.0050
- **Inventory:** 0.00 lb

## Characteristics
- **Color:** 1.8°L
- **Yield:** 82%
```

### Step 2: Convert Your Price (Simple!)
```
convert_ingredient_price(3.75, "grain")
```

**Result:**
```markdown
# Price Conversion for Grain

**Input:** GBP3.75/kg

✓ No currency conversion needed (GBP=GBP)

## Step 2: Unit Conversion
- GBP3.75/kg ÷ 35.2740 = GBP0.1063/oz
- Conversion: 1 kg = 35.2740 oz

## Result
**BeerSmith Price:** GBP0.1063/oz

✅ Ready to use:
```json
{"price": 0.1063}
```

Update command:
```
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 0.1063}')
```

### Step 3: Update BeerSmith
```
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 0.1063}')
```

**Result:**
```
✅ Successfully updated Pilsner (2 Row) Ger

Updated fields: price

A backup was created before making changes.
```

### Step 4: Verify
```
get_grain("Pilsner (2 Row) Ger")
```

**Result:**
```markdown
## Pricing & Inventory
- **Price ($/oz):** $0.1063 ← BeerSmith storage format
- **Price ($/lb):** $1.70
- **Price ($/kg):** $3.75  ✓ Correct!
- **Inventory:** 0.00 oz
```

## Example 2: Hop Price with Currency Conversion

**Scenario**: European supplier lists "Cascade Hops" at €25.00/kg

### Step 1: Convert with Explicit Currency
```
convert_ingredient_price(25.0, "hop", "kg", "EUR", "GBP")
```

**Result:**
```markdown
# Price Conversion for Hop

**Input:** EUR25.00/kg

## Step 1: Currency Conversion
- EUR25.00 × 0.8600 = GBP21.50
- Exchange rate: 1 EUR = 0.8600 GBP

## Step 2: Unit Conversion
- GBP21.50/kg ÷ 35.2740 = GBP0.6095/oz
- Conversion: 1 kg = 35.2740 oz

## Result
**BeerSmith Price:** GBP0.6095/oz

✅ Ready to use:
```json
{"price": 0.6095}
```

Update command:
```
update_ingredient("hop", "Cascade", '{"price": 0.6095}')
```

### Step 2: Update
```
update_ingredient("hop", "Cascade", '{"price": 0.6095}')
```

## Example 3: Bulk Update Multiple Ingredients

```python
# List of ingredients from Grocy (all in £/kg)
ingredients = [
    {"name": "Pilsner (2 Row) Ger", "type": "grain", "price_kg": 3.75},
    {"name": "Crystal 60", "type": "grain", "price_kg": 4.20},
    {"name": "Munich Malt", "type": "grain", "price_kg": 3.85},
    {"name": "Cascade", "type": "hop", "price_kg": 20.00},
    {"name": "Centennial", "type": "hop", "price_kg": 22.50},
]

# For each ingredient:
# 1. convert_ingredient_price(price, type)
# 2. Get the converted value
# 3. update_ingredient(type, name, {"price": converted})
```

## Key Points

✅ **Metric is Default**: Just use `convert_ingredient_price(3.75, "grain")` - no need to specify "kg"

✅ **Currency Handled**: Configure once in `currency_config.json`, forget about it

✅ **No Mental Math**: Tool shows every conversion step clearly

✅ **Safe Updates**: Automatic backups before every change

✅ **Easy Verification**: Use `get_grain/get_hop/get_yeast` to check results

## Common Scenarios

### Imperial User (USA)?
Edit `currency_config.json`:
```json
{
  "user_currency": "USD",
  "user_default_unit": "lb",
  "beersmith_currency": "USD"
}
```

Then: `convert_ingredient_price(1.50, "grain")` - defaults to lb, no conversion needed!

### Different Display Currency?
If BeerSmith displays in USD but you work in GBP:
```json
{
  "user_currency": "GBP",
  "user_default_unit": "kg",
  "beersmith_currency": "USD"
}
```

The tool will convert: GBP → USD → lb automatically!

## Troubleshooting

**Problem**: "Exchange rate not found"  
**Solution**: Add the rate to `currency_config.json`:
```json
"CAD_to_GBP": 0.58,
"GBP_to_CAD": 1.72
```

**Problem**: Price looks wrong in BeerSmith  
**Solution**: 
1. Check your BeerSmith display units (File → Options → Display)
2. Run `get_grain("name")` to see all unit conversions
3. Verify currency_config matches your setup
