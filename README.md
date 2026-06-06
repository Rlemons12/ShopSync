# ShopSync Tablet

This repository now contains a native Android tablet rebuild of ShopSync in the `app` module.

## Original repository inspection

The source that originally shipped in this repository is a Python desktop implementation centered on local inventory management:

- `app/app_shopsync.py` is a large PyQt6 desktop app titled `ShopSync - Equipment Management System`.
- `scanner.py` is a separate Tkinter utility for a `MASTER -> VERIFY` barcode workflow that stores scan history in SQLite.
- `app/modules/database/shopsync_db.py` defines a large SQLAlchemy schema with spare parts, inventory, campuses, buildings, site locations, containers, shelves, drawers, slots, and a broader equipment hierarchy.
- `app/modules/database/db_manager.py` and `app/modules/configuration/database_config.py` wire the app to a local SQLite database at `app/modules/database/shopsync.db`.
- Spreadsheet loader scripts under `app/modules/database/loadsheets/` seed or validate data from Excel files.

### Original screens and user flows

The desktop app's implemented workflows cluster around these screens:

- `Inventory`: deduplicated parts list, part search, add part, add stock, delete part, and drill into all locations holding a part.
- `Remote Inventory`: search a room and then browse `room -> container -> shelf -> drawer -> slot`, with a summary panel and stock contents table.
- `Add New Location`: create campuses, buildings, rooms, containers, shelves, drawers, and slots in sequence.
- `Search`: a partial search UI with filters for areas, equipment groups, models, assets, and parts. The code structure exists, but the search implementation is incomplete.
- `Details`: editable entity-detail form for some hierarchy objects.
- `Scanner utility`: choose or arm a master code, verify incoming scans, and persist scan logs.

### Original data flow and storage

- All persistent app data is local SQLite.
- SQLAlchemy models and session scopes act as the service layer.
- The main user flow is location-driven inventory control rather than network-backed API sync.
- No production HTTP API client exists in the checked-in codebase.
- The repo includes logging, database initialization, and spreadsheet import helpers, but not a mobile or web frontend.

## Native Android rebuild

The new Android app preserves the repository's working flows while rebuilding them with modern Android architecture:

- App name: `ShopSync`
- Package: `com.shopsync.tablet`
- UI stack: Kotlin, Jetpack Compose, Material 3
- Architecture: Compose Navigation, ViewModels, StateFlow, repositories, Room
- Target form factor: tablet-first with portrait and landscape support

### Native screens

- `Overview`: dashboard with inventory and scan summaries.
- `Inventory`: search parts, inspect metadata, review stock locations, add parts, and add stock.
- `Remote`: browse room/container/shelf/drawer/slot contents.
- `Locations`: create and browse location hierarchy records.
- `Search`: cross-entity search over parts and storage hierarchy.
- `Scanner`: live camera barcode scanning with CameraX and on-device ML Kit decoding, plus manual fallback entry.

### Project structure

- `app/src/main/java/com/shopsync/tablet/data`: Room database, DAOs, entities, repositories, seed data.
- `app/src/main/java/com/shopsync/tablet/domain`: UI/domain models.
- `app/src/main/java/com/shopsync/tablet/ui`: app shell, navigation, components, theme, and screen ViewModels.
- `app/src/main/AndroidManifest.xml`: Android app manifest.

## Build

Requirements:

- Android Studio with Android SDK installed
- JDK 17

Build from the repository root:

```bash
./gradlew :app:assembleDebug
```

Windows:

```powershell
.\gradlew.bat :app:assembleDebug
```

The APK output is generated under `app/build/outputs/apk/debug/`.

## Notes

- The legacy Python implementation has been removed after the Android migration; the summary above documents the original workflow and structure.
- The Android app uses seeded Room data so the tablet UI is usable immediately after install.
- The scanner requests camera permission and performs barcode decoding on-device.
- `local.properties` is machine-specific and should not be committed.
