"""Verify Earth Engine auth and catalog access. Run before any ingestion.

Prints the size of COPERNICUS/S5P/OFFL/L3_NO2. A number here means auth,
project binding, and catalog access all work.
"""

import sys
import traceback

PROJECT = "storied-depot-291800"
COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"


def main():
    import ee

    print(f"earthengine-api version: {ee.__version__}")

    try:
        ee.Initialize(project=PROJECT)
    except Exception:
        print(f"FAIL: ee.Initialize(project='{PROJECT}') raised:", file=sys.stderr)
        traceback.print_exc()
        return 1
    print(f"ee.Initialize OK  (project={PROJECT})")

    try:
        n = ee.ImageCollection(COLLECTION).size().getInfo()
    except Exception:
        print(f"FAIL: could not read {COLLECTION}:", file=sys.stderr)
        traceback.print_exc()
        return 2

    print(f"{COLLECTION} size: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
