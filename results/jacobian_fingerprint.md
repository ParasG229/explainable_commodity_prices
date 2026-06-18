# E3: Decoder-Jacobian commodity fingerprint

Mean decoder loadings aligned to the E0 reference identity. Sector mass = share of absolute loading per sector.

## Sector mass per factor (share of total |loading|)

|                |    f1 |    f2 |    f3 |    f4 |    f5 |
|:---------------|------:|------:|------:|------:|------:|
| Agriculture    | 0.336 | 0.322 | 0.469 | 0.329 | 0.378 |
| BaseMetals     | 0.116 | 0.109 | 0.182 | 0.294 | 0.129 |
| Energy         | 0.378 | 0.307 | 0.14  | 0.312 | 0.416 |
| PreciousMetals | 0.169 | 0.262 | 0.209 | 0.064 | 0.078 |

## Sector intensity per factor (mean |loading| per commodity)

|                |    f1 |    f2 |    f3 |    f4 |    f5 |
|:---------------|------:|------:|------:|------:|------:|
| Agriculture    | 0.275 | 0.233 | 0.364 | 0.277 | 0.275 |
| BaseMetals     | 0.122 | 0.102 | 0.182 | 0.319 | 0.121 |
| Energy         | 0.347 | 0.251 | 0.122 | 0.295 | 0.341 |
| PreciousMetals | 0.415 | 0.57  | 0.486 | 0.162 | 0.17  |

## Factor f1
- Dominant sector: **PreciousMetals** (top-2 concentration 0.15)
- Macro hypothesis: real rates (TIPS), USD, risk-off (VIX)
- Top loadings:
| commodity   |   loading | sector         |
|:------------|----------:|:---------------|
| HRWWheat    |  0.593799 | Agriculture    |
| HeatingOil  |  0.538738 | Energy         |
| Corn        |  0.521384 | Agriculture    |
| Brent       |  0.509632 | Energy         |
| Silver      | -0.473665 | PreciousMetals |

## Factor f2
- Dominant sector: **PreciousMetals** (top-2 concentration 0.18)
- Macro hypothesis: real rates (TIPS), USD, risk-off (VIX)
- Top loadings:
| commodity   |   loading | sector         |
|:------------|----------:|:---------------|
| Silver      |  0.604644 | PreciousMetals |
| Gold        |  0.59174  | PreciousMetals |
| Soybeans    | -0.545665 | Agriculture    |
| Corn        | -0.528631 | Agriculture    |
| Platinum    |  0.512659 | PreciousMetals |

## Factor f3
- Dominant sector: **PreciousMetals** (top-2 concentration 0.17)
- Macro hypothesis: real rates (TIPS), USD, risk-off (VIX)
- Top loadings:
| commodity   |   loading | sector         |
|:------------|----------:|:---------------|
| Soybeans    |  0.585249 | Agriculture    |
| Silver      |  0.581076 | PreciousMetals |
| Gold        |  0.501049 | PreciousMetals |
| Corn        |  0.500642 | Agriculture    |
| SoybeanOil  |  0.489437 | Agriculture    |

## Factor f4
- Dominant sector: **BaseMetals** (top-2 concentration 0.13)
- Macro hypothesis: global industrial production, USD, real rates
- Top loadings:
| commodity   |   loading | sector      |
|:------------|----------:|:------------|
| Zinc        | -0.505978 | BaseMetals  |
| Copper      | -0.478742 | BaseMetals  |
| HRWWheat    | -0.473159 | Agriculture |
| Gasoline    | -0.467027 | Energy      |
| Aluminium   | -0.46243  | BaseMetals  |

## Factor f5
- Dominant sector: **Energy** (top-2 concentration 0.16)
- Macro hypothesis: Kilian (2009) aggregate-demand & oil-specific supply shocks
- Top loadings:
| commodity   |   loading | sector      |
|:------------|----------:|:------------|
| SoybeanOil  | -0.586782 | Agriculture |
| Soybeans    | -0.476081 | Agriculture |
| Diesel      | -0.456786 | Energy      |
| LeanHogs    | -0.444221 | Agriculture |
| WTI         | -0.415439 | Energy      |
