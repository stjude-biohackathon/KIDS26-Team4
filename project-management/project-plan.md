# Project Plan

## Goal

Support the Hartwell Center's production NGS run planner, which uses historical sequencing outcomes to recommend adjusted sample loading amounts that help samples reach their desired read counts in the first run. This repository provides the documented, repeatable process for importing the planner's sequencing quality-control inputs into PostgreSQL.

## Tools

- Python 3
- pandas for Excel ingestion
- psycopg for PostgreSQL connections and bulk upserts
- PostgreSQL
- R Shiny frontend deployed on the Hartwell Center's R Shiny server
- Illumina NovaSeq X Plus, BCL-Convert, and TapeStation export files

## First Tasks

- [ ] Provision or identify a non-production PostgreSQL database with the required destination tables and unique constraints. - Database owner
- [ ] Configure approved local source paths for each importer and validate file discovery on a small de-identified subset. - Data steward
- [ ] Run each importer against the test database and reconcile row counts with the input exports. - Pipeline developer
- [ ] Record final schema decisions, source provenance, and known data-quality limitations. - Documentation owner

## Milestones

- **Day 1:** Confirm the source formats, destination schema, credentials process, and data-access boundaries.
- **Day 2:** Run and validate the three historical import paths against a non-production database, then verify that the loaded metrics are available to the planner's database backend.
- **Day 3:** Document validated commands, reconciliation results, limitations, and the production handoff for the deployed R Shiny planner.

## Definition of Done

The project is complete when each approved input type can be imported into a non-production database, source-to-destination row counts have been reviewed, and another team member can reproduce the data-ingestion process using the README and import guide without access to private source data. The deployed R Shiny planner should use the resulting historical data to provide loading recommendations for production operations.

Next steps include command-line configuration, database migrations, de-identified parser fixtures, automated tests, and operational monitoring.

## Risks and Questions

- Source exports may vary by instrument or BCL-Convert version; validate headers and XML structure before each new data source.
- Upsert conflict keys require corresponding database constraints; confirm them before loading data.
- Sample names that do not begin with a numeric ID followed by `_` are intentionally skipped by the BCL-Convert and TapeStation parsers.
- Historical source locations and database credentials must remain outside version control and follow the relevant data-governance process.
