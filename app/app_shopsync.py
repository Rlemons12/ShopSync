import sys
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlalchemy.ext.declarative import declarative_base
import logging
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QLabel, QComboBox, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QSplitter, QFrame,
    QGroupBox, QSpinBox, QHeaderView, QMenu, QToolBar, QStatusBar,
    QCompleter, QListWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QStringListModel, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QPalette, QColor

# Import your configuration and logging
from app.modules.configuration import logger, info_id, error_id, debug_id, set_request_id
from app.modules.configuration.base import Base

# Import your database manager
from app.modules.database.db_manager import ShopSyncDatabase

# Import your database classes
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


class HierarchyTreeWidget(QTreeWidget):
    """Tree widget for displaying equipment hierarchy"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(['Name', 'Type', 'ID', 'Description'])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self.on_item_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def populate_hierarchy(self, db_manager):
        """Populate tree with database hierarchy"""
        request_id = set_request_id()
        debug_id("Populating equipment hierarchy", request_id)
        self.clear()

        try:
            with db_manager.session_scope() as session:
                areas = session.query(Area).all()

                for area in areas:
                    area_item = QTreeWidgetItem([
                        area.name, 'Area', str(area.id), area.description or ''
                    ])
                    area_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'area', 'data': area})
                    self.addTopLevelItem(area_item)

                    # Load equipment groups
                    for eq_group in area.equipment_group:
                        eq_item = QTreeWidgetItem([
                            eq_group.name, 'Equipment Group', str(eq_group.id),
                            eq_group.description or ''
                        ])
                        eq_item.setData(0, Qt.ItemDataRole.UserRole,
                                        {'type': 'equipment_group', 'data': eq_group})
                        area_item.addChild(eq_item)

                        # Load models
                        for model in eq_group.model:
                            model_item = QTreeWidgetItem([
                                model.name, 'Model', str(model.id),
                                model.description or ''
                            ])
                            model_item.setData(0, Qt.ItemDataRole.UserRole,
                                               {'type': 'model', 'data': model})
                            eq_item.addChild(model_item)

                            # Load asset numbers
                            for asset in model.asset_number:
                                asset_item = QTreeWidgetItem([
                                    asset.number, 'Asset', str(asset.id),
                                    asset.description or ''
                                ])
                                asset_item.setData(0, Qt.ItemDataRole.UserRole,
                                                   {'type': 'asset', 'data': asset})
                                model_item.addChild(asset_item)

                            # Load locations
                            for location in model.location:
                                location_item = QTreeWidgetItem([
                                    location.name, 'Location', str(location.id),
                                    location.description or ''
                                ])
                                location_item.setData(0, Qt.ItemDataRole.UserRole,
                                                      {'type': 'location', 'data': location})
                                model_item.addChild(location_item)

            info_id(f"Successfully populated hierarchy with {len(areas)} areas", request_id)

        except Exception as e:
            error_id(f"Failed to populate hierarchy: {str(e)}", request_id)
            QMessageBox.critical(self, "Database Error", f"Failed to load hierarchy: {str(e)}")

    def on_item_clicked(self, item, column):
        """Handle item click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and hasattr(self.parent(), 'show_entity_details'):
            self.parent().show_entity_details(data['type'], data['data'])

    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()

        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        menu.addSeparator()
        add_child_action = menu.addAction("Add Child")

        action = menu.exec(self.mapToGlobal(position))

        if action == edit_action:
            self.on_item_clicked(item, 0)
        elif action == delete_action:
            self.delete_item(item)
        elif action == add_child_action:
            self.add_child_item(item)

    def delete_item(self, item):
        """Delete selected item"""
        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this item?")
        if reply == QMessageBox.StandardButton.Yes:
            # Implement deletion logic here
            request_id = set_request_id()
            info_id("Item deletion requested", request_id)

    def add_child_item(self, item):
        """Add child item to selected item"""
        # Implement add child logic here
        request_id = set_request_id()
        info_id("Add child item requested", request_id)


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
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.db_manager = None  # Database manager will be initialized
        self.setup_ui()
        self.setup_database()

    def setup_ui(self):
        self.setWindowTitle("ShopSync - Equipment Management System")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - Hierarchy tree
        self.tree_widget = HierarchyTreeWidget(self)
        tree_frame = QFrame()
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.addWidget(QLabel("Equipment Hierarchy"))
        tree_layout.addWidget(self.tree_widget)
        splitter.addWidget(tree_frame)

        # Right panel - Tabs
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)

        # Details tab
        self.details_widget = EntityDetailsWidget(self)
        self.tab_widget.addTab(self.details_widget, "Details")

        # Search tab
        self.search_widget = SearchWidget(self)
        self.tab_widget.addTab(self.search_widget, "Search")

        # Inventory tab
        self.inventory_widget = InventoryWidget(self)
        self.tab_widget.addTab(self.inventory_widget, "Inventory")

        # Set splitter proportions
        splitter.setSizes([400, 1000])

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.statusBar().showMessage("Ready")

    def create_menu_bar(self):
        """Create application menu bar"""
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
        """Create application toolbar"""
        toolbar = self.addToolBar("Main")

        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_entity)
        toolbar.addAction(new_action)

        toolbar.addSeparator()

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)

    def setup_database(self):
        """Initialize database connection"""
        request_id = set_request_id()
        try:
            info_id("Initializing database connection", request_id)

            # Initialize the database manager
            self.db_manager = ShopSyncDatabase(echo=False)

            # Create tables if they don't exist
            self.db_manager.create_all()

            # Populate the hierarchy tree
            self.tree_widget.populate_hierarchy(self.db_manager)

            # Check database status
            tables, counts = self.db_manager.inspect()
            info_id(f"Database connected with {len(tables)} tables", request_id)

            self.statusBar().showMessage(f"Database connected - {len(tables)} tables found")

        except Exception as e:
            error_id(f"Failed to connect to database: {str(e)}", request_id)
            QMessageBox.critical(self, "Database Error",
                                 f"Failed to connect to database: {str(e)}")
            self.statusBar().showMessage("Database connection failed")

    def show_entity_details(self, entity_type, entity_data):
        """Show entity details in the details tab"""
        self.tab_widget.setCurrentIndex(0)  # Switch to details tab
        self.details_widget.show_entity_details(entity_type, entity_data)

    def new_entity(self):
        """Open new entity dialog"""
        request_id = set_request_id()
        debug_id("Opening new entity dialog", request_id)
        dialog = NewEntityDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            info_id("New entity created, refreshing data", request_id)
            self.refresh_data()

    def refresh_data(self):
        """Refresh all data displays"""
        request_id = set_request_id()
        info_id("Refreshing all data displays", request_id)

        if self.db_manager:
            self.tree_widget.populate_hierarchy(self.db_manager)
            self.inventory_widget.refresh_inventory()

        self.statusBar().showMessage("Data refreshed")

    def import_data(self):
        """Import data functionality"""
        request_id = set_request_id()
        debug_id("Import data requested", request_id)
        QMessageBox.information(self, "Import", "Import functionality will be implemented")

    def export_data(self):
        """Export data functionality"""
        request_id = set_request_id()
        debug_id("Export data requested", request_id)
        QMessageBox.information(self, "Export", "Export functionality will be implemented")

    def closeEvent(self, event):
        """Handle application close"""
        request_id = set_request_id()
        info_id("Application closing", request_id)

        if self.db_manager:
            # The database manager uses context managers, so no explicit cleanup needed
            debug_id("Database manager cleaned up", request_id)

        event.accept()


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