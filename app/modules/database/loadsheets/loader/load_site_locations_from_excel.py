#!/usr/bin/env python3
"""
Interactive Load Sheet Importer for SiteLocations.

Features:
  Prompts user to enter the folder path containing the load sheet.
  Detects Excel load sheets (.xls or .xlsx) in that folder.
  Prompts to select one if multiple exist.
  Uses Campus.add_campus(), Building.add_building(), SiteLocation.find_or_create().
  Prompts for creating missing Campuses/Buildings with "apply-to-all" options.
  Logs all actions and writes a CSV summary report.

Expected Excel Columns:
  Room # | Description | Area | building_id | campus_id
"""

import os
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.modules.database.db_manager import ShopSyncDatabase
from app.modules.configuration.log_config import (
    info_id, error_id, debug_id, set_request_id
)
from app.modules.database.shopsync_db import SiteLocation, Building, Campus


# ----------------------------------------------------------------------
# UTILITY: Ask for Folder and Select Excel File
# ----------------------------------------------------------------------
def select_load_sheet():
    """Prompt user to enter either a folder path or a full Excel file path."""
    print("\n📁 Please enter the folder *or* file path where your Excel load sheet is located.")
    print("Examples:")
    print("  Folder: C:\\Users\\10169062\\PycharmProjects\\ShopSync\\app\\modules\\database\\loadsheets\\")
    print("  File:   C:\\Users\\10169062\\PycharmProjects\\ShopSync\\app\\modules\\database\\loadsheets\\map_pack.xls")
    folder_or_file = input("\nEnter path: ").strip().strip('"')

    if not folder_or_file:
        print("❌ No path entered.")
        return None

    # Case 1: Direct Excel file path
    if os.path.isfile(folder_or_file) and folder_or_file.lower().endswith((".xls", ".xlsx")):
        print(f"Using Excel file: {folder_or_file}")
        return folder_or_file

    # Case 2: Folder path
    if os.path.isdir(folder_or_file):
        excel_files = [
            f for f in os.listdir(folder_or_file)
            if f.lower().endswith((".xls", ".xlsx"))
        ]

        if not excel_files:
            print(f"❌ No Excel files (.xls or .xlsx) found in: {folder_or_file}")
            return None

        if len(excel_files) == 1:
            print(f"Found Excel file: {excel_files[0]}")
            confirm = input("Use this file? (Y/N): ").strip().lower()
            if confirm in {"y", "yes"}:
                return os.path.join(folder_or_file, excel_files[0])
            else:
                print("Operation cancelled by user.")
                return None

        print("\n📂 Multiple Excel files detected:")
        for i, file in enumerate(excel_files, start=1):
            print(f"  {i}. {file}")
        while True:
            choice = input(f"Enter the number of the file to load (1-{len(excel_files)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(excel_files):
                selected = excel_files[int(choice) - 1]
                print(f"Selected: {selected}")
                return os.path.join(folder_or_file, selected)
            else:
                print("Invalid choice. Please enter a valid number.")

    print(f"❌ Invalid path or unsupported file type: {folder_or_file}")
    return None

# ----------------------------------------------------------------------
# UTILITY: Prompt for Missing Entities
# ----------------------------------------------------------------------
def prompt_user_for_creation(entity_type, entity_id):
    """Prompt user to confirm creation of a missing entity (Campus or Building)."""
    while True:
        print(f"\n⚠️ {entity_type} with ID {entity_id} not found in the database.")
        choice = input(
            f"Would you like to create it? "
            f"(Y)es / (N)o / (YA) yes to all / (NA) no to all: "
        ).strip().lower()
        if choice in {"y", "yes"}:
            return "create"
        elif choice in {"n", "no"}:
            return "skip"
        elif choice == "ya":
            return "apply_all_create"
        elif choice == "na":
            return "apply_all_skip"
        else:
            print("Invalid input. Please enter Y, N, YA, or NA.")


# ----------------------------------------------------------------------
# MAIN LOAD FUNCTION
# ----------------------------------------------------------------------
def load_site_locations_from_excel(file_path: str, sheet_name: str = "rooms"):
    """Interactive loader for SiteLocations with user prompts for missing entities."""
    request_id = set_request_id()
    info_id(f"Starting SiteLocation import from: {file_path}", request_id)

    if not os.path.exists(file_path):
        error_id(f"Excel file not found: {file_path}", request_id)
        return

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df.columns = df.columns.str.strip()

        required_columns = {"Room #", "Description", "Area", "building_id", "campus_id"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")

        db = ShopSyncDatabase()
        summary_records = []
        inserted_count = 0
        skipped_count = 0

        # Flags to remember user choices
        apply_all_campus = None
        apply_all_building = None

        with db.session_scope() as session:
            for _, row in df.iterrows():
                room_number = str(row["Room #"]).strip() if pd.notna(row["Room #"]) else "Unknown"
                title = str(row["Description"]).strip() if pd.notna(row["Description"]) else "Unnamed"
                site_area = str(row["Area"]).strip() if pd.notna(row["Area"]) else "General"
                campus_id = row.get("campus_id")
                building_id = row.get("building_id")

                debug_id(
                    f"Processing Room={room_number}, Title={title}, Area={site_area}, "
                    f"Building ID={building_id}, Campus ID={campus_id}",
                    request_id
                )

                # ------------------- CAMPUS VALIDATION -------------------
                campus = None
                if pd.notna(campus_id):
                    campus = session.query(Campus).filter_by(id=int(campus_id)).first()
                    if not campus:
                        action = apply_all_campus
                        if not action:
                            response = prompt_user_for_creation("Campus", campus_id)
                            if response == "apply_all_create":
                                apply_all_campus = "create"
                                action = "create"
                            elif response == "apply_all_skip":
                                apply_all_campus = "skip"
                                action = "skip"
                            else:
                                action = response

                        if action == "create":
                            campus = Campus.add_campus(
                                session=session,
                                name=f"Campus_{int(campus_id)}",
                                description="Auto-created from load sheet",
                                city=None,
                                state=None,
                                country=None,
                                request_id=request_id
                            )
                            debug_id(f"Created Campus_{int(campus_id)}", request_id)
                        else:
                            skipped_count += 1
                            summary_records.append({
                                "Room #": room_number,
                                "Title": title,
                                "Area": site_area,
                                "Building ID": building_id,
                                "Campus ID": campus_id,
                                "Status": "Skipped - Missing Campus"
                            })
                            continue
                else:
                    skipped_count += 1
                    summary_records.append({
                        "Room #": room_number,
                        "Title": title,
                        "Area": site_area,
                        "Building ID": building_id,
                        "Campus ID": campus_id,
                        "Status": "Skipped - No Campus ID"
                    })
                    continue

                # ------------------- BUILDING VALIDATION -------------------
                building = None
                if pd.notna(building_id):
                    building = session.query(Building).filter_by(id=int(building_id)).first()
                    if not building:
                        action = apply_all_building
                        if not action:
                            response = prompt_user_for_creation("Building", building_id)
                            if response == "apply_all_create":
                                apply_all_building = "create"
                                action = "create"
                            elif response == "apply_all_skip":
                                apply_all_building = "skip"
                                action = "skip"
                            else:
                                action = response

                        if action == "create":
                            building = Building.add_building(
                                session=session,
                                name=f"Building_{int(building_id)}",
                                campus_id=campus.id,
                                description="Auto-created from load sheet",
                                address=None,
                                request_id=request_id
                            )
                            debug_id(f"Created Building_{int(building_id)} under Campus {campus.id}", request_id)
                        else:
                            skipped_count += 1
                            summary_records.append({
                                "Room #": room_number,
                                "Title": title,
                                "Area": site_area,
                                "Building ID": building_id,
                                "Campus ID": campus_id,
                                "Status": "Skipped - Missing Building"
                            })
                            continue
                else:
                    skipped_count += 1
                    summary_records.append({
                        "Room #": room_number,
                        "Title": title,
                        "Area": site_area,
                        "Building ID": building_id,
                        "Campus ID": campus_id,
                        "Status": "Skipped - No Building ID"
                    })
                    continue

                # ------------------- SITE LOCATION CREATION -------------------
                site_location = SiteLocation.find_or_create(
                    session=session,
                    title=title,
                    room_number=room_number,
                    site_area=site_area,
                    request_id=request_id
                )
                site_location.building_id = building.id
                session.commit()

                inserted_count += 1
                summary_records.append({
                    "Room #": room_number,
                    "Title": title,
                    "Area": site_area,
                    "Building ID": building_id,
                    "Campus ID": campus_id,
                    "Status": "Inserted"
                })

        # ------------------------------------------------------------------
        # WRITE SUMMARY CSV
        # ------------------------------------------------------------------
        summary_df = pd.DataFrame(summary_records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = os.path.join(os.getcwd(), f"{timestamp}_site_location_load_summary.csv")
        summary_df.to_csv(summary_path, index=False)
        info_id(f"Completed loading {inserted_count} site locations.", request_id)
        info_id(f"Skipped {skipped_count} records.", request_id)
        info_id(f"Summary written to: {summary_path}", request_id)

    except SQLAlchemyError as e:
        error_id(f"Database error: {e}", request_id)
    except Exception as e:
        error_id(f"Unexpected error: {e}", request_id)


# ----------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    selected_file = select_load_sheet()
    if not selected_file:
        print("❌ Load operation cancelled.")
    else:
        load_site_locations_from_excel(selected_file)
