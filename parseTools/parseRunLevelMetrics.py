import os
import pandas as pd
import psycopg

# ------------------------------------------------------------
# PostgreSQL
# ------------------------------------------------------------

DB_HOST = os.environ['PSQL_DB_HOST']
DB_NAME = os.environ['PSQL_DB_NAME']
DB_USER = os.environ['PSQL_DB_USERNAME']
DB_PASSWORD = os.environ['PSQL_DB_PASS']

DB_PORT = int(os.environ.get("PGPORT", 5432))

df = pd.read_excel("~/kids26/NovaSeq X Plus.xlsx")

df = df.rename(columns={
    "Run": "run_name",
    "SoftwareVersion": "software_version",
    "Occupancy": "occupancy",
    "Q30": "q30",
    "PF": "pf",
    "Flowcell": "flowcell"
})

rows = df.to_dict("records")

sql = """
INSERT INTO novaseq_x_run_metrics (
    run_name,
    software_version,
    occupancy,
    q30,
    pf,
    flowcell
)
VALUES (
    %(run_name)s,
    %(software_version)s,
    %(occupancy)s,
    %(q30)s,
    %(pf)s,
    %(flowcell)s
)
ON CONFLICT (run_name)
DO UPDATE SET
    software_version = EXCLUDED.software_version,
    occupancy = EXCLUDED.occupancy,
    q30 = EXCLUDED.q30,
    pf = EXCLUDED.pf,
    flowcell = EXCLUDED.flowcell;
"""

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

    print("Importing NovaSeq X Plus run-level metrics...")


    with conn.cursor() as cur:

        cur.executemany(
            sql,
            rows
        )

    conn.commit()