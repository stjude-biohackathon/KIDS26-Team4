#!/usr/bin/env python3

from pathlib import Path
import csv
import re
import os
import psycopg

DEMUX_INSERT_SQL = """
INSERT INTO bcl_demultiplex_stats (
    run_name,
    lane,
    sample_id,
    sample_project,
    sample_name,
    index_sequence,

    reads,
    perfect_index_reads,
    one_mismatch_index_reads,
    two_mismatch_index_reads,

    pct_reads,
    pct_perfect_index_reads,
    pct_one_mismatch_index_reads,
    pct_two_mismatch_index_reads,

    source_file,
    source_path
)
VALUES (
    %(run_name)s,
    %(lane)s,
    %(sample_id)s,
    %(sample_project)s,
    %(sample_name)s,
    %(index_sequence)s,

    %(reads)s,
    %(perfect_index_reads)s,
    %(one_mismatch_index_reads)s,
    %(two_mismatch_index_reads)s,

    %(pct_reads)s,
    %(pct_perfect_index_reads)s,
    %(pct_one_mismatch_index_reads)s,
    %(pct_two_mismatch_index_reads)s,

    %(source_file)s,
    %(source_path)s
)

ON CONFLICT (
    run_name,
    lane,
    sample_id,
    index_sequence
)

DO UPDATE SET
    sample_project = EXCLUDED.sample_project,
    sample_name = EXCLUDED.sample_name,

    reads = EXCLUDED.reads,
    perfect_index_reads = EXCLUDED.perfect_index_reads,
    one_mismatch_index_reads = EXCLUDED.one_mismatch_index_reads,
    two_mismatch_index_reads = EXCLUDED.two_mismatch_index_reads,

    pct_reads = EXCLUDED.pct_reads,
    pct_perfect_index_reads = EXCLUDED.pct_perfect_index_reads,
    pct_one_mismatch_index_reads = EXCLUDED.pct_one_mismatch_index_reads,
    pct_two_mismatch_index_reads = EXCLUDED.pct_two_mismatch_index_reads,

    source_file = EXCLUDED.source_file,
    source_path = EXCLUDED.source_path;
"""

QUALITY_INSERT_SQL = """
INSERT INTO bcl_quality_metrics (
    run_name,
    lane,
    sample_id,
    sample_project,
    sample_name,

    index1,
    index2,
    read_number,

    yield_bases,
    yield_q30_bases,
    quality_score_sum,
    mean_quality_score_pf,
    pct_q30,

    source_file,
    source_path
)
VALUES (
    %(run_name)s,
    %(lane)s,
    %(sample_id)s,
    %(sample_project)s,
    %(sample_name)s,

    %(index1)s,
    %(index2)s,
    %(read_number)s,

    %(yield_bases)s,
    %(yield_q30_bases)s,
    %(quality_score_sum)s,
    %(mean_quality_score_pf)s,
    %(pct_q30)s,

    %(source_file)s,
    %(source_path)s
)

ON CONFLICT (
    run_name,
    lane,
    sample_id,
    index1,
    read_number
)

DO UPDATE SET
    sample_project = EXCLUDED.sample_project,
    sample_name = EXCLUDED.sample_name,
    index2 = EXCLUDED.index2,

    yield_bases = EXCLUDED.yield_bases,
    yield_q30_bases = EXCLUDED.yield_q30_bases,
    quality_score_sum = EXCLUDED.quality_score_sum,
    mean_quality_score_pf = EXCLUDED.mean_quality_score_pf,
    pct_q30 = EXCLUDED.pct_q30,

    source_file = EXCLUDED.source_file,
    source_path = EXCLUDED.source_path;
"""


# ------------------------------------------------------------
# CSV locations
# ------------------------------------------------------------

CSV_ROOT = Path("/insert/your/path/here")

csv_demux_files = list(
    CSV_ROOT.glob("*/*Unaligned*/Reports/*Demultiplex_Stats.csv")
)

csv_quality_files = list(
    CSV_ROOT.glob("*/*Unaligned*/Reports/*Quality_Metrics.csv")
)


# ------------------------------------------------------------
# PostgreSQL
# ------------------------------------------------------------

DB_HOST = os.environ['PSQL_DB_HOST']
DB_NAME = os.environ['PSQL_DB_NAME']
DB_USER = os.environ['PSQL_DB_USERNAME']
DB_PASSWORD = os.environ['PSQL_DB_PASS']

DB_PORT = int(os.environ.get("PGPORT", 5432))


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean(value):
    """Convert blank strings to None."""
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def as_int(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def as_float(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def get_run_name(filename):

    filename = Path(filename)

    for parent in filename.parents:

        if "Unaligned" in parent.name:
            return parent.parent.name


    try:
        return filename.parent.parent.parent.name

    except IndexError:
        return None

# ------------------------------------------------------------
# Parsers
# ------------------------------------------------------------

def parse_sample_id(sample_name):
    """
    Extract integer before the first underscore.

    Example:
        3480951_P25 -> 3480951
    """

    sample_name = clean(sample_name)

    if not sample_name:
        return None

    match = re.match(r"^(\d+)_", sample_name)

    if not match:
        return None

    return int(match.group(1))

def parse_demux_csv(filename):

    rows = []

    run_name = get_run_name(filename)

    with open(filename, newline="", encoding="utf-8-sig") as handle:

        reader = csv.DictReader(handle)

        for r in reader:

            sample_name = clean(r.get("Sample_Name"))

            sample_id = parse_sample_id(sample_name)

            index_sequence = clean(r.get("Index"))

            if sample_id is None or not index_sequence:
                continue

            rows.append({
                "run_name":
                    run_name,

                "lane":
                    as_int(r.get("Lane")),

                "sample_id":
                    sample_id,

                "sample_project":
                    clean(r.get("Sample_Project")),

                "sample_name":
                    sample_name,

                "index_sequence":
                    index_sequence,

                "reads":
                    as_int(r.get("# Reads")),

                "perfect_index_reads":
                    as_int(r.get("# Perfect Index Reads")),

                "one_mismatch_index_reads":
                    as_int(r.get("# One Mismatch Index Reads")),

                "two_mismatch_index_reads":
                    as_int(r.get("# Two Mismatch Index Reads")),

                "pct_reads":
                    as_float(r.get("% Reads")),

                "pct_perfect_index_reads":
                    as_float(r.get("% Perfect Index Reads")),

                "pct_one_mismatch_index_reads":
                    as_float(r.get("% One Mismatch Index Reads")),

                "pct_two_mismatch_index_reads":
                    as_float(r.get("% Two Mismatch Index Reads")),

                "source_file":
                    Path(filename).name,

                "source_path":
                    str(filename),
            })

    return rows

def parse_quality_csv(filename):

    rows = []

    run_name = get_run_name(filename)

    with open(filename, newline="", encoding="utf-8-sig") as handle:

        reader = csv.DictReader(handle)

        for r in reader:

            sample_name = clean(r.get("Sample_Name"))

            sample_id = parse_sample_id(sample_name)

            index1 = clean(r.get("index"))
            read_number = clean(r.get("ReadNumber"))

            if sample_id is None or not index1 or not read_number:
                continue

            rows.append({
                "run_name":
                    run_name,

                "lane":
                    as_int(r.get("Lane")),

                # DERIVED FROM Sample_Name
                "sample_id":
                    sample_id,

                "sample_project":
                    clean(r.get("Sample_Project")),

                "sample_name":
                    sample_name,

                "index1":
                    index1,

                "index2":
                    clean(r.get("index2")),

                "read_number":
                    read_number,

                "yield_bases":
                    as_int(r.get("Yield")),

                "yield_q30_bases":
                    as_int(r.get("YieldQ30")),

                "quality_score_sum":
                    as_int(r.get("QualityScoreSum")),

                "mean_quality_score_pf":
                    as_float(r.get("Mean Quality Score (PF)")),

                "pct_q30":
                    as_float(r.get("% Q30")),

                "source_file":
                    Path(filename).name,

                "source_path":
                    str(filename),
            })

    return rows

def main():

    print()
    print("BCL-Convert historical import")
    print("--------------------------------")
    print(f"Demultiplex files: {len(csv_demux_files):,}")
    print(f"Quality files:     {len(csv_quality_files):,}")
    print()

    total_demux_rows = 0
    total_quality_rows = 0

    demux_errors = 0
    quality_errors = 0

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    ) as conn:

        # -----------------------------------------------------
        # Demultiplex stats
        # -----------------------------------------------------

        print("Importing Demultiplex_Stats.csv files...")

        for i, filename in enumerate(csv_demux_files, start=1):

            try:

                rows = parse_demux_csv(filename)

                with conn.cursor() as cur:

                    cur.executemany(
                        DEMUX_INSERT_SQL,
                        rows
                    )

                conn.commit()

                total_demux_rows += len(rows)

                print(
                    f"[DEMUX {i:,}/{len(csv_demux_files):,}] "
                    f"{get_run_name(filename)} "
                    f"({len(rows):,} rows)"
                )

            except Exception as e:

                conn.rollback()

                demux_errors += 1

                print(
                    f"ERROR DEMUX: {filename}\n"
                    f"    {type(e).__name__}: {e}"
                )

        # -----------------------------------------------------
        # Quality metrics
        # -----------------------------------------------------

        print()
        print("Importing Quality_Metrics.csv files...")

        for i, filename in enumerate(csv_quality_files, start=1):

            try:

                rows = parse_quality_csv(filename)

                with conn.cursor() as cur:

                    cur.executemany(
                        QUALITY_INSERT_SQL,
                        rows
                    )

                conn.commit()

                total_quality_rows += len(rows)

                print(
                    f"[QUALITY {i:,}/{len(csv_quality_files):,}] "
                    f"{get_run_name(filename)} "
                    f"({len(rows):,} rows)"
                )

            except Exception as e:

                conn.rollback()

                quality_errors += 1

                print(
                    f"ERROR QUALITY: {filename}\n"
                    f"    {type(e).__name__}: {e}"
                )

    print()
    print("--------------------------------")
    print("Import complete")
    print("--------------------------------")
    print(f"Demux rows:       {total_demux_rows:,}")
    print(f"Quality rows:     {total_quality_rows:,}")
    print(f"Demux errors:     {demux_errors:,}")
    print(f"Quality errors:   {quality_errors:,}")


if __name__ == "__main__":
    main()