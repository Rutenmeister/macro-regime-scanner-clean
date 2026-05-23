# NOAA/NWS Weather Hazard Lane

Version: v0.31

This lane adds public NOAA/National Weather Service active-alert context to Macro Regime Scanner. It uses the official `api.weather.gov` active alerts endpoint and requires no API key.

## Variables

- NOAA/NWS active weather alerts
- Heat stress alerts
- Cold / freeze alerts
- Winter storm alerts
- Flood alerts
- Severe storm / tornado alerts
- Tropical storm / hurricane alerts
- Fire weather alerts
- Sparse drought alert wording

## Interpretation boundary

This lane is a live weather-hazard context lane. It is not a complete drought monitor, crop-weather model, seasonal forecast, hurricane forecast, or global weather feed.

For energy and agriculture, elevated weather hazards can be supportive for price pressure through demand/supply disruption. For equities, FX, rates, and precious metals, the lane is mostly contextual and should not dominate macro scoring.

## Source

NOAA / National Weather Service public API: `https://api.weather.gov/alerts/active`
