import sys
import logging
from typing import Optional, List, Dict, Any

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
    QCompleter, QListWidget, QScrollArea
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
    logger, info_id, error_id, debug_id, set_request_id
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
    """Inventory management widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        self.setup_ui()
        self.inventory_table.itemDoubleClicked.connect(self.open_part_locations)

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
            part_id = s.query(Part.id).filter(Part.part_number == sku).scalar()
            if not part_id:
                return

        # keep reference so it doesn't get GC'd mid-use
        self._locations_dlg = PartLocationsDialog(self, self.db_manager, part_id)
        result = self._locations_dlg.exec()

        if result == QDialog.DialogCode.Accepted:
            self.refresh_inventory()

        # safer cleanup
        self._locations_dlg.deleteLater()
        self._locations_dlg = None

    # Allow MainWindow to hand us the DB
    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        self.refresh_inventory()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Controls layout ---
        controls_layout = QHBoxLayout()

        # Buttons created first so they exist before signal connections
        self.refresh_btn = QPushButton("Refresh")
        self.add_part_btn = QPushButton("Add Part")  # 🔹 New
        self.add_stock_btn = QPushButton("Add Stock")
        self.transfer_btn = QPushButton("Transfer")
        self.delete_btn = QPushButton("Delete")  # 🔹 New

        # Search + location filter
        self.part_search = QLineEdit()
        self.part_search.setPlaceholderText("Search parts…")

        self.location_combo = QComboBox()
        self.location_combo.setEnabled(False)  # not used in this iteration

        # Add controls to row
        controls_layout.addWidget(QLabel("Part:"))
        controls_layout.addWidget(self.part_search)
        controls_layout.addWidget(QLabel("Location:"))
        controls_layout.addWidget(self.location_combo)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.add_part_btn)  # 🔹 New
        controls_layout.addWidget(self.add_stock_btn)
        controls_layout.addWidget(self.transfer_btn)
        controls_layout.addWidget(self.delete_btn)  # 🔹 New
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # --- Inventory table ---
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(8)
        self.inventory_table.setHorizontalHeaderLabels([
            "Part Number", "Part Name", "OEM Mfg", "OEM Model",
            "Location", "Quantity", "Unit", "Last Updated"
        ])

        self.inventory_table.horizontalHeader().setStretchLastSection(True)
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Disable sorting until data is filled (will re-enable with QTimer in refresh_inventory)
        self.inventory_table.setSortingEnabled(False)

        # Auto-resize columns for readability — ALL 8 COLUMNS
        header = self.inventory_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # default stretch
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Part Number
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Part Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # OEM Mfg
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # OEM Model
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Location
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Quantity
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Unit
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Last Updated

        layout.addWidget(self.inventory_table)

        # --- Signals ---
        self.refresh_btn.clicked.connect(self.refresh_inventory)
        self.add_part_btn.clicked.connect(self.add_part)  # 🔹 New
        self.add_stock_btn.clicked.connect(self.add_stock)
        self.transfer_btn.clicked.connect(self.transfer_stock)
        self.delete_btn.clicked.connect(self.delete_selected)  # 🔹 New
        self.part_search.returnPressed.connect(self.refresh_inventory)

    # -------------------------
    # Safe location resolver
    # -------------------------
    def resolve_location_string(self, inv: "Inventory") -> str:
        """Build a human-readable location string from any inventory level."""
        sl = getattr(inv, "drawer_slot", None)
        dr = getattr(inv, "drawer", None)
        sh = getattr(inv, "shelf", None)
        co = getattr(inv, "container", None)

        # Try to resolve room from any available level
        pos = (
                getattr(co, "position", None)
                or getattr(sh, "position", None)
                or getattr(dr, "position", None)
        )
        rm = getattr(pos, "site_location", None) if pos else None

        parts = []
        if rm:
            parts.append(getattr(rm, "title", "Room ?"))
        if co:
            parts.append(getattr(co, "name", "Container ?"))
        if sh:
            parts.append(getattr(sh, "name", "Shelf ?"))
        if dr:
            parts.append(getattr(dr, "name", "Drawer ?"))
        if sl:
            slot_label = sl.slot_label or (
                f"R{sl.row_index:02d}-C{sl.col_index:02d}"
                if sl.row_index is not None and sl.col_index is not None
                else f"S{sl.id}"
            )
            parts.append(slot_label)

        return " / ".join(parts) if parts else "(unassigned)"

    # -------------------------
    # Inventory refresh
    # -------------------------

    def refresh_inventory(self):
        """Refresh inventory display (catalog view)"""
        request_id = set_request_id()
        debug_id("Refreshing inventory display (catalog view)", request_id)
        if not self.db_manager:
            return

        text = (self.part_search.text() or "").strip()
        like = f"%{text}%" if text else None

        with self.db_manager.session_scope() as s:
            q = s.query(Inventory).options(
                joinedload(Inventory.part),
                joinedload(Inventory.drawer_slot).joinedload(DrawerSlot.drawer),
                joinedload(Inventory.drawer),
                joinedload(Inventory.shelf),
                joinedload(Inventory.container),
            )
            if like:
                q = q.join(Part).filter(
                    (Part.part_number.ilike(like)) | (Part.name.ilike(like))
                )

            inv_rows = q.order_by(Inventory.id.desc()).limit(500).all()

        # ---- Render table safely ----
        self.inventory_table.setSortingEnabled(False)  # prevent crashes mid-fill
        self.inventory_table.clearContents()
        self.inventory_table.setRowCount(0)

        for i in inv_rows:
            r = self.inventory_table.rowCount()
            self.inventory_table.insertRow(r)

            def safe_set(col: int, value, sort_val=None):
                try:
                    print(f"[refresh_inventory] row={r}, col={col}, value={value!r}")
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    if sort_val is not None:
                        item.setData(Qt.ItemDataRole.EditRole, sort_val)
                    self.inventory_table.setItem(r, col, item)
                except Exception as e:
                    print(f"[refresh_inventory] ERROR at row={r}, col={col}: {e}")

            # Part Number (SKU)
            sku = getattr(i.part, "part_number", f"#{i.part_id}") if i.part else f"#{i.part_id}"
            safe_set(0, sku)

            # Part Name
            safe_set(1, getattr(i.part, "name", "") if i.part else "")

            # OEM Manufacturer
            safe_set(2, getattr(i.part, "oem_mfg", "") if i.part else "")

            # OEM Model
            safe_set(3, getattr(i.part, "model", "") if i.part else "")

            # Location (safe resolver)
            try:
                loc_str = self.resolve_location_string(i)
            except Exception as e:
                error_id(f"Failed to resolve location string for Inventory {i.id}: {e}", request_id=request_id)
                loc_str = "(error resolving location)"
            safe_set(4, loc_str)

            # Quantity (store int for proper sort)
            qty_val = int(i.quantity or 0)
            safe_set(5, qty_val, sort_val=qty_val)

            # Unit
            safe_set(6, i.unit or "")

            # Last Updated (sortable timestamp)
            if i.updated_at:
                updated_str = i.updated_at.strftime("%Y-%m-%d %H:%M")
                updated_ts = i.updated_at.timestamp()
            else:
                updated_str, updated_ts = "", 0
            safe_set(7, updated_str, sort_val=updated_ts)

        # ✅ Delay sorting re-enable until Qt event loop is safe
        """if inv_rows:  # only if we actually inserted rows
            QTimer.singleShot(0, lambda: self.inventory_table.setSortingEnabled(True))
        else:
            print("[refresh_inventory] no rows found, leaving sorting disabled")"""

    # -------------------------
    # Stock management dialogs
    # -------------------------
    def add_stock(self):
        """Add stock dialog (diagnostic)"""
        print("[InventoryWidget.add_stock] clicked")
        if not self.db_manager:
            QMessageBox.warning(self, "Database", "Database not initialized.")
            return

        try:
            print("[InventoryWidget.add_stock] about to create dialog…")
            dlg = AddStockDialog(self, self.db_manager)
            print("[InventoryWidget.add_stock] dialog created successfully")
        except Exception as e:
            import traceback
            print("[InventoryWidget.add_stock] ERROR during dialog creation:", e)
            traceback.print_exc()
            return

        try:
            if dlg.exec():
                print("[InventoryWidget.add_stock] dialog accepted")
                self.refresh_inventory()
            else:
                print("[InventoryWidget.add_stock] dialog cancelled")
        except Exception as e:
            import traceback
            print("[InventoryWidget.add_stock] ERROR during exec:", e)
            traceback.print_exc()

    def transfer_stock(self):
        """Transfer stock dialog (to be implemented later)"""
        request_id = set_request_id()
        debug_id("Opening transfer stock dialog", request_id)
        QMessageBox.information(self, "Transfer", "Transfer workflow not implemented yet.")

    def delete_selected(self):
        row = self.inventory_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete", "Select a row to delete first.")
            return

        sku_item = self.inventory_table.item(row, 0)
        sku = sku_item.text() if sku_item else None

        with self.db_manager.session_scope() as s:
            part = s.query(Part).filter(Part.part_number == sku).first()
            if not part:
                QMessageBox.warning(self, "Delete", f"Part {sku} not found.")
                return

            choice = QMessageBox.question(
                self,
                "Delete",
                f"Delete only this location for '{part.name}' ({sku}), "
                f"or delete the entire part and all its inventory?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )

            if choice == QMessageBox.StandardButton.Cancel:
                return

            if choice == QMessageBox.StandardButton.Yes:
                # Delete just one inventory row
                inv = s.query(Inventory).filter(Inventory.part_id == part.id).first()
                if inv:
                    s.delete(inv)
            else:
                # Delete part (cascade inventory rows)
                s.delete(part)

            s.commit()

        self.refresh_inventory()

class AddPartDialog(QDialog):
    """Dialog to create a new Part (optionally with initial stock)."""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Add Part")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Part Number (SKU)
        sku_layout = QHBoxLayout()
        sku_layout.addWidget(QLabel("Part Number (SKU):"))
        self.sku_edit = QLineEdit()
        sku_layout.addWidget(self.sku_edit)
        layout.addLayout(sku_layout)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Part Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # OEM Manufacturer
        oem_layout = QHBoxLayout()
        oem_layout.addWidget(QLabel("OEM Manufacturer:"))
        self.oem_edit = QLineEdit()
        oem_layout.addWidget(self.oem_edit)
        layout.addLayout(oem_layout)

        # OEM Model / Mfg Part Number
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("OEM Model / Catalog #:"))
        self.model_edit = QLineEdit()
        model_layout.addWidget(self.model_edit)
        layout.addLayout(model_layout)

        # Category (Class Flag)
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("Category (Class Flag):"))
        self.class_edit = QLineEdit()
        class_layout.addWidget(self.class_edit)
        layout.addLayout(class_layout)

        # Stock Unit (only used if adding stock)
        unit_layout = QHBoxLayout()
        unit_layout.addWidget(QLabel("Stock Unit (optional):"))
        self.unit_edit = QLineEdit()
        unit_layout.addWidget(self.unit_edit)
        layout.addLayout(unit_layout)

        # Optional initial quantity
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Initial Quantity (optional):"))
        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("Leave blank for none")
        qty_layout.addWidget(self.qty_edit)
        layout.addLayout(qty_layout)

        # Buttons
        btns = QHBoxLayout()
        self.ok_btn = QPushButton("Add")
        self.continue_btn = QPushButton("Add && Continue")
        self.cancel_btn = QPushButton("Cancel")
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.continue_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

        # Signals
        self.ok_btn.clicked.connect(self.add_part_and_close)
        self.continue_btn.clicked.connect(self.add_part_and_continue)
        self.cancel_btn.clicked.connect(self.reject)

    # ----------------------------
    # Logic
    # ----------------------------
    def _collect_fields(self):
        """Grab all values from the form, return (sku, name, oem, model, class_flag, unit, qty)."""
        sku = self.sku_edit.text().strip()
        name = self.name_edit.text().strip()
        oem = self.oem_edit.text().strip()
        model = self.model_edit.text().strip()
        class_flag = self.class_edit.text().strip()
        unit = self.unit_edit.text().strip()
        qty_text = self.qty_edit.text().strip()

        if not sku or not name:
            QMessageBox.warning(self, "Invalid", "Part Number and Name are required.")
            return None

        try:
            qty = int(qty_text) if qty_text else None
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Quantity must be a number.")
            return None

        return sku, name, oem, model, class_flag, unit, qty

    def _save_part(self, sku, name, oem, model, class_flag, unit, qty):
        """Insert the part and optional stock into DB."""
        with self.db_manager.session_scope() as s:
            part = Part(
                part_number=sku,
                name=name,
                oem_mfg=oem or None,
                model=model or None,
                class_flag=class_flag or None,
            )
            s.add(part)
            s.flush()  # assign part.id

            if qty is not None:
                inv = Inventory(
                    part_id=part.id,
                    quantity=qty,
                    unit=unit or None
                )
                s.add(inv)

            s.commit()

    def add_part_and_close(self):
        fields = self._collect_fields()
        if not fields:
            return
        self._save_part(*fields)
        self.accept()  # close dialog

    def add_part_and_continue(self):
        fields = self._collect_fields()
        if not fields:
            return
        self._save_part(*fields)
        # Clear fields for next entry
        self.sku_edit.clear()
        self.name_edit.clear()
        self.oem_edit.clear()
        self.model_edit.clear()
        self.class_edit.clear()
        self.unit_edit.clear()
        self.qty_edit.clear()
        self.sku_edit.setFocus()

class PartLocationsDialog(QDialog):

    def __init__(self, parent, db_manager, part_id: int):
        super().__init__(parent)
        self.db_manager = db_manager
        self.part_id = part_id

        # fetch title info safely
        with self.db_manager.session_scope() as s:
            p = s.get(Part, self.part_id)
            pn = p.part_number if p else f"#{self.part_id}"
            nm = p.name if p else ""
        self.setWindowTitle(f"Locations for {pn} - {nm}")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Location","Quantity","Unit","Last Updated","ID"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Location")
        self.edit_btn = QPushButton("Edit Selected")
        self.delete_btn = QPushButton("Delete Selected")
        btn_row.addWidget(self.add_btn); btn_row.addWidget(self.edit_btn); btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self.add_location)
        self.edit_btn.clicked.connect(self.edit_location)
        self.delete_btn.clicked.connect(self.delete_location)

        self.load_locations()

    def load_locations(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        try:
            from sqlalchemy.orm import joinedload
            with self.db_manager.session_scope() as s:
                inv_rows = (
                    s.query(Inventory)
                     .options(
                         joinedload(Inventory.container),
                         joinedload(Inventory.shelf),
                         joinedload(Inventory.drawer),
                         joinedload(Inventory.drawer_slot),
                     )
                     .filter(Inventory.part_id == self.part_id)
                     .order_by(Inventory.id.asc())
                     .all()
                )
            for inv in inv_rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(self._resolve_location(inv)))
                self.table.setItem(r, 1, QTableWidgetItem(str(inv.quantity or 0)))
                self.table.setItem(r, 2, QTableWidgetItem(inv.unit or ""))
                self.table.setItem(r, 3, QTableWidgetItem(inv.updated_at.strftime("%Y-%m-%d %H:%M") if inv.updated_at else ""))
                self.table.setItem(r, 4, QTableWidgetItem(str(inv.id)))
        except Exception as e:
            error_id(f"Failed to load locations for Part {self.part_id}: {e}")
        self.table.setSortingEnabled(True)

    def _resolve_location(self, inv):
        # crash-proof resolver
        try:
            parts = []
            if getattr(inv, "container", None):
                parts.append(getattr(inv.container, "name", f"Container {inv.container_id}"))
            if getattr(inv, "shelf", None):
                parts.append(getattr(inv.shelf, "label", f"Shelf {inv.shelf_id}"))
            if getattr(inv, "drawer", None):
                parts.append(getattr(inv.drawer, "label", f"Drawer {inv.drawer_id}"))
            if getattr(inv, "drawer_slot", None):
                slot = inv.drawer_slot
                label = getattr(slot, "slot_label", None) or (
                    f"R{slot.row_index:02d}-C{slot.col_index:02d}"
                    if slot.row_index is not None and slot.col_index is not None else f"Slot {slot.id}"
                )
                parts.append(label)
            return " / ".join(parts) if parts else "(unassigned)"
        except Exception as e:
            error_id(f"[PartLocationsDialog] resolve_location failed inv={getattr(inv,'id','?')}: {e}")
            return "(unassigned)"

    def add_location(self):
        print("[PartLocationsDialog] add_location clicked")
        try:
            dlg = AddStockDialog(self, self.db_manager, preselected_part_id=self.part_id)
            print("[PartLocationsDialog] dialog instantiated")
        except Exception as e:
            import traceback
            print("[PartLocationsDialog] ERROR creating AddStockDialog:", e)
            traceback.print_exc()
            return

        try:
            result = dlg.exec()
            print(f"[PartLocationsDialog] dialog result={result}")
            if result == QDialog.DialogCode.Accepted:
                self.load_locations()
        finally:
            dlg.deleteLater()

    def edit_location(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Edit", "Please select a location to edit.")
            return

        inv_id_item = self.table.item(row, 4)
        if not inv_id_item:
            return
        try:
            inv_id = int(inv_id_item.text())
        except (ValueError, AttributeError):
            return

        dlg = AddStockDialog(
            self, self.db_manager,
            preselected_part_id=self.part_id,
            existing_inventory_id=inv_id
        )
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            self.load_locations()
        dlg.deleteLater()

    def delete_location(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Delete", "Please select a location to delete.")
            return

        inv_id_item = self.table.item(row, 4)
        if not inv_id_item:
            return
        try:
            inv_id = int(inv_id_item.text())
        except (ValueError, AttributeError):
            return

        if QMessageBox.question(
            self, "Confirm Delete",
            f"Delete inventory ID {inv_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        try:
            with self.db_manager.session_scope() as s:
                inv = s.get(Inventory, inv_id)
                if inv:
                    s.delete(inv)
                    s.commit()
            self.load_locations()
        except Exception as e:
            error_id(f"Failed to delete inventory {inv_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

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
        self._has_drawer_slot = True   # we imported DrawerSlot explicitly
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
        self.site_pick.lineEdit().textEdited.connect(lambda _t: self._site_search_timer.start())

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
        DrawerSlot = globals().get("DrawerSlot")
        with self.db_manager.session_scope() as s:
            slots = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id).order_by(DrawerSlot.id.asc()).all()
        for sl in slots:
            label = sl.slot_label or f"R{getattr(sl,'row_index','-')}-C{getattr(sl,'col_index','-')}"
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
                # Ensure a Position exists for this site
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()

                # Use ORM helper instead of direct add
                obj = Container.find_or_create(
                    session=s,
                    position_id=pos.id,
                    name=name,
                    description=None,
                    request_id=request_id,
                )
                StorageAddress.upsert_for_container(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created/Found Container id={obj.id}", request_id=request_id)

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
                # Ensure a Position exists for this site
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()

                # Use ORM helper instead of direct add
                obj = Shelf.find_or_create(
                    session=s,
                    position_id=pos.id,
                    name=name,
                    container_id=cont_id,
                    description=None,
                    request_id=request_id,
                )
                StorageAddress.upsert_for_shelf(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created/Found Shelf id={obj.id}", request_id=request_id)

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
                # Ensure we have a Position
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()

                # Create drawer
                obj = Drawer.add_drawer(
                    session=s,
                    position_id=pos.id,
                    name=name,
                    shelf_id=shelf_id,
                    description=None,
                    request_id=request_id,
                )

                # Ensure complete object state
                s.flush()
                s.refresh(obj)

                StorageAddress.upsert_for_drawer(s, obj, request_id=request_id)
                info_id(f"[AddLocation] Created Drawer id={obj.id}", request_id=request_id)

            self.drawer_label.clear()
            self._load_drawers()

            # Safe inventory refresh
            try:
                self._notify_inventory_refresh()
            except Exception as refresh_error:
                error_id(f"[AddLocation] Inventory refresh failed but drawer created: {refresh_error}",
                         request_id=request_id)

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
                drawer = s.get(Drawer, drawer_id)  # fetch Drawer object
                if not drawer:
                    QMessageBox.critical(self, "Error", f"Drawer {drawer_id} not found.")
                    return

                # ✅ Create the slot with explicit drawer_id
                obj = DrawerSlot(
                    drawer_id=drawer_id,
                    slot_label=label
                )
                s.add(obj)
                s.flush()  # Flush to get the slot ID and ensure it's persisted

                # ✅ Double-check drawer_id is set
                if obj.drawer_id is None:
                    obj.drawer_id = drawer_id

                # ✅ Set the relationship for good measure
                obj.drawer = drawer

                # ✅ Safe upsert, slot now has both drawer_id and drawer relationship
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

    def _on_container_changed(self, _):
        self._load_shelves()
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._update_buttons_enabled()

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
    Shows contents at every step.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        self._has_drawer_slot = 'DrawerSlot' in globals()

        self._build_ui()
        self._wire_signals()

    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        self.refresh_all()

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

        # Dependent picks
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
        outer.addLayout(form)

        # Contents table
        self.contents = QTableWidget()
        self.contents.setColumnCount(6)
        self.contents.setHorizontalHeaderLabels(
            ["Level", "ID", "Name/Number", "Type", "Qty / Unit", "Last Updated"]
        )
        self.contents.horizontalHeader().setStretchLastSection(True)
        self.contents.setSortingEnabled(True)  # enable click-to-sort
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
            error_id(f"[RemoteInventory.refresh_all] error: {e!r}", request_id=request_id)
            raise

    def clear_all(self):
        self.room_search.clear()
        for combo in (self.room_combo, self.container_combo, self.shelf_combo, self.drawer_combo, self.slot_combo):
            combo.clear()
        self.contents.setRowCount(0)

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

    # ---------- Contents ----------
    def _refresh_contents(self):
        """Show what's contained at the most specific selected level."""
        request_id = set_request_id()
        self.contents.setRowCount(0)

        level = None
        rows = []

        with self.db_manager.session_scope() as s:
            if self._has_drawer_slot and (slot_id := self._current_id(self.slot_combo)):
                level = "Slot"
                rows = self._fetch_contents_for_slot(s, slot_id)
            elif (drawer_id := self._current_id(self.drawer_combo)):
                level = "Drawer"
                rows = self._fetch_contents_for_drawer(s, drawer_id)
            elif (shelf_id := self._current_id(self.shelf_combo)):
                level = "Shelf"
                rows = self._fetch_contents_for_shelf(s, shelf_id)
            elif (container_id := self._current_id(self.container_combo)):
                level = "Container"
                rows = self._fetch_contents_for_container(s, container_id)
            elif (room_id := self._current_id(self.room_combo)):
                level = "Room"
                rows = self._fetch_contents_for_room(s, room_id)

        for r in rows:
            self._append_row(level, *r)

        self.contents.sortItems(5, Qt.SortOrder.DescendingOrder)  # newest updated first

    # ---------- Queries ----------
    def _fetch_contents_for_room(self, s, room_id):
        containers = s.query(Container).filter(Container.position.has(site_location_id=room_id)).all()
        return [(c.id, getattr(c, "name", f"Container {c.id}"), "Container", "", "") for c in containers]

    def _fetch_contents_for_container(self, s, cont_id):
        shelves = s.query(Shelf).filter(Shelf.container_id == cont_id).all()
        return [(sh.id, getattr(sh, "label", f"Shelf {sh.id}"), "Shelf", "", "") for sh in shelves]

    def _fetch_contents_for_shelf(self, s, shelf_id):
        drawers = s.query(Drawer).filter(Drawer.shelf_id == shelf_id).all()
        return [(dr.id, getattr(dr, "label", f"Drawer {dr.id}"), "Drawer", "", "") for dr in drawers]

    def _fetch_contents_for_drawer(self, s, drawer_id):
        inv = s.query(Inventory).options(joinedload(Inventory.part)).filter(Inventory.drawer_id == drawer_id).all()
        rows = []
        for i in inv:
            part_name = i.part.name if i.part else f"Part {i.part_id}"
            qty_unit = f"{i.quantity} {i.unit or ''}".strip()
            updated = i.updated_at.strftime("%Y-%m-%d %H:%M") if i.updated_at else ""
            rows.append((i.part_id, part_name, "Part", qty_unit, updated))
        return rows

    def _fetch_contents_for_slot(self, s, slot_id):
        inv = s.query(Inventory).options(joinedload(Inventory.part)).filter(Inventory.drawer_slot_id == slot_id).all()
        rows = []
        for i in inv:
            part_name = i.part.name if i.part else f"Part {i.part_id}"
            qty_unit = f"{i.quantity} {i.unit or ''}".strip()
            updated = i.updated_at.strftime("%Y-%m-%d %H:%M") if i.updated_at else ""
            rows.append((i.part_id, part_name, "Part", qty_unit, updated))
        return rows

    # ---------- Helpers ----------
    def _current_id(self, combo):
        idx = combo.currentIndex()
        return combo.itemData(idx) if idx >= 0 else None

    def _append_row(self, level, id_, name, typ, qty, updated):
        r = self.contents.rowCount()
        self.contents.insertRow(r)
        self.contents.setItem(r, 0, QTableWidgetItem(level or ""))
        self.contents.setItem(r, 1, QTableWidgetItem(str(id_)))
        self.contents.setItem(r, 2, QTableWidgetItem(name or ""))
        self.contents.setItem(r, 3, QTableWidgetItem(typ or ""))

        qty_item = QTableWidgetItem(qty or "")
        try:
            qty_item.setData(Qt.ItemDataRole.EditRole, int(qty.split()[0]))
        except Exception:
            pass
        self.contents.setItem(r, 4, qty_item)

        updated_item = QTableWidgetItem(updated or "")
        if updated:
            from datetime import datetime
            try:
                updated_item.setData(Qt.ItemDataRole.EditRole, datetime.strptime(updated, "%Y-%m-%d %H:%M"))
            except Exception:
                pass
        self.contents.setItem(r, 5, updated_item)

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