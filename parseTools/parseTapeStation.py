#!/usr/bin/env python3

import os
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import psycopg


XML_ROOT = Path("/insert/your/path/here")

PSQL_DB_HOST = os.environ['PSQL_DB_HOST']
PSQL_DB_NAME = os.environ['PSQL_DB_NAME']
PSQL_DB_USERNAME = os.environ['PSQL_DB_USERNAME']
PSQL_DB_PASS = os.environ['PSQL_DB_PASS']

INSERT_SQL = """
INSERT INTO tapestation_samples (
    source_file,
    source_file_path,
    assay,
    run_end_date,
    tape_run_date,
    instrument_serial,
    analysis_version,
    well_number,
    sample_name,
    srm_sample_id,
    screen_tape_id,
    concentration_ng_ul,
    observations,
    alert,
    region_from_bp,
    region_to_bp,
    average_size_bp,
    region_conc_ng_ul,
    molarity_nmol_l,
    percent_of_total,
    region_area,
    peak_count
)
VALUES (
    %(source_file)s,
    %(source_file_path)s,
    %(assay)s,
    %(run_end_date)s,
    %(tape_run_date)s,
    %(instrument_serial)s,
    %(analysis_version)s,
    %(well_number)s,
    %(sample_name)s,
    %(srm_sample_id)s,
    %(screen_tape_id)s,
    %(concentration_ng_ul)s,
    %(observations)s,
    %(alert)s,
    %(region_from_bp)s,
    %(region_to_bp)s,
    %(average_size_bp)s,
    %(region_conc_ng_ul)s,
    %(molarity_nmol_l)s,
    %(percent_of_total)s,
    %(region_area)s,
    %(peak_count)s
)
ON CONFLICT (
    source_file,
    well_number,
    sample_name
)
DO UPDATE SET
    concentration_ng_ul = EXCLUDED.concentration_ng_ul,
    average_size_bp = EXCLUDED.average_size_bp,
    region_conc_ng_ul = EXCLUDED.region_conc_ng_ul,
    molarity_nmol_l = EXCLUDED.molarity_nmol_l,
    percent_of_total = EXCLUDED.percent_of_total,
    region_area = EXCLUDED.region_area,
    peak_count = EXCLUDED.peak_count;
"""


def text(node, path, default=None):
    element = node.find(path)

    if element is None or element.text is None:
        return default

    value = element.text.strip()

    return value if value else default


def as_float(value):
    if value in (None, "", "-"):
        return None

    try:
        return float(value)
    except ValueError:
        return None


def as_int(value):
    if value in (None, "", "-"):
        return None

    try:
        return int(value)
    except ValueError:
        return None


def parse_tapestation_xml(filename):

    tree = ET.parse(filename)
    root = tree.getroot()

    # ---------------------------------------------------------
    # Run-level information
    # ---------------------------------------------------------

    assay = text(root, "./FileInformation/Assay")
    run_end_date = text(root, "./FileInformation/RunEndDate")
    internal_file_path = text(root, "./FileInformation/FileName")

    tapes = {}

    for tape in root.findall("./ScreenTapes/ScreenTape"):

        tape_id = text(tape, "ScreenTapeID")

        tapes[tape_id] = {
            "tape_run_date":
                text(tape, "TapeRunDate"),

            "instrument_serial":
                text(tape, "./Environment/InstrumentSerialNumber"),

            "analysis_version":
                text(tape, "./Environment/AnalysisVersion"),
        }

    # ---------------------------------------------------------
    # Samples
    # ---------------------------------------------------------

    rows = []

    for sample in root.findall("./Samples/Sample"):

        sample_name = text(sample, "Comment")
        match = re.match(r"^(\d+)_", sample_name)
        srm_sample_id = int(match.group(1)) if match else None
        observations = text(sample, "Observations")

        # Skip electronic ladders
        if observations == "Ladder" or sample_name == "Electronic Ladder":
            continue

        screen_tape_id = text(sample, "ScreenTapeID")

        tape = tapes.get(screen_tape_id, {})

        # Region
        region = sample.find("./Regions/Region")

        row = {
            "source_file": Path(filename).name,
            "source_file_path": internal_file_path,

            "assay": assay,
            "run_end_date": run_end_date,

            "tape_run_date":
                tape.get("tape_run_date"),

            "instrument_serial":
                tape.get("instrument_serial"),

            "analysis_version":
                tape.get("analysis_version"),

            "well_number":
                text(sample, "WellNumber"),

            "sample_name":
                sample_name,

            "srm_sample_id":
                srm_sample_id,

            "screen_tape_id":
                screen_tape_id,

            "concentration_ng_ul":
                as_float(text(sample, "Concentration")),

            "observations":
                observations,

            "alert":
                text(sample, "Alert"),

            "peak_count":
                len(sample.findall("./Peaks/Peak")),
        }

        if region is not None:

            row.update({
                "region_from_bp":
                    as_int(text(region, "From")),

                "region_to_bp":
                    as_int(text(region, "To")),

                "average_size_bp":
                    as_float(text(region, "AverageSize")),

                "region_conc_ng_ul":
                    as_float(text(region, "Concentration")),

                "molarity_nmol_l":
                    as_float(text(region, "Molarity")),

                "percent_of_total":
                    as_float(text(region, "PercentOfTotal")),

                "region_area":
                    as_float(text(region, "Area")),
            })

        else:

            row.update({
                "region_from_bp": None,
                "region_to_bp": None,
                "average_size_bp": None,
                "region_conc_ng_ul": None,
                "molarity_nmol_l": None,
                "percent_of_total": None,
                "region_area": None,
            })

        rows.append(row)

    return rows

def main():

    xml_files = list(XML_ROOT.rglob("*.xml"))
    print(f"Found {len(xml_files):,} XML files")
    total_samples = 0

    with psycopg.connect(
            host=PSQL_DB_HOST,
            dbname=PSQL_DB_NAME,
            user=PSQL_DB_USERNAME,
            password=PSQL_DB_PASS,
    ) as conn:
        with conn.cursor() as cur:
            for i, filename in enumerate(xml_files, start=1):
                try:
                    rows = parse_tapestation_xml(filename)
                    cur.executemany(
                        INSERT_SQL,
                        rows
                    )

                    total_samples += len(rows)

                    print(
                        f"[{i:,}/{len(xml_files):,}] "
                        f"{filename.name}: "
                        f"{len(rows)} samples"
                    )

                except Exception as e:

                    print(
                        f"ERROR: {filename}: {e}"
                    )

            conn.commit()

    print(
        f"Imported {total_samples:,} samples "
        f"from {len(xml_files):,} XML files"
    )


if __name__ == "__main__":
    main()