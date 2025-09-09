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
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        self.part_search = QLineEdit()
        self.part_search.setPlaceholderText("Search parts...")

        self.location_combo = QComboBox()
        # Populate from database

        self.refresh_btn = QPushButton("Refresh")
        self.add_stock_btn = QPushButton("Add Stock")
        self.transfer_btn = QPushButton("Transfer")

        controls_layout.addWidget(QLabel("Part:"))
        controls_layout.addWidget(self.part_search)
        controls_layout.addWidget(QLabel("Location:"))
        controls_layout.addWidget(self.location_combo)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.add_stock_btn)
        controls_layout.addWidget(self.transfer_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Inventory table
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(6)
        self.inventory_table.setHorizontalHeaderLabels([
            "Part SKU", "Part Name", "Location", "Quantity", "Unit", "Last Updated"
        ])
        self.inventory_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.inventory_table)

        # Connect signals
        self.refresh_btn.clicked.connect(self.refresh_inventory)
        self.add_stock_btn.clicked.connect(self.add_stock)
        self.transfer_btn.clicked.connect(self.transfer_stock)

    def refresh_inventory(self):
        """Refresh inventory display"""
        request_id = set_request_id()
        debug_id("Refreshing inventory display", request_id)
        # Implement database query to load inventory

    def add_stock(self):
        """Add stock dialog"""
        request_id = set_request_id()
        debug_id("Opening add stock dialog", request_id)
        # Implement add stock dialog

    def transfer_stock(self):
        """Transfer stock dialog"""
        request_id = set_request_id()
        debug_id("Opening transfer stock dialog", request_id)
        # Implement transfer stock dialog


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

            # ✅ Add this:
            if hasattr(self, "add_location_widget"):
                self.add_location_widget.set_db_manager(self.db_manager)

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
    """
    Add New Location workflow:
    - Users can pick existing items or create new ones for:
      SiteLocation → Container → Shelf → Drawer → Slot (slot is optional).
    - Enforces parent-child relations by disabling buttons until a parent is chosen.
    - Uses your DB manager's session_scope() and your logging utils.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        # Slot group only shown if DrawerSlot model exists
        self._has_drawer_slot = 'DrawerSlot' in globals()
        self._build_ui()
        self._wire_signals()

    # Externally called by MainWindow after DB is ready
    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        self.refresh_all()

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)

        # --- Site Location group ---
        grp_site = QGroupBox("Site Location (Room)")
        frm_site = QFormLayout(grp_site)

        # Editable combo with type-ahead
        self.site_pick = QComboBox()
        self.site_pick.setEditable(True)
        self.site_pick.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # Completer (lets you navigate results with arrows/enter)
        self._site_completer = QCompleter(self.site_pick.model(), self.site_pick)
        self._site_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._site_completer.setFilterMode(Qt.MatchFlag.MatchContains)  # <-- PyQt6 enum
        self.site_pick.setCompleter(self._site_completer)

        # Debounce timer for server-side search
        self._site_search_timer = QTimer(self)
        self._site_search_timer.setSingleShot(True)
        self._site_search_timer.setInterval(200)  # ms
        self._site_search_timer.timeout.connect(self._perform_site_search)

        # Kick off debounced search when user types
        self.site_pick.lineEdit().textEdited.connect(lambda _t: self._site_search_timer.start())

        self.site_title = QLineEdit()  # create new
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
        self.shelf_label = QLineEdit()
        self.btn_shelf_refresh = QPushButton("Refresh")
        self.btn_shelf_add = QPushButton("Add Shelf")
        self.btn_shelf_add.setEnabled(False)
        frm_shelf.addRow("Pick Existing:", self.shelf_pick)
        frm_shelf.addRow("Label (e.g., 'Shelf A'):", self.shelf_label)
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

        # --- Slot group (optional) ---
        self.grp_slot = QGroupBox("Slot")
        frm_slot = QFormLayout(self.grp_slot)
        self.slot_pick = QComboBox()
        self.slot_label = QLineEdit()  # free label (or row/col if you add those fields)
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

        # Footer controls
        foot = QHBoxLayout()
        self.btn_refresh_all = QPushButton("Refresh All")
        self.btn_clear_fields = QPushButton("Clear Fields")
        foot.addWidget(self.btn_refresh_all)
        foot.addWidget(self.btn_clear_fields)
        foot.addStretch()
        outer.addLayout(foot)

    def _wire_signals(self):
        # Refresh chains
        self.btn_site_refresh.clicked.connect(self._load_sites)
        self.btn_cont_refresh.clicked.connect(self._load_containers)
        self.btn_shelf_refresh.clicked.connect(self._load_shelves)
        self.btn_drawer_refresh.clicked.connect(self._load_drawers)
        self.btn_slot_refresh.clicked.connect(self._load_slots)

        self.btn_refresh_all.clicked.connect(self.refresh_all)
        self.btn_clear_fields.clicked.connect(self._clear_fields)

        # Add actions
        self.btn_site_add.clicked.connect(self._add_site)
        self.btn_cont_add.clicked.connect(self._add_container)
        self.btn_shelf_add.clicked.connect(self._add_shelf)
        self.btn_drawer_add.clicked.connect(self._add_drawer)
        self.btn_slot_add.clicked.connect(self._add_slot)

        # Enable/disable based on parent selection
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
        """Initial/refresh load: use the same search path (top 50)."""
        self.site_pick.clear()
        if not self.db_manager:
            return
        # Use current text if user has typed, otherwise empty = top 50
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
            self.cont_pick.addItem(getattr(c, "name", f"Container {c.id}"), c.id)
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
            self.shelf_pick.addItem(getattr(sh, "label", f"Shelf {sh.id}"), sh.id)
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
            self.drawer_pick.addItem(getattr(dr, "label", f"Drawer {dr.id}"), dr.id)
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
            label = getattr(sl, "slot_label", None) or f"R{getattr(sl,'row_index','-')}-C{getattr(sl,'col_index','-')}"
            self.slot_pick.addItem(label, sl.id)
        self._update_buttons_enabled()

    # ---------- Create ops ----------
    def _add_site(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import SiteLocation
        request_id = set_request_id()

        title = self.site_title.text().strip()
        room  = self.site_room.text().strip()
        area  = self.site_area.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Data", "Please enter a Site Location title.")
            return

        try:
            with self.db_manager.session_scope() as s:
                obj = SiteLocation(title=title, room_number=room or None, site_area=area or None)
                s.add(obj)
                s.flush()
                info_id(f"[AddLocation] Created SiteLocation id={obj.id}", request_id)
            self._clear_site_fields()
            self._load_sites()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create SiteLocation: {e}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Site Location:\n{e}")

    def _add_container(self):
        """
        Containers are linked to Position; ensure there's a Position tied to the selected SiteLocation.
        """
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Container, Position
        request_id = set_request_id()

        site_id = self._current_id(self.site_pick)
        name = self.cont_name.text().strip()
        if not site_id:
            QMessageBox.warning(self, "Select Site", "Pick a Site Location first.")
            return
        if not name:
            QMessageBox.warning(self, "Missing Data", "Please enter a Container name.")
            return

        try:
            with self.db_manager.session_scope() as s:
                # find or create a position attached to this site location
                pos = s.query(Position).filter(Position.site_location_id == site_id).first()
                if not pos:
                    pos = Position(site_location_id=site_id)
                    s.add(pos)
                    s.flush()
                obj = Container(name=name, position_id=pos.id)
                s.add(obj)
                s.flush()
                info_id(f"[AddLocation] Created Container id={obj.id} (position_id={pos.id})", request_id)
            self.cont_name.clear()
            self._load_containers()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Container: {e}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Container:\n{e}")

    def _add_shelf(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Shelf
        request_id = set_request_id()

        cont_id = self._current_id(self.cont_pick)
        label = self.shelf_label.text().strip()
        if not cont_id:
            QMessageBox.warning(self, "Select Container", "Pick a Container first.")
            return
        if not label:
            QMessageBox.warning(self, "Missing Data", "Please enter a Shelf label.")
            return

        try:
            with self.db_manager.session_scope() as s:
                obj = Shelf(container_id=cont_id, label=label)
                s.add(obj)
                s.flush()
                info_id(f"[AddLocation] Created Shelf id={obj.id}", request_id)
            self.shelf_label.clear()
            self._load_shelves()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Shelf: {e}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Shelf:\n{e}")

    def _add_drawer(self):
        from app.modules.configuration import info_id, error_id, set_request_id
        from app.modules.database.shopsync_db import Drawer
        request_id = set_request_id()

        shelf_id = self._current_id(self.shelf_pick)
        label = self.drawer_label.text().strip()
        if not shelf_id:
            QMessageBox.warning(self, "Select Shelf", "Pick a Shelf first.")
            return
        if not label:
            QMessageBox.warning(self, "Missing Data", "Please enter a Drawer label.")
            return

        try:
            with self.db_manager.session_scope() as s:
                obj = Drawer(shelf_id=shelf_id, label=label)
                s.add(obj)
                s.flush()
                info_id(f"[AddLocation] Created Drawer id={obj.id}", request_id)
            self.drawer_label.clear()
            self._load_drawers()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Drawer: {e}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Drawer:\n{e}")

    def _add_slot(self):
        if not self._has_drawer_slot:
            return
        from app.modules.configuration import info_id, error_id, set_request_id
        DrawerSlot = globals().get("DrawerSlot")
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
                obj = DrawerSlot(drawer_id=drawer_id, slot_label=label)
                s.add(obj)
                s.flush()
                info_id(f"[AddLocation] Created Slot id={obj.id}", request_id)
            self.slot_label.clear()
            self._load_slots()
            self._notify_inventory_refresh()
        except Exception as e:
            error_id(f"[AddLocation] Failed to create Slot: {e}", request_id)
            QMessageBox.critical(self, "Error", f"Failed to create Slot:\n{e}")

    # ---------- Helpers ----------
    def _current_id(self, combo: QComboBox):
        idx = combo.currentIndex()
        return combo.itemData(idx) if idx >= 0 else None

    def _clear_fields(self):
        self._clear_site_fields()
        self.cont_name.clear()
        self.shelf_label.clear()
        self.drawer_label.clear()
        if self._has_drawer_slot:
            self.slot_label.clear()

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
        """
        If the parent MainWindow has a RemoteInventoryWidget, refresh it
        so new items appear immediately.
        """
        mw = self.parent()
        while mw and not isinstance(mw, QMainWindow):
            mw = mw.parent()
        if mw and hasattr(mw, "remote_inventory"):
            mw.remote_inventory.refresh_all()

    def _on_site_text_edited(self, text: str):
        # Start/reset debounce timer
        self._site_search_timer.start()

    def _perform_site_search(self):
        if not self.db_manager:
            return
        query = self.site_pick.lineEdit().text().strip()
        self._search_and_fill_sites(query)

    def _search_and_fill_sites(self, query: str):
        """
        Query SiteLocation by partial match on title / room_number / site_area.
        Populate combo with up to 50 matches.
        """
        from app.modules.database.shopsync_db import SiteLocation
        self.site_pick.blockSignals(True)
        try:
            # Keep current text to restore caret position after refill
            current_text = self.site_pick.lineEdit().text()

            # Execute server-side search
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

            # Refill the combo
            self.site_pick.clear()
            if not rows:
                self.site_pick.addItem("— no matches —", None)
            else:
                for pid, title, room, area in rows:
                    self.site_pick.addItem(f"{title} (Room {room or '-'}, {area or '-'})", pid)

            # Keep the typed text visible in the line edit
            self.site_pick.lineEdit().setText(current_text)
            # Ensure popup shows current filtered list
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
        self.room_combo     = QComboBox()
        self.container_combo= QComboBox()
        self.shelf_combo    = QComboBox()
        self.drawer_combo   = QComboBox()
        self.slot_combo     = QComboBox()
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
            ["Level", "ID", "Name/Number", "Type", "Qty / Unit", "Notes"]
        )
        self.contents.horizontalHeader().setStretchLastSection(True)
        outer.addWidget(QLabel("Contents"))
        outer.addWidget(self.contents, 1)

        # Footer actions
        foot = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.clear_btn   = QPushButton("Clear Selections")
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
    def refresh_all(self):
        if not self.db_manager:
            return
        self._load_rooms()
        self._load_containers()
        self._load_shelves()
        self._load_drawers()
        if self._has_drawer_slot:
            self._load_slots()
        self._refresh_contents()

    def clear_all(self):
        self.room_search.clear()
        self.room_combo.clear()
        self.container_combo.clear()
        self.shelf_combo.clear()
        self.drawer_combo.clear()
        if self._has_drawer_slot:
            self.slot_combo.clear()
        self.contents.setRowCount(0)

    def search_rooms(self):
        """Filter SiteLocations by title / room_number / site_area"""
        if not self.db_manager:
            return
        text = self.room_search.text().strip()
        request_id = set_request_id()
        debug_id(f"[RemoteInventory] room search: {text!r}", request_id)
        self.room_combo.clear()

        with self.db_manager.session_scope() as s:
            q = s.query(SiteLocation)
            if text:
                like = f"%{text}%"
                q = q.filter(
                    (SiteLocation.title.ilike(like)) |
                    (SiteLocation.room_number.ilike(like)) |
                    (SiteLocation.site_area.ilike(like))
                )
            q = q.order_by(SiteLocation.title.asc(), SiteLocation.room_number.asc())
            rooms = q.all()

        for r in rooms:
            self.room_combo.addItem(f"{r.title} (Room {r.room_number}, {r.site_area})", r.id)
        info_id(f"[RemoteInventory] loaded {len(rooms)} rooms", request_id)

    def _load_rooms(self):
        """Initial load of some rooms (no filter)"""
        if self.room_combo.count() > 0:
            return
        with self.db_manager.session_scope() as s:
            rooms = s.query(SiteLocation).order_by(SiteLocation.title.asc()).limit(100).all()
        for r in rooms:
            self.room_combo.addItem(f"{r.title} (Room {r.room_number}, {r.site_area})", r.id)

    def _load_containers(self):
        self.container_combo.clear()
        room_id = self._current_id(self.room_combo)
        if not room_id:
            return
        with self.db_manager.session_scope() as s:
            containers = s.query(Container).filter(Container.position.has(site_location_id=room_id)).order_by(Container.name.asc()).all()
        for c in containers:
            self.container_combo.addItem(getattr(c, "name", f"Container {c.id}"), c.id)

    def _load_shelves(self):
        self.shelf_combo.clear()
        cont_id = self._current_id(self.container_combo)
        if not cont_id:
            return
        with self.db_manager.session_scope() as s:
            shelves = s.query(Shelf).filter(Shelf.container_id == cont_id).order_by(Shelf.id.asc()).all()
        for sh in shelves:
            self.shelf_combo.addItem(getattr(sh, "label", f"Shelf {sh.id}"), sh.id)

    def _load_drawers(self):
        self.drawer_combo.clear()
        shelf_id = self._current_id(self.shelf_combo)
        if not shelf_id:
            return
        with self.db_manager.session_scope() as s:
            drawers = s.query(Drawer).filter(Drawer.shelf_id == shelf_id).order_by(Drawer.id.asc()).all()
        for dr in drawers:
            self.drawer_combo.addItem(getattr(dr, "label", f"Drawer {dr.id}"), dr.id)

    def _load_slots(self):
        self.slot_combo.clear()
        if not self._has_drawer_slot:
            return
        drawer_id = self._current_id(self.drawer_combo)
        if not drawer_id:
            return
        DrawerSlot = globals().get("DrawerSlot")  # optional
        if not DrawerSlot:
            return
        with self.db_manager.session_scope() as s:
            slots = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id).order_by(DrawerSlot.id.asc()).all()
        for sl in slots:
            label = getattr(sl, "slot_label", None) or f"R{getattr(sl, 'row_index', '-')}-C{getattr(sl, 'col_index', '-')}"
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
        """
        Show what's contained at the most specific selected level.
        Priority: Slot > Drawer > Shelf > Container > Room
        """
        request_id = set_request_id()
        self.contents.setRowCount(0)

        level = None
        rows = []

        with self.db_manager.session_scope() as s:
            # try slot
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

        # Render
        for r in rows:
            self._append_row(level, *r)

        info_id(f"[RemoteInventory] contents refreshed: level={level}, rows={len(rows)}", request_id)

    # ---------- Queries for each level ----------
    def _fetch_contents_for_room(self, s, room_id):
        # all containers in room + their immediate children counts (fast summary)
        containers = s.query(Container).filter(Container.position.has(site_location_id=room_id)).all()
        out = []
        for c in containers:
            out.append((c.id, getattr(c, "name", f"Container {c.id}"), "Container", "", ""))
        return out

    def _fetch_contents_for_container(self, s, cont_id):
        shelves = s.query(Shelf).filter(Shelf.container_id == cont_id).all()
        return [(sh.id, getattr(sh, "label", f"Shelf {sh.id}"), "Shelf", "", "") for sh in shelves]

    def _fetch_contents_for_shelf(self, s, shelf_id):
        drawers = s.query(Drawer).filter(Drawer.shelf_id == shelf_id).all()
        return [(dr.id, getattr(dr, "label", f"Drawer {dr.id}"), "Drawer", "", "") for dr in drawers]

    def _fetch_contents_for_drawer(self, s, drawer_id):
        # show either slots (if any) or parts in this drawer
        rows = []
        DrawerSlot = globals().get("DrawerSlot")
        if DrawerSlot:
            slots = s.query(DrawerSlot).filter(DrawerSlot.drawer_id == drawer_id).all()
            if slots:
                for sl in slots:
                    label = getattr(sl, "slot_label", None) or f"R{getattr(sl, 'row_index','-')}-C{getattr(sl, 'col_index','-')}"
                    rows.append((sl.id, label, "Slot", "", ""))
                return rows
        # Fallback: parts directly associated with drawer (if your schema supports it)
        inv = s.query(Inventory).filter(Inventory.drawer_id == drawer_id).all()
        for i in inv:
            part_name = getattr(i.part, "name", f"Part {i.part_id}") if getattr(i, "part", None) else f"Part {i.part_id}"
            qty_unit  = f"{getattr(i,'quantity', '')} {getattr(i,'unit','')}".strip()
            rows.append((i.part_id, part_name, "Part", qty_unit, getattr(i, "note", "")))
        return rows

    def _fetch_contents_for_slot(self, s, slot_id):
        inv = s.query(Inventory).filter(Inventory.drawer_slot_id == slot_id).all()
        rows = []
        for i in inv:
            part_name = getattr(i.part, "name", f"Part {i.part_id}") if getattr(i, "part", None) else f"Part {i.part_id}"
            qty_unit  = f"{getattr(i,'quantity','')} {getattr(i,'unit','')}".strip()
            rows.append((i.part_id, part_name, "Part", qty_unit, getattr(i, "note", "")))
        return rows

    # ---------- Helpers ----------
    def _current_id(self, combo):
        idx = combo.currentIndex()
        return combo.itemData(idx) if idx >= 0 else None

    def _append_row(self, level, id_, name, typ, qty, notes):
        r = self.contents.rowCount()
        self.contents.insertRow(r)
        self.contents.setItem(r, 0, QTableWidgetItem(level or ""))
        self.contents.setItem(r, 1, QTableWidgetItem(str(id_)))
        self.contents.setItem(r, 2, QTableWidgetItem(name or ""))
        self.contents.setItem(r, 3, QTableWidgetItem(typ or ""))
        self.contents.setItem(r, 4, QTableWidgetItem(qty or ""))
        self.contents.setItem(r, 5, QTableWidgetItem(notes or ""))


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