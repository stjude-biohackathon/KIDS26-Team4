# Sequencing Metrics Import Pipeline

## Prerequisites

All importers require a reachable PostgreSQL database and these environment variables:

```text
PSQL_DB_HOST
PSQL_DB_NAME
PSQL_DB_USERNAME
PSQL_DB_PASS
```

`parseRunLevelMetrics.py` and `parseSeqRuns.py` use `PGPORT` when present and otherwise default to `5432`. The TapeStation importer relies on the PostgreSQL client default port unless the connection environment supplies one.

The destination schema must exist before an import. Each conflict key named below must be backed by a unique constraint or unique index so that the scripts' `ON CONFLICT` clauses can run.

## NovaSeq X Plus Run Metrics

`parseTools/parseRunLevelMetrics.py` reads the configured Excel workbook with pandas. The workbook must provide these source columns:

| Source column | Destination column |
| --- | --- |
| `Run` | `run_name` |
| `SoftwareVersion` | `software_version` |
| `Occupancy` | `occupancy` |
| `Q30` | `q30` |
| `PF` | `pf` |
| `Flowcell` | `flowcell` |

Records are inserted into `novaseq_x_run_metrics` and upserted on `run_name`.

## BCL-Convert Reports

`parseTools/parseSeqRuns.py` searches the configured root for:

```text
*/<run>/*Unaligned*/Reports/Demultiplex_Stats.csv
*/<run>/*Unaligned*/Reports/Quality_Metrics.csv
```

The script determines `run_name` from the directory that contains the `Unaligned` directory. It accepts UTF-8 CSV files with a byte-order mark.

### Demultiplex statistics

`Demultiplex_Stats.csv` is loaded into `bcl_demultiplex_stats`. Required source values are `Sample_Name` in the form `<numeric-id>_<suffix>` and `Index`. The script also reads lane, project, count, and percentage fields when present. Its conflict key is:

```text
(run_name, lane, sample_id, index_sequence)
```

### Quality metrics

`Quality_Metrics.csv` is loaded into `bcl_quality_metrics`. Required source values are `Sample_Name` in the form `<numeric-id>_<suffix>`, `index`, and `ReadNumber`. The script reads lane, project, yield, quality-score, and percentage fields when present. Its conflict key is:

```text
(run_name, lane, sample_id, index1, read_number)
```

Blank numeric fields become `NULL`. Rows that do not satisfy the required identifier fields are skipped.

## TapeStation XML

`parseTools/parseTapeStation.py` recursively reads every `*.xml` file below its configured root and inserts sample records into `tapestation_samples`.

The importer reads run-level metadata from `FileInformation`, tape metadata from `ScreenTapes`, and sample metadata from `Samples`. It ignores an `Electronic Ladder` sample and samples whose observation is `Ladder`. If `Comment` begins with `<numeric-id>_`, that prefix is saved as `srm_sample_id`.

The importer records source-file provenance and upserts on:

```text
(source_file, well_number, sample_name)
```

## Safe Operation

1. Use only approved, access-controlled data locations.
2. Run a small import against a non-production database first.
3. Confirm the unique constraints match the conflict keys above.
4. Review the terminal output for skipped rows and file-level errors.
5. Reconcile imported counts with the source files before using the data downstream.

No source data, connection strings, passwords, or database dumps belong in this repository.
