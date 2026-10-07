# NGS Run Planner and Sequencing Metrics Import Tools

The Hartwell Center's production NGS run planner uses historical sequencing outcomes to recommend adjusted sample loading amounts that help each sample reach its target read count in the first sequencing run. The application uses a PostgreSQL backend and an R Shiny frontend deployed on the Hartwell Center's R Shiny server.

This repository documents the ParseTools ingestion utilities that import the run, demultiplexing, quality, and TapeStation metrics supporting that historical database. It does not include sequencing output, source data, or the deployed R Shiny application.

## Project Profile

- **Problem:** Sequencing quality-control metrics are distributed across instrument exports, making it difficult to use prior run outcomes when planning sample loading.
- **Goal:** Support an NGS run planner that predicts adjusted sample loading amounts needed to reach each sample's desired read count in its first sequencing run.
- **Inputs:** Historical NovaSeq X Plus run-metrics workbooks, BCL-Convert report CSVs, and TapeStation XML exports.
- **Output:** PostgreSQL records with source-file provenance that support the planner's historical analysis and loading recommendations.
- **Stack:** Python 3, pandas, psycopg, PostgreSQL, and R Shiny.
- **Deployment:** The NGS run planner is live on the Hartwell Center's R Shiny server and is in production use.
- **Data handling:** Do not commit source data, database credentials, or clinical/identifiable information.

## Application and Import Utilities

The run planner queries the PostgreSQL database to incorporate previous sequencing performance into its loading recommendations. The R Shiny frontend provides the operational interface; the ParseTools below load the historical metrics that underpin the planner. The R Shiny application is deployed separately and is not included in this repository.

| Script | Input | Destination tables | Notes |
| --- | --- | --- | --- |
| `parseTools/parseRunLevelMetrics.py` | NovaSeq X Plus Excel workbook | `novaseq_x_run_metrics` | Imports one row per run and upserts by `run_name`. |
| `parseTools/parseSeqRuns.py` | BCL-Convert `Demultiplex_Stats.csv` and `Quality_Metrics.csv` reports | `bcl_demultiplex_stats`, `bcl_quality_metrics` | Recursively finds report files beneath the configured root and continues after individual-file errors. |
| `parseTools/parseTapeStation.py` | TapeStation XML files | `tapestation_samples` | Skips electronic ladders and derives an SRM sample ID from names beginning with `<numeric-id>_`. |

See [the import guide](docs/import-pipeline.md) for expected file layouts, field mapping, and database constraints.

## Setup

Use Python 3.10 or later and a PostgreSQL database whose schema meets the requirements in the import guide.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Set the database values in `.env`, then export them before running an importer:

```bash
set -a
source .env
set +a
```

The scripts read these variables:

```text
PSQL_DB_HOST
PSQL_DB_NAME
PSQL_DB_USERNAME
PSQL_DB_PASS
PGPORT                 # Optional; defaults to 5432 where supported
```

`parseRunLevelMetrics.py`, `parseSeqRuns.py`, and `parseTapeStation.py` each contain an input path constant. Set that constant to an approved local data location before running the corresponding script. Keep input data outside the repository.

## Running an Import

After configuring the relevant source path and exporting the database environment variables, run one script at a time:

```bash
python parseTools/parseRunLevelMetrics.py
python parseTools/parseSeqRuns.py
python parseTools/parseTapeStation.py
```

All importers use PostgreSQL upserts, so rerunning an unchanged source updates its matching records rather than creating duplicate records. Review script output for per-file errors before considering an import complete.

## Validation and Operational Notes

- Check that the expected source files are found before importing; each script prints discovery or progress information.
- Test against a non-production database or a small, approved input subset first.
- Back up the target database before a historical import.
- The scripts intentionally skip rows lacking the identifier fields required for their destination-table conflict keys.
- Database table creation and migrations are outside the scope of this repository; create and review the schema before loading data.

## Repository Layout

```text
parseTools/                  Import scripts
docs/import-pipeline.md      Input, mapping, and schema reference
project-management/          Project scope and ownership planning
requirements.txt             Python dependencies
.env.example                 Non-secret environment-variable template
```

## Limitations and Next Steps

The current scripts require source paths to be configured in code and assume the listed destination tables already exist. Future work should add command-line path options, schema migrations, automated parser tests with de-identified fixtures, structured import logging, and ongoing evaluation of planner recommendations against observed sequencing outcomes.
