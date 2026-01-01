# BeerSmith Price Conversion Guide

## Understanding BeerSmith Price Storage

BeerSmith 3 stores ingredient prices internally in **US customary units**:

| Ingredient Type | Storage Unit | Example |
|-----------------|--------------|---------|
| **Grains** | $/lb (dollars per pound) | 0.08 = $0.08/lb |
| **Hops** | $/oz (dollars per ounce) | 1.25 = $1.25/oz |
| **Yeast** | $ per package | 5.99 = $5.99/pkg |
| **Misc** | $ per unit | 0.50 = $0.50/unit |

When you view ingredients in BeerSmith with metric units enabled, it converts these internally stored values to your display preferences (e.g., £/kg). However, when **updating** prices via the MCP server, you must provide them in BeerSmith's internal format.

## Common Conversion Scenarios

### Scenario 1: Grocy Grain Price (£/kg) → BeerSmith ($/lb)

**Problem**: Grocy shows "Barke Pilsner - Weyermann" costs £3.75/kg

**Solution**:
```
1. Use convert_ingredient_price tool:
   convert_ingredient_price(3.75, "kg", "lb", "grain")
   
2. Result: £3.75/kg ÷ 2.20462 = £1.70/lb
   
3. Update BeerSmith:
   update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 1.70}')
```

**Verification**: Use `get_grain("Pilsner (2 Row) Ger")` to verify the price was set correctly.

### Scenario 2: Grocy Hop Price (£/kg) → BeerSmith ($/oz)

**Problem**: Grocy shows "Cascade Hops" costs £20.00/kg

**Solution**:
```
1. Use convert_ingredient_price tool:
   convert_ingredient_price(20.00, "kg", "oz", "hop")
   
2. Result: £20.00/kg ÷ 35.274 = £0.57/oz
   
3. Update BeerSmith:
   update_ingredient("hop", "Cascade", '{"price": 0.57}')
```

### Scenario 3: Online Store Price ($/oz) → BeerSmith ($/oz)

**Problem**: You bought Centennial hops for $1.25/oz online

**Solution**:
```
No conversion needed! Already in BeerSmith's format.

update_ingredient("hop", "Centennial", '{"price": 1.25}')
```

## Quick Conversion Reference

### Grain Conversions (to $/lb)

| From | Formula | Example |
|------|---------|---------|
| £/kg | price ÷ 2.20462 | £3.75/kg → $1.70/lb |
| $/kg | price ÷ 2.20462 | $8.00/kg → $3.63/lb |
| £/lb | price × 1.0 | £1.70/lb → $1.70/lb |
| $/oz | price × 16 | $0.10/oz → $1.60/lb |

### Hop Conversions (to $/oz)

| From | Formula | Example |
|------|---------|---------|
| £/kg | price ÷ 35.274 | £20.00/kg → $0.57/oz |
| $/kg | price ÷ 35.274 | $44.00/kg → $1.25/oz |
| £/oz | price × 1.0 | £0.57/oz → $0.57/oz |
| $/lb | price ÷ 16 | $20.00/lb → $1.25/oz |
| $/100g | price ÷ 2.835 | $3.50/100g → $1.23/oz |

## Using the Tools

### Step 1: Check Current Price
```
get_grain("Pilsner (2 Row) Ger")
```
Returns current price in multiple units:
- Price ($/lb): $0.08
- Price ($/kg): $0.18
- Price ($/oz): $0.0050

### Step 2: Convert Your Price
```
convert_ingredient_price(3.75, "kg", "lb", "grain")
```
Returns:
- Original Price: $3.75/kg
- Converted Price: $1.70/lb
- Ready-to-use JSON: `{"price": 1.70}`

### Step 3: Update BeerSmith
```
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 1.70}')
```
Returns:
- ✅ Successfully updated Pilsner (2 Row) Ger
- Updated fields: price
- A backup was created before making changes

### Step 4: Verify
```
get_grain("Pilsner (2 Row) Ger")
```
Check that the price section shows the expected values.

## Bulk Updates with sync_prices_from_grocy

The `sync_prices_from_grocy` tool automatically handles conversions:

```json
{
  "products": [
    {
      "name": "Barke Pilsner - Weyermann",
      "price": 3.75,
      "price_unit": "kg",
      "product_group": "Grain"
    },
    {
      "name": "Cascade Hops 2024",
      "price": 20.00,
      "price_unit": "kg", 
      "product_group": "Hops"
    }
  ]
}
```

**Important**: Ensure `price_unit` is set correctly in your Grocy data. The sync tool uses this to determine the appropriate conversion.

## Common Mistakes

### ❌ Wrong: Setting metric price directly
```
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 3.75}')
```
Result: BeerSmith shows £132.28/kg (35x too high!)

### ✅ Correct: Convert first
```
convert_ingredient_price(3.75, "kg", "lb", "grain")
# Returns 1.70
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 1.70}')
```
Result: BeerSmith shows £3.75/kg ✓

## Debugging Price Issues

If prices appear incorrect in BeerSmith:

1. **Check the XML directly**:
   ```bash
   grep -A1 "F_G_NAME>Pilsner (2 Row) Ger" ~/Library/Application\ Support/BeerSmith3/Grain.bsmx | grep F_G_PRICE
   ```
   Should show: `<F_G_PRICE>1.7000000</F_G_PRICE>`

2. **Verify with get_grain**:
   ```
   get_grain("Pilsner (2 Row) Ger")
   ```
   Check all price formats match expectations

3. **Calculate expected display value**:
   - If you set price to 1.70 ($/lb)
   - BeerSmith displays in £/kg
   - Multiply: 1.70 × 2.20462 = £3.75/kg ✓

## Currency Handling

The price field stores a **numeric value only** - no currency symbol. BeerSmith applies your configured currency symbol when displaying. 

- If your BeerSmith is set to GBP (£), all prices display with £
- If set to USD ($), all prices display with $
- The conversion examples use $ in formulas but work for any currency

When updating from Grocy:
- Ignore currency symbols in calculations
- Focus on unit conversion (kg→lb, kg→oz)
- The numeric value is what matters

## Summary

✅ **Always convert to BeerSmith's internal units before updating**
✅ **Use `convert_ingredient_price` tool for accurate conversions**
✅ **Verify updates with `get_grain/get_hop/get_yeast` tools**
✅ **Grains in $/lb, Hops in $/oz, Yeast in $/pkg**

For questions or issues, check the CHANGELOG.md for recent fixes or open an issue on GitHub.
