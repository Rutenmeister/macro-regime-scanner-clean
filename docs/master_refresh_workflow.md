# Manual GitHub Workflow: Refresh All Public Sources

Because `.github` folders have not reliably uploaded through the GitHub web uploader, create or replace this workflow manually.

File name:

```text
.github/workflows/refresh-all-public-sources.yml
```

Paste this full file:

```yaml
name: Refresh All Public Sources

on:
  workflow_dispatch:
  schedule:
    - cron: "45 23 * * 5"

permissions:
  contents: write

concurrency:
  group: macro-regime-source-refresh
  cancel-in-progress: false

jobs:
  refresh-all:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Refresh all enabled public-source lanes
        env:
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
          USDA_API_KEY: ${{ secrets.USDA_API_KEY }}
          BEA_API_KEY: ${{ secrets.BEA_API_KEY }}
          CENSUS_API_KEY: ${{ secrets.CENSUS_API_KEY }}
        run: python scripts/refresh_all_sources.py

      - name: Commit refreshed public-source data
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Refresh all public-source lanes"
          file_pattern: data/ config/
```

Required current secrets:

- `EIA_API_KEY`
- `USDA_API_KEY`

Optional/future secrets:

- `BEA_API_KEY`
- `CENSUS_API_KEY`

Do not add contract hardener, audit scripts, or scoring experiments to this workflow.
