# E3: Decoder-Jacobian commodity fingerprint

Mean decoder loadings aligned to the E0 reference identity. Sector mass = share of absolute loading per sector.

## Sector mass per factor (share of total |loading|)

|                |    f1 |    f2 |    f3 |    f4 |    f5 |
|:---------------|------:|------:|------:|------:|------:|
| Agriculture    | 0.349 | 0.445 | 0.242 | 0.445 | 0.671 |
| BaseMetals     | 0.234 | 0.104 | 0.137 | 0.392 | 0.171 |
| Energy         | 0.314 | 0.302 | 0.436 | 0.147 | 0.082 |
| PreciousMetals | 0.103 | 0.148 | 0.185 | 0.016 | 0.075 |

## Sector intensity per factor (mean |loading| per commodity)

|                |    f1 |    f2 |    f3 |    f4 |    f5 |
|:---------------|------:|------:|------:|------:|------:|
| Agriculture    | 0.168 | 0.208 | 0.131 | 0.201 | 0.332 |
| BaseMetals     | 0.31  | 0.134 | 0.204 | 0.486 | 0.233 |
| Energy         | 0.334 | 0.311 | 0.52  | 0.146 | 0.089 |
| PreciousMetals | 0.274 | 0.381 | 0.551 | 0.041 | 0.204 |

## Factor f1
- Dominant sector: **Energy** (top-2 concentration 0.17)
- Macro hypothesis: Kilian (2009) aggregate-demand & oil-specific supply shocks
- Top loadings:
| commodity   |   loading | sector     |
|:------------|----------:|:-----------|
| Gasoline    |  0.454257 | Energy     |
| Diesel      |  0.437916 | Energy     |
| Copper      |  0.411135 | BaseMetals |
| WTI         |  0.38809  | Energy     |
| Brent       |  0.371777 | Energy     |

## Factor f2
- Dominant sector: **PreciousMetals** (top-2 concentration 0.22)
- Macro hypothesis: real rates (TIPS), USD, risk-off (VIX)
- Top loadings:
| commodity   |   loading | sector         |
|:------------|----------:|:---------------|
| Wheat       |  0.567084 | Agriculture    |
| HRWWheat    |  0.549689 | Agriculture    |
| Gold        | -0.402693 | PreciousMetals |
| Silver      | -0.359278 | PreciousMetals |
| Brent       | -0.35619  | Energy         |

## Factor f3
- Dominant sector: **PreciousMetals** (top-2 concentration 0.22)
- Macro hypothesis: real rates (TIPS), USD, risk-off (VIX)
- Top loadings:
| commodity   |   loading | sector         |
|:------------|----------:|:---------------|
| Brent       | -0.681653 | Energy         |
| Gasoline    | -0.614571 | Energy         |
| WTI         | -0.613452 | Energy         |
| Gold        |  0.596295 | PreciousMetals |
| Diesel      | -0.549838 | Energy         |

## Factor f4
- Dominant sector: **BaseMetals** (top-2 concentration 0.21)
- Macro hypothesis: global industrial production, USD, real rates
- Top loadings:
| commodity   |   loading | sector      |
|:------------|----------:|:------------|
| Nickel      | -0.53919  | BaseMetals  |
| Copper      | -0.487582 | BaseMetals  |
| Zinc        | -0.480841 | BaseMetals  |
| Corn        |  0.471045 | Agriculture |
| Aluminium   | -0.436919 | BaseMetals  |

## Factor f5
- Dominant sector: **Agriculture** (top-2 concentration 0.22)
- Macro hypothesis: USD and supply/weather (typically weak macro link)
- Top loadings:
| commodity   |   loading | sector      |
|:------------|----------:|:------------|
| Wheat       | -0.6151   | Agriculture |
| HRWWheat    | -0.561077 | Agriculture |
| Corn        | -0.536359 | Agriculture |
| Soybeans    | -0.497943 | Agriculture |
| SoybeanMeal | -0.360171 | Agriculture |
