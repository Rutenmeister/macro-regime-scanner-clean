# Macro Regime Scanner v0.24M — Deep Source Extraction Manifest

This is the blueprint layer. It does not change workflows or scoring. It defines the deeper variable universe that each public-source lane should eventually extract before the scoring engine is rebuilt.

## Non-negotiable rules
- Feeds first, but not shallow feeds: every source lane must define the full target variable set before scripts are expanded.
- No variable becomes score-eligible until it has source provenance, freshness, asset relevance, and directional interpretation rules.
- Source extraction, asset mapping, and scoring are separate layers.
- If a variable is contextual only, it remains visible but should not dominate scoring.
- No market-price or copyrighted vendor market data is included in this manifest.

## Current and planned sources

### U.S. Treasury Fiscal Data / Daily Treasury Par Yield Curve Rates (`us_treasury_fiscal_data`)
- Status: **implemented_v024**
- Access: Public API, no key expected for current lane
- Official URL: https://fiscaldata.treasury.gov/api-documentation/
- Primary use: Rates pressure, curve shape, yield-asset direct readings, cross-asset discount-rate pressure.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| 1M Treasury yield (`treasury_1m`) | daily business day | daily_change, weekly_change | front-end rate pressure; cash/short-rate context | live_scored_candidate |
| 3M Treasury yield (`treasury_3m`) | daily business day | daily_change, weekly_change, 10y_minus_3m | curve inversion/growth pressure context | live_scored_candidate |
| 6M Treasury yield (`treasury_6m`) | daily business day | daily_change, weekly_change | front-end policy pressure | live_context |
| 1Y Treasury yield (`treasury_1y`) | daily business day | daily_change, weekly_change | front-end policy pressure | live_context |
| 2Y Treasury yield (`treasury_2y`) | daily business day | daily_change, weekly_change, 10y_minus_2y, 5y_minus_2y | Fed-sensitive rate pressure; direct for 2Y yield asset; pressure for rate-sensitive risk assets | live_scored_candidate |
| 3Y Treasury yield (`treasury_3y`) | daily business day | daily_change, weekly_change | intermediate curve context | live_context |
| 5Y Treasury yield (`treasury_5y`) | daily business day | daily_change, weekly_change, 5y_minus_2y, 30y_minus_5y | intermediate rates/real-economy discount pressure | live_scored_candidate |
| 7Y Treasury yield (`treasury_7y`) | daily business day | daily_change, weekly_change | curve context | live_context |
| 10Y Treasury yield (`treasury_10y`) | daily business day | daily_change, weekly_change, 10y_minus_2y, 10y_minus_3m | core discount-rate pressure; direct for 10Y yield; pressure for equities/gold when rising unless offset by inflation/real-yield context | live_scored_candidate |
| 20Y Treasury yield (`treasury_20y`) | daily business day | daily_change, weekly_change | long-end duration context | live_context |
| 30Y Treasury yield (`treasury_30y`) | daily business day | daily_change, weekly_change, 30y_minus_5y | long-end duration/growth/inflation pressure | live_scored_candidate |

Direction rules:
- Higher yield is support for the yield asset itself.
- Higher U.S. yields usually pressure rate-sensitive equities and gold/silver through discount-rate and real-yield channels.
- Higher U.S. yields can support USD when relative-rate advantage matters.
- Curve inversion/steepening should be interpreted separately from level changes.

### CFTC Commitments of Traders (`cftc_cot`)
- Status: **implemented_v024**
- Access: Public files/API-style downloads, no key expected
- Official URL: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
- Primary use: Positioning participation, crowding, commercial/spec conflict, futures-market sentiment context.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Managed money / leveraged fund longs (`cot_spec_longs`) | weekly | weekly_change, share_of_open_interest | spec participation | live_scored_candidate |
| Managed money / leveraged fund shorts (`cot_spec_shorts`) | weekly | weekly_change, share_of_open_interest | spec pressure participation | live_scored_candidate |
| Spec net position (`cot_spec_net`) | weekly | net_as_pct_open_interest, weekly_change, historical_percentile_later | directional participation; not automatically contrarian | live_scored_candidate |
| Commercial / producer / dealer net position (`cot_commercial_net`) | weekly | net_as_pct_open_interest, weekly_change, historical_percentile_later | hedging/value/extreme context; not automatic direction | live_context |
| Open interest (`cot_open_interest`) | weekly | weekly_change | quality of positioning change | live_context |
| Spec-commercial spread/conflict (`cot_spec_commercial_spread`) | weekly | spread, historical_percentile_later | crowding/conflict warning | live_scored_candidate |
| Positioning crowding percentile (`cot_crowding_percentile`) | weekly | 3y_percentile, 5y_percentile | unwind/squeeze risk; requires historical COT expansion | future |

Direction rules:
- Spec net long and increasing = trend participation support, not a guaranteed bullish signal.
- Spec extreme long = support plus crowded-long risk.
- Spec extreme short = pressure plus short-covering risk.
- Commercial extremes are contextual/contrarian warnings, especially at historical extremes.
- Treasury futures signs must be inverted for Treasury yield assets. FX mappings need base/quote direction handling.

### U.S. Energy Information Administration API (`eia_energy`)
- Status: **implemented_v024**
- Access: Public API, EIA_API_KEY required for current implementation
- Official URL: https://www.eia.gov/opendata/documentation.php
- Primary use: Energy supply/demand, inventory, production, refinery, storage, and inflation-cost pressure.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Commercial crude oil inventories (`eia_crude_stocks`) | weekly | weekly_change, year_ago_change, 5y_range_later | direct for WTI/Brent; inventory draw supports oil, build pressures oil | live_scored_candidate |
| Cushing crude inventories (`eia_cushing_stocks`) | weekly | weekly_change, year_ago_change | WTI delivery hub tightness/looseness | live_scored_candidate |
| Gasoline inventories (`eia_gasoline_stocks`) | weekly | weekly_change, year_ago_change | gasoline balance and demand/inflation context | live_scored_candidate |
| Distillate inventories (`eia_distillate_stocks`) | weekly | weekly_change, year_ago_change | diesel/heating oil tightness and industrial demand context | live_scored_candidate |
| Refinery utilization (`eia_refinery_utilization`) | weekly | weekly_change | crude demand from refiners and product supply pressure | planned_deepening |
| U.S. crude production (`eia_crude_production`) | weekly | weekly_change, year_ago_change | supply pressure for oil | planned_deepening |
| Crude imports (`eia_crude_imports`) | weekly | weekly_change | balance/context, not usually primary alone | live_context |
| Crude exports (`eia_crude_exports`) | weekly | weekly_change | export demand / domestic balance | live_context |
| Gasoline product supplied (`eia_product_supplied_gasoline`) | weekly | weekly_change, 4w_avg_later | demand proxy | planned_deepening |
| Distillate product supplied (`eia_product_supplied_distillate`) | weekly | weekly_change, 4w_avg_later | industrial/freight demand proxy | planned_deepening |
| Natural gas working storage (`eia_natural_gas_storage`) | weekly | weekly_change, surplus_deficit_vs_year_ago, surplus_deficit_vs_5y_later | direct for natural gas; surplus pressures gas, deficit supports gas | live_scored_candidate |

Direction rules:
- Inventory draw = supportive for related energy price pressure; build = pressure.
- Production growth is supply pressure for oil/gas unless demand absorbs it.
- Product supplied improves demand interpretation but should be smoothed to avoid noise.
- Energy variables are direct for energy assets and contextual for inflation/risk/commodity baskets.

### USDA/NASS Quick Stats (`usda_nass_quickstats`)
- Status: **implemented_v024**
- Access: Public API, USDA_API_KEY required for current implementation
- Official URL: https://www.nass.usda.gov/developer/index.php
- Primary use: Crop supply, condition, progress, acreage, production, yield, and agriculture balance context.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Crop condition good/excellent (`usda_crop_condition_good_excellent`) | weekly/seasonal | weekly_change, year_ago_compare | worse condition supports crop price pressure; better condition eases supply risk | live_scored_candidate |
| Planting progress (`usda_crop_progress_planting`) | weekly/seasonal | vs_5y_avg_later, year_ago_compare | delays can support risk premium; smooth progress eases risk | live_context |
| Harvest progress (`usda_crop_progress_harvest`) | weekly/seasonal | vs_5y_avg_later, year_ago_compare | delays can support risk premium; smooth harvest eases risk | live_context |
| Production estimate (`usda_production_estimate`) | monthly/seasonal | revision, year_ago_compare | lower production supports crop price pressure; higher production pressures | live_scored_candidate |
| Yield estimate (`usda_yield_estimate`) | monthly/seasonal | revision, year_ago_compare | lower yield supports crop price pressure; higher yield pressures | planned_deepening |
| Planted/harvested acreage (`usda_acres_planted_harvested`) | seasonal | revision, year_ago_compare | acreage expansion/decline supply context | planned_deepening |
| Ending stocks / carryout (`usda_ending_stocks`) | monthly WASDE, if sourceable | revision, year_ago_compare | tighter carryout supports crop price pressure; looser carryout pressures | future |
| Stock/use ratio (`usda_stock_use_ratio`) | monthly WASDE, if sourceable/calculable | revision, percentile_later | core tightness metric for grains/softs | future |
| Export sales/commitments (`usda_export_sales`) | weekly, separate USDA/FAS source likely | weekly_change, vs_expected_later | demand pressure for crops | research_required |

Direction rules:
- Tighter supply or worsening condition = supportive crop price pressure.
- Larger supply, higher yield, or better condition = crop price pressure relief.
- Progress data is seasonal/contextual unless significantly delayed or ahead of normal.
- WASDE/stock-use data should become primary when implemented, but may require a separate source parser.

### Bureau of Labor Statistics Public Data API (`bls_public_data`)
- Status: **implemented_v024**
- Access: Public API, no key required at current small request size
- Official URL: https://www.bls.gov/developers/
- Primary use: Inflation, labor strength, wage pressure, Fed/rates pressure, growth/recession pressure.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Headline CPI (`bls_cpi_headline`) | monthly | mom_change, yoy_change, acceleration | inflation/rate pressure; usually pressure for risk assets if hot | live_scored_candidate |
| Core CPI (`bls_cpi_core`) | monthly | mom_change, yoy_change, acceleration | persistent inflation/Fed pressure | live_scored_candidate |
| CPI shelter (`bls_cpi_shelter`) | monthly | mom_change, yoy_change | inflation persistence context | planned_deepening |
| CPI energy (`bls_cpi_energy`) | monthly | mom_change, yoy_change | energy inflation channel and consumer pressure | planned_deepening |
| CPI food (`bls_cpi_food`) | monthly | mom_change, yoy_change | food inflation/agriculture context | planned_deepening |
| Headline PPI (`bls_ppi_headline`) | monthly | mom_change, yoy_change, acceleration | pipeline inflation / margin pressure | live_scored_candidate |
| Core PPI (`bls_ppi_core`) | monthly | mom_change, yoy_change | pipeline inflation persistence | planned_deepening |
| Unemployment rate (`bls_unemployment_rate`) | monthly | monthly_change, trend | labor slack/recession risk; weak labor can lower rate pressure but hurt risk appetite | live_scored_candidate |
| Nonfarm payroll growth (`bls_nonfarm_payrolls`) | monthly | monthly_change, 3m_avg_later | growth/labor strength; can support risk but pressure rates if too hot | live_scored_candidate |
| Average hourly earnings (`bls_average_hourly_earnings`) | monthly | mom_change, yoy_change | wage inflation pressure | live_scored_candidate |
| Labor force participation (`bls_labor_force_participation`) | monthly | monthly_change | labor supply context | planned_deepening |
| U-6 unemployment (`bls_u6_unemployment`) | monthly | monthly_change | broader labor slack | planned_deepening |

Direction rules:
- Hot inflation = rate pressure; generally negative for equities/bonds/gold if real yields rise, but commodity effects can be contextual.
- Strong labor = growth support and possible Fed tightness; asset interpretation must separate growth support from rate pressure.
- Weak labor = lower rate pressure but higher recession/risk pressure.

### Bureau of Economic Analysis API (`bea_macro`)
- Status: **planned_new_lane**
- Access: Public API; key may be required/recommended depending request path
- Official URL: https://apps.bea.gov/API/signup/
- Primary use: Growth, GDP components, PCE/core PCE, consumption, income, savings, corporate profits.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Real GDP growth (`bea_real_gdp_growth`) | quarterly | qoq_annualized, revision | growth regime; positive for cyclical risk unless inflation/rates dominate | future |
| Nominal GDP growth (`bea_nominal_gdp_growth`) | quarterly | qoq_annualized, revision | nominal demand context | future |
| PCE inflation (`bea_pce_inflation`) | monthly | mom_change, yoy_change | Fed preferred inflation broad pressure | future |
| Core PCE inflation (`bea_core_pce_inflation`) | monthly | mom_change, yoy_change | Fed preferred persistent inflation pressure | future |
| Personal consumption expenditures (`bea_personal_consumption`) | monthly/quarterly | monthly_change, real_vs_nominal_later | consumer demand/growth context | future |
| Personal income (`bea_personal_income`) | monthly | monthly_change | consumer income support context | future |
| Personal saving rate (`bea_savings_rate`) | monthly | level_change | consumer cushion/strain context | future |
| Corporate profits (`bea_corporate_profits`) | quarterly | qoq_change, yoy_change | equity earnings/margin macro context | future |

### Federal Reserve official data/releases (`federal_reserve_official`)
- Status: **planned_new_lane**
- Access: Public; endpoint varies by dataset
- Official URL: https://www.federalreserve.gov/data.htm
- Primary use: Policy stance, balance sheet/liquidity, reserves/reverse repo, rate-setting context.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Federal funds target range (`fed_funds_target_upper_lower`) | event-driven | change, stance | policy pressure, USD/rates context | future |
| Fed total assets (`fed_balance_sheet_assets`) | weekly | weekly_change, trend | liquidity context | future |
| Reserve balances (`fed_reserve_balances`) | weekly | weekly_change | liquidity/risk context | future |
| Reverse repo usage (`fed_reverse_repo`) | daily/weekly | change, trend | liquidity drain/release context | future |
| Discount window / liquidity facilities (`fed_discount_window`) | weekly | change, stress_flag | banking/liquidity stress context | future |

### U.S. Census economic indicators / API (`census_economic_indicators`)
- Status: **planned_new_lane**
- Access: Public API; key likely helpful or required depending endpoint
- Official URL: https://www.census.gov/data/developers.html
- Primary use: Retail sales, housing, trade, durable goods/orders/inventories, real-economy demand.

| Variable | Frequency | Target transformations | Asset use | Scoring eligibility |
|---|---|---|---|---|
| Retail sales (`census_retail_sales`) | monthly | mom_change, control_group_if_sourceable | consumer demand/risk/growth context | future |
| Housing starts (`census_housing_starts`) | monthly | mom_change, trend | housing/growth/rate sensitivity | future |
| Building permits (`census_building_permits`) | monthly | mom_change, trend | forward housing construction signal | future |
| New home sales (`census_new_home_sales`) | monthly | mom_change, inventory_months_supply | housing demand context | future |
| Durable goods orders (`census_durable_goods_orders`) | monthly | mom_change, core_capex_proxy_if_sourceable | business investment/cyclical demand | future |
| Goods/services trade balance (`census_trade_balance`) | monthly | change | USD/growth/export-import demand context | future |

## Required next config before scoring

Before rebuilding scoring, create `config/asset_variable_map.json` with one row per asset-variable relationship: direct, secondary, contextual, display-only, or not applicable. This prevents generic source values from being scored incorrectly across unrelated markets.
