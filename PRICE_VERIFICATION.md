# Price Storage Format Verification

## Test Case: Pilsner (2 Row) Ger

### Current State in BeerSmith XML
```xml
<F_G_PRICE>0.0800000</F_G_PRICE>
<F_G_NAME>Pilsner (2 Row) Ger</F_G_NAME>
```

### If BeerSmith stores in $/oz (our hypothesis):
- Stored: $0.08/oz
- Display in $/lb: $0.08 × 16 = $1.28/lb
- Display in $/kg: $0.08 × 35.274 = $2.82/kg

### User's Bug Report:
- Set price to 1.70 → BeerSmith showed 60.00 (35.29x)
- Set price to 3.75 → BeerSmith showed 132.28 (35.27x)

### Analysis:
The 35x multiplier matches oz→kg conversion exactly.

**Conclusion**: BeerSmith stores prices in $/oz for ALL ingredients.

### Correct Conversion:
To set £3.75/kg:
1. Convert: £3.75/kg ÷ 35.274 = £0.1063/oz
2. Store: 0.1063 in F_G_PRICE
3. BeerSmith displays: £0.1063 × 35.274 = £3.75/kg ✓

### Previous Error:
We were converting: £3.75/kg ÷ 2.20462 = £1.70/lb
Then storing: 1.70
BeerSmith interpreted as: £1.70/oz
Displayed as: £1.70 × 35.274 = £60.00/kg ❌

This matches the user's bug report exactly!
