# v0.41 Official Release Calendar Hardening

v0.41 is a narrow hardening pass for the Upcoming Tracked Reports module.

## Why it exists

The previous release calendar was useful but too rule-based. It could show estimated dates such as Retail Sales on May 20 or PCE on May 23 even when official calendars showed different dates. That created false confidence.

## New model

Every event now has `calendarConfidence`:

| Value | Meaning |
|---|---|
| `official` | Date is from an official/confirmed release schedule embedded in the generator. |
| `official-pattern` | Recurring event follows an official schedule pattern, such as EIA WPSR Wednesday 10:30 AM ET or Fed H.4.1 Thursday 4:30 PM ET. |
| `estimated` | Calendar reminder only. Official date has not been embedded/confirmed in the generator. |

## What the UI should communicate

The calendar should not imply all rows are equally reliable. Official rows are strongest, official-pattern rows are usually reliable but holiday-sensitive, and estimated rows are lower confidence.

## What scoring does with calendar events

Nothing. Release-calendar events do not directly affect asset scores. They are watchlist/context rows only.

## Next upgrade

The next improvement would be live parsing of official calendars from agency endpoints/pages where practical:

- BEA release schedule
- Census economic indicator calendar
- BLS release calendar
- EIA release schedule pages
- USDA/NASS report calendar
- CFTC COT release schedule
- Federal Reserve H.4.1 schedule

For now, v0.41 solves the immediate trust problem without overbuilding.
