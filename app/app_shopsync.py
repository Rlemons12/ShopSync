import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# SQLAlchemy
from sqlalchemy import Column, select, or_
from sqlalchemy.types import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import joinedload

# PyQt6
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QStringListModel, QTimer
)
from PyQt6.QtGui import (
    QAction, QIcon, QFont, QPalette, QColor
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QLabel, QComboBox, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QSplitter, QFrame,
    QGroupBox, QSpinBox, QHeaderView, QMenu, QToolBar, QStatusBar,
    QCompleter, QListWidget, QScrollArea,QGridLayout,QInputDialog

)
from PyQt6.QtCore import QSignalBlocker

# App configuration and logging
from app.modules.configuration import (
    logger, info_id, error_id, debug_id, set_request_id, with_request_id
)
from app.modules.configuration.base import Base

# Database manager
from app.modules.database.db_manager import ShopSyncDatabase

# Database models
from app.modules.database.shopsync_db import (
    Area, EquipmentGroup, Model, AssetNumber, Location, Position,
    Container, Shelf, Drawer, Part, Inventory, Drawing, SiteLocation,
    Subassembly, ComponentAssembly, AssemblyView, StorageAddress, DrawerSlot)
import sys
import logging
from typing import Optional, List, Dict, Any
from app.modules.configuration.log_config import with_request_id, get_request_id
# SQLAlchemy
from sqlalchemy import Column, select, or_
from sqlalchemy.types import JSON
from sqlalchemy.ext.declarative import declarative_base

# PyQt6
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QStringListModel, QTimer
)
from PyQt6.QtGui import (
    QAction, QIcon, QFont, QPalette, QColor
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QLabel, QComboBox, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QSplitter, QFrame,
    QGroupBox, QSpinBox, QHeaderView, QMenu, QToolBar, QStatusBar,
    QCompleter, QListWidget, QScrollArea
)

# App configuration and logging
from app.modules.configuration import (
    logger, info_id, error_id, debug_id, set_request_id, warning_id
)
from app.modules.configuration.base import Base

# Database manager
from app.modules.database.db_manager import ShopSyncDatabase

# Database models
from app.modules.database.shopsync_db import (
    Area, EquipmentGroup, Model, AssetNumber, Location, Position,
    Container, Shelf, Drawer, Part, Inventory, Drawing, SiteLocation,
    Subassembly, ComponentAssembly, AssemblyView
)

import faulthandler, sys, os
faulthandler.enable(all_threads=True)

# Optional: also dump tracebacks on crash signals
import signal
for sig in (signal.SIGSEGV, signal.SIGABRT, signal.SIGFPE, signal.SIGILL):
    try:
        faulthandler.register(sig, file=sys.__stderr__, all_threads=True)
    except Exception as e:
        print(f"[faulthandler] Could not register {sig}: {e}")


class DatabaseWorker(QThread):
    """Background thread for database operations"""
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs

    def run(self):
        request_id = set_request_id()  # Set request ID for this thread
        try:
            debug_id("Starting database operation", request_id)
            result = self.operation(*self.args, **self.kwargs)
            debug_id("Database operation completed successfully", request_id)
            self.result_ready.emit(result)
        except Exception as e:
            error_id(f"Database operation failed: {str(e)}", request_id)
            self.error_occurred.emit(str(e))

class EntityDetailsWidget(QWidget):
    """Widget for displaying and editing entity details"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_entity = None
        self.current_entity_type = None

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        self.header_label = QLabel("Select an item to view details")
        self.header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.header_label)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        scroll.setWidget(self.form_widget)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.delete_btn = QPushButton("Delete")
        self.new_btn = QPushButton("New")
        self.cancel_btn = QPushButton("Cancel")

        self.save_btn.clicked.connect(self.save_entity)
        self.delete_btn.clicked.connect(self.delete_entity)
        self.new_btn.clicked.connect(self.create_new_entity)
        self.cancel_btn.clicked.connect(self.cancel_changes)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Initially disable buttons
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def show_entity_details(self, entity_type, entity_data):
        """Display details for the selected entity"""
        request_id = set_request_id()
        debug_id(f"Showing details for {entity_type} with ID {entity_data.id}", request_id)

        self.current_entity = entity_data
        self.current_entity_type = entity_type

        self.header_label.setText(f"{entity_type.title()} Details (ID: {entity_data.id})")

        # Clear existing form
        self.clear_form()

        # Add form fields based on entity type
        if entity_type == 'area':
            self.setup_area_form(entity_data)
        elif entity_type == 'equipment_group':
            self.setup_equipment_group_form(entity_data)
        elif entity_type == 'model':
            self.setup_model_form(entity_data)
        elif entity_type == 'asset':
            self.setup_asset_form(entity_data)
        elif entity_type == 'location':
            self.setup_location_form(entity_data)

        # Enable buttons
        self.save_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def clear_form(self):
        """Clear all form fields"""
        for i in reversed(range(self.form_layout.count())):
            child = self.form_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

    def setup_area_form(self, area):
        """Setup form fields for Area entity"""
        self.name_edit = QLineEdit(area.name)
        self.description_edit = QTextEdit(area.description or '')

        self.form_layout.addRow("Name:", self.name_edit)
        self.form_layout.addRow("Description:", self.description_edit)

    def setup_equipment_group_form(self, equipment_group):
        """Setup form fields for Equipment Group entity"""
        self.name_edit = QLineEdit(equipment_group.name)
        self.area_combo = QComboBox()
        # Populate with areas from database
        self.description_edit = QTextEdit(equipment_group.description or '')

        self.form_layout.addRow("Name:", self.name_edit)
        self.form_layout.addRow("Area:", self.area_combo)
        self.form_layout.addRow("Description:", self.description_edit)

    def setup_model_form(self, model):
        """Setup form fields for Model entity"""
        self.name_edit = QLineEdit(model.name)
        self.equipment_group_combo = QComboBox()
        # Populate with equipment groups from database
        self.description_edit = QTextEdit(model.description or '')

        self.form_layout.addRow("Name:", self.name_edit)
        self.form_layout.addRow("Equipment Group:", self.equipment_group_combo)
        self.form_layout.addRow("Description:", self.description_edit)

    def setup_asset_form(self, asset):
        """Setup form fields for Asset entity"""
        self.number_edit = QLineEdit(asset.number)
        self.description_edit = QTextEdit(asset.description or '')
        self.model_combo = QComboBox()
        # Populate with models from database

        self.form_layout.addRow("Asset Number:", self.number_edit)
        self.form_layout.addRow("Model:", self.model_combo)
        self.form_layout.addRow("Description:", self.description_edit)

    def setup_location_form(self, location):
        """Setup form fields for Location entity"""
        self.name_edit = QLineEdit(location.name)
        self.description_edit = QTextEdit(location.description or '')
        self.model_combo = QComboBox()
        # Populate with models from database

        self.form_layout.addRow("Name:", self.name_edit)
        self.form_layout.addRow("Model:", self.model_combo)
        self.form_layout.addRow("Description:", self.description_edit)

    def save_entity(self):
        """Save the current entity"""
        if not self.current_entity:
            return

        request_id = set_request_id()
        try:
            info_id(f"Saving {self.current_entity_type} entity", request_id)
            # Implement save logic based on entity type
            QMessageBox.information(self, "Success", "Entity saved successfully!")
        except Exception as e:
            error_id(f"Failed to save entity: {str(e)}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to save entity: {str(e)}")

    def delete_entity(self):
        """Delete the current entity"""
        if not self.current_entity:
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this entity?")
        if reply == QMessageBox.StandardButton.Yes:
            request_id = set_request_id()
            try:
                info_id(f"Deleting {self.current_entity_type} entity", request_id)
                # Implement delete logic based on entity type
                QMessageBox.information(self, "Success", "Entity deleted successfully!")
                self.clear_form()
                self.current_entity = None
                self.save_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)
            except Exception as e:
                error_id(f"Failed to delete entity: {str(e)}", request_id)
                QMessageBox.critical(self, "Error", f"Failed to delete entity: {str(e)}")

    def create_new_entity(self):
        """Create a new entity"""
        request_id = set_request_id()
        debug_id("Opening new entity dialog", request_id)
        dialog = NewEntityDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Handle new entity creation
            info_id("New entity creation accepted", request_id)

    def cancel_changes(self):
        """Cancel changes and reload original data"""
        if self.current_entity:
            self.show_entity_details(self.current_entity_type, self.current_entity)

class SearchWidget(QWidget):
    """Advanced search widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Search controls
        search_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search equipment, models, parts...")
        self.search_btn = QPushButton("Search")
        self.clear_btn = QPushButton("Clear")

        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_btn)

        layout.addLayout(search_layout)

        # Search filters
        filters_group = QGroupBox("Filters")
        filters_layout = QFormLayout(filters_group)

        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItems(["All", "Areas", "Equipment Groups", "Models", "Assets", "Parts"])

        self.area_filter_combo = QComboBox()
        # Populate from database

        filters_layout.addRow("Entity Type:", self.entity_type_combo)
        filters_layout.addRow("Area:", self.area_filter_combo)

        layout.addWidget(filters_group)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Area", "Description"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.results_table)

        # Connect signals
        self.search_btn.clicked.connect(self.perform_search)
        self.clear_btn.clicked.connect(self.clear_search)
        self.search_edit.returnPressed.connect(self.perform_search)
        self.results_table.itemDoubleClicked.connect(self.open_selected_item)

    def perform_search(self):
        """Perform search operation"""
        search_text = self.search_edit.text().strip()
        entity_type = self.entity_type_combo.currentText()

        if not search_text:
            return

        request_id = set_request_id()
        debug_id(f"Performing search for '{search_text}' in {entity_type}", request_id)

        # Implement database search logic here
        self.results_table.setRowCount(0)  # Clear previous results

    def clear_search(self):
        """Clear search results"""
        self.search_edit.clear()
        self.results_table.setRowCount(0)

    def open_selected_item(self, item):
        """Open selected item in details view"""
        row = item.row()
        # Get item data and emit signal to show details
        request_id = set_request_id()
        debug_id(f"Opening selected item from search results, row {row}", request_id)

class InventoryWidget(QWidget):
    """Inventory management widget (SQLAlchemy 2.0 style)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        self._locations_dlg = None
        self.setup_ui()
        self.inventory_table.itemDoubleClicked.connect(self.open_part_locations)

    # -------------------------
    # UI Setup
    # -------------------------
    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Controls layout ---
        controls_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.add_part_btn = QPushButton("Add Part")
        self.add_stock_btn = QPushButton("Add Stock")
        self.transfer_btn = QPushButton("Transfer")
        self.delete_btn = QPushButton("Delete")

        self.part_search = QLineEdit()
        self.part_search.setPlaceholderText("Search parts…")

        controls_layout.addWidget(QLabel("Part:"))
        controls_layout.addWidget(self.part_search)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.add_part_btn)
        controls_layout.addWidget(self.add_stock_btn)
        controls_layout.addWidget(self.transfer_btn)
        controls_layout.addWidget(self.delete_btn)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # --- Inventory table ---
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(7)  # Removed "Location"
        self.inventory_table.setHorizontalHeaderLabels([
            "Part Number", "Part Name", "OEM Mfg", "OEM Model",
            "Quantity", "Unit", "Last Updated"
        ])
        self.inventory_table.horizontalHeader().setStretchLastSection(True)
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.inventory_table.setSortingEnabled(False)

        header = self.inventory_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.inventory_table)

        # --- Signals ---
        self.refresh_btn.clicked.connect(self.refresh_inventory)
        self.add_part_btn.clicked.connect(self.add_part)
        self.add_stock_btn.clicked.connect(self.add_stock)
        self.transfer_btn.clicked.connect(self.transfer_stock)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.part_search.returnPressed.connect(self.refresh_inventory)

    # -------------------------
    # DB Manager hook
    # -------------------------
    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        self.refresh_inventory()

    # -------------------------
    # Inventory refresh
    # -------------------------
    def refresh_inventory(self):
        """Refresh inventory display (deduplicated parts)."""
        request_id = set_request_id()
        debug_id("Refreshing inventory display (deduplicated)", request_id)
        if not self.db_manager:
            return

        text = (self.part_search.text() or "").strip()
        like = f"%{text}%" if text else None

        with self.db_manager.session_scope() as s:
            stmt = (
                select(Inventory)
                .options(
                    joinedload(Inventory.part),
                    joinedload(Inventory.container).joinedload(Container.position).joinedload(Position.site_location),
                    joinedload(Inventory.shelf).joinedload(Shelf.container).joinedload(Container.position).joinedload(
                        Position.site_location),
                    joinedload(Inventory.drawer).joinedload(Drawer.shelf).joinedload(Shelf.container).joinedload(
                        Container.position).joinedload(Position.site_location),
                    joinedload(Inventory.drawer_slot)
                    .joinedload(DrawerSlot.drawer)
                    .joinedload(Drawer.shelf)
                    .joinedload(Shelf.container)
                    .joinedload(Container.position)
                    .joinedload(Position.site_location),
                )
            )
            if like:
                stmt = stmt.join(Inventory.part).filter(
                    (Part.part_number.ilike(like)) | (Part.name.ilike(like))
                )

            inv_rows = s.execute(stmt).scalars().all()

        # Deduplicate by Part ID
        seen = {}
        for i in inv_rows:
            if not i.part:
                continue
            pid = i.part.id
            qty_val = int(i.quantity or 0)
            if pid not in seen:
                seen[pid] = {
                    "sku": i.part.part_number,
                    "name": i.part.name,
                    "oem": i.part.oem_mfg,
                    "model": i.part.model,
                    "qty": qty_val,
                    "unit": i.unit or "",
                    "updated": i.updated_at,
                }
            else:
                seen[pid]["qty"] += qty_val
                if i.updated_at and (
                        not seen[pid]["updated"] or i.updated_at > seen[pid]["updated"]
                ):
                    seen[pid]["updated"] = i.updated_at

        table_data = []
        for part in seen.values():
            updated_dt = part["updated"]
            updated_str = updated_dt.strftime("%Y-%m-%d %H:%M") if updated_dt else ""
            display_vals = [
                part["sku"], part["name"], part["oem"], part["model"],
                part["qty"], part["unit"], updated_str
            ]
            # for sorting: keep int for qty, datetime for updated
            sort_vals = [None, None, None, None, part["qty"], None, updated_dt]
            table_data.append((display_vals, sort_vals))

        # Fill table
        self.inventory_table.setSortingEnabled(False)
        self.inventory_table.clearContents()
        self.inventory_table.setRowCount(len(table_data))

        for r, (display_vals, sort_vals) in enumerate(table_data):
            for c in range(7):
                item = QTableWidgetItem()
                # always set display string
                item.setText("" if display_vals[c] is None else str(display_vals[c]))
                # set proper sort role
                sv = sort_vals[c]
                if sv is not None:
                    item.setData(Qt.ItemDataRole.EditRole, sv)
                self.inventory_table.setItem(r, c, item)

        debug_id(f"Inserted {len(table_data)} unique parts", request_id)

    # -------------------------
    # Part actions
    # -------------------------
    def add_part(self):
        if not self.db_manager:
            QMessageBox.warning(self, "Database", "Database not initialized.")
            return
        dlg = AddPartDialog(self, self.db_manager)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_inventory()

    def open_part_locations(self, item):
        row = item.row()
        sku_item = self.inventory_table.item(row, 0)
        sku = sku_item.text() if sku_item else None
        if not sku:
            return

        with self.db_manager.session_scope() as s:
            stmt = select(Part.id).filter(Part.part_number == sku)
            part_id = s.execute(stmt).scalar_one_or_none()
            if not part_id:
                return

        self._locations_dlg = PartLocationsDialog(self, self.db_manager, part_id)
        result = self._locations_dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            self.refresh_inventory()
        self._locations_dlg.deleteLater()
        self._locations_dlg = None

    def add_stock(self):
        if not self.db_manager:
            QMessageBox.warning(self, "Database", "Database not initialized.")
            return
        dlg = AddStockDialog(self, self.db_manager)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_inventory()

    def transfer_stock(self):
        QMessageBox.information(self, "Transfer", "Transfer workflow not implemented yet.")

    def delete_selected(self):
        row = self.inventory_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete", "Select a row to delete first.")
            return

        sku_item = self.inventory_table.item(row, 0)
        sku = sku_item.text() if sku_item else None

        with self.db_manager.session_scope() as s:
            stmt = select(Part).filter(Part.part_number == sku)
            part = s.execute(stmt).scalar_one_or_none()
            if not part:
                QMessageBox.warning(self, "Delete", f"Part {sku} not found.")
                return

            choice = QMessageBox.question(
                self,
                "Delete",
                f"Delete part '{part.name}' ({sku}) and all its inventory?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            if choice == QMessageBox.StandardButton.Cancel:
                return

            s.delete(part)
            s.commit()

        self.refresh_inventory()

class AddPartDialog(QDialog):
    """
    Create a new Part (SKU, metadata) and optionally seed initial stock at a chosen
    Room -> Container -> Shelf -> Drawer -> Slot location.

    Rules:
      - Part Number (SKU) and Part Name are required.
      - If Initial Quantity is provided (>0), a location selection is REQUIRED
        (at least a Container; deeper levels shelf/drawer/slot are optional unless your schema enforces them).
    """

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Add Part")
        self.setMinimumWidth(600)
        self._build_ui()
        self._wire_signals()
        self._prime_location_dropdowns()

    # ----------------------------
    # UI
    # ----------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)

        # --- Part fields ---
        form = QFormLayout()
        self.sku_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.oem_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.class_edit = QLineEdit()

        form.addRow("Part Number (SKU)*:", self.sku_edit)
        form.addRow("Part Name*:", self.name_edit)
        form.addRow("OEM Manufacturer:", self.oem_edit)
        form.addRow("OEM Model / Catalog #:", self.model_edit)
        form.addRow("Category (Class Flag):", self.class_edit)

        outer.addLayout(form)

        # --- Initial Stock fields ---
        stock_form = QFormLayout()

        # Quantity as SpinBox to avoid bad input; 0 means "no initial stock"
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 1_000_000)
        self.qty_spin.setValue(0)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("Unit (e.g., ea, box, ft)")

        stock_form.addRow("Initial Quantity:", self.qty_spin)
        stock_form.addRow("Stock Unit:", self.unit_edit)

        # Dependent location selectors
        self.room_combo = QComboBox()
        self.container_combo = QComboBox()
        self.shelf_combo = QComboBox()
        self.drawer_combo = QComboBox()
        self.slot_combo = QComboBox()

        stock_form.addRow("Room:", self.room_combo)
        stock_form.addRow("Container:", self.container_combo)
        stock_form.addRow("Shelf:", self.shelf_combo)
        stock_form.addRow("Drawer:", self.drawer_combo)
        stock_form.addRow("Slot:", self.slot_combo)

        outer.addLayout(stock_form)

        # --- Buttons ---
        btns = QHBoxLayout()
        self.ok_btn = QPushButton("Add")
        self.continue_btn = QPushButton("Add && Continue")
        self.cancel_btn = QPushButton("Cancel")
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.continue_btn)
        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        outer.addLayout(btns)

    def _wire_signals(self):
        # Buttons
        self.ok_btn.clicked.connect(self._on_add_and_close)
        self.continue_btn.clicked.connect(self._on_add_and_continue)
        self.cancel_btn.clicked.connect(self.reject)

        # Dependent dropdowns
        self.room_combo.currentIndexChanged.connect(self._on_room_changed)
        self.container_combo.currentIndexChanged.connect(self._on_container_changed)
        self.shelf_combo.currentIndexChanged.connect(self._on_shelf_changed)
        self.drawer_combo.currentIndexChanged.connect(self._on_drawer_changed)

    # ----------------------------
    # Location combos
    # ----------------------------
    def _prime_location_dropdowns(self):
        request_id = set_request_id()
        info_id("[AddPartDialog] Prime location dropdowns", request_id)

        # Rooms
        self.room_combo.clear()
        self.room_combo.addItem("-- Select Room --", None)

        with self.db_manager.session_scope() as s:
            rooms = s.execute(
                select(SiteLocation).order_by(SiteLocation.title.asc())
            ).scalars().all()

        for r in rooms:
            label = f"{r.title} (Room {r.room_number}, {r.site_area})" if r.room_number or r.site_area else (r.title or f"Room {r.id}")
            self.room_combo.addItem(label, r.id)

        # Seed others as empty until a parent is chosen
        for combo, placeholder in (
            (self.container_combo, "-- Select Container --"),
            (self.shelf_combo, "-- Select Shelf --"),
            (self.drawer_combo, "-- Select Drawer --"),
            (self.slot_combo, "-- Select Slot --"),
        ):
            combo.clear()
            combo.addItem(placeholder, None)

    def _on_room_changed(self, _idx):
        # Containers for the selected room
        rid = self.room_combo.currentData()
        self.container_combo.blockSignals(True)
        self.container_combo.clear()
        self.container_combo.addItem("-- Select Container --", None)
        if rid:
            with self.db_manager.session_scope() as s:
                containers = s.execute(
                    select(Container).where(Container.position.has(site_location_id=rid)).order_by(Container.name.asc())
                ).scalars().all()
            for c in containers:
                self.container_combo.addItem(c.name or f"Container {c.id}", c.id)
        self.container_combo.blockSignals(False)

        # Clear deeper levels
        self._reset_deeper_levels(from_combo="container")

    def _on_container_changed(self, _idx):
        cid = self.container_combo.currentData()
        self.shelf_combo.blockSignals(True)
        self.shelf_combo.clear()
        self.shelf_combo.addItem("-- Select Shelf --", None)
        if cid:
            with self.db_manager.session_scope() as s:
                shelves = s.execute(
                    select(Shelf).where(Shelf.container_id == cid).order_by(Shelf.id.asc())
                ).scalars().all()
            for sh in shelves:
                self.shelf_combo.addItem(sh.label or f"Shelf {sh.id}", sh.id)
        self.shelf_combo.blockSignals(False)
        self._reset_deeper_levels(from_combo="shelf")

    def _on_shelf_changed(self, _idx):
        sid = self.shelf_combo.currentData()
        self.drawer_combo.blockSignals(True)
        self.drawer_combo.clear()
        self.drawer_combo.addItem("-- Select Drawer --", None)
        if sid:
            with self.db_manager.session_scope() as s:
                drawers = s.execute(
                    select(Drawer).where(Drawer.shelf_id == sid).order_by(Drawer.id.asc())
                ).scalars().all()
            for dr in drawers:
                self.drawer_combo.addItem(dr.label or f"Drawer {dr.id}", dr.id)
        self.drawer_combo.blockSignals(False)
        self._reset_deeper_levels(from_combo="drawer")

    def _on_drawer_changed(self, _idx):
        did = self.drawer_combo.currentData()
        self.slot_combo.blockSignals(True)
        self.slot_combo.clear()
        self.slot_combo.addItem("-- Select Slot --", None)
        if did:
            with self.db_manager.session_scope() as s:
                slots = s.execute(
                    select(DrawerSlot).where(DrawerSlot.drawer_id == did).order_by(DrawerSlot.id.asc())
                ).scalars().all()
            for sl in slots:
                label = sl.slot_label or (
                    f"R{sl.row_index:02d}-C{sl.col_index:02d}"
                    if getattr(sl, "row_index", None) is not None and getattr(sl, "col_index", None) is not None
                    else f"Slot {sl.id}"
                )
                self.slot_combo.addItem(label, sl.id)
        self.slot_combo.blockSignals(False)

    def _reset_deeper_levels(self, from_combo: str):
        """Clear combos deeper than the given level name."""
        if from_combo in ("container",):
            self.shelf_combo.clear();  self.shelf_combo.addItem("-- Select Shelf --", None)
            self.drawer_combo.clear(); self.drawer_combo.addItem("-- Select Drawer --", None)
            self.slot_combo.clear();   self.slot_combo.addItem("-- Select Slot --", None)
        elif from_combo in ("shelf",):
            self.drawer_combo.clear(); self.drawer_combo.addItem("-- Select Drawer --", None)
            self.slot_combo.clear();   self.slot_combo.addItem("-- Select Slot --", None)
        elif from_combo in ("drawer",):
            self.slot_combo.clear();   self.slot_combo.addItem("-- Select Slot --", None)

    # ----------------------------
    # Save logic
    # ----------------------------
    def _collect_part_fields(self):
        """Return dict or None if invalid."""
        sku = self.sku_edit.text().strip()
        name = self.name_edit.text().strip()
        oem = (self.oem_edit.text() or "").strip() or None
        model = (self.model_edit.text() or "").strip() or None
        class_flag = (self.class_edit.text() or "").strip() or None

        if not sku or not name:
            QMessageBox.warning(self, "Invalid", "Part Number (SKU) and Part Name are required.")
            return None

        qty = int(self.qty_spin.value() or 0)
        unit = (self.unit_edit.text() or "").strip() or None

        return {
            "sku": sku, "name": name, "oem": oem, "model": model, "class_flag": class_flag,
            "qty": qty, "unit": unit
        }

    def _collect_location_ids(self):
        """Collect selected location ids; returns tuple (room_id, container_id, shelf_id, drawer_id, slot_id)."""
        return (
            self.room_combo.currentData(),
            self.container_combo.currentData(),
            self.shelf_combo.currentData(),
            self.drawer_combo.currentData(),
            self.slot_combo.currentData(),
        )

    def _validate_stock_requirements(self, qty: int) -> bool:
        """If qty>0, require at least a Container selection."""
        if qty <= 0:
            return True
        room_id, container_id, *_ = self._collect_location_ids()
        if not container_id:
            QMessageBox.warning(
                self, "Location Required",
                "Initial Quantity was entered; please select a Room and Container (and deeper levels if applicable)."
            )
            return False
        return True

    def _save_part_and_optional_stock(self, fields: dict):
        """
        Create the Part, and if qty>0, create initial Inventory at the selected location.
        If an inventory row already exists for the same (part+location), merge by increasing quantity.
        """
        request_id = set_request_id()
        try:
            with self.db_manager.session_scope() as s:
                # (1) Enforce unique SKU if you want (optional)
                existing = s.execute(
                    select(Part).where(Part.part_number == fields["sku"])
                ).scalar_one_or_none()
                if existing:
                    QMessageBox.warning(self, "Duplicate SKU", f"Part Number '{fields['sku']}' already exists.")
                    return False

                # (2) Create Part
                p = Part(
                    part_number=fields["sku"],
                    name=fields["name"],
                    oem_mfg=fields["oem"],
                    model=fields["model"],
                    class_flag=fields["class_flag"],
                )
                s.add(p)
                s.flush()  # get p.id
                info_id(f"[AddPartDialog] Created Part id={p.id} sku={p.part_number} name={p.name}", request_id)

                # (3) If qty > 0, create/merge Inventory at location
                qty = fields["qty"]
                if qty > 0:
                    if not self._validate_stock_requirements(qty):
                        s.rollback()
                        return False

                    _room_id, container_id, shelf_id, drawer_id, slot_id = self._collect_location_ids()

                    # Try to merge with an existing row for same location
                    inv = s.execute(
                        select(Inventory).where(
                            Inventory.part_id == p.id,
                            Inventory.container_id == container_id,
                            Inventory.shelf_id == shelf_id,
                            Inventory.drawer_id == drawer_id,
                            Inventory.drawer_slot_id == slot_id,
                        )
                    ).scalar_one_or_none()

                    now = datetime.now()
                    if inv:
                        inv.quantity = int(inv.quantity or 0) + qty
                        if fields["unit"]:
                            inv.unit = fields["unit"]
                        inv.updated_at = now
                        info_id(f"[AddPartDialog] Merged initial stock +{qty} into inv#{inv.id}", request_id)
                    else:
                        inv = Inventory(
                            part_id=p.id,
                            container_id=container_id,
                            shelf_id=shelf_id,
                            drawer_id=drawer_id,
                            drawer_slot_id=slot_id,
                            quantity=qty,
                            unit=fields["unit"],
                            updated_at=now,
                        )
                        s.add(inv)
                        info_id(f"[AddPartDialog] Created initial stock row for part#{p.id}", request_id)

                s.commit()
                return True
        except Exception as e:
            error_id(f"[AddPartDialog._save_part_and_optional_stock] {e}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to add part:\n{e!r}")
            return False

    # ----------------------------
    # Button handlers
    # ----------------------------
    def _on_add_and_close(self):
        fields = self._collect_part_fields()
        if not fields:
            return
        if self._save_part_and_optional_stock(fields):
            self.accept()

    def _on_add_and_continue(self):
        fields = self._collect_part_fields()
        if not fields:
            return
        if self._save_part_and_optional_stock(fields):
            # Clear for next
            self._reset_form_fields()

    def _reset_form_fields(self):
        self.sku_edit.clear()
        self.name_edit.clear()
        self.oem_edit.clear()
        self.model_edit.clear()
        self.class_edit.clear()
        self.qty_spin.setValue(0)
        self.unit_edit.clear()
        self._prime_location_dropdowns()
        self.sku_edit.setFocus()

class PartLocationsDialog(QDialog):
    """Dialog to manage stock for a specific Part (with editable locations)."""

    def __init__(self, parent, db_manager, part_id):
        super().__init__(parent)
        self.db_manager = db_manager
        self.part_id = part_id
        self.setWindowTitle("Manage Part Locations")
        self.setMinimumWidth(800)

        self._building_dropdowns = False
        self.setup_ui()
        self._prime_dropdowns()
        self.refresh_table()

    # -------------------------
    # UI Setup
    # -------------------------
    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QGridLayout()
        self.room_combo = QComboBox()
        self.container_combo = QComboBox()
        self.shelf_combo = QComboBox()
        self.drawer_combo = QComboBox()
        self.slot_combo = QComboBox()

        form.addWidget(QLabel("Room:"), 0, 0)
        form.addWidget(self.room_combo, 0, 1)
        form.addWidget(QLabel("Container:"), 0, 2)
        form.addWidget(self.container_combo, 0, 3)
        form.addWidget(QLabel("Shelf:"), 1, 0)
        form.addWidget(self.shelf_combo, 1, 1)
        form.addWidget(QLabel("Drawer:"), 1, 2)
        form.addWidget(self.drawer_combo, 1, 3)
        form.addWidget(QLabel("Slot:"), 2, 0)
        form.addWidget(self.slot_combo, 2, 1)
        layout.addLayout(form)

        # Stock table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Location", "Quantity", "Unit", "Last Updated"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_row_selected)  # NEW
        layout.addWidget(self.table)

        # Buttons
        btns = QHBoxLayout()
        self.add_btn = QPushButton("Add Stock")
        self.delete_btn = QPushButton("Delete Stock")
        self.update_btn = QPushButton("Update Location")
        self.close_btn = QPushButton("Close")
        btns.addWidget(self.add_btn)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.update_btn)
        btns.addStretch()
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

        # Signals
        self.add_btn.clicked.connect(self.add_stock)
        self.delete_btn.clicked.connect(self.delete_stock)
        self.update_btn.clicked.connect(self.update_location)
        self.close_btn.clicked.connect(self.reject)

        # Cascade dropdown signals
        self.room_combo.currentIndexChanged.connect(self._on_room_changed)
        self.container_combo.currentIndexChanged.connect(self._on_container_changed)
        self.shelf_combo.currentIndexChanged.connect(self._on_shelf_changed)
        self.drawer_combo.currentIndexChanged.connect(self._on_drawer_changed)

        # Location buttons
        loc_btns = QHBoxLayout()
        self.add_loc_btn = QPushButton("Add Location")
        self.del_loc_btn = QPushButton("Delete Location")
        loc_btns.addWidget(self.add_loc_btn)
        loc_btns.addWidget(self.del_loc_btn)
        layout.addLayout(loc_btns)

        # Location signals
        self.add_loc_btn.clicked.connect(self.add_location)
        self.del_loc_btn.clicked.connect(self.delete_location)

        self.add_loc_btn = QPushButton("Add Part to Location")
        btns.addWidget(self.add_loc_btn)
        self.add_loc_btn.clicked.connect(self.add_part_location)

    # -------------------------
    # Helpers
    # -------------------------
    def _get_current_id(self, combo: QComboBox):
        """Return the DB id stored in current combo item (or None)."""
        data = combo.currentData()
        return int(data) if data is not None else None

    # -------------------------
    # Update Location Logic
    # -------------------------
    def update_location(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Update", "Select a stock row first.")
            return

        inv_id_item = self.table.item(row, 0)
        if not inv_id_item:
            return
        inv_id = int(inv_id_item.text())

        # Validation: require at least Room + Container
        if not self._get_current_id(self.room_combo) or not self._get_current_id(self.container_combo):
            QMessageBox.warning(
                self,
                "Invalid Location",
                "Please select at least a Room and a Container before updating."
            )
            return

        with self.db_manager.session_scope() as s:
            inv = s.get(Inventory, inv_id)
            if not inv:
                QMessageBox.warning(self, "Update", "Inventory record not found.")
                return

            # Apply new dropdown selections
            inv.container_id = self._get_current_id(self.container_combo)
            inv.shelf_id = self._get_current_id(self.shelf_combo)
            inv.drawer_id = self._get_current_id(self.drawer_combo)
            inv.drawer_slot_id = self._get_current_id(self.slot_combo)

            s.commit()

        self.refresh_table()
        QMessageBox.information(self, "Updated", "Location updated successfully.")

    # -------------------------
    # Dropdown priming
    # -------------------------
    def _prime_dropdowns(self):
        request_id = set_request_id()
        info_id("[PartLocationsDialog] prime dropdowns", request_id)

        with self.db_manager.session_scope() as s:
            rooms = s.execute(select(SiteLocation).order_by(SiteLocation.title)).scalars().all()
        self.room_combo.clear()
        self.room_combo.addItem("-- Select Room --", None)
        for r in rooms:
            self.room_combo.addItem(r.title, r.id)

    def _on_row_selected(self):
        """Auto-select dropdowns when a row is clicked."""
        row = self.table.currentRow()
        if row < 0:
            return
        inv_id_item = self.table.item(row, 0)
        if not inv_id_item:
            return
        inv_id = int(inv_id_item.text())

        with self.db_manager.session_scope() as s:
            inv = s.get(Inventory, inv_id)
            if not inv:
                return

            # Prefill by triggering cascades
            if inv.container and inv.container.position and inv.container.position.site_location_id:
                self._select_combo(self.room_combo, inv.container.position.site_location_id)
                self._on_room_changed(self.room_combo.currentIndex())
            if inv.container_id:
                self._select_combo(self.container_combo, inv.container_id)
                self._on_container_changed(self.container_combo.currentIndex())
            if inv.shelf_id:
                self._select_combo(self.shelf_combo, inv.shelf_id)
                self._on_shelf_changed(self.shelf_combo.currentIndex())
            if inv.drawer_id:
                self._select_combo(self.drawer_combo, inv.drawer_id)
                self._on_drawer_changed(self.drawer_combo.currentIndex())
            if inv.drawer_slot_id:
                self._select_combo(self.slot_combo, inv.drawer_slot_id)

    def _on_room_changed(self, idx):
        rid = self.room_combo.itemData(idx)
        self.container_combo.clear()
        self.container_combo.addItem("-- Select Container --", None)
        if not rid:
            return
        with self.db_manager.session_scope() as s:
            containers = s.execute(
                select(Container).where(Container.position.has(site_location_id=rid))
            ).scalars().all()
        for c in containers:
            self.container_combo.addItem(c.name or f"Container {c.id}", c.id)
        self._on_container_changed(self.container_combo.currentIndex())

    def _on_container_changed(self, idx):
        cid = self.container_combo.itemData(idx)
        self.shelf_combo.clear()
        self.shelf_combo.addItem("-- Select Shelf --", None)
        if not cid:
            return
        with self.db_manager.session_scope() as s:
            shelves = s.execute(
                select(Shelf).where(Shelf.container_id == cid)
            ).scalars().all()
        for sh in shelves:
            # Use name if available, else id
            label = getattr(sh, "name", None) or getattr(sh, "description", None) or f"Shelf {sh.id}"
            self.shelf_combo.addItem(label, sh.id)
        self._on_shelf_changed(self.shelf_combo.currentIndex())

    def _on_shelf_changed(self, idx):
        sid = self.shelf_combo.itemData(idx)
        self.drawer_combo.clear()
        self.drawer_combo.addItem("-- Select Drawer --", None)
        if not sid:
            return
        with self.db_manager.session_scope() as s:
            drawers = s.execute(
                select(Drawer).where(Drawer.shelf_id == sid)
            ).scalars().all()
        for dr in drawers:
            label = getattr(dr, "name", None) or getattr(dr, "description", None) or f"Drawer {dr.id}"
            self.drawer_combo.addItem(label, dr.id)
        self._on_drawer_changed(self.drawer_combo.currentIndex())

    def _on_drawer_changed(self, idx):
        did = self.drawer_combo.itemData(idx)
        self.slot_combo.clear()
        self.slot_combo.addItem("-- Select Slot --", None)
        if not did:
            return
        with self.db_manager.session_scope() as s:
            slots = s.execute(
                select(DrawerSlot).where(DrawerSlot.drawer_id == did)
            ).scalars().all()
        for sl in slots:
            label = getattr(sl, "slot_label", None) or f"Slot {sl.id}"
            self.slot_combo.addItem(label, sl.id)
        self.refresh_table()

    def _select_combo(self, combo: QComboBox, value):
        if value is None:
            combo.setCurrentIndex(0)
            return
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    # -------------------------
    # Stock table
    # -------------------------
    def refresh_table(self):
        request_id = set_request_id()
        debug_id("[PartLocationsDialog] refresh_table", request_id)

        with self.db_manager.session_scope() as s:
            stmt = (
                select(Inventory)
                .options(
                    joinedload(Inventory.container),
                    joinedload(Inventory.shelf),
                    joinedload(Inventory.drawer),
                    joinedload(Inventory.drawer_slot),
                )
                .where(Inventory.part_id == self.part_id)
            )
            rows = s.execute(stmt).scalars().all()

        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(rows))

        for r, inv in enumerate(rows):
            loc = self._resolve_location(inv)
            qty = str(inv.quantity or 0)
            unit = inv.unit or ""
            updated = inv.updated_at.strftime("%Y-%m-%d %H:%M") if inv.updated_at else ""
            self.table.setItem(r, 0, QTableWidgetItem(str(inv.id)))
            self.table.setItem(r, 1, QTableWidgetItem(loc))
            self.table.setItem(r, 2, QTableWidgetItem(qty))
            self.table.setItem(r, 3, QTableWidgetItem(unit))
            self.table.setItem(r, 4, QTableWidgetItem(updated))

        self.table.setSortingEnabled(True)

    def _resolve_location(self, inv):
        parts = []
        if inv.container:
            parts.append(inv.container.name or f"C{inv.container.id}")
        if inv.shelf:
            parts.append(
                getattr(inv.shelf, "name", None) or getattr(inv.shelf, "description", None) or f"S{inv.shelf.id}")
        if inv.drawer:
            parts.append(
                getattr(inv.drawer, "name", None) or getattr(inv.drawer, "description", None) or f"D{inv.drawer.id}")
        if inv.drawer_slot:
            parts.append(inv.drawer_slot.slot_label or f"Slot{inv.drawer_slot.id}")
        return " → ".join(parts) if parts else "(unassigned)"

    def add_stock(self):
        rid = self.room_combo.currentData()
        cid = self.container_combo.currentData()
        sid = self.shelf_combo.currentData()
        did = self.drawer_combo.currentData()
        slid = self.slot_combo.currentData()

        if not cid:
            QMessageBox.warning(self, "Invalid Location", "Please select at least a Container.")
            return

        # Ask for quantity
        qty, ok = QInputDialog.getInt(self, "Quantity", "Enter quantity:", 1, 1, 100000, 1)
        if not ok:
            return

        # Ask for unit
        unit, ok = QInputDialog.getText(self, "Unit", "Enter unit:", text="ea")
        if not ok or not unit.strip():
            return

        with self.db_manager.session_scope() as s:
            stmt = select(Inventory).where(
                Inventory.part_id == self.part_id,
                Inventory.container_id == cid,
                Inventory.shelf_id == sid,
                Inventory.drawer_id == did,
                Inventory.drawer_slot_id == slid,
            )
            inv = s.execute(stmt).scalar_one_or_none()
            if inv:
                inv.quantity += qty
                inv.unit = unit
            else:
                inv = Inventory(
                    part_id=self.part_id,
                    container_id=cid,
                    shelf_id=sid,
                    drawer_id=did,
                    drawer_slot_id=slid,
                    quantity=qty,
                    unit=unit,
                )
                s.add(inv)
            s.commit()
        self.refresh_table()
        QMessageBox.information(self, "Added", "Stock added successfully.")

    def delete_stock(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Delete", "Select a row first.")
            return
        inv_id_item = self.table.item(row, 0)
        if not inv_id_item:
            return
        inv_id = int(inv_id_item.text())

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete stock entry ID {inv_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        with self.db_manager.session_scope() as s:
            inv = s.get(Inventory, inv_id)
            if inv:
                s.delete(inv)
            s.commit()
        self.refresh_table()
        QMessageBox.information(self, "Deleted", "Stock deleted successfully.")

    # -------------------------
    # Inline editing save
    # -------------------------
    def _save_inline_edit(self, item):
        row = item.row()
        col = item.column()
        inv_id_item = self.table.item(row, 0)
        if not inv_id_item:
            return
        inv_id = int(inv_id_item.text())

        with self.db_manager.session_scope() as s:
            inv = s.get(Inventory, inv_id)
            if not inv:
                return
            if col == 2:  # quantity
                try:
                    inv.quantity = int(item.text())
                except ValueError:
                    pass
            elif col == 3:  # unit
                inv.unit = item.text()
            s.commit()

    # -------------------------
    # Location management
    # -------------------------
    def add_location(self):
        """Add a new container/shelf/drawer/slot depending on current context."""
        if self.room_combo.currentData() and not self.container_combo.currentData():
            # Add Container
            text, ok = QInputDialog.getText(self, "New Container", "Enter container name:")
            if not ok or not text.strip():
                return
            with self.db_manager.session_scope() as s:
                c = Container(name=text.strip(), position_id=None)  # adjust if your Container links to Position
                s.add(c)
                s.commit()
            self._on_room_changed(self.room_combo.currentIndex())
            QMessageBox.information(self, "Added", f"Container '{text}' added.")

        elif self.container_combo.currentData() and not self.shelf_combo.currentData():
            # Add Shelf
            text, ok = QInputDialog.getText(self, "New Shelf", "Enter shelf name/description:")
            if not ok or not text.strip():
                return
            with self.db_manager.session_scope() as s:
                sh = Shelf(container_id=self.container_combo.currentData(), name=text.strip())
                s.add(sh)
                s.commit()
            self._on_container_changed(self.container_combo.currentIndex())
            QMessageBox.information(self, "Added", f"Shelf '{text}' added.")

        elif self.shelf_combo.currentData() and not self.drawer_combo.currentData():
            # Add Drawer
            text, ok = QInputDialog.getText(self, "New Drawer", "Enter drawer name/description:")
            if not ok or not text.strip():
                return
            with self.db_manager.session_scope() as s:
                dr = Drawer(shelf_id=self.shelf_combo.currentData(), name=text.strip())
                s.add(dr)
                s.commit()
            self._on_shelf_changed(self.shelf_combo.currentIndex())
            QMessageBox.information(self, "Added", f"Drawer '{text}' added.")

        elif self.drawer_combo.currentData():
            # Add Slot
            text, ok = QInputDialog.getText(self, "New Slot", "Enter slot label:")
            if not ok or not text.strip():
                return
            with self.db_manager.session_scope() as s:
                sl = DrawerSlot(drawer_id=self.drawer_combo.currentData(), slot_label=text.strip())
                s.add(sl)
                s.commit()
            self._on_drawer_changed(self.drawer_combo.currentIndex())
            QMessageBox.information(self, "Added", f"Slot '{text}' added.")

        else:
            QMessageBox.warning(self, "Invalid Context", "Select a room/container/shelf/drawer first.")

    def add_part_location(self):
        cid = self.container_combo.currentData()
        sid = self.shelf_combo.currentData()
        did = self.drawer_combo.currentData()
        slid = self.slot_combo.currentData()

        if not cid:
            QMessageBox.warning(self, "Invalid Location", "Please select at least a Container.")
            return

        qty, ok = QInputDialog.getInt(self, "Quantity", "Enter quantity:", 1, 1, 100000, 1)
        if not ok:
            return

        unit, ok = QInputDialog.getText(self, "Unit", "Enter unit:", text="ea")
        if not ok or not unit.strip():
            return

        with self.db_manager.session_scope() as s:
            inv = Inventory(
                part_id=self.part_id,
                container_id=cid,
                shelf_id=sid,
                drawer_id=did,
                drawer_slot_id=slid,
                quantity=qty,
                unit=unit,
            )
            s.add(inv)
            s.commit()

        self.refresh_table()
        QMessageBox.information(self, "Added", "New location assigned to part successfully.")


    def delete_location(self):
        """Delete selected container/shelf/drawer/slot (with confirmation)."""
        if self.slot_combo.currentData():
            lid = self.slot_combo.currentData()
            model = DrawerSlot
            label = "Slot"
        elif self.drawer_combo.currentData():
            lid = self.drawer_combo.currentData()
            model = Drawer
            label = "Drawer"
        elif self.shelf_combo.currentData():
            lid = self.shelf_combo.currentData()
            model = Shelf
            label = "Shelf"
        elif self.container_combo.currentData():
            lid = self.container_combo.currentData()
            model = Container
            label = "Container"
        else:
            QMessageBox.warning(self, "Delete Location", "Select a location first.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete", f"Delete {label} ID {lid}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        with self.db_manager.session_scope() as s:
            loc = s.get(model, lid)
            if loc:
                s.delete(loc)
            s.commit()

        # Refresh cascade
        if label == "Container":
            self._on_room_changed(self.room_combo.currentIndex())
        elif label == "Shelf":
            self._on_container_changed(self.container_combo.currentIndex())
        elif label == "Drawer":
            self._on_shelf_changed(self.shelf_combo.currentIndex())
        elif label == "Slot":
            self._on_drawer_changed(self.drawer_combo.currentIndex())

        QMessageBox.information(self, "Deleted", f"{label} deleted successfully.")


class AddStockDialog(QDialog):
    """Add or edit an Inventory row at Container/Shelf/Drawer/Slot level (with diagnostics)."""
    def __init__(self, parent, db_manager, *, preselected_part_id: int | None = None, existing_inventory_id: int | None = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.preselected_part_id = preselected_part_id
        self.existing_inventory_id = existing_inventory_id
        self.setWindowTitle("Edit Stock" if existing_inventory_id else "Add Stock")
        self.setMinimumWidth(520)
        self._signals_connected = False
        self.setup_ui()
        self.load_initial_state()

    # ---------- util: safe index set + combo dump ----------
    def safe_set_index(self, combo: QComboBox, idx: int, label: str):
        print(f"[safe_set_index] {label} idx={idx}, count={combo.count()}")
        if idx is None or idx < 0 or idx >= combo.count():
            print(f"[safe_set_index] SKIP {label}: invalid idx")
            return
        with QSignalBlocker(combo):
            combo.setCurrentIndex(idx)
        # echo the selected data
        print(f"[safe_set_index] {label} -> '{combo.currentText()}', data={combo.currentData()}")

    def dump_combo(self, combo: QComboBox, label: str, max_items: int = 10):
        n = combo.count()
        print(f"[dump_combo] {label}: count={n}")
        for i in range(min(n, max_items)):
            print(f"  [{i}] text='{combo.itemText(i)}' data={combo.itemData(i)}")
        if n > max_items:
            print(f"  ... (+{n - max_items} more)")

    def connect_cascade_signals(self):
        if not self._signals_connected:
            self.container_combo.currentIndexChanged.connect(self.load_shelves)
            self.shelf_combo.currentIndexChanged.connect(self.load_drawers)
            self.drawer_combo.currentIndexChanged.connect(self.load_slots)
            self._signals_connected = True
            print("[signals] connected")

    def disconnect_cascade_signals(self):
        if self._signals_connected:
            try:
                self.container_combo.currentIndexChanged.disconnect(self.load_shelves)
            except Exception:
                pass
            try:
                self.shelf_combo.currentIndexChanged.disconnect(self.load_drawers)
            except Exception:
                pass
            try:
                self.drawer_combo.currentIndexChanged.disconnect(self.load_slots)
            except Exception:
                pass
            self._signals_connected = False
            print("[signals] disconnected")

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Part picker
        row = QHBoxLayout()
        row.addWidget(QLabel("Part:"))
        self.part_combo = QComboBox()
        row.addWidget(self.part_combo)
        layout.addLayout(row)

        # Location group
        grp = QGroupBox("Location")
        form = QFormLayout(grp)
        self.container_combo = QComboBox()
        self.shelf_combo = QComboBox()
        self.drawer_combo = QComboBox()
        self.slot_combo = QComboBox()
        form.addRow("Container:", self.container_combo)
        form.addRow("Shelf:", self.shelf_combo)
        form.addRow("Drawer:", self.drawer_combo)
        form.addRow("Slot:", self.slot_combo)
        layout.addWidget(grp)

        # qty/unit
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Quantity:"))
        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("Enter quantity")
        self.qty_edit.setValidator(QIntValidator(1, 2_147_483_647, self))  # positive ints
        r2.addWidget(self.qty_edit)
        layout.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Unit:"))
        self.unit_edit = QLineEdit()
        r3.addWidget(self.unit_edit)
        layout.addLayout(r3)

        # buttons
        b = QHBoxLayout()
        self.ok_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        b.addWidget(self.ok_btn); b.addWidget(self.cancel_btn)
        layout.addLayout(b)

        self.ok_btn.clicked.connect(self.save)
        self.cancel_btn.clicked.connect(self.reject)

        # Connect cascade now (we may still disconnect during prefill)
        self.connect_cascade_signals()

    # ---------- Loaders (with prints) ----------
    def load_parts(self):
        print("[load_parts] start")
        with QSignalBlocker(self.part_combo):
            self.part_combo.clear()
            self.part_combo.addItem("— Select Part —", None)
            try:
                with self.db_manager.session_scope() as s:
                    parts = s.query(Part).order_by(Part.part_number).all()
                print(f"[load_parts] fetched {len(parts)} parts")
                for p in parts:
                    print(f"[load_parts] add: id={p.id} '{p.part_number} - {p.name}'")
                    self.part_combo.addItem(f"{p.part_number} - {p.name}", p.id)
            except Exception as e:
                print(f"[load_parts] ERROR: {e}")
        self.dump_combo(self.part_combo, "part_combo")

    def load_containers(self):
        print("[load_containers] start")
        with QSignalBlocker(self.container_combo):
            self.container_combo.clear()
            self.container_combo.addItem("— Select Container —", None)
            try:
                with self.db_manager.session_scope() as s:
                    rows = s.query(Container).order_by(Container.name).all()
                print(f"[load_containers] fetched {len(rows)} containers")
                for c in rows:
                    print(f"[load_containers] add: id={c.id} name='{c.name}'")
                    self.container_combo.addItem(c.name, c.id)
            except Exception as e:
                print(f"[load_containers] ERROR: {e}")
        self.dump_combo(self.container_combo, "container_combo")

    def load_shelves(self):
        cont_id = self.container_combo.currentData()
        print(f"[load_shelves] start container_id={cont_id}")
        with QSignalBlocker(self.shelf_combo):
            self.shelf_combo.clear()
            self.shelf_combo.addItem("— Select Shelf —", None)
            if not cont_id:
                self.dump_combo(self.shelf_combo, "shelf_combo (empty)")
                return
            try:
                with self.db_manager.session_scope() as s:
                    rows = s.query(Shelf).filter(Shelf.container_id == cont_id).all()
                print(f"[load_shelves] fetched {len(rows)} shelves for cont_id={cont_id}")
                for sh in rows:
                    print(f"[load_shelves] add: id={sh.id} label='{sh.label}'")
                    self.shelf_combo.addItem(sh.label, sh.id)
            except Exception as e:
                print(f"[load_shelves] ERROR: {e}")
        self.dump_combo(self.shelf_combo, "shelf_combo")

    def load_drawers(self):
        shelf_id = self.shelf_combo.currentData()
        print(f"[load_drawers] start shelf_id={shelf_id}")
        with QSignalBlocker(self.drawer_combo):
            self.drawer_combo.clear()
            self.drawer_combo.addItem("— Select Drawer —", None)
            if not shelf_id:
                self.dump_combo(self.drawer_combo, "drawer_combo (empty)")
                return
            try:
                with self.db_manager.session_scope() as s:
                    rows = s.query(Drawer).filter(Drawer.shelf_id == shelf_id).all()
                print(f"[load_drawers] fetched {len(rows)} drawers for shelf_id={shelf_id}")
                for dr in rows:
                    print(f"[load_drawers] add: id={dr.id} label='{dr.label}'")
                    self.drawer_combo.addItem(dr.label, dr.id)
            except Exception as e:
                print(f"[load_drawers] ERROR: {e}")
        self.dump_combo(self.drawer_combo, "drawer_combo")

    def load_slots(self):
        drawer_id = self.drawer_combo.currentData()
        print(f"[load_slots] start drawer_id={drawer_id}")
        with QSignalBlocker(self.slot_combo):
            self.slot_combo.clear()
            self.slot_combo.addItem("— Select Slot —", None)
            if not drawer_id:
                self.dump_combo(self.slot_combo, "slot_combo (empty)")
                return
            try:
                with self.db_manager.session_scope() as s:
                    rows = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id).all()
                print(f"[load_slots] fetched {len(rows)} slots for drawer_id={drawer_id}")
                for sl in rows:
                    lbl = (
                        sl.slot_label
                        or (f"R{sl.row_index}-C{sl.col_index}"
                            if sl.row_index is not None and sl.col_index is not None
                            else f"Slot {sl.id}")
                    )
                    print(f"[load_slots] add: id={sl.id} label='{lbl}'")
                    self.slot_combo.addItem(lbl, sl.id)
            except Exception as e:
                print(f"[load_slots] ERROR: {e}")
        self.dump_combo(self.slot_combo, "slot_combo")

    # ---------- Initial state / edit prefill (with signals disconnected) ----------
    def load_initial_state(self):
        print("[init] load_initial_state starting")
        # Disconnect cascade to avoid re-entrant storms during programmatic prefill
        self.disconnect_cascade_signals()

        # Base lists
        self.load_parts()
        self.load_containers()

        # Part preselect
        if self.preselected_part_id:
            print(f"[init] preselected_part_id={self.preselected_part_id}")
            idx = self.part_combo.findData(self.preselected_part_id)
            self.safe_set_index(self.part_combo, idx, "part_combo (preselect)")
            self.part_combo.setEnabled(False)

        # Editing case: select existing hierarchy in strict order
        if self.existing_inventory_id:
            print(f"[init] existing_inventory_id={self.existing_inventory_id}")
            try:
                with self.db_manager.session_scope() as s:
                    inv = s.get(Inventory, self.existing_inventory_id)
                if inv:
                    print(f"[init] inv: id={inv.id} qty={inv.quantity} unit={inv.unit} "
                          f"cont={inv.container_id} shelf={inv.shelf_id} "
                          f"drawer={inv.drawer_id} slot={inv.drawer_slot_id}")

                    # container -> shelves
                    if inv.container_id:
                        ci = self.container_combo.findData(inv.container_id)
                        self.safe_set_index(self.container_combo, ci, "container_combo (prefill)")
                        self.load_shelves()  # fills shelves list for that container

                    # shelf -> drawers
                    if inv.shelf_id:
                        si = self.shelf_combo.findData(inv.shelf_id)
                        self.safe_set_index(self.shelf_combo, si, "shelf_combo (prefill)")
                        self.load_drawers()

                    # drawer -> slots
                    if inv.drawer_id:
                        di = self.drawer_combo.findData(inv.drawer_id)
                        self.safe_set_index(self.drawer_combo, di, "drawer_combo (prefill)")
                        self.load_slots()

                    # slot
                    if inv.drawer_slot_id:
                        sli = self.slot_combo.findData(inv.drawer_slot_id)
                        self.safe_set_index(self.slot_combo, sli, "slot_combo (prefill)")

                    # qty/unit
                    self.qty_edit.setText(str(inv.quantity or ""))
                    self.unit_edit.setText(inv.unit or "")
            except Exception as e:
                print(f"[init] ERROR prefill: {e}")

        # Reconnect cascade signals for user interaction
        self.connect_cascade_signals()
        print("[init] load_initial_state done")

    # ---------- Save ----------
    def save(self):
        request_id = set_request_id()
        try:
            part_id = self.part_combo.currentData()
            if not part_id:
                QMessageBox.warning(self, "Invalid", "Please select a part.")
                return

            qty_txt = (self.qty_edit.text() or "").strip()
            if not qty_txt:
                QMessageBox.warning(self, "Invalid", "Quantity is required.")
                return
            try:
                qty = int(qty_txt)
            except ValueError:
                QMessageBox.warning(self, "Invalid", "Quantity must be an integer.")
                return
            if qty <= 0:
                QMessageBox.warning(self, "Invalid", "Quantity must be positive.")
                return

            unit = (self.unit_edit.text().strip() or None)

            container_id = self.container_combo.currentData()
            shelf_id = self.shelf_combo.currentData()
            drawer_id = self.drawer_combo.currentData()
            slot_id = self.slot_combo.currentData()

            with self.db_manager.session_scope() as s:
                if self.existing_inventory_id:
                    inv = s.get(Inventory, self.existing_inventory_id)
                    if not inv:
                        QMessageBox.warning(self, "Missing", "Inventory row no longer exists.")
                        return
                else:
                    inv = Inventory(part_id=part_id)
                    s.add(inv)

                inv.quantity = qty
                inv.unit = unit
                inv.container_id = container_id
                inv.shelf_id = shelf_id
                inv.drawer_id = drawer_id
                inv.drawer_slot_id = slot_id

                s.commit()

            info_id(f"Saved stock part={part_id} qty={qty}", request_id=request_id)
            self.accept()

        except Exception as e:
            error_id("Failed to save stock", exc_info=True, request_id=request_id)
            QMessageBox.critical(self, "Error", str(e))

class NewEntityDialog(QDialog):
    """Dialog for creating new entities"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Entity")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Entity type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Entity Type:"))

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Area", "Equipment Group", "Model", "Asset Number",
            "Location", "Part", "Container", "Shelf", "Drawer"
        ])
        type_layout.addWidget(self.type_combo)

        layout.addLayout(type_layout)

        # Form area
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        layout.addWidget(self.form_widget)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect type change
        self.type_combo.currentTextChanged.connect(self.setup_form_for_type)
        self.setup_form_for_type(self.type_combo.currentText())

    def setup_form_for_type(self, entity_type):
        """Setup form fields based on entity type"""
        # Clear existing form
        for i in reversed(range(self.form_layout.count())):
            child = self.form_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Add fields based on type
        if entity_type == "Area":
            self.name_edit = QLineEdit()
            self.description_edit = QTextEdit()
            self.form_layout.addRow("Name:", self.name_edit)
            self.form_layout.addRow("Description:", self.description_edit)

        # Add similar setups for other entity types

class MainWindow(QMainWindow):
    """Main application window (no Equipment Hierarchy panel)"""

    def __init__(self):
        super().__init__()
        self.db_manager = None
        self.setup_ui()
        self.setup_database()

    def setup_ui(self):
        self.setWindowTitle("ShopSync - Equipment Management System")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Full-width tabs (no splitter / no tree)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget, 1)

        # Remote Inventory tab (room → container → shelf → drawer → slot)
        # NOTE: Ensure RemoteInventoryWidget class is defined above.
        self.remote_inventory = RemoteInventoryWidget(self)
        self.tab_widget.addTab(self.remote_inventory, "Remote Inventory")

        # Search tab
        self.search_widget = SearchWidget(self)
        self.tab_widget.addTab(self.search_widget, "Search")

        #Add New Location tab
        self.add_location_widget = AddLocationWidget(self)
        self.tab_widget.addTab(self.add_location_widget, "Add New Location")

        # Details tab
        self.details_widget = EntityDetailsWidget(self)
        self.tab_widget.addTab(self.details_widget, "Details")

        # Inventory tab
        self.inventory_widget = InventoryWidget(self)
        self.tab_widget.addTab(self.inventory_widget, "Inventory")



        # Menus / toolbar / status bar
        self.create_menu_bar()
        self.create_toolbar()
        self.statusBar().showMessage("Ready")

    def create_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        new_action = QAction("New Entity", self)
        new_action.triggered.connect(self.new_entity)
        file_menu.addAction(new_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        view_menu.addAction(refresh_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        import_action = QAction("Import Data", self)
        import_action.triggered.connect(self.import_data)
        tools_menu.addAction(import_action)
        export_action = QAction("Export Data", self)
        export_action.triggered.connect(self.export_data)
        tools_menu.addAction(export_action)

    def create_toolbar(self):
        toolbar = self.addToolBar("Main")
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_entity)
        toolbar.addAction(new_action)
        toolbar.addSeparator()
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)

    def setup_database(self):
        """Initialize database connection (no hierarchy population)"""
        request_id = set_request_id()
        try:
            info_id("Initializing database connection", request_id)

            # Initialize DB manager
            self.db_manager = ShopSyncDatabase(echo=False)

            # Create tables if needed
            self.db_manager.create_all()

            # Hand DB manager to tabs that use it
            if hasattr(self, "remote_inventory"):
                self.remote_inventory.set_db_manager(self.db_manager)

            if hasattr(self, "add_location_widget"):
                self.add_location_widget.set_db_manager(self.db_manager)

            # ✅ Add this line
            if hasattr(self, "inventory_widget"):
                self.inventory_widget.set_db_manager(self.db_manager)

            # Inspect DB
            tables, counts = self.db_manager.inspect()
            info_id(f"Database connected with {len(tables)} tables", request_id)
            self.statusBar().showMessage(f"Database connected - {len(tables)} tables found")

        except Exception as e:
            error_id(f"Failed to connect to database: {str(e)}", request_id)
            QMessageBox.critical(self, "Database Error",
                                 f"Failed to connect to database: {str(e)}")
            self.statusBar().showMessage("Database connection failed")

    def show_entity_details(self, entity_type, entity_data):
        """Still available (e.g., open from Search results)."""
        self.tab_widget.setCurrentIndex(0)
        self.details_widget.show_entity_details(entity_type, entity_data)

    def new_entity(self):
        request_id = set_request_id()
        debug_id("Opening new entity dialog", request_id)
        dialog = NewEntityDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            info_id("New entity created, refreshing data", request_id)
            self.refresh_data()

    def refresh_data(self):
        """Refresh tabs (no hierarchy to refresh)."""
        request_id = set_request_id()
        info_id("Refreshing all data displays", request_id)
        if self.db_manager:
            self.inventory_widget.refresh_inventory()
            self.remote_inventory.refresh_all()
        self.statusBar().showMessage("Data refreshed")

    def import_data(self):
        request_id = set_request_id()
        debug_id("Import data requested", request_id)
        QMessageBox.information(self, "Import", "Import functionality will be implemented")

    def export_data(self):
        request_id = set_request_id()
        debug_id("Export data requested", request_id)
        QMessageBox.information(self, "Export", "Export functionality will be implemented")

    def closeEvent(self, event):
        request_id = set_request_id()
        info_id("Application closing", request_id)
        if self.db_manager:
            debug_id("Database manager cleaned up", request_id)
        event.accept()

class AddLocationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        # Slot group only shown if DrawerSlot model is available
        self._has_drawer_slot = True
        self._build_ui()
        self._wire_signals()

    def _clear_fields(self):
        self._clear_site_fields()
        self.cont_name.clear()
        self.shelf_name.clear()
        self.drawer_label.clear()
        if self._has_drawer_slot:
            self.slot_label.clear()

    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        self.refresh_all()

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)

        # --- Site Location group ---
        grp_site = QGroupBox("Site Location (Room)")
        frm_site = QFormLayout(grp_site)

        self.site_pick = QComboBox()
        self.site_pick.setEditable(True)
        self.site_pick.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self._site_completer = QCompleter(self.site_pick.model(), self.site_pick)
        self._site_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._site_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.site_pick.setCompleter(self._site_completer)

        self._site_search_timer = QTimer(self)
        self._site_search_timer.setSingleShot(True)
        self._site_search_timer.setInterval(200)
        self._site_search_timer.timeout.connect(self._perform_site_search)
        self.site_pick.lineEdit().textEdited.connect(self._on_site_text_edited)

        self.site_title = QLineEdit()
        self.site_room = QLineEdit()
        self.site_area = QLineEdit()
        self.btn_site_refresh = QPushButton("Refresh")
        self.btn_site_add = QPushButton("Add Site Location")
        frm_site.addRow("Pick Existing:", self.site_pick)
        frm_site.addRow("Title (e.g., 'Storeroom A'):", self.site_title)
        frm_site.addRow("Room Number:", self.site_room)
        frm_site.addRow("Area:", self.site_area)
        row_site_btns = QHBoxLayout()
        row_site_btns.addWidget(self.btn_site_refresh)
        row_site_btns.addWidget(self.btn_site_add)
        frm_site.addRow(row_site_btns)
        outer.addWidget(grp_site)

        # --- Container group ---
        grp_cont = QGroupBox("Container")
        frm_cont = QFormLayout(grp_cont)
        self.cont_pick = QComboBox()
        self.cont_name = QLineEdit()
        self.btn_cont_refresh = QPushButton("Refresh")
        self.btn_cont_add = QPushButton("Add Container")
        self.btn_cont_add.setEnabled(False)
        frm_cont.addRow("Pick Existing:", self.cont_pick)
        frm_cont.addRow("Name (e.g., 'Rack 12'):", self.cont_name)
        row_cont_btns = QHBoxLayout()
        row_cont_btns.addWidget(self.btn_cont_refresh)
        row_cont_btns.addWidget(self.btn_cont_add)
        frm_cont.addRow(row_cont_btns)
        outer.addWidget(grp_cont)

        # --- Shelf group ---
        grp_shelf = QGroupBox("Shelf")
        frm_shelf = QFormLayout(grp_shelf)
        self.shelf_pick = QComboBox()
        self.shelf_name = QLineEdit()
        self.btn_shelf_refresh = QPushButton("Refresh")
        self.btn_shelf_add = QPushButton("Add Shelf")
        self.btn_shelf_add.setEnabled(False)
        frm_shelf.addRow("Pick Existing:", self.shelf_pick)
        frm_shelf.addRow("Name (required):", self.shelf_name)
        row_shelf_btns = QHBoxLayout()
        row_shelf_btns.addWidget(self.btn_shelf_refresh)
        row_shelf_btns.addWidget(self.btn_shelf_add)
        frm_shelf.addRow(row_shelf_btns)
        outer.addWidget(grp_shelf)

        # --- Drawer group ---
        grp_drawer = QGroupBox("Drawer")
        frm_drawer = QFormLayout(grp_drawer)
        self.drawer_pick = QComboBox()
        self.drawer_label = QLineEdit()
        self.btn_drawer_refresh = QPushButton("Refresh")
        self.btn_drawer_add = QPushButton("Add Drawer")
        self.btn_drawer_add.setEnabled(False)
        frm_drawer.addRow("Pick Existing:", self.drawer_pick)
        frm_drawer.addRow("Label (e.g., 'Drawer 1'):", self.drawer_label)
        row_drawer_btns = QHBoxLayout()
        row_drawer_btns.addWidget(self.btn_drawer_refresh)
        row_drawer_btns.addWidget(self.btn_drawer_add)
        frm_drawer.addRow(row_drawer_btns)
        outer.addWidget(grp_drawer)

        # --- Slot group ---
        self.grp_slot = QGroupBox("Slot")
        frm_slot = QFormLayout(self.grp_slot)
        self.slot_pick = QComboBox()
        self.slot_label = QLineEdit()
        self.btn_slot_refresh = QPushButton("Refresh")
        self.btn_slot_add = QPushButton("Add Slot")
        self.btn_slot_add.setEnabled(False)
        frm_slot.addRow("Pick Existing:", self.slot_pick)
        frm_slot.addRow("Label (e.g., 'R1-C3' or 'Bin A'):", self.slot_label)
        row_slot_btns = QHBoxLayout()
        row_slot_btns.addWidget(self.btn_slot_refresh)
        row_slot_btns.addWidget(self.btn_slot_add)
        frm_slot.addRow(row_slot_btns)
        if self._has_drawer_slot:
            outer.addWidget(self.grp_slot)
        else:
            self.grp_slot.setVisible(False)

        # Footer
        foot = QHBoxLayout()
        self.btn_refresh_all = QPushButton("Refresh All")
        self.btn_clear_fields = QPushButton("Clear Fields")
        foot.addWidget(self.btn_refresh_all)
        foot.addWidget(self.btn_clear_fields)
        foot.addStretch()
        outer.addLayout(foot)

    def _wire_signals(self):
        self.btn_site_refresh.clicked.connect(self._load_sites)
        self.btn_cont_refresh.clicked.connect(self._load_containers)
        self.btn_shelf_refresh.clicked.connect(self._load_shelves)
        self.btn_drawer_refresh.clicked.connect(self._load_drawers)
        self.btn_slot_refresh.clicked.connect(self._load_slots)

        self.btn_refresh_all.clicked.connect(self.refresh_all)
        self.btn_clear_fields.clicked.connect(self._clear_fields)

        self.btn_site_add.clicked.connect(self._add_site)
        self.btn_cont_add.clicked.connect(self._add_container)
        self.btn_shelf_add.clicked.connect(self._add_shelf)
        self.btn_drawer_add.clicked.connect(self._add_drawer)
        self.btn_slot_add.clicked.connect(self._add_slot)

        self.site_pick.currentIndexChanged.connect(self._on_site_changed)
        self.cont_pick.currentIndexChanged.connect(self._on_container_changed)
        self.shelf_pick.currentIndexChanged.connect(self._on_shelf_changed)
        self.drawer_pick.currentIndexChanged.connect(self._on_drawer_changed)

    # ---------- Public ----------
    def refresh_all(self):
        if not self.db_manager:
            return
        self._load_sites()
        self._load_containers()
        self._load_shelves()
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._update_buttons_enabled()

    # ---------- Loaders ----------
    def _load_sites(self):
        self.site_pick.clear()
        if not self.db_manager:
            return
        query = ""
        if self.site_pick.isEditable():
            query = (self.site_pick.lineEdit().text() or "").strip()
        self._search_and_fill_sites(query=query)

    def _load_containers(self):
        self.cont_pick.clear()
        if not self.db_manager:
            return
        site_id = self._current_id(self.site_pick)
        if not site_id:
            return
        from app.modules.database.shopsync_db import Container
        with self.db_manager.session_scope() as s:
            containers = s.query(Container).filter(
                Container.position.has(site_location_id=site_id)
            ).order_by(Container.name.asc()).all()
        for c in containers:
            self.cont_pick.addItem(c.name or f"Container {c.id}", c.id)
        self._update_buttons_enabled()

    def _load_shelves(self):
        self.shelf_pick.clear()
        if not self.db_manager:
            return
        cont_id = self._current_id(self.cont_pick)
        if not cont_id:
            return
        from app.modules.database.shopsync_db import Shelf
        with self.db_manager.session_scope() as s:
            shelves = s.query(Shelf).filter(Shelf.container_id == cont_id).order_by(Shelf.id.asc()).all()
        for sh in shelves:
            self.shelf_pick.addItem(sh.name or f"Shelf {sh.id}", sh.id)
        self._update_buttons_enabled()

    def _load_drawers(self):
        self.drawer_pick.clear()
        if not self.db_manager:
            return
        shelf_id = self._current_id(self.shelf_pick)
        if not shelf_id:
            return
        from app.modules.database.shopsync_db import Drawer
        with self.db_manager.session_scope() as s:
            drawers = s.query(Drawer).filter(Drawer.shelf_id == shelf_id).order_by(Drawer.id.asc()).all()
        for dr in drawers:
            self.drawer_pick.addItem(dr.name or f"Drawer {dr.id}", dr.id)
        self._update_buttons_enabled()

    def _load_slots(self):
        if not self._has_drawer_slot:
            return
        self.slot_pick.clear()
        if not self.db_manager:
            return
        drawer_id = self._current_id(self.drawer_pick)
        if not drawer_id:
            return
        from app.modules.database.shopsync_db import DrawerSlot
        with self.db_manager.session_scope() as s:
            slots = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id).order_by(DrawerSlot.id.asc()).all()
        for sl in slots:
            label = sl.slot_label or f"Slot {sl.id}"
            self.slot_pick.addItem(label, sl.id)
        self._update_buttons_enabled()

    # ---------- Create ops ----------
    def _add_site(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import SiteLocation
        request_id = set_request_id()

        title = self.site_title.text().strip()
        room = self.site_room.text().strip()
        area = self.site_area.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Data", "Please enter a Site Location title.")
            return

        try:
            with self.db_manager.session_scope() as s:
                existing = s.query(SiteLocation).filter(
                    SiteLocation.title == title,
                    SiteLocation.room_number == (room or None),
                    SiteLocation.site_area == (area or None)
                ).first()
                if existing:
                    QMessageBox.information(self, "Duplicate", "Site Location already exists.")
                    return
                obj = SiteLocation(title=title, room_number=room or None, site_area=area or None)
                s.add(obj)
                s.flush()
                info_id(f"[AddLocation] Created SiteLocation id={obj.id}", request_id=request_id)
            self._clear_site_fields()
            self._load_sites()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create SiteLocation: {e}", request_id=request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Site Location:\n{e}")

    def _add_container(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Container, Position, StorageAddress
        request_id = set_request_id()

        site_id = self._current_id(self.site_pick)
        name = (self.cont_name.text() or "").strip()

        if not site_id:
            QMessageBox.warning(self, "Select Site", "Pick a Site Location first.")
            return
        if not name:
            QMessageBox.warning(self, "Missing Data", "Please enter a Container name.")
            return

        try:
            with self.db_manager.session_scope() as s:
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()

                existing = s.query(Container).filter(Container.position_id == pos.id, Container.name == name).first()
                if existing:
                    QMessageBox.information(self, "Duplicate", "Container already exists.")
                    return

                obj = Container(position_id=pos.id, name=name)
                s.add(obj)
                s.flush()
                StorageAddress.upsert_for_container(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created Container id={obj.id}", request_id=request_id)

            self.cont_name.clear()
            self._load_containers()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Container: {e}", request_id=request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Container:\n{e}")

    def _add_shelf(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Shelf, Position, StorageAddress
        request_id = set_request_id()

        cont_id = self._current_id(self.cont_pick)
        name = (self.shelf_name.text() or "").strip()
        site_id = self._current_id(self.site_pick)

        if not cont_id:
            QMessageBox.warning(self, "Select Container", "Pick a Container first.")
            return
        if not name:
            QMessageBox.warning(self, "Missing Data", "Shelf 'Name' is required.")
            return

        try:
            with self.db_manager.session_scope() as s:
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()

                existing = s.query(Shelf).filter(Shelf.container_id == cont_id, Shelf.name == name).first()
                if existing:
                    QMessageBox.information(self, "Duplicate", "Shelf already exists.")
                    return

                obj = Shelf(position_id=pos.id, name=name, container_id=cont_id)
                s.add(obj)
                s.flush()
                StorageAddress.upsert_for_shelf(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created Shelf id={obj.id}", request_id=request_id)

            self.shelf_name.clear()
            self._load_shelves()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Shelf: {e}", request_id=request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Shelf:\n{e}")

    def _add_drawer(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Drawer, Position, StorageAddress
        request_id = set_request_id()

        shelf_id = self._current_id(self.shelf_pick)
        name = self.drawer_label.text().strip()
        site_id = self._current_id(self.site_pick)

        if not shelf_id:
            QMessageBox.warning(self, "Select Shelf", "Pick a Shelf first.")
            return
        if not name:
            QMessageBox.warning(self, "Missing Data", "Please enter a Drawer label.")
            return

        try:
            with self.db_manager.session_scope() as s:
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()

                existing = s.query(Drawer).filter(Drawer.shelf_id == shelf_id, Drawer.name == name).first()
                if existing:
                    QMessageBox.information(self, "Duplicate", "Drawer already exists.")
                    return

                obj = Drawer(position_id=pos.id, name=name, shelf_id=shelf_id)
                s.add(obj)
                s.flush()
                StorageAddress.upsert_for_drawer(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created Drawer id={obj.id}", request_id=request_id)

            self.drawer_label.clear()
            self._load_drawers()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Drawer: {e}", request_id=request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Drawer:\n{e}")

    def _add_slot(self):
        if not self._has_drawer_slot:
            return
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Drawer, DrawerSlot, StorageAddress
        request_id = set_request_id()

        drawer_id = self._current_id(self.drawer_pick)
        label = self.slot_label.text().strip()
        if not drawer_id:
            QMessageBox.warning(self, "Select Drawer", "Pick a Drawer first.")
            return
        if not label:
            QMessageBox.warning(self, "Missing Data", "Please enter a Slot label.")
            return

        try:
            with self.db_manager.session_scope() as s:
                drawer = s.get(Drawer, drawer_id)
                if not drawer:
                    QMessageBox.critical(self, "Error", f"Drawer {drawer_id} not found.")
                    return

                existing = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id, DrawerSlot.slot_label == label).first()
                if existing:
                    QMessageBox.information(self, "Duplicate", "Slot already exists.")
                    return

                obj = DrawerSlot(drawer_id=drawer_id, slot_label=label)
                s.add(obj)
                s.flush()
                StorageAddress.upsert_for_slot(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created Slot id={obj.id}", request_id=request_id)

            self.slot_label.clear()
            self._load_slots()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Slot: {e}", request_id=request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Slot:\n{e}")

    # ---------- Helpers ----------
    def _current_id(self, combo: QComboBox):
        idx = combo.currentIndex()
        return combo.itemData(idx) if idx >= 0 else None

    def _clear_site_fields(self):
        self.site_title.clear()
        self.site_room.clear()
        self.site_area.clear()

    def _on_site_changed(self, _):
        self._load_containers()
        self._load_shelves()
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._update_buttons_enabled()

    def _on_container_changed(self, idx):
        self._load_shelves()

    def _on_shelf_changed(self, _):
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._update_buttons_enabled()

    def _on_drawer_changed(self, _):
        if self._has_drawer_slot:
            self._load_slots()
        self._update_buttons_enabled()

    def _update_buttons_enabled(self):
        site_ok = self._current_id(self.site_pick) is not None or self.site_pick.count() > 0
        cont_ok = self._current_id(self.cont_pick) is not None
        shelf_ok = self._current_id(self.shelf_pick) is not None
        drawer_ok = self._current_id(self.drawer_pick) is not None

        self.btn_cont_add.setEnabled(bool(site_ok))
        self.btn_shelf_add.setEnabled(bool(cont_ok))
        self.btn_drawer_add.setEnabled(bool(shelf_ok))
        if self._has_drawer_slot:
            self.btn_slot_add.setEnabled(bool(drawer_ok))

    def _notify_inventory_refresh(self):
        mw = self.parent()
        while mw and not isinstance(mw, QMainWindow):
            mw = mw.parent()
        if mw and hasattr(mw, "remote_inventory"):
            mw.remote_inventory.refresh_all()

    def _on_site_text_edited(self, text: str):
        self._site_search_timer.start()

    def _perform_site_search(self):
        if not self.db_manager:
            return
        query = self.site_pick.lineEdit().text().strip()
        self._search_and_fill_sites(query)

    def _search_and_fill_sites(self, query: str):
        from app.modules.database.shopsync_db import SiteLocation
        self.site_pick.blockSignals(True)
        try:
            current_text = self.site_pick.lineEdit().text()
            with self.db_manager.session_scope() as s:
                stmt = (
                    select(
                        SiteLocation.id,
                        SiteLocation.title,
                        SiteLocation.room_number,
                        SiteLocation.site_area,
                    )
                    .where(
                        or_(
                            SiteLocation.title.ilike(f"%{query}%"),
                            SiteLocation.room_number.ilike(f"%{query}%"),
                            SiteLocation.site_area.ilike(f"%{query}%"),
                        )
                    )
                    .order_by(SiteLocation.title.asc())
                    .limit(50)
                )
                rows = s.execute(stmt).all()
            self.site_pick.clear()
            if not rows:
                self.site_pick.addItem("— no matches —", None)
            else:
                for pid, title, room, area in rows:
                    self.site_pick.addItem(f"{title} (Room {room or '-'}, {area or '-'})", pid)
            self.site_pick.lineEdit().setText(current_text)
            if self.site_pick.count() > 0:
                self.site_pick.showPopup()
        finally:
            self.site_pick.blockSignals(False)
            self._update_buttons_enabled()

class RemoteInventoryWidget(QWidget):
    """
    Remote inventory workflow:
    Room (SiteLocation) -> Container -> Shelf -> Drawer -> Slot
    Shows structure summary in right-hand panel and parts in table.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        self._has_drawer_slot = 'DrawerSlot' in globals()

        self._build_ui()
        self._wire_signals()

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)

        # Top: search for room
        search_row = QHBoxLayout()
        self.room_search = QLineEdit()
        self.room_search.setPlaceholderText("Search room (title / room number / area)…")
        self.room_btn = QPushButton("Search")
        search_row.addWidget(QLabel("Room:"))
        search_row.addWidget(self.room_search, 1)
        search_row.addWidget(self.room_btn)
        outer.addLayout(search_row)

        # Dropdowns + summary panel
        top_split = QHBoxLayout()
        form = QFormLayout()

        self.room_combo = QComboBox()
        self.container_combo = QComboBox()
        self.shelf_combo = QComboBox()
        self.drawer_combo = QComboBox()
        self.slot_combo = QComboBox()

        form.addRow("Select Room:", self.room_combo)
        form.addRow("Container:", self.container_combo)
        form.addRow("Shelf:", self.shelf_combo)
        form.addRow("Drawer:", self.drawer_combo)
        if self._has_drawer_slot:
            form.addRow("Slot:", self.slot_combo)

        top_split.addLayout(form, 2)

        # Summary panel
        self.summary_group = QGroupBox("Selected Info")
        self.summary_label = QLabel("No selection")
        self.summary_label.setWordWrap(True)
        summ_layout = QVBoxLayout(self.summary_group)
        summ_layout.addWidget(self.summary_label)
        top_split.addWidget(self.summary_group, 1)

        outer.addLayout(top_split)

        # Contents table
        self.contents = QTableWidget()
        self.contents.setColumnCount(6)
        self.contents.setHorizontalHeaderLabels(
            ["Level", "ID", "Name/Number", "Type", "Qty / Unit", "Last Updated"]
        )
        self.contents.horizontalHeader().setStretchLastSection(True)
        self.contents.setSortingEnabled(True)
        header = self.contents.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        outer.addWidget(QLabel("Contents"))
        outer.addWidget(self.contents, 1)

        # Footer actions
        foot = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.clear_btn = QPushButton("Clear Selections")
        foot.addWidget(self.refresh_btn)
        foot.addWidget(self.clear_btn)
        foot.addStretch()
        outer.addLayout(foot)

    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        self.refresh_all()

    def _wire_signals(self):
        self.room_btn.clicked.connect(self.search_rooms)
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.clear_btn.clicked.connect(self.clear_all)

        self.room_combo.currentIndexChanged.connect(self._on_room_changed)
        self.container_combo.currentIndexChanged.connect(self._on_container_changed)
        self.shelf_combo.currentIndexChanged.connect(self._on_shelf_changed)
        self.drawer_combo.currentIndexChanged.connect(self._on_drawer_changed)
        if self._has_drawer_slot:
            self.slot_combo.currentIndexChanged.connect(self._on_slot_changed)

    # ---------- Data loaders ----------
    @with_request_id
    def refresh_all(self):
        request_id = set_request_id()
        info_id("[RemoteInventory] refresh_all starting", request_id)

        if not self.db_manager:
            warning_id("[RemoteInventory] refresh_all called with no db_manager", request_id)
            return

        try:
            self._load_rooms()
            self._load_containers()
            self._load_shelves()
            self._load_drawers()
            if self._has_drawer_slot:
                self._load_slots()
            self._refresh_contents()
            info_id("[RemoteInventory] refresh_all complete", request_id)
        except Exception as e:
            error_id(f"[RemoteInventory.refresh_all] error: {e!r}", request_id)
            raise

    def clear_all(self):
        self.room_search.clear()
        for combo in (self.room_combo, self.container_combo, self.shelf_combo, self.drawer_combo, self.slot_combo):
            combo.clear()
        self.contents.setRowCount(0)
        self.summary_label.setText("No selection")

    def search_rooms(self):
        """Filter SiteLocations by title / room_number / site_area"""
        if not self.db_manager:
            return
        text = self.room_search.text().strip()
        request_id = set_request_id()
        self.room_combo.clear()
        self.room_combo.addItem("-- Select Room --", None)

        with self.db_manager.session_scope() as s:
            q = s.query(SiteLocation)
            if text:
                like = f"%{text}%"
                q = q.filter(
                    (SiteLocation.title.ilike(like)) |
                    (SiteLocation.room_number.ilike(like)) |
                    (SiteLocation.site_area.ilike(like))
                )
            rooms = q.order_by(SiteLocation.title.asc(), SiteLocation.room_number.asc()).all()

        for r in rooms:
            self.room_combo.addItem(f"{r.title} (Room {r.room_number}, {r.site_area})", r.id)

    def _load_rooms(self):
        self.room_combo.clear()
        self.room_combo.addItem("-- Select Room --", None)
        with self.db_manager.session_scope() as s:
            rooms = s.query(SiteLocation).order_by(SiteLocation.title.asc()).limit(100).all()
        for r in rooms:
            self.room_combo.addItem(f"{r.title} (Room {r.room_number}, {r.site_area})", r.id)

    def _load_containers(self):
        self.container_combo.clear()
        self.container_combo.addItem("-- Select Container --", None)
        room_id = self._current_id(self.room_combo)
        if not room_id:
            return
        with self.db_manager.session_scope() as s:
            containers = s.query(Container).filter(
                Container.position.has(site_location_id=room_id)
            ).order_by(Container.name.asc()).all()
        for c in containers:
            self.container_combo.addItem(getattr(c, "name", f"Container {c.id}"), c.id)

    def _load_shelves(self):
        self.shelf_combo.clear()
        self.shelf_combo.addItem("-- Select Shelf --", None)
        cont_id = self._current_id(self.container_combo)
        if not cont_id:
            return
        with self.db_manager.session_scope() as s:
            shelves = s.query(Shelf).filter(Shelf.container_id == cont_id).order_by(Shelf.id.asc()).all()
        for sh in shelves:
            self.shelf_combo.addItem(getattr(sh, "label", f"Shelf {sh.id}"), sh.id)

    def _load_drawers(self):
        self.drawer_combo.clear()
        self.drawer_combo.addItem("-- Select Drawer --", None)
        shelf_id = self._current_id(self.shelf_combo)
        if not shelf_id:
            return
        with self.db_manager.session_scope() as s:
            drawers = s.query(Drawer).filter(Drawer.shelf_id == shelf_id).order_by(Drawer.id.asc()).all()
        for dr in drawers:
            self.drawer_combo.addItem(getattr(dr, "label", f"Drawer {dr.id}"), dr.id)

    def _load_slots(self):
        self.slot_combo.clear()
        self.slot_combo.addItem("-- Select Slot --", None)
        drawer_id = self._current_id(self.drawer_combo)
        if not drawer_id:
            return
        with self.db_manager.session_scope() as s:
            slots = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id).order_by(DrawerSlot.id.asc()).all()
        for sl in slots:
            label = sl.slot_label or (
                f"R{sl.row_index:02d}-C{sl.col_index:02d}"
                if sl.row_index is not None and sl.col_index is not None
                else f"Slot {sl.id}"
            )
            self.slot_combo.addItem(label, sl.id)

    # ---------- Change handlers ----------
    def _on_room_changed(self, idx):
        self._load_containers()
        self._load_shelves()
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._refresh_contents()

    def _on_container_changed(self, idx):
        self._load_shelves()
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._refresh_contents()

    def _on_shelf_changed(self, idx):
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._refresh_contents()

    def _on_drawer_changed(self, idx):
        if self._has_drawer_slot:
            self._load_slots()
        self._refresh_contents()

    def _on_slot_changed(self, idx):
        self._refresh_contents()

    def _refresh_contents(self):
        """
        Refresh the contents table and summary panel.
        """
        request_id = set_request_id()
        rows = []
        summary_text = "No selection"

        try:
            with self.db_manager.session_scope() as s:
                if self._current_id(self.slot_combo):
                    rows = self._fetch_contents_for_slot(s, self._current_id(self.slot_combo))
                    summary_text = f"Slot {self._current_id(self.slot_combo)} selected"
                elif self._current_id(self.drawer_combo):
                    rows = self._fetch_contents_for_drawer(s, self._current_id(self.drawer_combo))
                    slot_count = s.query(DrawerSlot).filter(
                        DrawerSlot.drawer_id == self._current_id(self.drawer_combo)
                    ).count()
                    summary_text = f"Drawer: {slot_count} slots"
                elif self._current_id(self.shelf_combo):
                    rows = self._fetch_contents_for_shelf(s, self._current_id(self.shelf_combo))
                    dr_count = s.query(Drawer).filter(
                        Drawer.shelf_id == self._current_id(self.shelf_combo)
                    ).count()
                    sl_count = (
                        s.query(DrawerSlot).join(Drawer).filter(
                            Drawer.shelf_id == self._current_id(self.shelf_combo)
                        ).count()
                    )
                    summary_text = f"Shelf: {dr_count} drawers, {sl_count} slots"
                elif self._current_id(self.container_combo):
                    rows = self._fetch_contents_for_container(s, self._current_id(self.container_combo))
                    sh_count = s.query(Shelf).filter(
                        Shelf.container_id == self._current_id(self.container_combo)
                    ).count()
                    dr_count = (
                        s.query(Drawer).join(Shelf).filter(
                            Shelf.container_id == self._current_id(self.container_combo)
                        ).count()
                    )
                    sl_count = (
                        s.query(DrawerSlot).join(Drawer).join(Shelf).filter(
                            Shelf.container_id == self._current_id(self.container_combo)
                        ).count()
                    )
                    summary_text = f"Container: {sh_count} shelves, {dr_count} drawers, {sl_count} slots"
                elif self._current_id(self.room_combo):
                    summary_text = "Room selected (no direct contents yet)"
        except Exception as e:
            error_id(f"[RemoteInventory._refresh_contents] error: {e}", request_id)

        # Update panel
        self.summary_label.setText(summary_text)

        # Update table
        table = self.contents
        table.setSortingEnabled(False)
        table.clearContents()
        table.setRowCount(0)

        for r, row in enumerate(rows):
            if len(row) != 6:
                continue
            (level, id_, name, typ, qty, updated) = row
            self._append_row(level, id_, name, typ, qty, updated)

        table.resizeColumnsToContents()
        table.setSortingEnabled(True)

    # ---------- Data fetchers (only return parts now) ----------
    def _fetch_contents_for_container(self, s, cont_id):
        inv = s.query(Inventory).options(joinedload(Inventory.part)).filter(
            Inventory.container_id == cont_id).all()
        return [(i.part_id, i.part_id, i.part.name if i.part else f"Part {i.part_id}",
                 "Part", f"{i.quantity} {i.unit or ''}".strip(),
                 i.updated_at.strftime("%Y-%m-%d %H:%M") if i.updated_at else "") for i in inv]

    def _fetch_contents_for_shelf(self, s, shelf_id):
        inv = s.query(Inventory).options(joinedload(Inventory.part)).filter(
            Inventory.shelf_id == shelf_id).all()
        return [(i.part_id, i.part_id, i.part.name if i.part else f"Part {i.part_id}",
                 "Part", f"{i.quantity} {i.unit or ''}".strip(),
                 i.updated_at.strftime("%Y-%m-%d %H:%M") if i.updated_at else "") for i in inv]

    def _fetch_contents_for_drawer(self, s, drawer_id):
        inv = s.query(Inventory).options(joinedload(Inventory.part)).filter(
            Inventory.drawer_id == drawer_id).all()
        return [(i.part_id, i.part_id, i.part.name if i.part else f"Part {i.part_id}",
                 "Part", f"{i.quantity} {i.unit or ''}".strip(),
                 i.updated_at.strftime("%Y-%m-%d %H:%M") if i.updated_at else "") for i in inv]

    def _fetch_contents_for_slot(self, s, slot_id):
        inv = s.query(Inventory).options(joinedload(Inventory.part)).filter(
            Inventory.drawer_slot_id == slot_id).all()
        return [(i.part_id, i.part_id, i.part.name if i.part else f"Part {i.part_id}",
                 "Part", f"{i.quantity} {i.unit or ''}".strip(),
                 i.updated_at.strftime("%Y-%m-%d %H:%M") if i.updated_at else "") for i in inv]

    # ---------- Helpers ----------
    def _current_id(self, combo):
        idx = combo.currentIndex()
        return combo.itemData(idx) if idx >= 0 else None

    def _append_row(self, level, id_, name, typ, qty, updated):
        r = self.contents.rowCount()
        self.contents.insertRow(r)

        self.contents.setItem(r, 0, QTableWidgetItem(str(level or "")))
        self.contents.setItem(r, 1, QTableWidgetItem("" if id_ is None else str(id_)))
        self.contents.setItem(r, 2, QTableWidgetItem(name or ""))
        self.contents.setItem(r, 3, QTableWidgetItem(typ or ""))
        self.contents.setItem(r, 4, QTableWidgetItem(qty or ""))
        self.contents.setItem(r, 5, QTableWidgetItem(updated or ""))

def main():
    """Main application entry point"""
    # Set up logging for the main application
    request_id = set_request_id()
    info_id("Starting ShopSync application", request_id)

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("ShopSync")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("ShopSync Systems")

    # Apply modern styling
    app.setStyle("Fusion")

    try:
        # Create and show main window
        info_id("Creating main window", request_id)
        window = MainWindow()
        window.show()

        info_id("Application initialized successfully", request_id)
        return app.exec()

    except Exception as e:
        error_id(f"Failed to start application: {str(e)}", request_id)
        return 1

if __name__ == "__main__":
    sys.exit(main())