# setup_raw_data.py
"""
Helper script to copy raw data files to the raw_data/ directory.

Run this ONCE to set up the raw_data directory with source files:
    python setup_raw_data.py

This script copies (not moves) files from their original locations
to raw_data/, ensuring the original files remain intact.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Source files and their target names in raw_data/
SOURCE_FILES = [
    # (source_path, target_name)
    (ROOT / "newData" / "Abadi et al. (2023) A Dataset of Social-Psychological and Emotional Reactions during the COVID-19 Pandemic across Four European Countries.csv",
     "abadi.csv"),
    (ROOT / "newData" / "mmc2.csv",
     "mmc2.csv"),
    (ROOT / "newData" / "mental_health_finaldata_1.csv",
     "mental_health_finaldata.csv"),
    (ROOT / "newData" / "pone.0246894.s005.csv",
     "pone.csv"),
    (ROOT / "Static" / "Data" / "dataset.csv",
     "dataset.csv"),
]

RAW_DATA_DIR = ROOT / "raw_data"


def main():
    print("=" * 60)
    print("SETTING UP RAW DATA DIRECTORY")
    print("=" * 60)
    print()
    
    # Create raw_data directory
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Raw data directory: {RAW_DATA_DIR}")
    print()
    
    copied = 0
    skipped = 0
    missing = 0
    
    for source, target_name in SOURCE_FILES:
        target = RAW_DATA_DIR / target_name
        
        if not source.exists():
            print(f"❌ MISSING: {source.name}")
            print(f"   Source not found: {source}")
            missing += 1
            continue
        
        if target.exists():
            print(f"⏭️  SKIPPED: {target_name} (already exists)")
            skipped += 1
            continue
        
        # Copy the file
        shutil.copy2(source, target)
        print(f"✅ COPIED: {source.name}")
        print(f"   → {target_name}")
        copied += 1
    
    print()
    print("-" * 60)
    print(f"Summary: {copied} copied, {skipped} skipped, {missing} missing")
    print()
    
    if missing > 0:
        print("⚠️  Some source files were not found.")
        print("   Please ensure all raw data files exist in their original locations.")
    
    if copied > 0 or skipped > 0:
        print()
        print("✅ Raw data directory is ready!")
        print("   Run the cleaning pipeline:")
        print("   python src/clean_data.py")


if __name__ == "__main__":
    main()

