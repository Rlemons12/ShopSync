# Standard library
from io import StringIO
from typing import Optional, List

# SQLAlchemy core/ORM
from sqlalchemy import (
    Column, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, select
)
from sqlalchemy.types import JSON
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, relationship, joinedload

# Base class for models (pure; no db manager here)
from app.modules.configuration.base import Base

# Logging utilities
from app.modules.configuration.log_config import (
    logger,
    with_request_id,
    info_id,
    debug_id,
    warning_id,
    error_id,
)

# -----------------------------
# Main Tables (drop-in fixed)
# -----------------------------


# -----------------------------
# Main Tables (drop-in fixed)
# -----------------------------

# -----------------------------
# Main Tables (fixed)
# -----------------------------

class Campus(Base):
    """A campus/site that contains buildings."""
    __tablename__ = 'campus'

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False, unique=False)
    description = Column(String)
    city        = Column(String)
    state       = Column(String)
    country     = Column(String)

    # One campus -> many buildings
    buildings = relationship(
        "Building",
        back_populates="campus",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One campus -> many positions (optional but required if Position.campus uses back_populates)
    positions = relationship(
        "Position",
        back_populates="campus",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Campus id={self.id} name={self.name!r}>"


class Building(Base):
    """A building that belongs to a campus."""
    __tablename__ = 'building'

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False)
    description = Column(String)
    address     = Column(String)

    campus_id = Column(Integer, ForeignKey('campus.id', ondelete="CASCADE"),
                       nullable=False, index=True)

    # Many buildings -> one campus
    campus = relationship("Campus", back_populates="buildings")

    # One building -> many site locations
    site_locations = relationship(
        "SiteLocation",
        back_populates="building",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One building -> many positions
    positions = relationship(
        "Position",
        back_populates="building",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Building id={self.id} name={self.name!r} campus_id={self.campus_id}>"


class SiteLocation(Base):
    """A specific location/room/area inside a building."""
    __tablename__ = 'site_location'

    id          = Column(Integer, primary_key=True)
    title       = Column(String, nullable=False)
    room_number = Column(String, nullable=False)
    site_area   = Column(String, nullable=False)
    building_id = Column(Integer, ForeignKey('building.id', ondelete="CASCADE"))

    # Many site locations -> one building
    building = relationship('Building', back_populates='site_locations')

    # One site location -> many positions
    positions = relationship(
        'Position',
        back_populates='site_location',
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # (Your classmethods can stay as-is, but if you referenced `site_location.position`,
    # update to `site_location.positions` since it's a collection.)


class Position(Base):
    __tablename__ = 'position'
    id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey('area.id'), nullable=True)
    equipment_group_id = Column(Integer, ForeignKey('equipment_group.id'), nullable=True)
    model_id = Column(Integer, ForeignKey('model.id'), nullable=True)
    asset_number_id = Column(Integer, ForeignKey('asset_number.id'), nullable=True)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=True)
    subassembly_id = Column(Integer, ForeignKey('subassembly.id'), nullable=True)
    component_assembly_id = Column(Integer, ForeignKey('component_assembly.id'), nullable=True)
    assembly_view_id = Column(Integer, ForeignKey('assembly_view.id'), nullable=True)
    site_location_id = Column(Integer, ForeignKey('site_location.id'), nullable=True)
    building_id = Column(Integer, ForeignKey('building.id'), nullable=True)
    campus_id = Column(Integer, ForeignKey('campus.id'), nullable=True)

    area = relationship("Area", back_populates="position")
    equipment_group = relationship("EquipmentGroup", back_populates="position")
    model = relationship("Model", back_populates="position")
    asset_number = relationship("AssetNumber", back_populates="position")
    location = relationship("Location", back_populates="position")
    """bill_of_material = relationship("BillOfMaterial", back_populates="position")"""
    part_position_image = relationship("PartsPositionImageAssociation", back_populates="position")
    image_position_association = relationship("ImagePositionAssociation", back_populates="position")
    drawing_position = relationship("DrawingPositionAssociation", back_populates="position")
    #problem_position = relationship("ProblemPositionAssociation", back_populates="position")
    #completed_document_position_association = relationship("CompletedDocumentPositionAssociation", back_populates="position")
    building = relationship("Building", back_populates="positions")
    campus = relationship("Campus", back_populates="positions")
    site_location = relationship("SiteLocation", back_populates="positions")
    #position_tasks = relationship("TaskPositionAssociation", back_populates="position", cascade="all, delete-orphan")
    tool_position_association = relationship("ToolPositionAssociation", back_populates="position")
    subassembly = relationship("Subassembly", back_populates="position")
    component_assembly = relationship("ComponentAssembly", back_populates="position")
    assembly_view = relationship("AssemblyView", back_populates="position")

    # in Position(...)
    container = relationship("Container", back_populates="position", cascade="all, delete-orphan", passive_deletes=True)
    shelf = relationship("Shelf", back_populates="position", cascade="all, delete-orphan", passive_deletes=True)
    drawer = relationship("Drawer", back_populates="position", cascade="all, delete-orphan", passive_deletes=True)

    # Hierarchy definition
    # Define HIERARCHY using string names instead of direct class references
    HIERARCHY = {
        'area': {
            'model': 'EquipmentGroup',
            'filter_field': 'area_id',
            'order_field': 'name',
            'next_level': 'equipment_group'
        },
        'equipment_group': {
            'model': 'Model',
            'filter_field': 'equipment_group_id',
            'order_field': 'name',
            'next_level': 'model'
        },
        'model': {
            # Models have two potential child types - asset_number and location
            'child_types': [
                {
                    'model': 'AssetNumber',
                    'filter_field': 'model_id',
                    'order_field': 'number',
                    'next_level': 'asset_number'
                },
                {
                    'model': 'Location',
                    'filter_field': 'model_id',
                    'order_field': 'name',
                    'next_level': 'location'
                }
            ]
        },
        'location': {
            'model': 'Subassembly',
            'filter_field': 'location_id',
            'order_field': 'name',
            'next_level': 'subassembly'
        },
        'subassembly': {
            'model': 'ComponentAssembly',
            'filter_field': 'subassembly_id',
            'order_field': 'name',
            'next_level': 'component_assembly'
        },
        'component_assembly': {
            'model': 'AssemblyView',
            'filter_field': 'component_assembly_id',
            'order_field': 'name',
            'next_level': 'assembly_view'
        }
    }

    # Model mapping - defined once for efficiency
    MODELS_MAP = None

    @classmethod
    @with_request_id
    def get_dependent_items(cls, session, parent_type, parent_id, child_type=None):
        """
        Generic method to get dependent items based on parent type and ID.

        Args:
            session: SQLAlchemy session
            parent_type: The type of the parent (e.g., 'area', 'equipment_group')
            parent_id: The ID of the parent
            child_type: Optional, to specify which child type to return when parent has multiple child types

        Returns:
            List of dependent items
        """
        if not parent_id:
            return []

        # Get parent configuration from hierarchy
        parent_config = cls.HIERARCHY.get(parent_type)
        if not parent_config:
            return []

        # Handle parents with multiple child types
        if 'child_types' in parent_config:
            if child_type:
                # Find the specific child type configuration
                for child_config in parent_config['child_types']:
                    if child_config.get('next_level') == child_type:
                        return cls._fetch_dependent_items(session, child_config, parent_id)
                return []
            else:
                # Return the first child type by default
                return cls._fetch_dependent_items(session, parent_config['child_types'][0], parent_id)
        else:
            # Standard single child type
            return cls._fetch_dependent_items(session, parent_config, parent_id)

    @staticmethod
    def _fetch_dependent_items(session, config, parent_id):
        """
        Helper method to fetch dependent items based on configuration.

        Args:
            session: SQLAlchemy session
            config: Configuration dictionary with model, filter_field, order_field
            parent_id: The ID of the parent

        Returns:
            List of dependent items
        """
        model_name = config.get('model')
        filter_field = config.get('filter_field')
        order_field = config.get('order_field')

        if not all([model_name, filter_field, order_field]):
            return []

        # Get the actual model class from its name
        if isinstance(model_name, str):
            # Use globals() to find the class by name
            model = globals().get(model_name)
            if not model:
                # Alternative approach - if globals() doesn't work, you can use a mapping
                models_map = {
                    'EquipmentGroup': EquipmentGroup,
                    'Model': Model,
                    'AssetNumber': AssetNumber,
                    'Location': Location,
                    'Subassembly': Subassembly,
                    'ComponentAssembly': ComponentAssembly,
                    'AssemblyView': AssemblyView,
                    'SiteLocation': SiteLocation
                }
                model = models_map.get(model_name)
                if not model:
                    return []
        else:
            model = model_name  # Already a class

        query = session.query(model).filter_by(**{filter_field: parent_id})

        # Apply ordering
        order_attr = getattr(model, order_field)
        query = query.order_by(order_attr)

        return query.all()

    @classmethod
    @with_request_id
    def get_next_level_type(cls, current_level):
        """Get the next level type in the hierarchy"""
        config = cls.HIERARCHY.get(current_level)
        if not config:
            return None

        if 'child_types' in config:
            # Return the first child type by default
            return config['child_types'][0].get('next_level')
        else:
            return config.get('next_level')

    @classmethod
    @with_request_id
    def add_to_db(cls, session=None, area_id=None, equipment_group_id=None, model_id=None, asset_number_id=None,
                  location_id=None, subassembly_id=None, component_assembly_id=None, assembly_view_id=None,
                  site_location_id=None):
        """
        Get-or-create a Position with exactly these FK values.
        If `session` is None, uses DatabaseConfig().get_main_session().
        Returns the Position ID (integer) of the new or existing position.
        """
        # 1) ensure we have a session
        if session is None:

            # Lazy import to avoid circulars at module import time

            from app.modules.configuration.database_config import DatabaseConfig
            session = DatabaseConfig().get_main_session()

        # 2) log input parameters - FIXED
        debug_id(
            f"add_to_db called with area_id={area_id}, equipment_group_id={equipment_group_id}, "
            f"model_id={model_id}, asset_number_id={asset_number_id}, location_id={location_id}, "
            f"subassembly_id={subassembly_id}, component_assembly_id={component_assembly_id}, "
            f"assembly_view_id={assembly_view_id}, site_location_id={site_location_id}"
        )

        # 3) build filter dict
        filters = {
            "area_id": area_id,
            "equipment_group_id": equipment_group_id,
            "model_id": model_id,
            "asset_number_id": asset_number_id,
            "location_id": location_id,
            "subassembly_id": subassembly_id,
            "component_assembly_id": component_assembly_id,
            "assembly_view_id": assembly_view_id,
            "site_location_id": site_location_id,
        }

        try:
            # 4) try to find an existing row
            existing = session.query(cls).filter_by(**filters).first()
            if existing:
                info_id("Found existing Position id=%s", existing.id)
                return existing.id

            # 5) not found → create new
            position = cls(**filters)
            session.add(position)
            session.commit()
            info_id("Created new Position id=%s", position.id)
            return position.id

        except SQLAlchemyError as e:
            session.rollback()
            error_id("Failed to add_or_get Position: %s", e, exc_info=True)
            raise

    @classmethod
    @with_request_id
    def get_corresponding_position_ids(cls, session=None, area_id=None, equipment_group_id=None,
                                       model_id=None, asset_number_id=None, location_id=None,
                                       request_id='no_request_id'):
        """
        Search for corresponding Position IDs based on the provided filters with request ID logging

        Args:
            session: SQLAlchemy session (Optional)
            area_id: ID of the area (optional)
            equipment_group_id: ID of the equipment group (optional)
            model_id: ID of the model (optional)
            asset_number_id: ID of the asset number (optional)
            location_id: ID of the location (optional)
            request_id: Unique identifier for the request

        Returns:
            List of Position IDs that match the criteria
        """
        # Ensure a session is available, if not use DatabaseConfig to get it
        if session is None:

            from app.modules.configuration.database_config import DatabaseConfig
            session = DatabaseConfig().get_main_session()

        # Log input parameters with request ID
        info_id(
            f"[{request_id}] get_corresponding_position_ids called with "
            f"area_id={area_id}, equipment_group_id={equipment_group_id}, "
            f"model_id={model_id}, asset_number_id={asset_number_id}, "
            f"location_id={location_id}"
        )

        try:
            # Start by fetching the root-level positions based on hierarchy
            positions = cls._get_positions_by_hierarchy(
                session,
                area_id=area_id,
                equipment_group_id=equipment_group_id,
                model_id=model_id,
                asset_number_id=asset_number_id,
                location_id=location_id,
                request_id=request_id
            )

            # Extract Position IDs
            position_ids = [position.id for position in positions]

            # Log the result
            info_id(f"[{request_id}] Retrieved {len(position_ids)} Position IDs")
            return position_ids

        except SQLAlchemyError as e:
            # Log any errors encountered during the query
            error_id(
                f"[{request_id}] Error in get_corresponding_position_ids: {str(e)}",
                exc_info=True
            )
            raise

    @classmethod
    @with_request_id
    def _get_positions_by_hierarchy(cls, session, area_id=None, equipment_group_id=None, model_id=None,
                                    asset_number_id=None, location_id=None, request_id=None):
        """
        Helper method to fetch positions based on hierarchical filters.

        Args:
            session: SQLAlchemy session
            area_id, equipment_group_id, model_id, asset_number_id, location_id: IDs for filtering

        Returns:
            List of Position objects that match the criteria
        """
        # Building the filter dynamically based on input parameters
        filters = {}
        if area_id:
            filters['area_id'] = area_id
        if equipment_group_id:
            filters['equipment_group_id'] = equipment_group_id
        if model_id:
            filters['model_id'] = model_id
        if asset_number_id:
            filters['asset_number_id'] = asset_number_id
        if location_id:
            filters['location_id'] = location_id

        # Log the filter parameters
        debug_id(f"Filtering Positions with filters: {filters}", request_id=request_id)

        try:
            # Query the Position table based on the filters
            query = session.query(Position).filter_by(**filters)

            # Log the query execution
            info_id(f"Executing query for positions with {len(filters)} filters.", request_id=request_id)

            # Return the positions matching the filter
            positions = query.all()

            # Log the result
            info_id(f"Retrieved {len(positions)} positions.", request_id=request_id)
            return positions

        except SQLAlchemyError as e:
            # Log any errors encountered during the query
            error_id(f"Error in _get_positions_by_hierarchy: {str(e)}", exc_info=True, request_id=request_id)
            raise

class Area(Base):
    __tablename__ = 'area'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)

    equipment_group = relationship("EquipmentGroup", back_populates="area")
    position = relationship("Position", back_populates="area")

    @classmethod
    @with_request_id
    def add(cls, session: Session, name: str, description: str = None, logger=None):
        """
        Add a new Area to the database.
        Returns the created Area instance, or None if failed.
        """
        try:
            area = cls(name=name, description=description)
            session.add(area)
            session.commit()
            if logger:
                logger.info(f"Added Area: {name}")
            return area
        except SQLAlchemyError as e:
            session.rollback()
            if logger:
                logger.error(f"Failed to add Area: {e}")
            return None

    @classmethod
    @with_request_id
    def delete(cls, session: Session, area_id: int, logger=None):
        """
        Delete an Area by ID.
        Returns True if deleted, False if not found or failed.
        """
        try:
            area = session.query(cls).get(area_id)
            if area:
                session.delete(area)
                session.commit()
                if logger:
                    logger.info(f"Deleted Area id={area_id}")
                return True
            else:
                if logger:
                    logger.warning(f"Area id={area_id} not found for deletion")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            if logger:
                logger.error(f"Failed to delete Area id={area_id}: {e}")
            return False

    @classmethod
    @with_request_id
    def search(cls, session: Session, name: str = None, description: str = None):
        """
        Search for Areas by name and/or description.
        Returns a list of Area instances matching the criteria.
        """
        query = session.query(cls)
        if name:
            query = query.filter(cls.name.ilike(f"%{name}%"))
        if description:
            query = query.filter(cls.description.ilike(f"%{description}%"))
        return query.all()

class EquipmentGroup(Base):
    __tablename__ = 'equipment_group'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    area_id = Column(Integer, ForeignKey('area.id'))
    description = Column(String ,nullable=True)

    area = relationship("Area", back_populates="equipment_group")
    model = relationship("Model", back_populates="equipment_group")
    position = relationship("Position", back_populates="equipment_group")

    @classmethod
    @with_request_id
    def add_equipment_group(cls, session, name, area_id, description=None, request_id=None):
        """
        Add a new equipment group to the database.

        Args:
            session: SQLAlchemy database session
            name (str): Name of the equipment group
            area_id (int): ID of the area this equipment group belongs to
            description (str, optional): Description of the equipment group
            request_id (str, optional): Unique identifier for the request

        Returns:
            EquipmentGroup: The newly created equipment group object
        """
        new_equipment_group = cls(
            name=name,
            area_id=area_id,
            description=description
        )

        session.add(new_equipment_group)
        session.commit()

        return new_equipment_group

    @classmethod
    @with_request_id
    def delete_equipment_group(cls, session, equipment_group_id, request_id=None):
        """
        Delete an equipment group from the database.

        Args:
            session: SQLAlchemy database session
            equipment_group_id (int): ID of the equipment group to delete
            request_id (str, optional): Unique identifier for the request

        Returns:
            bool: True if deletion was successful, False if equipment group not found
        """
        equipment_group = session.query(cls).filter(cls.id == equipment_group_id).first()

        if equipment_group:
            session.delete(equipment_group)
            session.commit()
            return True
        else:
            return False

    @classmethod
    @with_request_id
    def find_related_entities(cls, session, identifier, is_id=True, request_id=None):
        """
        Find all related entities for an equipment group, traversing both up and down
        the hierarchy: Area → EquipmentGroup → Model → (AssetNumber, Location, Position).

        Args:
            session: SQLAlchemy database session
            identifier: Either equipment_group ID (int) or name (str)
            is_id (bool): If True, identifier is an ID, otherwise it's a name
            request_id (str, optional): Unique identifier for the request

        Returns:
            dict: Dictionary containing:
                - 'equipment_group': The found equipment group object
                - 'upward': Dictionary containing 'area' the equipment group belongs to
                - 'downward': Dictionary containing:
                    - 'models': List of all models belonging to this equipment group
                    - 'positions': List of all positions directly related to this equipment group
        """
        # Find the equipment group
        if is_id:
            equipment_group = session.query(cls).filter(cls.id == identifier).first()
        else:
            equipment_group = session.query(cls).filter(cls.name == identifier).first()

        if not equipment_group:
            return None

        # Going upward in the hierarchy
        upward = {
            'area': equipment_group.area
        }

        # Going downward in the hierarchy
        downward = {
            'models': equipment_group.model,
            'positions': equipment_group.position
        }

        # Collecting more detailed information from models if needed
        model_details = []
        for model in equipment_group.model:
            model_info = {
                'id': model.id,
                'name': model.name,
                'description': model.description,
                'asset_numbers': model.asset_number,
                'locations': model.location,
                'positions': model.position
            }
            model_details.append(model_info)

        downward['model_details'] = model_details

        return {
            'equipment_group': equipment_group,
            'upward': upward,
            'downward': downward
        }

class Model(Base):
    __tablename__ = 'model'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String ,nullable=True)
    equipment_group_id = Column(Integer, ForeignKey('equipment_group.id'))

    equipment_group = relationship("EquipmentGroup", back_populates="model")
    asset_number = relationship("AssetNumber", back_populates="model")
    location = relationship("Location", back_populates="model")
    position = relationship("Position", back_populates="model")

    @classmethod
    @with_request_id
    def search_models(cls, session, query, limit=10):
        """
        Searches for models that match the provided query using a case-insensitive
        partial match on the name field. Useful for autocomplete or dynamic search interfaces.

        Parameters:
            session: SQLAlchemy session object used for querying.
            query: The partial model name input by the user.
            limit: Maximum number of results to return (default is 10).

        Returns:
            A list of dictionaries, each containing details about a model:
              - id: The model's unique identifier.
              - name: The model's name.
              - description: The model's description.
              - equipment_group_id: The associated equipment group ID.
            If no records match, an empty list is returned.
        """
        logger.info("========== MODEL AUTOCOMPLETE SEARCH ==========")
        logger.debug(f"Initiating search for models with query: '{query}'")

        try:
            if not query:
                logger.debug("Empty query received; returning empty result set.")
                return []

            search_pattern = f"%{query}%"
            logger.debug(f"Using search pattern: '{search_pattern}'")

            results = session.query(cls).filter(cls.name.ilike(search_pattern)).limit(limit).all()

            if results:
                models = []
                for model in results:
                    model_details = {
                        "id": model.id,
                        "name": model.name,
                        "description": model.description,
                        "equipment_group_id": model.equipment_group_id
                    }
                    models.append(model_details)
                    logger.debug(f"Found model: {model_details}")
                logger.info(f"Found {len(models)} model(s) matching query '{query}'.")
                return models
            else:
                logger.warning(f"No models found matching query '{query}'.")
                return []
        except Exception as e:
            logger.error(f"Error searching for models with query '{query}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            logger.info("========== MODEL AUTOCOMPLETE SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def add_model(cls, session, name, equipment_group_id, description=None, request_id=None):
        """
        Add a new model to the database.

        Args:
            session: SQLAlchemy database session
            name (str): Name of the model
            equipment_group_id (int): ID of the equipment group this model belongs to
            description (str, optional): Description of the model
            request_id (str, optional): Unique identifier for the request

        Returns:
            Model: The newly created model object
        """
        new_model = cls(
            name=name,
            equipment_group_id=equipment_group_id,
            description=description
        )

        session.add(new_model)
        session.commit()

        return new_model

    @classmethod
    @with_request_id
    def delete_model(cls, session, model_id, request_id=None):
        """
        Delete a model from the database.

        Args:
            session: SQLAlchemy database session
            model_id (int): ID of the model to delete
            request_id (str, optional): Unique identifier for the request

        Returns:
            bool: True if deletion was successful, False if model not found
        """
        model = session.query(cls).filter(cls.id == model_id).first()

        if model:
            session.delete(model)
            session.commit()
            return True
        else:
            return False

    @classmethod
    @with_request_id
    def find_related_entities(cls, session, identifier, is_id=True, request_id=None):
        """
        Find all related entities for a model, traversing both up and down
        the hierarchy: Area → EquipmentGroup → Model → (AssetNumber, Location, Position).

        Args:
            session: SQLAlchemy database session
            identifier: Either model ID (int) or name (str)
            is_id (bool): If True, identifier is an ID, otherwise it's a name
            request_id (str, optional): Unique identifier for the request

        Returns:
            dict: Dictionary containing:
                - 'model': The found model object
                - 'upward': Dictionary containing 'equipment_group' and 'area'
                - 'downward': Dictionary containing:
                    - 'asset_numbers': List of all asset numbers belonging to this model
                    - 'locations': List of all locations for this model
                    - 'positions': List of all positions related to this model
        """
        # Find the model
        if is_id:
            model = session.query(cls).filter(cls.id == identifier).first()
        else:
            model = session.query(cls).filter(cls.name == identifier).first()

        if not model:
            return None

        # Going upward in the hierarchy
        upward = {
            'equipment_group': model.equipment_group,
            'area': model.equipment_group.area if model.equipment_group else None
        }

        # Going downward in the hierarchy
        downward = {
            'asset_numbers': model.asset_number,
            'locations': model.location,
            'positions': model.position
        }

        return {
            'model': model,
            'upward': upward,
            'downward': downward
        }

class AssetNumber(Base):
    __tablename__ = 'asset_number'

    id = Column(Integer, primary_key=True)
    number = Column(String, nullable=False)
    description = Column(String)
    model_id = Column(Integer, ForeignKey('model.id'))

    model = relationship("Model", back_populates="asset_number")
    position = relationship("Position", back_populates="asset_number")

    @classmethod
    @with_request_id
    def get_ids_by_number(cls, session, number):
        """Retrieve all AssetNumber IDs that match the given number."""
        logger.info(f"========== ASSET NUMBER SEARCH ==========")
        logger.debug(f"Querying AssetNumber IDs for number: '{number}'")

        try:
            # Log the search pattern being used
            logger.debug(f"Using exact match search pattern for number: '{number}'")

            # Execute the query
            results = session.query(cls.id).filter(cls.number == number).all()

            # Extract IDs from the results
            ids = [id_ for (id_,) in results]

            # Log detailed information about the results
            if ids:
                logger.info(f"Found {len(ids)} AssetNumbers with number '{number}': {ids}")
                for i, asset_id in enumerate(ids):
                    try:
                        # Get more details about each asset found
                        asset = session.query(cls).filter(cls.id == asset_id).first()
                        if asset:
                            logger.debug(f"Asset #{i + 1}: ID={asset_id}, Number={asset.number}, " +
                                         f"Description={asset.description or 'None'}, Model ID={asset.model_id}")

                            # Get model info if available
                            if asset.model_id:
                                model = session.query(Model).filter(Model.id == asset.model_id).first()
                                if model:
                                    logger.debug(f"  -> Model: ID={model.id}, Name={model.name}")
                    except Exception as e:
                        logger.warning(f"Error getting details for asset ID {asset_id}: {e}")
            else:
                logger.warning(f"No AssetNumbers found with number '{number}'")

            return ids
        except Exception as e:
            logger.error(f"Error querying AssetNumbers by number '{number}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            logger.info(f"========== ASSET NUMBER SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def get_model_id_by_asset_number_id(cls, session, asset_number_id):
        """
        Given an asset_number_id, returns the associated model_id.

        Parameters:
            session: SQLAlchemy session object used for querying.
            asset_number_id: The id of the AssetNumber record.

        Returns:
            The model_id associated with the asset_number, or None if not found.
        """
        logger.info(f"========== GETTING MODEL FOR ASSET ID {asset_number_id} ==========")
        logger.debug(f"Querying AssetNumber for asset_number_id: {asset_number_id}")

        try:
            # First try to get the full asset record for more detailed logging
            asset = session.query(cls).filter(cls.id == asset_number_id).first()
            if asset:
                logger.debug(f"Found asset: ID={asset.id}, Number={asset.number}, " +
                             f"Description={asset.description or 'None'}, Model ID={asset.model_id}")
                model_id = asset.model_id
            else:
                # Fallback to just getting the model_id directly
                logger.debug(f"Asset not found, querying only for the model_id")
                model_id = session.query(cls.model_id).filter(cls.id == asset_number_id).scalar()

            if model_id is not None:
                logger.info(f"Found model_id: {model_id} for asset_number_id: {asset_number_id}")

                # Get model details for better logging
                try:
                    model = session.query(Model).filter(Model.id == model_id).first()
                    if model:
                        logger.debug(f"Model details: ID={model.id}, Name={model.name}, " +
                                     f"Equipment Group ID={model.equipment_group_id}")
                except Exception as e:
                    logger.warning(f"Error getting model details: {e}")
            else:
                logger.warning(f"No AssetNumber found with id: {asset_number_id}")

            return model_id
        except Exception as e:
            logger.error(f"Error getting model_id for asset_number_id {asset_number_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            logger.info(f"========== MODEL SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def get_equipment_group_id_by_asset_number_id(cls, session, asset_number_id):
        """
        Given an asset_number_id, retrieves the equipment_group id that is associated with its model.

        This method works in two steps:
          1. It joins the AssetNumber table with the Model table (using AssetNumber.model_id).
          2. It selects the 'equipment_group_id' field from Model, which holds the id of the associated EquipmentGroup.

        Parameters:
            session: SQLAlchemy session object used for querying.
            asset_number_id: The id of the AssetNumber record.

        Returns:
            The equipment_group id if found, otherwise None.
        """
        logger.info(f"========== GETTING EQUIPMENT GROUP FOR ASSET ID {asset_number_id} ==========")
        logger.debug(f"Querying for equipment_group id using asset_number_id: {asset_number_id}")

        try:
            # Try to get the model_id first for more detailed logging
            model_id = cls.get_model_id_by_asset_number_id(session, asset_number_id)

            if model_id is not None:
                logger.debug(f"Found model_id: {model_id} for asset_number_id: {asset_number_id}")

                # Query directly using the model ID for better performance
                equipment_group_id = session.query(Model.equipment_group_id).filter(Model.id == model_id).scalar()

                if equipment_group_id is not None:
                    logger.info(f"Found equipment_group_id: {equipment_group_id} via model_id {model_id}")

                    # Get equipment group details for better logging
                    try:
                        group = session.query(EquipmentGroup).filter(EquipmentGroup.id == equipment_group_id).first()
                        if group:
                            logger.debug(f"Equipment Group details: ID={group.id}, Name={group.name}, " +
                                         f"Area ID={group.area_id}")
                    except Exception as e:
                        logger.warning(f"Error getting equipment group details: {e}")
                else:
                    logger.warning(f"No equipment_group_id found for model_id: {model_id}")

                    # Fall back to the join method
                    logger.debug(f"Falling back to join query method")
                    equipment_group_id = (
                        session.query(Model.equipment_group_id)
                        .join(Model, Model.id == cls.model_id)
                        .filter(cls.id == asset_number_id)
                        .scalar()
                    )
            else:
                # If we couldn't get the model_id, use the join method directly
                logger.debug(f"No model_id found, using join query method directly")
                equipment_group_id = (
                    session.query(Model.equipment_group_id)
                    .join(Model, Model.id == cls.model_id)
                    .filter(cls.id == asset_number_id)
                    .scalar()
                )

            if equipment_group_id is not None:
                logger.info(
                    f"Final result: Found equipment_group_id: {equipment_group_id} for asset_number_id: {asset_number_id}")
            else:
                logger.warning(f"Final result: No EquipmentGroup found for asset_number_id: {asset_number_id}")

            return equipment_group_id
        except Exception as e:
            logger.error(f"Error getting equipment_group_id for asset_number_id {asset_number_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            logger.info(f"========== EQUIPMENT GROUP SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def get_area_id_by_asset_number_id(cls, session, asset_number_id):
        """
        Given an asset_number_id, retrieves the associated area_id.

        This method performs a series of joins:
          1. Join Area to EquipmentGroup on Area.id equals EquipmentGroup.area_id.
          2. Join EquipmentGroup to Model on EquipmentGroup.id equals Model.equipment_group_id.
          3. Join Model to AssetNumber on Model.id equals AssetNumber.model_id.
          4. Filter by the specified asset_number_id to ultimately extract the Area.id.

        Parameters:
            session: SQLAlchemy session object used for querying.
            asset_number_id: The id of the AssetNumber record.

        Returns:
            The area_id associated with the asset_number, or None if no matching record is found.
        """
        logger.info(f"========== GETTING AREA FOR ASSET ID {asset_number_id} ==========")
        logger.debug(f"Querying for area_id using asset_number_id: {asset_number_id}")

        try:
            # Try to get the equipment_group_id first for more detailed logging
            equipment_group_id = cls.get_equipment_group_id_by_asset_number_id(session, asset_number_id)

            if equipment_group_id is not None:
                logger.debug(f"Found equipment_group_id: {equipment_group_id} for asset_number_id: {asset_number_id}")

                # Query directly using the equipment group ID for better performance
                area_id = session.query(EquipmentGroup.area_id).filter(EquipmentGroup.id == equipment_group_id).scalar()

                if area_id is not None:
                    logger.info(f"Found area_id: {area_id} via equipment_group_id {equipment_group_id}")

                    # Get area details for better logging
                    try:
                        area = session.query(Area).filter(Area.id == area_id).first()
                        if area:
                            logger.debug(f"Area details: ID={area.id}, Name={area.name}")
                    except Exception as e:
                        logger.warning(f"Error getting area details: {e}")
                else:
                    logger.warning(f"No area_id found for equipment_group_id: {equipment_group_id}")

                    # Fall back to the join method
                    logger.debug(f"Falling back to join query method")
                    area_id = (
                        session.query(Area.id)
                        .join(EquipmentGroup, EquipmentGroup.area_id == Area.id)
                        .join(Model, Model.equipment_group_id == EquipmentGroup.id)
                        .join(AssetNumber, AssetNumber.model_id == Model.id)
                        .filter(AssetNumber.id == asset_number_id)
                        .scalar()
                    )
            else:
                # If we couldn't get the equipment_group_id, use the join method directly
                logger.debug(f"No equipment_group_id found, using join query method directly")
                area_id = (
                    session.query(Area.id)
                    .join(EquipmentGroup, EquipmentGroup.area_id == Area.id)
                    .join(Model, Model.equipment_group_id == EquipmentGroup.id)
                    .join(AssetNumber, AssetNumber.model_id == Model.id)
                    .filter(AssetNumber.id == asset_number_id)
                    .scalar()
                )

            if area_id is not None:
                logger.info(f"Final result: Found area_id: {area_id} for asset_number_id: {asset_number_id}")
            else:
                logger.warning(f"Final result: No area found for asset_number_id: {asset_number_id}")

            return area_id
        except Exception as e:
            logger.error(f"Error getting area_id for asset_number_id {asset_number_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            logger.info(f"========== AREA SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def get_position_ids_by_asset_number_id(cls, session, asset_number_id):
        """
        Given an asset_number_id, retrieves all Position IDs that reference this asset_number.

        This method performs a query on the Position table where the asset_number_id
        matches the provided value. It returns a list of Position.id values.

        Parameters:
            session: SQLAlchemy session object used for querying.
            asset_number_id: The id value of the AssetNumber record.

        Returns:
            A list of Position IDs associated with the given asset_number_id.
            If no matching positions are found, an empty list is returned.
        """
        logger.info(f"========== GETTING POSITIONS FOR ASSET ID {asset_number_id} ==========")
        logger.debug(f"Querying for all Position IDs with asset_number_id: {asset_number_id}")

        try:
            # Get the asset details for more context in logging
            asset = session.query(cls).filter(cls.id == asset_number_id).first()
            if asset:
                logger.debug(f"Asset details: ID={asset.id}, Number={asset.number}, " +
                             f"Description={asset.description or 'None'}, Model ID={asset.model_id}")

            # Execute the query to get positions
            results = session.query(Position.id).filter(Position.asset_number_id == asset_number_id).all()
            position_ids = [pos_id for (pos_id,) in results]

            # Log detailed information about the results
            if position_ids:
                logger.info(
                    f"Found {len(position_ids)} Position(s) for asset_number_id: {asset_number_id}: {position_ids}")

                # Log details about each position
                for i, pos_id in enumerate(position_ids):
                    try:
                        position = session.query(Position).filter(Position.id == pos_id).first()
                        if position:
                            logger.debug(f"Position #{i + 1}: ID={pos_id}, " +
                                         f"Area ID={position.area_id}, " +
                                         f"Group ID={position.equipment_group_id}, " +
                                         f"Model ID={position.model_id}, " +
                                         f"Location ID={position.location_id}")

                            # Try to get location name for more context
                            if position.location_id:
                                location = session.query(Location).filter(Location.id == position.location_id).first()
                                if location:
                                    logger.debug(f"  -> Location: ID={location.id}, Name={location.name}")
                    except Exception as e:
                        logger.warning(f"Error getting details for position ID {pos_id}: {e}")
            else:
                logger.warning(f"No Positions found for asset_number_id: {asset_number_id}")

            return position_ids
        except Exception as e:
            logger.error(f"Error getting position_ids for asset_number_id {asset_number_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            logger.info(f"========== POSITION SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def search_asset_numbers(cls, session, query, limit=10):
        """
        Searches for asset numbers that match the provided query using
        a case-insensitive partial match. Useful for autocomplete or dynamic
        search interfaces.

        Parameters:
            session: SQLAlchemy session object used for querying.
            query: The partial asset number string input by the user.
            limit: Maximum number of results to return (default is 10).

        Returns:
            A list of dictionaries, each containing details about an asset:
              - id: The asset's unique identifier.
              - number: The asset number.
              - description: The asset description.
              - model_id: The associated model ID.
            If no records match, an empty list is returned.
        """
        logger.info("========== ASSET NUMBER AUTOCOMPLETE SEARCH ==========")
        logger.debug(f"Initiating search for asset numbers with query: '{query}'")

        try:
            # If the query is empty, just return an empty list early
            if not query:
                logger.debug("Empty query received; returning empty result set.")
                return []

            # Create a search pattern for a partial, case-insensitive match.
            search_pattern = f"%{query}%"
            logger.debug(f"Using search pattern: '{search_pattern}'")

            # Query for matching asset numbers; you can adjust the limit as needed.
            results = session.query(cls).filter(cls.number.ilike(search_pattern)).limit(limit).all()

            if results:
                assets = []
                # Loop through the found results to build a structured list with detailed logging
                for asset in results:
                    asset_details = {
                        "id": asset.id,
                        "number": asset.number,
                        "description": asset.description,
                        "model_id": asset.model_id
                    }
                    assets.append(asset_details)
                    logger.debug(f"Found asset: {asset_details}")

                logger.info(f"Found {len(assets)} asset(s) matching query '{query}'.")
                return assets
            else:
                logger.warning(f"No assets found matching query '{query}'.")
                return []
        except Exception as e:
            logger.error(f"Error searching for asset numbers with query '{query}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            logger.info("========== ASSET NUMBER AUTOCOMPLETE SEARCH COMPLETE ==========")

    @classmethod
    @with_request_id
    def add_asset_number(cls, session, number, model_id, description=None, request_id=None):
        """
        Add a new asset number to the database.

        Args:
            session: SQLAlchemy database session
            number (str): Asset number
            model_id (int): ID of the model this asset number belongs to
            description (str, optional): Description of the asset number
            request_id (str, optional): Unique identifier for the request

        Returns:
            AssetNumber: The newly created asset number object
        """
        new_asset_number = cls(
            number=number,
            model_id=model_id,
            description=description
        )

        session.add(new_asset_number)
        session.commit()

        logger.info(f"Created new asset number: {number} for model ID {model_id}")
        return new_asset_number

    @classmethod
    @with_request_id
    def delete_asset_number(cls, session, asset_number_id, request_id=None):
        """
        Delete an asset number from the database.

        Args:
            session: SQLAlchemy database session
            asset_number_id (int): ID of the asset number to delete
            request_id (str, optional): Unique identifier for the request

        Returns:
            bool: True if deletion was successful, False if asset number not found
        """
        asset_number = session.query(cls).filter(cls.id == asset_number_id).first()

        if asset_number:
            session.delete(asset_number)
            session.commit()
            logger.info(f"Deleted asset number ID {asset_number_id}")
            return True
        else:
            logger.warning(f"Failed to delete asset number ID {asset_number_id} - not found")
            return False

    @classmethod
    @with_request_id
    def find_related_entities(cls, session, identifier, is_id=True, request_id=None):
        """
        Find all related entities for an asset number, traversing both up and down
        the hierarchy: Area → EquipmentGroup → Model → AssetNumber → Position.

        Args:
            session: SQLAlchemy database session
            identifier: Either asset_number ID (int) or number (str)
            is_id (bool): If True, identifier is an ID, otherwise it's a number
            request_id (str, optional): Unique identifier for the request

        Returns:
            dict: Dictionary containing:
                - 'asset_number': The found asset number object
                - 'upward': Dictionary containing 'model', 'equipment_group', and 'area'
                - 'downward': Dictionary containing:
                    - 'positions': List of all positions related to this asset number
        """
        # Find the asset number
        if is_id:
            asset_number = session.query(cls).filter(cls.id == identifier).first()
        else:
            asset_number = session.query(cls).filter(cls.number == identifier).first()

        if not asset_number:
            logger.warning(f"Asset number not found for identifier: {identifier}")
            return None

        # Going upward in the hierarchy
        upward = {
            'model': asset_number.model,
            'equipment_group': asset_number.model.equipment_group if asset_number.model else None,
            'area': asset_number.model.equipment_group.area if asset_number.model and asset_number.model.equipment_group else None
        }

        # Going downward in the hierarchy
        downward = {
            'positions': asset_number.position
        }

        logger.info(f"Found related entities for asset number ID {asset_number.id}")
        return {
            'asset_number': asset_number,
            'upward': upward,
            'downward': downward
        }

class Location(Base):
    __tablename__ = 'location'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    model_id = Column(Integer, ForeignKey('model.id'))
    description = Column(String, nullable=True)

    model = relationship("Model", back_populates="location")
    position = relationship("Position", back_populates="location")
    subassembly = relationship("Subassembly", back_populates="location")

    @classmethod
    @with_request_id
    def add_location(cls, session, name, model_id, description=None, request_id=None):
        """
        Add a new location to the database.

        Args:
            session: SQLAlchemy database session
            name (str): Name of the location
            model_id (int): ID of the model this location belongs to
            description (str, optional): Description of the location
            request_id (str, optional): Unique identifier for the request

        Returns:
            Location: The newly created location object
        """
        new_location = cls(
            name=name,
            model_id=model_id,
            description=description
        )

        session.add(new_location)
        session.commit()

        logger.info(f"Created new location: {name} for model ID {model_id}")
        return new_location

    @classmethod
    @with_request_id
    def delete_location(cls, session, location_id, request_id=None):
        """
        Delete a location from the database.

        Args:
            session: SQLAlchemy database session
            location_id (int): ID of the location to delete
            request_id (str, optional): Unique identifier for the request

        Returns:
            bool: True if deletion was successful, False if location not found
        """
        location = session.query(cls).filter(cls.id == location_id).first()

        if location:
            session.delete(location)
            session.commit()
            logger.info(f"Deleted location ID {location_id}")
            return True
        else:
            logger.warning(f"Failed to delete location ID {location_id} - not found")
            return False

    @classmethod
    @with_request_id
    def find_related_entities(cls, session, identifier, is_id=True, request_id=None):
        """
        Find all related entities for a location, traversing both up and down
        the hierarchy: Area → EquipmentGroup → Model → Location → (Position, Subassembly).

        Args:
            session: SQLAlchemy database session
            identifier: Either location ID (int) or name (str)
            is_id (bool): If True, identifier is an ID, otherwise it's a name
            request_id (str, optional): Unique identifier for the request

        Returns:
            dict: Dictionary containing:
                - 'location': The found location object
                - 'upward': Dictionary containing 'model', 'equipment_group', and 'area'
                - 'downward': Dictionary containing:
                    - 'positions': List of all positions related to this location
                    - 'subassemblies': List of all subassemblies related to this location
        """
        # Find the location
        if is_id:
            location = session.query(cls).filter(cls.id == identifier).first()
        else:
            location = session.query(cls).filter(cls.name == identifier).first()

        if not location:
            logger.warning(f"Location not found for identifier: {identifier}")
            return None

        # Going upward in the hierarchy
        upward = {
            'model': location.model,
            'equipment_group': location.model.equipment_group if location.model else None,
            'area': location.model.equipment_group.area if location.model and location.model.equipment_group else None
        }

        # Going downward in the hierarchy
        downward = {
            'positions': location.position,
            'subassemblies': location.subassembly
        }

        logger.info(f"Found related entities for location ID {location.id}")
        return {
            'location': location,
            'upward': upward,
            'downward': downward
        }

class Subassembly(Base):
    __tablename__ = 'subassembly'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    location_id = Column(Integer, ForeignKey('location.id'))
    description = Column(String, nullable=True)  # CHANGED to allow NULL
    # Relationships
    location = relationship("Location", back_populates="subassembly")
    component_assembly = relationship("ComponentAssembly", back_populates="subassembly")
    position = relationship("Position", back_populates="subassembly")

class ComponentAssembly(Base):
    # specific group of components of a subassembly
    __tablename__ = 'component_assembly'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    subassembly_id = Column(Integer, ForeignKey('subassembly.id'), nullable=False)

    # Relationships
    subassembly = relationship("Subassembly", back_populates="component_assembly")
    assembly_view = relationship("AssemblyView", back_populates="component_assembly")
    position = relationship("Position", back_populates="component_assembly")

class AssemblyView(Base): # # TODO Rename to ComponentView
    __tablename__ = 'assembly_view'
    # location within component_assembly. example front,back,right-side top left ect...
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    component_assembly_id = Column(Integer, ForeignKey('component_assembly.id'), nullable=False)
    # Relationships
    component_assembly = relationship("ComponentAssembly", back_populates="assembly_view")
    position = relationship("Position", back_populates="assembly_view")

class Container(Base):
    __tablename__ = "container"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("position.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # A container sits on an equipment Position
    position = relationship("Position", back_populates="container")

    # A container can hold shelves
    shelves = relationship(
        "Shelf",
        back_populates="container",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("position_id", "code", name="uq_container_pos_code"),
        Index("ix_container_code", "code"),
    )

    @staticmethod
    def _norm(code: str, name: str) -> tuple[str, str]:
        c = (code or "").strip()
        n = (name or "").strip()
        if not c or not n:
            raise ValueError("code and name are required.")
        return c, n


    @classmethod
    @with_request_id
    def add_container(cls, session: Session, position_id: int, code: str, name: str,
                      description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        obj = cls(position_id=position_id, code=code, name=name,
                  description=(description or "").strip() or None)
        session.add(obj)
        try:
            session.commit()
            info_id("Created Container '%s' on position %s", code, position_id, request_id=request_id)
            return obj
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to create Container", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def delete_container(cls, session: Session, container_id: int, request_id=None) -> bool:
        obj = session.get(cls, container_id)
        if not obj:
            warning_id("Container %s not found", container_id, request_id=request_id)
            return False
        session.delete(obj)
        try:
            session.commit()
            info_id("Deleted Container %s", container_id, request_id=request_id)
            return True
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to delete Container", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def find_or_create(cls, session: Session, position_id: int, code: str, name: str,
                       description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        existing = session.execute(
            select(cls).where(cls.position_id == position_id, cls.code == code)
        ).scalar_one_or_none()
        if existing:
            info_id("Found Container '%s' on position %s", code, position_id, request_id=request_id)
            return existing
        return cls.add_container(session, position_id, code, name,
                                 description=description, request_id=request_id)

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, container_id: int, request_id=None):
        obj = session.execute(
            select(cls).options(joinedload(cls.shelves)).where(cls.id == container_id)
        ).scalar_one_or_none()
        if not obj:
            logger.warning(f"Container {container_id} not found", extra={'request_id': request_id} if request_id else None)
            return None
        return {"container": obj, "downward": {"shelves": obj.shelves}}

class Shelf(Base):
    __tablename__ = "shelf"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("position.id", ondelete="CASCADE"), nullable=False)
    # shelf can be directly on equipment (no container)
    container_id = Column(Integer, ForeignKey("container.id", ondelete="CASCADE"), nullable=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    position = relationship("Position", back_populates="shelf")
    container = relationship("Container", back_populates="shelves")
    drawers = relationship(
        "Drawer",
        back_populates="shelf",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # unique within a position and (optionally) within a specific container
        UniqueConstraint("position_id", "container_id", "code", name="uq_shelf_pos_container_code"),
        Index("ix_shelf_code", "code"),
    )

    @staticmethod
    def _norm(code: str, name: str) -> tuple[str, str]:
        c = (code or "").strip()
        n = (name or "").strip()
        if not c or not n:
            raise ValueError("code and name are required.")
        return c, n

    @classmethod
    @with_request_id
    def add_shelf(
        cls,
        session: Session,
        position_id: int,
        code: str,
        name: str,
        container_id: int | None = None,
        description: str | None = None,
        request_id=None,
    ):
        code, name = cls._norm(code, name)
        obj = cls(
            position_id=position_id,
            container_id=container_id,
            code=code,
            name=name,
            description=(description or "").strip() or None,
        )
        session.add(obj)
        try:
            session.commit()
            where = f"container={container_id}" if container_id else "no-container"
            # NOTE: request_id passed positionally (last arg)
            info_id("Created Shelf '%s' on position %s (%s)", code, position_id, where, request_id)
            return obj
        except SQLAlchemyError:
            session.rollback()
            # positional request_id must come BEFORE any keyword args (e.g., exc_info)
            error_id("Failed to create Shelf", request_id, exc_info=True)
            raise

    @classmethod
    @with_request_id
    def delete_shelf(cls, session: Session, shelf_id: int, request_id=None) -> bool:
        obj = session.get(cls, shelf_id)
        if not obj:
            warning_id("Shelf %s not found", shelf_id, request_id)
            return False
        session.delete(obj)
        try:
            session.commit()
            info_id("Deleted Shelf %s", shelf_id, request_id)
            return True
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to delete Shelf", request_id, exc_info=True)
            raise

    @classmethod
    @with_request_id
    def find_or_create(
        cls,
        session: Session,
        position_id: int,
        code: str,
        name: str,
        container_id: int | None = None,
        description: str | None = None,
        request_id=None,
    ):
        code, name = cls._norm(code, name)
        existing = session.execute(
            select(cls).where(
                cls.position_id == position_id,
                (cls.container_id.is_(container_id) if container_id is None else cls.container_id == container_id),
                cls.code == code,
            )
        ).scalar_one_or_none()
        if existing:
            info_id("Found Shelf '%s' on position %s", code, position_id, request_id)
            return existing
        return cls.add_shelf(
            session,
            position_id,
            code,
            name,
            container_id=container_id,
            description=description,
            request_id=request_id,
        )

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, shelf_id: int, request_id=None):
        obj = session.execute(
            select(cls).options(joinedload(cls.drawers)).where(cls.id == shelf_id)
        ).scalar_one_or_none()
        if not obj:
            warning_id("Shelf %s not found", shelf_id, request_id)
            return None
        return {"shelf": obj, "downward": {"drawers": obj.drawers}}


class Drawer(Base):
    __tablename__ = "drawer"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("position.id", ondelete="CASCADE"), nullable=False)
    # drawer can be directly on equipment (no shelf)
    shelf_id = Column(Integer, ForeignKey("shelf.id", ondelete="CASCADE"), nullable=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    position = relationship("Position", back_populates="drawer")
    shelf = relationship("Shelf", back_populates="drawers")
    slots = relationship(
        "DrawerSlot",
        back_populates="drawer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("position_id", "shelf_id", "code", name="uq_drawer_pos_shelf_code"),
        Index("ix_drawer_code", "code"),
    )

    @staticmethod
    def _norm(code: str, name: str) -> tuple[str, str]:
        c = (code or "").strip()
        n = (name or "").strip()
        if not c or not n:
            raise ValueError("code and name are required.")
        return c, n

    @classmethod
    @with_request_id
    def add_drawer(
        cls,
        session: Session,
        position_id: int,
        code: str,
        name: str,
        shelf_id: int | None = None,
        description: str | None = None,
        request_id=None,
    ):
        code, name = cls._norm(code, name)
        obj = cls(
            position_id=position_id,
            shelf_id=shelf_id,
            code=code,
            name=name,
            description=(description or "").strip() or None,
        )
        session.add(obj)
        try:
            session.commit()
            where = f"shelf={shelf_id}" if shelf_id else "no-shelf"
            info_id(
                "Created Drawer '%s' on position %s (%s)",
                code, position_id, where, request_id=request_id
            )
            return obj
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to create Drawer", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def delete_drawer(cls, session: Session, drawer_id: int, request_id=None) -> bool:
        obj = session.get(cls, drawer_id)
        if not obj:
            warning_id("Drawer %s not found", drawer_id, request_id=request_id)
            return False
        session.delete(obj)
        try:
            session.commit()
            info_id("Deleted Drawer %s", drawer_id, request_id=request_id)
            return True
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to delete Drawer", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def find_or_create(
        cls,
        session: Session,
        position_id: int,
        code: str,
        name: str,
        shelf_id: int | None = None,
        description: str | None = None,
        request_id=None,
    ):
        code, name = cls._norm(code, name)
        existing = session.execute(
            select(cls).where(
                cls.position_id == position_id,
                (cls.shelf_id.is_(shelf_id) if shelf_id is None else cls.shelf_id == shelf_id),
                cls.code == code,
            )
        ).scalar_one_or_none()
        if existing:
            info_id("Found Drawer '%s' on position %s", code, position_id, request_id=request_id)
            return existing
        return cls.add_drawer(
            session, position_id, code, name, shelf_id=shelf_id, description=description, request_id=request_id
        )

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, drawer_id: int, request_id=None):
        obj = session.execute(
            select(cls).options(joinedload(cls.slots)).where(cls.id == drawer_id)
        ).scalar_one_or_none()
        if not obj:
            warning_id("Drawer %s not found", drawer_id, request_id=request_id)
            return None
        return {"drawer": obj, "downward": {"slots": obj.slots}}

class DrawerSlot(Base):
    """
    A specific "position in drawer" — addressable by a label (e.g., 'A5') or row/col.
    """
    __tablename__ = "drawer_slot"

    id = Column(Integer, primary_key=True)
    drawer_id = Column(Integer, ForeignKey("drawer.id", ondelete="CASCADE"), nullable=False)

    # Either use a human label (e.g., "A5") or row/col, or both.
    slot_label = Column(String, nullable=True)
    row_index = Column(Integer, nullable=True)
    col_index = Column(Integer, nullable=True)
    note = Column(String, nullable=True)

    drawer = relationship("Drawer", back_populates="slots")

    __table_args__ = (
        # Prevent duplicate labels within the same drawer
        UniqueConstraint("drawer_id", "slot_label", name="uq_drawer_slot_label"),
        Index("ix_drawer_slot_label", "slot_label"),
    )

    inventories = relationship(
        "Inventory",
        back_populates="drawer_slot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    @classmethod
    @with_request_id
    def add_slot(
        cls,
        session: Session,
        drawer_id: int,
        *,
        slot_label: str | None = None,
        row_index: int | None = None,
        col_index: int | None = None,
        note: str | None = None,
        request_id=None,
    ):
        if not slot_label and row_index is None and col_index is None:
            raise ValueError("Provide slot_label or row/col to identify a slot.")
        obj = cls(
            drawer_id=drawer_id,
            slot_label=(slot_label or "").strip() or None,
            row_index=row_index,
            col_index=col_index,
            note=(note or "").strip() or None,
        )
        session.add(obj)
        try:
            session.commit()
            where = slot_label or f"r{row_index}c{col_index}"
            info_id("Created DrawerSlot '%s' in drawer %s", where, drawer_id, request_id=request_id)
            return obj
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to create DrawerSlot", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def delete_slot(cls, session: Session, slot_id: int, request_id=None) -> bool:
        obj = session.get(cls, slot_id)
        if not obj:
            warning_id("DrawerSlot %s not found", slot_id, request_id=request_id)
            return False
        session.delete(obj)
        try:
            session.commit()
            info_id("Deleted DrawerSlot %s", slot_id, request_id=request_id)
            return True
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to delete DrawerSlot", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def find_or_create(
        cls,
        session: Session,
        drawer_id: int,
        *,
        slot_label: str | None = None,
        row_index: int | None = None,
        col_index: int | None = None,
        note: str | None = None,
        request_id=None,
    ):
        if slot_label:
            existing = session.execute(
                select(cls).where(cls.drawer_id == drawer_id, cls.slot_label == slot_label.strip())
            ).scalar_one_or_none()
            if existing:
                return existing
        # (Optional) add UNIQUE(drawer_id,row_index,col_index) if you need strict grid semantics.
        return cls.add_slot(
            session,
            drawer_id,
            slot_label=slot_label,
            row_index=row_index,
            col_index=col_index,
            note=note,
            request_id=request_id,
        )

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, slot_id: int, request_id=None):
        obj = session.get(cls, slot_id)
        if not obj:
            warning_id("DrawerSlot %s not found", slot_id, request_id=request_id)
            return None
        return {"drawer_slot": obj, "downward": {}}


class Part(Base):
    __tablename__ = "part"

    id            = Column(Integer, primary_key=True)

    # MP2/SPC-style fields
    part_number   = Column(String, nullable=False, unique=True, index=True)  # ITEMNUM
    name          = Column(String, nullable=False)                           # DESCRIPTION
    oem_mfg       = Column(String, nullable=True)                            # OEMMFG (Manufacturer)
    model         = Column(String, nullable=True)                            # MODEL (MFG Part Number)
    class_flag    = Column(String, nullable=True)                            # Class Flag (Category)
    ud6           = Column(String, nullable=True)                            # UD6
    type          = Column(String, nullable=True)                            # TYPE
    notes         = Column(String, nullable=True)                            # Notes (Long Description)
    documentation = Column(String, nullable=True)                            # Specifications

    # Link to stock records
    inventories = relationship(
        "Inventory",
        back_populates="part",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_part_name", "name"),  # keep name index for quick lookups
    )

    # ------------- helpers -------------
    @staticmethod
    def _norm(part_number: str, name: str) -> tuple[str, str]:
        pn = (part_number or "").strip()
        nm = (name or "").strip()
        if not pn or not nm:
            raise ValueError("part_number and name are required.")
        return pn, nm

    # ------------- API -------------
    @classmethod
    @with_request_id
    def find_or_create(
        cls,
        session: Session,
        *,
        part_number: str,
        name: str,
        oem_mfg: Optional[str] = None,
        model: Optional[str] = None,
        class_flag: Optional[str] = None,
        ud6: Optional[str] = None,
        type: Optional[str] = None,
        notes: Optional[str] = None,
        documentation: Optional[str] = None,
        request_id=None,
    ) -> "Part":
        part_number, name = cls._norm(part_number, name)
        existing = session.execute(select(cls).where(cls.part_number == part_number)).scalar_one_or_none()
        if existing:
            logger.info(f"Found Part part_number={part_number}", extra={'request_id': request_id} if request_id else None)
            return existing

        obj = cls(
            part_number=part_number,
            name=name,
            oem_mfg=(oem_mfg or "").strip() or None,
            model=(model or "").strip() or None,
            class_flag=(class_flag or "").strip() or None,
            ud6=(ud6 or "").strip() or None,
            type=(type or "").strip() or None,
            notes=(notes or "").strip() or None,
            documentation=(documentation or "").strip() or None,
        )
        session.add(obj)
        try:
            session.commit()
            logger.info(f"Created Part part_number={part_number}", extra={'request_id': request_id} if request_id else None)
            return obj
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create Part", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    def search(cls, session: Session, q: str, limit: int = 50) -> List["Part"]:
        if not q:
            return []
        like = f"%{q.strip()}%"
        stmt = (
            select(cls)
            .where(
                (cls.part_number.ilike(like)) |
                (cls.name.ilike(like)) |
                (cls.model.ilike(like)) |
                (cls.oem_mfg.ilike(like))
            )
            .order_by(cls.part_number.asc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def __repr__(self) -> str:
        return f"<Part id={self.id} part_number={self.part_number!r} name={self.name!r}>"

class Inventory(Base):
    """
    Stock record: how much of a Part exists at a given drawer slot.
        Inventory.part_id        -> Part.id
        Inventory.drawer_slot_id -> DrawerSlot.id
    """
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("part.id", ondelete="CASCADE"), nullable=False)
    drawer_slot_id = Column(Integer, ForeignKey("drawer_slot.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)

    part = relationship("Part", back_populates="inventories")
    drawer_slot = relationship("DrawerSlot", back_populates="inventories")

    __table_args__ = (
        UniqueConstraint("part_id", "drawer_slot_id", name="uq_inventory_part_slot"),
        Index("ix_inventory_slot", "drawer_slot_id"),
    )

    # -------- adjustments / transfers --------
    @classmethod
    @with_request_id
    def adjust(
        cls,
        session: Session,
        *,
        part_id: int,
        drawer_slot_id: int,
        delta: int,
        request_id=None,
    ) -> "Inventory":
        """Add/remove quantity at a slot (positive delta adds, negative removes)."""
        if delta == 0:
            raise ValueError("delta must be non-zero.")

        row = session.execute(
            select(cls).where(cls.part_id == part_id, cls.drawer_slot_id == drawer_slot_id)
        ).scalar_one_or_none()

        if row:
            new_qty = (row.quantity or 0) + delta
            if new_qty < 0:
                raise ValueError(f"Insufficient stock (have {row.quantity}, need {-delta}).")
            row.quantity = new_qty
        else:
            if delta < 0:
                raise ValueError("Cannot create inventory with negative quantity.")
            row = cls(part_id=part_id, drawer_slot_id=drawer_slot_id, quantity=delta)
            session.add(row)

        try:
            session.commit()
            info_id(
                "Adjusted stock part=%s slot=%s by %s → qty=%s",
                part_id, drawer_slot_id, delta, row.quantity, request_id=request_id
            )
            return row
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to adjust inventory", exc_info=True, request_id=request_id)
            raise

    @classmethod
    @with_request_id
    def transfer(
        cls,
        session: Session,
        *,
        part_id: int,
        from_slot_id: int,
        to_slot_id: int,
        qty: int,
        request_id=None,
    ) -> tuple["Inventory", "Inventory"]:
        """Move qty of a part from one slot to another."""
        if qty <= 0:
            raise ValueError("qty must be positive.")

        # decrement source
        src = session.execute(
            select(cls).where(cls.part_id == part_id, cls.drawer_slot_id == from_slot_id)
        ).scalar_one_or_none()
        if not src or (src.quantity or 0) < qty:
            have = src.quantity if src else 0
            raise ValueError(f"Insufficient stock at source (have {have}, need {qty}).")
        src.quantity = src.quantity - qty

        # increment destination
        dst = session.execute(
            select(cls).where(cls.part_id == part_id, cls.drawer_slot_id == to_slot_id)
        ).scalar_one_or_none()
        if dst:
            dst.quantity = (dst.quantity or 0) + qty
        else:
            dst = cls(part_id=part_id, drawer_slot_id=to_slot_id, quantity=qty)
            session.add(dst)

        try:
            session.commit()
            info_id(
                "Transferred part=%s qty=%s from slot=%s to slot=%s",
                part_id, qty, from_slot_id, to_slot_id, request_id=request_id
            )
            return src, dst
        except SQLAlchemyError:
            session.rollback()
            error_id("Failed to transfer inventory", exc_info=True, request_id=request_id)
            raise

class DrawingType(Enum):
    ELECTRICAL = "Electrical"
    MECHANICAL = "Mechanical"
    PIPING = "Piping"
    INSTRUMENTATION = "Instrumentation"
    CIVIL = "Civil"
    STRUCTURAL = "Structural"
    PROCESS = "Process"
    ASSEMBLY = "Assembly"
    DETAIL = "Detail"
    SCHEMATIC = "Schematic"
    LAYOUT = "Layout"
    OTHER = "Other"

class Drawing(Base):
    __tablename__ = 'drawing'

    id = Column(Integer, primary_key=True)
    drw_equipment_name = Column(String)
    drw_number = Column(String)
    drw_name = Column(String)
    drw_revision = Column(String)
    drw_spare_part_number = Column(String)
    drw_type = Column(String, default="Other")  # enum value stored as string
    file_path = Column(String, nullable=False)

    # Associations (keep/remove to match your schema)
    drawing_position = relationship("DrawingPositionAssociation", back_populates="drawing")
    #drawing_problem  = relationship("DrawingProblemAssociation",    back_populates="drawing")
    #drawing_task     = relationship("DrawingTaskAssociation",       back_populates="drawing")
    #drawing_part     = relationship("DrawingPartAssociation",       back_populates="drawing")

    @classmethod
    @with_request_id
    def search(cls,
               search_text: Optional[str] = None,
               fields: Optional[List[str]] = None,
               exact_match: bool = False,
               drawing_id: Optional[int] = None,
               drw_equipment_name: Optional[str] = None,
               drw_number: Optional[str] = None,
               drw_name: Optional[str] = None,
               drw_revision: Optional[str] = None,
               drw_spare_part_number: Optional[str] = None,
               drw_type: Optional[str] = None,
               file_path: Optional[str] = None,
               limit: int = 100,
               request_id: Optional[str] = None,
               session: Optional[Session] = None) -> List['Drawing']:

        rid = request_id or get_request_id()

        # session handling
        db_config = DatabaseConfig()
        created = False
        if session is None:
            session = db_config.get_main_session()
            created = True

        try:
            query = session.query(cls)
            filters = []

            if search_text:
                search_text = search_text.strip()
                if search_text:
                    if not fields:
                        fields = ['drw_number', 'drw_name', 'drw_equipment_name', 'drw_spare_part_number', 'drw_type']
                    text_filters = []
                    for fname in fields:
                        if hasattr(cls, fname):
                            col = getattr(cls, fname)
                            text_filters.append(col == search_text if exact_match else col.ilike(f"%{search_text}%"))
                    if text_filters:
                        filters.append(or_(*text_filters))

            def add_filter(col, val):
                if val is None: return
                filters.append(col == val if exact_match else col.ilike(f"%{val}%"))

            if drawing_id is not None: filters.append(cls.id == drawing_id)
            add_filter(cls.drw_equipment_name, drw_equipment_name)
            add_filter(cls.drw_number,         drw_number)
            add_filter(cls.drw_name,           drw_name)
            add_filter(cls.drw_revision,       drw_revision)
            add_filter(cls.drw_spare_part_number, drw_spare_part_number)
            add_filter(cls.drw_type,           drw_type)
            add_filter(cls.file_path,          file_path)

            if filters:
                query = query.filter(and_(*filters))

            return query.limit(limit).all()

        except Exception as e:
            # optionally log with your logger here
            raise
        finally:
            if created:
                session.close()

    @classmethod
    @with_request_id
    def get_by_id(cls, drawing_id: int, request_id: Optional[str] = None, session: Optional[Session] = None) -> Optional['Drawing']:
        rid = request_id or get_request_id()
        db_config = DatabaseConfig()
        created = False
        if session is None:
            session = db_config.get_main_session()
            created = True
        try:
            return session.query(cls).filter(cls.id == drawing_id).first()
        finally:
            if created:
                session.close()

    @classmethod
    def get_available_types(cls) -> List[str]:
        return [t.value for t in DrawingType]

    @classmethod
    @with_request_id
    def search_by_type(cls, drawing_type: str, request_id: Optional[str] = None,
                       session: Optional[Session] = None) -> List['Drawing']:
        return cls.search(drw_type=drawing_type, request_id=request_id, session=session)

class ImagePositionAssociation(Base):
    __tablename__ = 'image_position_association'
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('position.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('image_id', 'position_id', name='uq_image_position'),
        Index('ix_image_position_image_id', 'image_id'),
        Index('ix_image_position_position_id', 'position_id'),
    )

    image = relationship("Image", back_populates="image_position_association")
    position = relationship("Position", back_populates="image_position_association")

    @classmethod
    @with_request_id
    def associate_image_position(cls,
                                 image_id: int,
                                 position_id: int,
                                 request_id: Optional[str] = None,
                                 session: Optional[Session] = None) -> Optional['ImagePositionAssociation']:
        """
        Associate an image with a position.

        Args:
            image_id: ID of the image to associate
            position_id: ID of the position to associate
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            The created ImagePositionAssociation object if successful, None otherwise
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for ImagePositionAssociation.associate_image_position", rid)

        # Log the operation with request ID
        debug_id(
            f"Starting ImagePositionAssociation.associate_image_position with parameters: image_id={image_id}, position_id={position_id}",
            rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("ImagePositionAssociation.associate_image_position", rid):

                # Check if image exists
                image = session.query(Image).filter(Image.id == image_id).first()
                if not image:
                    error_id(
                        f"Error in ImagePositionAssociation.associate_image_position: Image with ID {image_id} not found",
                        rid)
                    return None

                # Check if position exists
                position = session.query(Position).filter(Position.id == position_id).first()
                if not position:
                    error_id(
                        f"Error in ImagePositionAssociation.associate_image_position: Position with ID {position_id} not found",
                        rid)
                    return None

                # Check if association already exists
                existing = session.query(cls).filter(
                    cls.image_id == image_id,
                    cls.position_id == position_id
                ).first()

                if existing:
                    debug_id(f"Association between image {image_id} and position {position_id} already exists", rid)
                    return existing

                # Create new association
                association = cls(image_id=image_id, position_id=position_id)
                session.add(association)

                # Commit if we created the session
                if not session_provided:
                    session.commit()
                    debug_id(f"Committed new association between image {image_id} and position {position_id}", rid)

                return association

        except Exception as e:
            error_id(f"Error in ImagePositionAssociation.associate_image_position: {str(e)}", rid, exc_info=True)
            if not session_provided:
                session.rollback()
                debug_id(f"Rolled back transaction in ImagePositionAssociation.associate_image_position", rid)
            return None
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for ImagePositionAssociation.associate_image_position", rid)

    @classmethod
    @with_request_id
    def dissociate_image_position(cls,
                                  image_id: int,
                                  position_id: int,
                                  request_id: Optional[str] = None,
                                  session: Optional[Session] = None) -> bool:
        """
        Remove an association between an image and a position.

        Args:
            image_id: ID of the image to dissociate
            position_id: ID of the position to dissociate
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            True if the association was removed, False otherwise
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for ImagePositionAssociation.dissociate_image_position", rid)

        # Log the operation with request ID
        debug_id(
            f"Starting ImagePositionAssociation.dissociate_image_position with parameters: image_id={image_id}, position_id={position_id}",
            rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("ImagePositionAssociation.dissociate_image_position", rid):
                # Find the association
                association = session.query(cls).filter(
                    cls.image_id == image_id,
                    cls.position_id == position_id
                ).first()

                if not association:
                    debug_id(f"No association found between image {image_id} and position {position_id}", rid)
                    return False

                # Delete the association
                session.delete(association)

                # Commit if we created the session
                if not session_provided:
                    session.commit()
                    debug_id(f"Removed association between image {image_id} and position {position_id}", rid)

                return True

        except Exception as e:
            error_id(f"Error in ImagePositionAssociation.dissociate_image_position: {str(e)}", rid, exc_info=True)
            if not session_provided:
                session.rollback()
                debug_id(f"Rolled back transaction in ImagePositionAssociation.dissociate_image_position", rid)
            return False
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for ImagePositionAssociation.dissociate_image_position", rid)

    @classmethod
    @with_request_id
    def get_positions_by_image(cls,
                               image_id: Optional[int] = None,
                               title: Optional[str] = None,
                               description: Optional[str] = None,
                               file_path: Optional[str] = None,
                               position_id: Optional[int] = None,
                               area_id: Optional[int] = None,
                               equipment_group_id: Optional[int] = None,
                               model_id: Optional[int] = None,
                               asset_number_id: Optional[int] = None,
                               location_id: Optional[int] = None,
                               subassembly_id: Optional[int] = None,
                               component_assembly_id: Optional[int] = None,
                               assembly_view_id: Optional[int] = None,
                               site_location_id: Optional[int] = None,
                               exact_match: bool = False,
                               limit: int = 100,
                               request_id: Optional[str] = None,
                               session: Optional[Session] = None) -> List['Position']:
        """
        Get positions associated with images based on flexible search criteria.

        Args:
            image_id: Optional image ID to filter by
            title: Optional image title to filter by
            description: Optional image description to filter by
            file_path: Optional file path to filter by
            position_id: Optional position ID to filter by
            area_id: Optional area ID to filter by
            equipment_group_id: Optional equipment group ID to filter by
            model_id: Optional model ID to filter by
            asset_number_id: Optional asset number ID to filter by
            location_id: Optional location ID to filter by
            subassembly_id: Optional subassembly ID to filter by
            component_assembly_id: Optional component assembly ID to filter by
            assembly_view_id: Optional assembly view ID to filter by
            site_location_id: Optional site location ID to filter by
            exact_match: If True, performs exact matching instead of partial matching for string fields
            limit: Maximum number of results to return (default 100)
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            List of Position objects matching the search criteria
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for ImagePositionAssociation.get_positions_by_image", rid)

        # Log the search operation with request ID
        search_params = {
            'image_id': image_id,
            'title': title,
            'description': description,
            'file_path': file_path,
            'position_id': position_id,
            'area_id': area_id,
            'equipment_group_id': equipment_group_id,
            'model_id': model_id,
            'asset_number_id': asset_number_id,
            'location_id': location_id,
            'subassembly_id': subassembly_id,
            'component_assembly_id': component_assembly_id,
            'assembly_view_id': assembly_view_id,
            'site_location_id': site_location_id,
            'exact_match': exact_match,
            'limit': limit
        }
        # Filter out None values for cleaner logging
        logged_params = {k: v for k, v in search_params.items() if v is not None}
        debug_id(f"Starting ImagePositionAssociation.get_positions_by_image with parameters: {logged_params}", rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("ImagePositionAssociation.get_positions_by_image", rid):

                # Start with a query that joins Position and ImagePositionAssociation
                query = session.query(Position).join(cls, Position.id == cls.position_id).join(Image,
                                                                                               Image.id == cls.image_id)

                # Apply image filters
                if image_id is not None:
                    query = query.filter(Image.id == image_id)

                if title is not None:
                    if exact_match:
                        query = query.filter(Image.title == title)
                    else:
                        query = query.filter(Image.title.ilike(f"%{title}%"))

                if description is not None:
                    if exact_match:
                        query = query.filter(Image.description == description)
                    else:
                        query = query.filter(Image.description.ilike(f"%{description}%"))

                if file_path is not None:
                    if exact_match:
                        query = query.filter(Image.file_path == file_path)
                    else:
                        query = query.filter(Image.file_path.ilike(f"%{file_path}%"))

                # Apply position filters
                if position_id is not None:
                    query = query.filter(Position.id == position_id)

                if area_id is not None:
                    query = query.filter(Position.area_id == area_id)

                if equipment_group_id is not None:
                    query = query.filter(Position.equipment_group_id == equipment_group_id)

                if model_id is not None:
                    query = query.filter(Position.model_id == model_id)

                if asset_number_id is not None:
                    query = query.filter(Position.asset_number_id == asset_number_id)

                if location_id is not None:
                    query = query.filter(Position.location_id == location_id)

                if subassembly_id is not None:
                    query = query.filter(Position.subassembly_id == subassembly_id)

                if component_assembly_id is not None:
                    query = query.filter(Position.component_assembly_id == component_assembly_id)

                if assembly_view_id is not None:
                    query = query.filter(Position.assembly_view_id == assembly_view_id)

                if site_location_id is not None:
                    query = query.filter(Position.site_location_id == site_location_id)

                # Make results distinct to avoid duplicates
                query = query.distinct()

                # Apply limit
                query = query.limit(limit)

                # Execute query and log results
                results = query.all()
                debug_id(f"ImagePositionAssociation.get_positions_by_image completed, found {len(results)} positions",
                         rid)
                return results

        except Exception as e:
            error_id(f"Error in ImagePositionAssociation.get_positions_by_image: {str(e)}", rid, exc_info=True)
            return []
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for ImagePositionAssociation.get_positions_by_image", rid)

    @classmethod
    @with_request_id
    def get_images_by_position(cls,
                               position_id: Optional[int] = None,
                               area_id: Optional[int] = None,
                               equipment_group_id: Optional[int] = None,
                               model_id: Optional[int] = None,
                               asset_number_id: Optional[int] = None,
                               location_id: Optional[int] = None,
                               subassembly_id: Optional[int] = None,
                               component_assembly_id: Optional[int] = None,
                               assembly_view_id: Optional[int] = None,
                               site_location_id: Optional[int] = None,
                               image_id: Optional[int] = None,
                               title: Optional[str] = None,
                               description: Optional[str] = None,
                               file_path: Optional[str] = None,
                               exact_match: bool = False,
                               limit: int = 100,
                               request_id: Optional[str] = None,
                               session: Optional[Session] = None) -> List['Image']:
        """
        Get images associated with positions based on flexible search criteria.

        Args:
            position_id: Optional position ID to filter by
            area_id: Optional area ID to filter by
            equipment_group_id: Optional equipment group ID to filter by
            model_id: Optional model ID to filter by
            asset_number_id: Optional asset number ID to filter by
            location_id: Optional location ID to filter by
            subassembly_id: Optional subassembly ID to filter by
            component_assembly_id: Optional component assembly ID to filter by
            assembly_view_id: Optional assembly view ID to filter by
            site_location_id: Optional site location ID to filter by
            image_id: Optional image ID to filter by
            title: Optional image title to filter by
            description: Optional image description to filter by
            file_path: Optional file path to filter by
            exact_match: If True, performs exact matching instead of partial matching for string fields
            limit: Maximum number of results to return (default 100)
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            List of Image objects matching the search criteria
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for ImagePositionAssociation.get_images_by_position", rid)

        # Log the search operation with request ID
        search_params = {
            'position_id': position_id,
            'area_id': area_id,
            'equipment_group_id': equipment_group_id,
            'model_id': model_id,
            'asset_number_id': asset_number_id,
            'location_id': location_id,
            'subassembly_id': subassembly_id,
            'component_assembly_id': component_assembly_id,
            'assembly_view_id': assembly_view_id,
            'site_location_id': site_location_id,
            'image_id': image_id,
            'title': title,
            'description': description,
            'file_path': file_path,
            'exact_match': exact_match,
            'limit': limit
        }
        # Filter out None values for cleaner logging
        logged_params = {k: v for k, v in search_params.items() if v is not None}
        debug_id(f"Starting ImagePositionAssociation.get_images_by_position with parameters: {logged_params}", rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("ImagePositionAssociation.get_images_by_position", rid):

                # Start with a query that joins Image and ImagePositionAssociation
                query = session.query(Image).join(cls, Image.id == cls.image_id).join(Position,
                                                                                      Position.id == cls.position_id)

                # Apply position filters
                if position_id is not None:
                    query = query.filter(Position.id == position_id)

                if area_id is not None:
                    query = query.filter(Position.area_id == area_id)

                if equipment_group_id is not None:
                    query = query.filter(Position.equipment_group_id == equipment_group_id)

                if model_id is not None:
                    query = query.filter(Position.model_id == model_id)

                if asset_number_id is not None:
                    query = query.filter(Position.asset_number_id == asset_number_id)

                if location_id is not None:
                    query = query.filter(Position.location_id == location_id)

                if subassembly_id is not None:
                    query = query.filter(Position.subassembly_id == subassembly_id)

                if component_assembly_id is not None:
                    query = query.filter(Position.component_assembly_id == component_assembly_id)

                if assembly_view_id is not None:
                    query = query.filter(Position.assembly_view_id == assembly_view_id)

                if site_location_id is not None:
                    query = query.filter(Position.site_location_id == site_location_id)

                # Apply image filters
                if image_id is not None:
                    query = query.filter(Image.id == image_id)

                if title is not None:
                    if exact_match:
                        query = query.filter(Image.title == title)
                    else:
                        query = query.filter(Image.title.ilike(f"%{title}%"))

                if description is not None:
                    if exact_match:
                        query = query.filter(Image.description == description)
                    else:
                        query = query.filter(Image.description.ilike(f"%{description}%"))

                if file_path is not None:
                    if exact_match:
                        query = query.filter(Image.file_path == file_path)
                    else:
                        query = query.filter(Image.file_path.ilike(f"%{file_path}%"))

                # Make results distinct to avoid duplicates
                query = query.distinct()

                # Apply limit
                query = query.limit(limit)

                # Execute query and log results
                results = query.all()
                debug_id(f"ImagePositionAssociation.get_images_by_position completed, found {len(results)} images", rid)
                return results

        except Exception as e:
            error_id(f"Error in ImagePositionAssociation.get_images_by_position: {str(e)}", rid, exc_info=True)
            return []
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for ImagePositionAssociation.get_images_by_position", rid)

class DrawingPositionAssociation(Base):
    __tablename__ = 'drawing_position'
    id = Column(Integer, primary_key=True)
    drawing_id = Column(Integer, ForeignKey('drawing.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('position.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('drawing_id', 'position_id', name='uq_drawing_position'),
        Index('ix_drawing_position_drawing_id', 'drawing_id'),
        Index('ix_drawing_position_position_id', 'position_id'),
    )

    drawing = relationship("Drawing", back_populates="drawing_position")
    position = relationship("Position", back_populates="drawing_position")

    @classmethod
    @with_request_id
    def associate_drawing_position(cls,
                                   drawing_id: int,
                                   position_id: int,
                                   request_id: Optional[str] = None,
                                   session: Optional[Session] = None) -> Optional['DrawingPositionAssociation']:
        """
        Associate a drawing with a position.

        Args:
            drawing_id: ID of the drawing to associate
            position_id: ID of the position to associate
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            The created DrawingPositionAssociation object if successful, None otherwise
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for DrawingPositionAssociation.associate_drawing_position", rid)

        # Log the operation with request ID
        debug_id(
            f"Starting DrawingPositionAssociation.associate_drawing_position with parameters: drawing_id={drawing_id}, position_id={position_id}",
            rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("DrawingPositionAssociation.associate_drawing_position", rid):

                # Check if drawing exists
                drawing = session.query(Drawing).filter(Drawing.id == drawing_id).first()
                if not drawing:
                    error_id(
                        f"Error in DrawingPositionAssociation.associate_drawing_position: Drawing with ID {drawing_id} not found",
                        rid)
                    return None

                # Check if position exists
                position = session.query(Position).filter(Position.id == position_id).first()
                if not position:
                    error_id(
                        f"Error in DrawingPositionAssociation.associate_drawing_position: Position with ID {position_id} not found",
                        rid)
                    return None

                # Check if association already exists
                existing = session.query(cls).filter(
                    cls.drawing_id == drawing_id,
                    cls.position_id == position_id
                ).first()

                if existing:
                    debug_id(f"Association between drawing {drawing_id} and position {position_id} already exists", rid)
                    return existing

                # Create new association
                association = cls(drawing_id=drawing_id, position_id=position_id)
                session.add(association)

                # Commit if we created the session
                if not session_provided:
                    session.commit()
                    debug_id(f"Committed new association between drawing {drawing_id} and position {position_id}", rid)

                return association

        except Exception as e:
            error_id(f"Error in DrawingPositionAssociation.associate_drawing_position: {str(e)}", rid, exc_info=True)
            if not session_provided:
                session.rollback()
                debug_id(f"Rolled back transaction in DrawingPositionAssociation.associate_drawing_position", rid)
            return None
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for DrawingPositionAssociation.associate_drawing_position", rid)

    @classmethod
    @with_request_id
    def dissociate_drawing_position(cls,
                                    drawing_id: int,
                                    position_id: int,
                                    request_id: Optional[str] = None,
                                    session: Optional[Session] = None) -> bool:
        """
        Remove an association between a drawing and a position.

        Args:
            drawing_id: ID of the drawing to dissociate
            position_id: ID of the position to dissociate
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            True if the association was removed, False otherwise
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for DrawingPositionAssociation.dissociate_drawing_position", rid)

        # Log the operation with request ID
        debug_id(
            f"Starting DrawingPositionAssociation.dissociate_drawing_position with parameters: drawing_id={drawing_id}, position_id={position_id}",
            rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("DrawingPositionAssociation.dissociate_drawing_position", rid):
                # Find the association
                association = session.query(cls).filter(
                    cls.drawing_id == drawing_id,
                    cls.position_id == position_id
                ).first()

                if not association:
                    debug_id(f"No association found between drawing {drawing_id} and position {position_id}", rid)
                    return False

                # Delete the association
                session.delete(association)

                # Commit if we created the session
                if not session_provided:
                    session.commit()
                    debug_id(f"Removed association between drawing {drawing_id} and position {position_id}", rid)

                return True

        except Exception as e:
            error_id(f"Error in DrawingPositionAssociation.dissociate_drawing_position: {str(e)}", rid, exc_info=True)
            if not session_provided:
                session.rollback()
                debug_id(f"Rolled back transaction in DrawingPositionAssociation.dissociate_drawing_position", rid)
            return False
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for DrawingPositionAssociation.dissociate_drawing_position", rid)

    @classmethod
    @with_request_id
    def get_positions_by_drawing(cls,
                                 drawing_id: Optional[int] = None,
                                 drw_equipment_name: Optional[str] = None,
                                 drw_number: Optional[str] = None,
                                 drw_name: Optional[str] = None,
                                 drw_revision: Optional[str] = None,
                                 drw_spare_part_number: Optional[str] = None,
                                 file_path: Optional[str] = None,
                                 position_id: Optional[int] = None,
                                 area_id: Optional[int] = None,
                                 equipment_group_id: Optional[int] = None,
                                 model_id: Optional[int] = None,
                                 asset_number_id: Optional[int] = None,
                                 location_id: Optional[int] = None,
                                 subassembly_id: Optional[int] = None,
                                 component_assembly_id: Optional[int] = None,
                                 assembly_view_id: Optional[int] = None,
                                 site_location_id: Optional[int] = None,
                                 exact_match: bool = False,
                                 limit: int = 100,
                                 request_id: Optional[str] = None,
                                 session: Optional[Session] = None) -> List['Position']:
        """
        Get positions associated with drawings based on flexible search criteria.

        Args:
            drawing_id: Optional drawing ID to filter by
            drw_equipment_name: Optional equipment name to filter by
            drw_number: Optional drawing number to filter by
            drw_name: Optional drawing name to filter by
            drw_revision: Optional revision to filter by
            drw_spare_part_number: Optional spare part number to filter by
            file_path: Optional file path to filter by
            position_id: Optional position ID to filter by
            area_id: Optional area ID to filter by
            equipment_group_id: Optional equipment group ID to filter by
            model_id: Optional model ID to filter by
            asset_number_id: Optional asset number ID to filter by
            location_id: Optional location ID to filter by
            subassembly_id: Optional subassembly ID to filter by
            component_assembly_id: Optional component assembly ID to filter by
            assembly_view_id: Optional assembly view ID to filter by
            site_location_id: Optional site location ID to filter by
            exact_match: If True, performs exact matching instead of partial matching for string fields
            limit: Maximum number of results to return (default 100)
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            List of Position objects matching the search criteria
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for DrawingPositionAssociation.get_positions_by_drawing", rid)

        # Log the search operation with request ID
        search_params = {
            'drawing_id': drawing_id,
            'drw_equipment_name': drw_equipment_name,
            'drw_number': drw_number,
            'drw_name': drw_name,
            'drw_revision': drw_revision,
            'drw_spare_part_number': drw_spare_part_number,
            'file_path': file_path,
            'position_id': position_id,
            'area_id': area_id,
            'equipment_group_id': equipment_group_id,
            'model_id': model_id,
            'asset_number_id': asset_number_id,
            'location_id': location_id,
            'subassembly_id': subassembly_id,
            'component_assembly_id': component_assembly_id,
            'assembly_view_id': assembly_view_id,
            'site_location_id': site_location_id,
            'exact_match': exact_match,
            'limit': limit
        }
        # Filter out None values for cleaner logging
        logged_params = {k: v for k, v in search_params.items() if v is not None}
        debug_id(f"Starting DrawingPositionAssociation.get_positions_by_drawing with parameters: {logged_params}", rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("DrawingPositionAssociation.get_positions_by_drawing", rid):

                # Start with a query that joins Position and DrawingPositionAssociation
                query = session.query(Position).join(cls, Position.id == cls.position_id).join(Drawing,
                                                                                               Drawing.id == cls.drawing_id)

                # Apply drawing filters
                if drawing_id is not None:
                    query = query.filter(Drawing.id == drawing_id)

                if drw_equipment_name is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_equipment_name == drw_equipment_name)
                    else:
                        query = query.filter(Drawing.drw_equipment_name.ilike(f"%{drw_equipment_name}%"))

                if drw_number is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_number == drw_number)
                    else:
                        query = query.filter(Drawing.drw_number.ilike(f"%{drw_number}%"))

                if drw_name is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_name == drw_name)
                    else:
                        query = query.filter(Drawing.drw_name.ilike(f"%{drw_name}%"))

                if drw_revision is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_revision == drw_revision)
                    else:
                        query = query.filter(Drawing.drw_revision.ilike(f"%{drw_revision}%"))

                if drw_spare_part_number is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_spare_part_number == drw_spare_part_number)
                    else:
                        query = query.filter(Drawing.drw_spare_part_number.ilike(f"%{drw_spare_part_number}%"))

                if file_path is not None:
                    if exact_match:
                        query = query.filter(Drawing.file_path == file_path)
                    else:
                        query = query.filter(Drawing.file_path.ilike(f"%{file_path}%"))

                # Apply position filters
                if position_id is not None:
                    query = query.filter(Position.id == position_id)

                if area_id is not None:
                    query = query.filter(Position.area_id == area_id)

                if equipment_group_id is not None:
                    query = query.filter(Position.equipment_group_id == equipment_group_id)

                if model_id is not None:
                    query = query.filter(Position.model_id == model_id)

                if asset_number_id is not None:
                    query = query.filter(Position.asset_number_id == asset_number_id)

                if location_id is not None:
                    query = query.filter(Position.location_id == location_id)

                if subassembly_id is not None:
                    query = query.filter(Position.subassembly_id == subassembly_id)

                if component_assembly_id is not None:
                    query = query.filter(Position.component_assembly_id == component_assembly_id)

                if assembly_view_id is not None:
                    query = query.filter(Position.assembly_view_id == assembly_view_id)

                if site_location_id is not None:
                    query = query.filter(Position.site_location_id == site_location_id)

                # Make results distinct to avoid duplicates
                query = query.distinct()

                # Apply limit
                query = query.limit(limit)

                # Execute query and log results
                results = query.all()
                debug_id(
                    f"DrawingPositionAssociation.get_positions_by_drawing completed, found {len(results)} positions",
                    rid)
                return results

        except Exception as e:
            error_id(f"Error in DrawingPositionAssociation.get_positions_by_drawing: {str(e)}", rid, exc_info=True)
            return []
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for DrawingPositionAssociation.get_positions_by_drawing", rid)

    @classmethod
    @with_request_id
    def get_drawings_by_position(cls,
                                 position_id: Optional[int] = None,
                                 area_id: Optional[int] = None,
                                 equipment_group_id: Optional[int] = None,
                                 model_id: Optional[int] = None,
                                 asset_number_id: Optional[int] = None,
                                 location_id: Optional[int] = None,
                                 subassembly_id: Optional[int] = None,
                                 component_assembly_id: Optional[int] = None,
                                 assembly_view_id: Optional[int] = None,
                                 site_location_id: Optional[int] = None,
                                 drawing_id: Optional[int] = None,
                                 drw_equipment_name: Optional[str] = None,
                                 drw_number: Optional[str] = None,
                                 drw_name: Optional[str] = None,
                                 drw_revision: Optional[str] = None,
                                 drw_spare_part_number: Optional[str] = None,
                                 file_path: Optional[str] = None,
                                 exact_match: bool = False,
                                 limit: int = 100,
                                 request_id: Optional[str] = None,
                                 session: Optional[Session] = None) -> List['Drawing']:
        """
        Get drawings associated with positions based on flexible search criteria.

        Args:
            position_id: Optional position ID to filter by
            area_id: Optional area ID to filter by
            equipment_group_id: Optional equipment group ID to filter by
            model_id: Optional model ID to filter by
            asset_number_id: Optional asset number ID to filter by
            location_id: Optional location ID to filter by
            subassembly_id: Optional subassembly ID to filter by
            component_assembly_id: Optional component assembly ID to filter by
            assembly_view_id: Optional assembly view ID to filter by
            site_location_id: Optional site location ID to filter by
            drawing_id: Optional drawing ID to filter by
            drw_equipment_name: Optional equipment name to filter by
            drw_number: Optional drawing number to filter by
            drw_name: Optional drawing name to filter by
            drw_revision: Optional revision to filter by
            drw_spare_part_number: Optional spare part number to filter by
            file_path: Optional file path to filter by
            exact_match: If True, performs exact matching instead of partial matching for string fields
            limit: Maximum number of results to return (default 100)
            request_id: Optional request ID for tracking this operation in logs
            session: Optional SQLAlchemy session. If None, a new session will be created

        Returns:
            List of Drawing objects matching the search criteria
        """
        # Get or use the provided request_id
        rid = request_id or get_request_id()

        # Get a database session if one wasn't provided
        db_config = DatabaseConfig()
        session_provided = session is not None
        if not session_provided:
            session = db_config.get_main_session()
            debug_id(f"Created new database session for DrawingPositionAssociation.get_drawings_by_position", rid)

        # Log the search operation with request ID
        search_params = {
            'position_id': position_id,
            'area_id': area_id,
            'equipment_group_id': equipment_group_id,
            'model_id': model_id,
            'asset_number_id': asset_number_id,
            'location_id': location_id,
            'subassembly_id': subassembly_id,
            'component_assembly_id': component_assembly_id,
            'assembly_view_id': assembly_view_id,
            'site_location_id': site_location_id,
            'drawing_id': drawing_id,
            'drw_equipment_name': drw_equipment_name,
            'drw_number': drw_number,
            'drw_name': drw_name,
            'drw_revision': drw_revision,
            'drw_spare_part_number': drw_spare_part_number,
            'file_path': file_path,
            'exact_match': exact_match,
            'limit': limit
        }
        # Filter out None values for cleaner logging
        logged_params = {k: v for k, v in search_params.items() if v is not None}
        debug_id(f"Starting DrawingPositionAssociation.get_drawings_by_position with parameters: {logged_params}", rid)

        try:
            # Use the timed operation context manager with request ID
            with log_timed_operation("DrawingPositionAssociation.get_drawings_by_position", rid):

                # Start with a query that joins Drawing and DrawingPositionAssociation
                query = session.query(Drawing).join(cls, Drawing.id == cls.drawing_id).join(Position,
                                                                                            Position.id == cls.position_id)

                # Apply position filters
                if position_id is not None:
                    query = query.filter(Position.id == position_id)

                if area_id is not None:
                    query = query.filter(Position.area_id == area_id)

                if equipment_group_id is not None:
                    query = query.filter(Position.equipment_group_id == equipment_group_id)

                if model_id is not None:
                    query = query.filter(Position.model_id == model_id)

                if asset_number_id is not None:
                    query = query.filter(Position.asset_number_id == asset_number_id)

                if location_id is not None:
                    query = query.filter(Position.location_id == location_id)

                if subassembly_id is not None:
                    query = query.filter(Position.subassembly_id == subassembly_id)

                if component_assembly_id is not None:
                    query = query.filter(Position.component_assembly_id == component_assembly_id)

                if assembly_view_id is not None:
                    query = query.filter(Position.assembly_view_id == assembly_view_id)

                if site_location_id is not None:
                    query = query.filter(Position.site_location_id == site_location_id)

                # Apply drawing filters
                if drawing_id is not None:
                    query = query.filter(Drawing.id == drawing_id)

                if drw_equipment_name is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_equipment_name == drw_equipment_name)
                    else:
                        query = query.filter(Drawing.drw_equipment_name.ilike(f"%{drw_equipment_name}%"))

                if drw_number is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_number == drw_number)
                    else:
                        query = query.filter(Drawing.drw_number.ilike(f"%{drw_number}%"))

                if drw_name is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_name == drw_name)
                    else:
                        query = query.filter(Drawing.drw_name.ilike(f"%{drw_name}%"))

                if drw_revision is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_revision == drw_revision)
                    else:
                        query = query.filter(Drawing.drw_revision.ilike(f"%{drw_revision}%"))

                if drw_spare_part_number is not None:
                    if exact_match:
                        query = query.filter(Drawing.drw_spare_part_number == drw_spare_part_number)
                    else:
                        query = query.filter(Drawing.drw_spare_part_number.ilike(f"%{drw_spare_part_number}%"))

                if file_path is not None:
                    if exact_match:
                        query = query.filter(Drawing.file_path == file_path)
                    else:
                        query = query.filter(Drawing.file_path.ilike(f"%{file_path}%"))

                # Make results distinct to avoid duplicates
                query = query.distinct()

                # Apply limit
                query = query.limit(limit)

                # Execute query and log results
                results = query.all()
                debug_id(
                    f"DrawingPositionAssociation.get_drawings_by_position completed, found {len(results)} drawings",
                    rid)
                return results

        except Exception as e:
            error_id(f"Error in DrawingPositionAssociation.get_drawings_by_position: {str(e)}", rid, exc_info=True)
            return []
        finally:
            # Close the session if we created it
            if not session_provided:
                session.close()
                debug_id(f"Closed database session for DrawingPositionAssociation.get_drawings_by_position", rid)

class PartsPositionImageAssociation(Base):
    __tablename__ = 'part_position_image'
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey('part.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('position.id'), nullable=False)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('part_id', 'position_id', 'image_id', name='uq_part_position_image'),
        Index('ix_ppi_part_id', 'part_id'),
        Index('ix_ppi_position_id', 'position_id'),
        Index('ix_ppi_image_id', 'image_id'),
    )
    image = relationship("Image", back_populates="parts_position_image")
    position = relationship("Position", back_populates="part_position_image")

    @classmethod
    @with_request_id
    def search(cls, session=None, **filters):
        """
        Search the 'part_position_image' table based on the provided filters.

        Args:
            session: SQLAlchemy session (optional).
            filters: A dictionary of filter parameters (e.g., part_id, position_id, image_id).

        Returns:
            List of matching 'PartPositionImageAssociation' objects.
        """
        if session is None:
            session = DatabaseConfig().get_main_session()

        # Get the request ID for logging
        request_id = get_request_id()

        # Log the start of the search operation
        info_id(f"Starting search with filters: {filters}", request_id=request_id)

        # Start with the base query
        query = session.query(cls)

        try:
            # Apply filters dynamically
            if filters:
                for field, value in filters.items():
                    if value is not None:  # Only apply non-None filters
                        query = query.filter(getattr(cls, field) == value)

            # Execute the query and log the result
            results = query.all()

            # Log the number of results found
            info_id(f"Search returned {len(results)} result(s) for filters: {filters}", request_id=request_id)

            return results
        except SQLAlchemyError as e:
            # Log the error
            error_id(f"Error during search operation with filters {filters}: {e}", request_id=request_id, exc_info=True)
            raise

    @classmethod
    @with_request_id
    def get_corresponding_position_ids(cls, session, area_id=None, equipment_group_id=None, model_id=None,
                                       asset_number_id=None, location_id=None):
        """
        Search for corresponding Position IDs based on the provided filters.
        Traverses the hierarchy and retrieves matching Position IDs.

        Args:
            session: SQLAlchemy session
            area_id: ID of the area (optional)
            equipment_group_id: ID of the equipment group (optional)
            model_id: ID of the model (optional)
            asset_number_id: ID of the asset number (optional)
            location_id: ID of the location (optional)

        Returns:
            List of Position IDs that match the criteria
        """
        # Get the request ID for logging
        request_id = get_request_id()

        # Log the start of the operation
        info_id(f"Starting get_corresponding_position_ids with filters: "
                f"area_id={area_id}, equipment_group_id={equipment_group_id}, "
                f"model_id={model_id}, asset_number_id={asset_number_id}, "
                f"location_id={location_id}", request_id=request_id)

        # Start by fetching the root-level positions based on area_id (or first level in hierarchy)
        try:
            positions = cls._get_positions_by_hierarchy(session, area_id=area_id,
                                                        equipment_group_id=equipment_group_id,
                                                        model_id=model_id,
                                                        asset_number_id=asset_number_id,
                                                        location_id=location_id)
            position_ids = [position.id for position in positions]

            # Log the number of Position IDs found
            info_id(f"Found {len(position_ids)} Position IDs for the given filters", request_id=request_id)

            return position_ids
        except SQLAlchemyError as e:
            error_id(f"Error during get_corresponding_position_ids with filters "
                     f"area_id={area_id}, equipment_group_id={equipment_group_id}, "
                     f"model_id={model_id}, asset_number_id={asset_number_id}, "
                     f"location_id={location_id}: {e}", request_id=request_id, exc_info=True)
            raise

    @classmethod
    @with_request_id
    def _get_positions_by_hierarchy(cls, session, area_id=None, equipment_group_id=None, model_id=None,
                                    asset_number_id=None, location_id=None):
        """
        Helper method to fetch positions based on hierarchical filters.

        Args:
            session: SQLAlchemy session
            area_id, equipment_group_id, model_id, asset_number_id, location_id: IDs for filtering

        Returns:
            List of Position objects that match the criteria
        """
        # Get the request ID for logging
        request_id = get_request_id()

        # Building the filter dynamically based on input parameters
        filters = {}
        if area_id:
            filters['area_id'] = area_id
        if equipment_group_id:
            filters['equipment_group_id'] = equipment_group_id
        if model_id:
            filters['model_id'] = model_id
        if asset_number_id:
            filters['asset_number_id'] = asset_number_id
        if location_id:
            filters['location_id'] = location_id

        try:
            # Log the filter being applied
            info_id(f"Applying filters to query: {filters}", request_id=request_id)

            # Query the Position table based on the filters
            query = session.query(Position).filter_by(**filters)

            # Execute and return the results
            positions = query.all()

            # Log the number of results
            info_id(f"Found {len(positions)} positions for the given filters", request_id=request_id)

            return positions
        except SQLAlchemyError as e:
            error_id(f"Error during _get_positions_by_hierarchy with filters {filters}: {e}", request_id=request_id,
                     exc_info=True)
            raise


class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)  # Made nullable for simplicity
    file_path = Column(String, nullable=False)
    img_metadata = Column(JSON, nullable=True)

    # Keep only the essential relationships that exist in your current schema
    image_position_association = relationship("ImagePositionAssociation", back_populates="image")
    parts_position_image = relationship("PartsPositionImageAssociation", back_populates="image")
    tool_image_association = relationship("ToolImageAssociation", back_populates="image")

    @classmethod
    @with_request_id
    def add_simple_image(cls, session: Session, title: str, file_path: str,
                         description: str = None, position_id: int = None,
                         request_id: str = None):
        """
        Simple method to add an image to the database without file copying.
        Stores the file_path as provided (could be relative or absolute).
        """
        try:
            image = cls(
                title=title.strip(),
                description=description.strip() if description else None,
                file_path=file_path,
                img_metadata={}
            )

            session.add(image)
            session.flush()  # Get the ID without committing

            # Optionally link to a position
            if position_id is not None:
                # Check if ImagePositionAssociation exists first
                existing_assoc = session.query(ImagePositionAssociation).filter(
                    ImagePositionAssociation.image_id == image.id,
                    ImagePositionAssociation.position_id == position_id
                ).first()

                if not existing_assoc:
                    assoc = ImagePositionAssociation(
                        image_id=image.id,
                        position_id=position_id
                    )
                    session.add(assoc)

            session.commit()
            logger.info(f"Added image: {title} with ID {image.id}")
            return image

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add image {title}: {e}")
            return None

    @classmethod
    @with_request_id
    def get_by_id(cls, session: Session, image_id: int, request_id: str = None):
        """Get an image by ID"""
        return session.query(cls).filter(cls.id == image_id).first()

    @classmethod
    @with_request_id
    def search_images(cls, session: Session, title: str = None, description: str = None,
                      limit: int = 50, request_id: str = None):
        """Search images by title or description"""
        query = session.query(cls)

        if title:
            query = query.filter(cls.title.ilike(f"%{title}%"))
        if description:
            query = query.filter(cls.description.ilike(f"%{description}%"))

        return query.limit(limit).all()

    @classmethod
    @with_request_id
    def delete_image(cls, session: Session, image_id: int, request_id: str = None):
        """Delete an image and its associations"""
        try:
            image = session.query(cls).filter(cls.id == image_id).first()
            if not image:
                return False

            # Delete the image (cascading will handle associations)
            session.delete(image)
            session.commit()
            logger.info(f"Deleted image ID {image_id}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete image {image_id}: {e}")
            return False

# tool_module.py
"""
Comprehensive tool management module for ShopSync database.
Contains all tool-related models and business logic classes.
"""

# Standard library
from typing import Optional, List, Dict, Any, Tuple
import logging

# SQLAlchemy Core & ORM
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, Table, Index,
    UniqueConstraint, and_, or_, func
)
from sqlalchemy.orm import relationship, Session, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Base class for models
from app.modules.configuration.base import Base

# Database configuration
from app.modules.database.db_manager import ShopSyncDatabase

# Logging utilities & decorators
from app.modules.configuration.log_config import (
    logger,
    with_request_id,
    info_id,
    debug_id,
    warning_id,
    error_id,
    get_request_id
)

# Database configuration alias
DatabaseConfig = ShopSyncDatabase

# ===========================================
# TOOL ASSOCIATION TABLES
# ===========================================

tool_package_association = Table(
    'tool_package_association',
    Base.metadata,
    Column('tool_id', Integer, ForeignKey('tool.id'), primary_key=True),
    Column('package_id', Integer, ForeignKey('tool_package.id'), primary_key=True),
    Column('quantity', Integer, nullable=False, default=1)
)


# ===========================================
# TOOL MODEL CLASSES
# ===========================================

class ToolImageAssociation(Base):
    """Association between tools and images with optional descriptions."""
    __tablename__ = 'tool_image_association'

    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey('tool.id'), nullable=False)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    tool = relationship('Tool', back_populates='tool_image_association')
    image = relationship('Image', back_populates='tool_image_association')

    __table_args__ = (
        UniqueConstraint('tool_id', 'image_id', name='uq_tool_image'),
        Index('ix_tool_image_tool_id', 'tool_id'),
        Index('ix_tool_image_image_id', 'image_id'),
    )

    @classmethod
    @with_request_id
    def associate_with_tool(cls, session, image_id, tool_id, description=None, request_id=None):
        """
        Associate an existing image with a tool in the database.

        Args:
            session: The database session
            image_id: ID of the existing image to associate
            tool_id: ID of the tool to associate with the image
            description: Optional description for this specific association
            request_id: Optional request ID for logging

        Returns:
            The created ToolImageAssociation object or existing one if found, or None on error
        """
        rid = request_id or get_request_id()
        info_id(f"Associating image ID {image_id} with tool ID {tool_id}", rid)

        try:
            # Check if association already exists
            existing_association = session.query(cls).filter(
                and_(
                    cls.image_id == image_id,
                    cls.tool_id == tool_id
                )
            ).first()

            if existing_association:
                info_id(f"Association already exists between image ID {image_id} and tool ID {tool_id}", rid)
                # Update description if provided and different
                if description is not None and existing_association.description != description:
                    existing_association.description = description
                    info_id(f"Updated description for existing association", rid)
                return existing_association
            else:
                # Create new association
                info_id(f"Creating new association between image ID {image_id} and tool ID {tool_id}", rid)
                new_association = cls(
                    image_id=image_id,
                    tool_id=tool_id,
                    description=description
                )
                session.add(new_association)
                session.flush()  # Get ID without committing transaction
                info_id(f"Created ToolImageAssociation with ID {new_association.id}", rid)
                return new_association

        except Exception as e:
            error_id(f"Error in associate_with_tool: {e}", rid, exc_info=True)
            try:
                session.rollback()
            except:
                pass
            return None

    @classmethod
    @with_request_id
    def add_and_associate_with_tool(cls, session, title, file_path, tool_id, description="",
                                    association_description=None, request_id=None):
        """
        Add an image to the database and associate it with a tool in one operation.

        Args:
            session: The database session
            title: Title for the image
            file_path: Path to the image file
            tool_id: ID of the tool to associate with the image
            description: Description for the image itself
            association_description: Optional description for the tool-image association
            request_id: Optional request ID for logging

        Returns:
            Tuple of (Image object, ToolImageAssociation object) or (None, None) on error
        """
        rid = request_id or get_request_id()

        try:
            info_id(f"Starting add_and_associate_with_tool for '{title}' with tool ID {tool_id}", rid)

            # Import Image class here to avoid circular imports
            from app.modules.database.image_db import Image

            # First add the image to the database - this returns just the ID (integer)
            created_image_id = Image.add_to_db(session, title, file_path, description, request_id=rid)

            if created_image_id is None:
                error_id(f"Failed to create image '{title}'", rid)
                return None, None

            info_id(f"Successfully created image with ID: {created_image_id}", rid)

            # Get the actual Image object from the database
            image_object = session.query(Image).filter(Image.id == created_image_id).first()
            if image_object is None:
                error_id(f"Could not retrieve created image with ID {created_image_id}", rid)
                return None, None

            debug_id(f"Successfully retrieved image object: '{image_object.title}'", rid)

            # Then create the association using the image ID (integer)
            association = cls.associate_with_tool(
                session,
                image_id=created_image_id,  # Use the integer ID directly
                tool_id=tool_id,
                description=association_description,
                request_id=rid
            )

            if association is None:
                error_id(f"Failed to create tool association for image ID {created_image_id}", rid)
                return image_object, None

            info_id(
                f"Successfully created image '{title}' (ID: {created_image_id}) and associated with tool ID {tool_id}",
                rid)
            return image_object, association

        except Exception as e:
            error_id(f"Error in add_and_associate_with_tool: {e}", rid, exc_info=True)
            try:
                session.rollback()
            except:
                pass
            return None, None

    @classmethod
    @with_request_id
    def get_tools_for_image(cls, session, image_id, request_id=None):
        """
        Get all tools associated with a specific image.

        Args:
            session: Database session
            image_id: ID of the image
            request_id: Optional request ID for logging

        Returns:
            List of dictionaries containing tool information
        """
        rid = request_id or get_request_id()

        try:
            associations = session.query(cls).filter(cls.image_id == image_id).all()
            tools = []

            for assoc in associations:
                if assoc.tool:  # Use relationship if available
                    tools.append({
                        'tool_id': assoc.tool_id,
                        'tool_name': assoc.tool.name if hasattr(assoc.tool, 'name') else 'Unknown',
                        'association_description': assoc.description,
                        'association_id': assoc.id
                    })

            debug_id(f"Found {len(tools)} tools for image {image_id}", rid)
            return tools

        except Exception as e:
            error_id(f"Error getting tools for image {image_id}: {e}", rid)
            return []

    @classmethod
    @with_request_id
    def get_images_for_tool(cls, session, tool_id, request_id=None):
        """
        Get all images associated with a specific tool.

        Args:
            session: Database session
            tool_id: ID of the tool
            request_id: Optional request ID for logging

        Returns:
            List of dictionaries containing image information
        """
        rid = request_id or get_request_id()

        try:
            associations = session.query(cls).filter(cls.tool_id == tool_id).all()
            images = []

            for assoc in associations:
                if assoc.image:  # Use relationship if available
                    images.append({
                        'image_id': assoc.image_id,
                        'image_title': assoc.image.title,
                        'image_description': assoc.image.description,
                        'image_path': assoc.image.file_path,
                        'association_description': assoc.description,
                        'association_id': assoc.id,
                        'view_url': f'/add_document/image/{assoc.image_id}'
                    })

            debug_id(f"Found {len(images)} images for tool {tool_id}", rid)
            return images

        except Exception as e:
            error_id(f"Error getting images for tool {tool_id}: {e}", rid)
            return []

    @with_request_id
    def remove_association(self, session, request_id=None):
        """
        Remove this tool-image association.

        Args:
            session: Database session
            request_id: Optional request ID for logging

        Returns:
            Boolean indicating success
        """
        rid = request_id or get_request_id()

        try:
            info_id(f"Removing tool-image association ID {self.id} (tool: {self.tool_id}, image: {self.image_id})", rid)
            session.delete(self)
            session.flush()
            info_id(f"Successfully removed association ID {self.id}", rid)
            return True

        except Exception as e:
            error_id(f"Error removing association {self.id}: {e}", rid)
            try:
                session.rollback()
            except:
                pass
            return False

    @classmethod
    @with_request_id
    def bulk_associate_images_with_tool(cls, session, image_ids, tool_id, description=None, request_id=None):
        """
        Associate multiple images with a single tool.

        Args:
            session: Database session
            image_ids: List of image IDs to associate
            tool_id: ID of the tool
            description: Optional description for all associations
            request_id: Optional request ID for logging

        Returns:
            List of created ToolImageAssociation objects
        """
        rid = request_id or get_request_id()

        try:
            info_id(f"Bulk associating {len(image_ids)} images with tool ID {tool_id}", rid)

            associations = []
            for image_id in image_ids:
                association = cls.associate_with_tool(
                    session, image_id, tool_id, description, request_id=rid
                )
                if association:
                    associations.append(association)

            info_id(f"Successfully created {len(associations)} associations", rid)
            return associations

        except Exception as e:
            error_id(f"Error in bulk_associate_images_with_tool: {e}", rid)
            return []


class ToolPositionAssociation(Base):
    """Association between tools and positions."""
    __tablename__ = 'tool_position_association'

    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey('tool.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('position.id'), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    tool = relationship('Tool', back_populates='tool_position_association')
    position = relationship('Position', back_populates='tool_position_association')

    __table_args__ = (
        UniqueConstraint('tool_id', 'position_id', name='uq_tool_position'),
        Index('ix_tool_position_tool_id', 'tool_id'),
        Index('ix_tool_position_position_id', 'position_id'),
    )

    @classmethod
    @with_request_id
    def associate_tool_with_position(cls, session, tool_id, position_id, description=None, request_id=None):
        """
        Associate a tool with a position.

        Args:
            session: Database session
            tool_id: ID of the tool
            position_id: ID of the position
            description: Optional description
            request_id: Optional request ID for logging

        Returns:
            Created or existing ToolPositionAssociation object
        """
        rid = request_id or get_request_id()

        try:
            # Check if association already exists
            existing = session.query(cls).filter(
                and_(cls.tool_id == tool_id, cls.position_id == position_id)
            ).first()

            if existing:
                info_id(f"Association already exists between tool {tool_id} and position {position_id}", rid)
                return existing

            # Create new association
            association = cls(
                tool_id=tool_id,
                position_id=position_id,
                description=description
            )
            session.add(association)
            session.flush()

            info_id(f"Created association between tool {tool_id} and position {position_id}", rid)
            return association

        except Exception as e:
            error_id(f"Error associating tool {tool_id} with position {position_id}: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def get_tools_for_position(cls, session, position_id, request_id=None):
        """Get all tools associated with a position."""
        rid = request_id or get_request_id()

        try:
            associations = session.query(cls).filter(cls.position_id == position_id).all()
            return [assoc.tool for assoc in associations if assoc.tool]
        except Exception as e:
            error_id(f"Error getting tools for position {position_id}: {e}", rid)
            return []

    @classmethod
    @with_request_id
    def get_positions_for_tool(cls, session, tool_id, request_id=None):
        """Get all positions associated with a tool."""
        rid = request_id or get_request_id()

        try:
            associations = session.query(cls).filter(cls.tool_id == tool_id).all()
            return [assoc.position for assoc in associations if assoc.position]
        except Exception as e:
            error_id(f"Error getting positions for tool {tool_id}: {e}", rid)
            return []


class ToolCategory(Base):
    """Hierarchical tool categories."""
    __tablename__ = 'tool_category'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey('tool_category.id'), nullable=True)

    # Self-referential relationships for hierarchy
    parent = relationship('ToolCategory', remote_side=[id], back_populates='subcategories')
    subcategories = relationship('ToolCategory', back_populates='parent', cascade="all, delete-orphan")
    tools = relationship('Tool', back_populates='tool_category', cascade="all, delete-orphan")

    @classmethod
    @with_request_id
    def add_category(cls, session, name, description=None, parent_id=None, request_id=None):
        """Add a new tool category."""
        rid = request_id or get_request_id()

        try:
            category = cls(
                name=name,
                description=description,
                parent_id=parent_id
            )
            session.add(category)
            session.commit()

            info_id(f"Created tool category: {name}", rid)
            return category

        except IntegrityError:
            session.rollback()
            error_id(f"Tool category '{name}' already exists", rid)
            return None
        except Exception as e:
            session.rollback()
            error_id(f"Error creating tool category: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def get_category_hierarchy(cls, session, category_id=None, request_id=None):
        """Get category hierarchy starting from a specific category or root."""
        rid = request_id or get_request_id()

        try:
            if category_id:
                category = session.query(cls).filter(cls.id == category_id).first()
                if not category:
                    return None
                return cls._build_hierarchy_dict(category)
            else:
                # Get all root categories (no parent)
                root_categories = session.query(cls).filter(cls.parent_id.is_(None)).all()
                return [cls._build_hierarchy_dict(cat) for cat in root_categories]

        except Exception as e:
            error_id(f"Error getting category hierarchy: {e}", rid, exc_info=True)
            return []

    @classmethod
    def _build_hierarchy_dict(cls, category):
        """Recursively build hierarchy dictionary."""
        return {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'subcategories': [cls._build_hierarchy_dict(sub) for sub in category.subcategories],
            'tool_count': len(category.tools)
        }

    @classmethod
    @with_request_id
    def delete_category(cls, session, category_id, force=False, request_id=None):
        """Delete a tool category."""
        rid = request_id or get_request_id()

        try:
            category = session.query(cls).filter(cls.id == category_id).first()
            if not category:
                warning_id(f"Tool category {category_id} not found", rid)
                return False

            # Check for dependencies
            if not force:
                if category.tools:
                    error_id(f"Cannot delete category {category.name}: has {len(category.tools)} tools", rid)
                    return False
                if category.subcategories:
                    error_id(f"Cannot delete category {category.name}: has subcategories", rid)
                    return False

            session.delete(category)
            session.commit()
            info_id(f"Deleted tool category: {category.name}", rid)
            return True

        except Exception as e:
            session.rollback()
            error_id(f"Error deleting tool category: {e}", rid, exc_info=True)
            return False


class ToolManufacturer(Base):
    """Tool manufacturers."""
    __tablename__ = 'tool_manufacturer'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    country = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # Relationships
    tools = relationship('Tool', back_populates='tool_manufacturer')

    @classmethod
    @with_request_id
    def add_manufacturer(cls, session, name, description=None, country=None, website=None, request_id=None):
        """Add a new tool manufacturer."""
        rid = request_id or get_request_id()

        try:
            manufacturer = cls(
                name=name,
                description=description,
                country=country,
                website=website
            )
            session.add(manufacturer)
            session.commit()

            info_id(f"Created tool manufacturer: {name}", rid)
            return manufacturer

        except IntegrityError:
            session.rollback()
            error_id(f"Tool manufacturer '{name}' already exists", rid)
            return None
        except Exception as e:
            session.rollback()
            error_id(f"Error creating tool manufacturer: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def search_manufacturers(cls, session, query, limit=50, request_id=None):
        """Search manufacturers by name."""
        rid = request_id or get_request_id()

        try:
            results = session.query(cls).filter(
                cls.name.ilike(f"%{query}%")
            ).limit(limit).all()

            debug_id(f"Found {len(results)} manufacturers matching '{query}'", rid)
            return results

        except Exception as e:
            error_id(f"Error searching manufacturers: {e}", rid, exc_info=True)
            return []

    @classmethod
    @with_request_id
    def delete_manufacturer(cls, session, manufacturer_id, force=False, request_id=None):
        """Delete a tool manufacturer."""
        rid = request_id or get_request_id()

        try:
            manufacturer = session.query(cls).filter(cls.id == manufacturer_id).first()
            if not manufacturer:
                warning_id(f"Tool manufacturer {manufacturer_id} not found", rid)
                return False

            # Check for dependencies
            if not force and manufacturer.tools:
                error_id(f"Cannot delete manufacturer {manufacturer.name}: has {len(manufacturer.tools)} tools", rid)
                return False

            session.delete(manufacturer)
            session.commit()
            info_id(f"Deleted tool manufacturer: {manufacturer.name}", rid)
            return True

        except Exception as e:
            session.rollback()
            error_id(f"Error deleting tool manufacturer: {e}", rid, exc_info=True)
            return False


class ToolPackage(Base):
    """Tool packages - collections of tools."""
    __tablename__ = 'tool_package'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    tools = relationship('Tool', secondary=tool_package_association, back_populates='tool_packages')

    @classmethod
    @with_request_id
    def add_package(cls, session, name, description=None, tool_ids=None, request_id=None):
        """Add a new tool package."""
        rid = request_id or get_request_id()

        try:
            package = cls(name=name, description=description)
            session.add(package)
            session.flush()  # Get ID

            # Add tools if provided
            if tool_ids:
                tools = session.query(Tool).filter(Tool.id.in_(tool_ids)).all()
                package.tools.extend(tools)

            session.commit()
            info_id(f"Created tool package: {name} with {len(tool_ids or [])} tools", rid)
            return package

        except Exception as e:
            session.rollback()
            error_id(f"Error creating tool package: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def get_package_contents(cls, session, package_id, request_id=None):
        """Get all tools in a package."""
        rid = request_id or get_request_id()

        try:
            package = session.query(cls).options(
                selectinload(cls.tools)
            ).filter(cls.id == package_id).first()

            if package:
                debug_id(f"Package '{package.name}' contains {len(package.tools)} tools", rid)
                return package.tools
            return []

        except Exception as e:
            error_id(f"Error getting package contents: {e}", rid, exc_info=True)
            return []


class Tool(Base):
    """Main tool model."""
    __tablename__ = 'tool'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    size = Column(String, nullable=True)
    type = Column(String, nullable=True)
    material = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    tool_category_id = Column(Integer, ForeignKey('tool_category.id'), nullable=False)
    tool_manufacturer_id = Column(Integer, ForeignKey('tool_manufacturer.id'), nullable=False)

    # Relationships
    tool_category = relationship('ToolCategory', back_populates='tools')
    tool_manufacturer = relationship('ToolManufacturer', back_populates='tools')
    tool_packages = relationship('ToolPackage', secondary=tool_package_association, back_populates='tools')
    tool_image_association = relationship('ToolImageAssociation', back_populates='tool')
    tool_position_association = relationship('ToolPositionAssociation', back_populates='tool')

    # Note: tool_tasks relationship would be added when TaskToolAssociation is defined

    @classmethod
    @with_request_id
    def add_tool(cls, session, name, tool_category_id, tool_manufacturer_id,
                 size=None, tool_type=None, material=None, description=None, request_id=None):
        """Add a new tool."""
        rid = request_id or get_request_id()

        try:
            # Validate that category and manufacturer exist
            category = session.query(ToolCategory).filter(ToolCategory.id == tool_category_id).first()
            if not category:
                error_id(f"Tool category {tool_category_id} not found", rid)
                return None

            manufacturer = session.query(ToolManufacturer).filter(ToolManufacturer.id == tool_manufacturer_id).first()
            if not manufacturer:
                error_id(f"Tool manufacturer {tool_manufacturer_id} not found", rid)
                return None

            tool = cls(
                name=name,
                size=size,
                type=tool_type,
                material=material,
                description=description,
                tool_category_id=tool_category_id,
                tool_manufacturer_id=tool_manufacturer_id
            )

            session.add(tool)
            session.commit()

            info_id(f"Created tool: {name} (ID: {tool.id})", rid)
            return tool

        except Exception as e:
            session.rollback()
            error_id(f"Error creating tool: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def search_tools(cls, session, query=None, category_id=None, manufacturer_id=None,
                     tool_type=None, material=None, limit=50, request_id=None):
        """Search tools with various criteria."""
        rid = request_id or get_request_id()

        try:
            q = session.query(cls).options(
                joinedload(cls.tool_category),
                joinedload(cls.tool_manufacturer)
            )

            # Apply filters
            if query:
                q = q.filter(or_(
                    cls.name.ilike(f"%{query}%"),
                    cls.description.ilike(f"%{query}%")
                ))

            if category_id:
                q = q.filter(cls.tool_category_id == category_id)

            if manufacturer_id:
                q = q.filter(cls.tool_manufacturer_id == manufacturer_id)

            if tool_type:
                q = q.filter(cls.type.ilike(f"%{tool_type}%"))

            if material:
                q = q.filter(cls.material.ilike(f"%{material}%"))

            results = q.limit(limit).all()
            debug_id(f"Found {len(results)} tools matching search criteria", rid)
            return results

        except Exception as e:
            error_id(f"Error searching tools: {e}", rid, exc_info=True)
            return []

    @classmethod
    @with_request_id
    def get_tool_by_id(cls, session, tool_id, include_relationships=True, request_id=None):
        """Get a tool by ID with optional relationship loading."""
        rid = request_id or get_request_id()

        try:
            query = session.query(cls)
            if include_relationships:
                query = query.options(
                    joinedload(cls.tool_category),
                    joinedload(cls.tool_manufacturer),
                    selectinload(cls.tool_packages),
                    selectinload(cls.tool_image_association),
                    selectinload(cls.tool_position_association)
                )

            tool = query.filter(cls.id == tool_id).first()
            if tool:
                debug_id(f"Retrieved tool: {tool.name} (ID: {tool_id})", rid)
            else:
                warning_id(f"Tool {tool_id} not found", rid)

            return tool

        except Exception as e:
            error_id(f"Error getting tool by ID: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def update_tool(cls, session, tool_id, **kwargs):
        """Update tool attributes."""
        rid = kwargs.pop('request_id', None) or get_request_id()

        try:
            tool = session.query(cls).filter(cls.id == tool_id).first()
            if not tool:
                warning_id(f"Tool {tool_id} not found for update", rid)
                return None

            # Update provided attributes
            for key, value in kwargs.items():
                if hasattr(tool, key):
                    setattr(tool, key, value)

            session.commit()
            info_id(f"Updated tool {tool.name} (ID: {tool_id})", rid)
            return tool

        except Exception as e:
            session.rollback()
            error_id(f"Error updating tool: {e}", rid, exc_info=True)
            return None

    @classmethod
    @with_request_id
    def delete_tool(cls, session, tool_id, force=False, request_id=None):
        """Delete a tool."""
        rid = request_id or get_request_id()

        try:
            tool = session.query(cls).filter(cls.id == tool_id).first()
            if not tool:
                warning_id(f"Tool {tool_id} not found for deletion", rid)
                return False

            tool_name = tool.name

            # Check for dependencies if not forcing
            if not force:
                # Check associations
                if tool.tool_image_association:
                    error_id(f"Cannot delete tool '{tool_name}': has image associations", rid)
                    return False
                if tool.tool_position_association:
                    error_id(f"Cannot delete tool '{tool_name}': has position associations", rid)
                    return False
                if tool.tool_packages:
                    error_id(f"Cannot delete tool '{tool_name}': belongs to packages", rid)
                    return False

            session.delete(tool)
            session.commit()
            info_id(f"Deleted tool: {tool_name} (ID: {tool_id})", rid)
            return True

        except Exception as e:
            session.rollback()
            error_id(f"Error deleting tool: {e}", rid, exc_info=True)
            return False

    @classmethod
    @with_request_id
    def get_tools_by_category(cls, session, category_id, include_subcategories=False, request_id=None):
        """Get all tools in a specific category."""
        rid = request_id or get_request_id()

        try:
            if include_subcategories:
                # Get category and all subcategories
                category_ids = cls._get_category_hierarchy_ids(session, category_id)
                tools = session.query(cls).filter(cls.tool_category_id.in_(category_ids)).all()
            else:
                tools = session.query(cls).filter(cls.tool_category_id == category_id).all()

            debug_id(f"Found {len(tools)} tools in category {category_id}", rid)
            return tools

        except Exception as e:
            error_id(f"Error getting tools by category: {e}", rid, exc_info=True)
            return []

    @classmethod
    def _get_category_hierarchy_ids(cls, session, category_id):
        """Recursively get category ID and all subcategory IDs."""
        ids = [category_id]
        subcategories = session.query(ToolCategory).filter(ToolCategory.parent_id == category_id).all()
        for sub in subcategories:
            ids.extend(cls._get_category_hierarchy_ids(session, sub.id))
        return ids

    @classmethod
    @with_request_id
    def get_tools_by_manufacturer(cls, session, manufacturer_id, request_id=None):
        """Get all tools from a specific manufacturer."""
        rid = request_id or get_request_id()

        try:
            tools = session.query(cls).filter(cls.tool_manufacturer_id == manufacturer_id).all()
            debug_id(f"Found {len(tools)} tools from manufacturer {manufacturer_id}", rid)
            return tools

        except Exception as e:
            error_id(f"Error getting tools by manufacturer: {e}", rid, exc_info=True)
            return []


# ===========================================
# TOOL MANAGER CLASS (Business Logic)
# ===========================================

class ToolManager:
    """
    Comprehensive tool management class providing search, add, and delete operations.
    Integrates with existing database configuration and logging system.
    """

    def __init__(self, db_config: DatabaseConfig = None):
        """
        Initialize the ToolManager with database configuration.

        Args:
            db_config: DatabaseConfig instance for database operations
        """
        self.db_config = db_config or DatabaseConfig()
        self.request_id = get_request_id()
        logger.info(f"ToolManager initialized with request ID: {self.request_id}")

    # ===================
    # SEARCH OPERATIONS
    # ===================

    @with_request_id
    def search_tools(self,
                     name: Optional[str] = None,
                     category_id: Optional[int] = None,
                     category_name: Optional[str] = None,
                     manufacturer_id: Optional[int] = None,
                     manufacturer_name: Optional[str] = None,
                     tool_type: Optional[str] = None,
                     material: Optional[str] = None,
                     size: Optional[str] = None,
                     description_contains: Optional[str] = None,
                     include_relationships: bool = True,
                     limit: Optional[int] = None,
                     offset: Optional[int] = 0,
                     request_id: Optional[str] = None) -> List[Tool]:
        """
        Search for tools with various filter criteria.

        Args:
            name: Partial or exact tool name match
            category_id: Filter by specific category ID
            category_name: Filter by category name (partial match)
            manufacturer_id: Filter by specific manufacturer ID
            manufacturer_name: Filter by manufacturer name (partial match)
            tool_type: Filter by tool type
            material: Filter by material
            size: Filter by size
            description_contains: Search in description text
            include_relationships: Whether to eagerly load related data
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            request_id: Optional request ID for logging

        Returns:
            List of Tool objects matching the criteria
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                # Start with base query
                query = session.query(Tool)

                # Add eager loading for relationships if requested
                if include_relationships:
                    query = query.options(
                        joinedload(Tool.tool_category),
                        joinedload(Tool.tool_manufacturer),
                        selectinload(Tool.tool_packages),
                        selectinload(Tool.tool_image_association),
                        selectinload(Tool.tool_position_association)
                    )

                # Build filter conditions
                conditions = []

                # Name filter (case-insensitive partial match)
                if name:
                    conditions.append(Tool.name.ilike(f'%{name}%'))

                # Category filters
                if category_id:
                    conditions.append(Tool.tool_category_id == category_id)
                elif category_name:
                    query = query.join(ToolCategory)
                    conditions.append(ToolCategory.name.ilike(f'%{category_name}%'))

                # Manufacturer filters
                if manufacturer_id:
                    conditions.append(Tool.tool_manufacturer_id == manufacturer_id)
                elif manufacturer_name:
                    query = query.join(ToolManufacturer)
                    conditions.append(ToolManufacturer.name.ilike(f'%{manufacturer_name}%'))

                # Type filter
                if tool_type:
                    conditions.append(Tool.type.ilike(f'%{tool_type}%'))

                # Material filter
                if material:
                    conditions.append(Tool.material.ilike(f'%{material}%'))

                # Size filter
                if size:
                    conditions.append(Tool.size.ilike(f'%{size}%'))

                # Description filter
                if description_contains:
                    conditions.append(Tool.description.ilike(f'%{description_contains}%'))

                # Apply all conditions
                if conditions:
                    query = query.filter(and_(*conditions))

                # Apply pagination
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)

                # Execute query
                tools = query.all()

                info_id(f"Search found {len(tools)} tools matching criteria", rid)
                return tools

        except SQLAlchemyError as e:
            error_id(f"Database error during tool search: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error during tool search: {e}", rid, exc_info=True)
            raise

    @with_request_id
    def get_tool_by_id(self, tool_id: int, include_relationships: bool = True, request_id: Optional[str] = None) -> \
    Optional[Tool]:
        """
        Get a specific tool by its ID.

        Args:
            tool_id: The ID of the tool to retrieve
            include_relationships: Whether to eagerly load related data
            request_id: Optional request ID for logging

        Returns:
            Tool object if found, None otherwise
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                return Tool.get_tool_by_id(session, tool_id, include_relationships, request_id=rid)

        except SQLAlchemyError as e:
            error_id(f"Database error getting tool by ID {tool_id}: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error getting tool by ID {tool_id}: {e}", rid, exc_info=True)
            raise

    @with_request_id
    def search_tools_full_text(self, search_term: str, limit: Optional[int] = 50, request_id: Optional[str] = None) -> \
    List[Tool]:
        """
        Perform full-text search across tool name, type, material, and description.

        Args:
            search_term: Text to search for
            limit: Maximum number of results
            request_id: Optional request ID for logging

        Returns:
            List of Tool objects matching the search term
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                # Create a comprehensive text search across multiple fields
                search_pattern = f'%{search_term}%'

                query = session.query(Tool).options(
                    joinedload(Tool.tool_category),
                    joinedload(Tool.tool_manufacturer)
                ).filter(
                    or_(
                        Tool.name.ilike(search_pattern),
                        Tool.type.ilike(search_pattern),
                        Tool.material.ilike(search_pattern),
                        Tool.description.ilike(search_pattern)
                    )
                )

                if limit:
                    query = query.limit(limit)

                tools = query.all()
                info_id(f"Full-text search for '{search_term}' found {len(tools)} tools", rid)
                return tools

        except SQLAlchemyError as e:
            error_id(f"Database error during full-text search: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error during full-text search: {e}", rid, exc_info=True)
            raise

    @with_request_id
    def get_tools_by_category(self, category_id: int, include_subcategories: bool = True,
                              request_id: Optional[str] = None) -> List[Tool]:
        """
        Get all tools in a specific category.

        Args:
            category_id: The category ID
            include_subcategories: Whether to include tools from subcategories
            request_id: Optional request ID for logging

        Returns:
            List of tools in the category
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                return Tool.get_tools_by_category(session, category_id, include_subcategories, request_id=rid)

        except SQLAlchemyError as e:
            error_id(f"Database error getting tools by category: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error getting tools by category: {e}", rid, exc_info=True)
            raise

    # ===================
    # ADD OPERATIONS
    # ===================

    @with_request_id
    def add_tool(self,
                 name: str,
                 tool_category_id: int,
                 tool_manufacturer_id: int,
                 size: Optional[str] = None,
                 tool_type: Optional[str] = None,
                 material: Optional[str] = None,
                 description: Optional[str] = None,
                 package_ids: Optional[List[int]] = None,
                 request_id: Optional[str] = None) -> Optional[Tool]:
        """
        Add a new tool to the database.

        Args:
            name: Tool name
            tool_category_id: Category ID (must exist)
            tool_manufacturer_id: Manufacturer ID (must exist)
            size: Tool size specification
            tool_type: Type of tool
            material: Material composition
            description: Detailed description
            package_ids: List of package IDs to associate with this tool
            request_id: Optional request ID for logging

        Returns:
            The created Tool object or None if failed

        Raises:
            ValueError: If required references don't exist
            IntegrityError: If database constraints are violated
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                tool = Tool.add_tool(
                    session=session,
                    name=name,
                    tool_category_id=tool_category_id,
                    tool_manufacturer_id=tool_manufacturer_id,
                    size=size,
                    tool_type=tool_type,
                    material=material,
                    description=description,
                    request_id=rid
                )

                # Add package associations if provided
                if tool and package_ids:
                    self._add_tool_package_associations(session, tool.id, package_ids, rid)
                    session.commit()

                return tool

        except ValueError as e:
            error_id(f"Validation error creating tool: {e}", rid, exc_info=True)
            raise
        except IntegrityError as e:
            error_id(f"Database integrity error creating tool: {e}", rid, exc_info=True)
            raise
        except SQLAlchemyError as e:
            error_id(f"Database error creating tool: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error creating tool: {e}", rid, exc_info=True)
            raise

    @with_request_id
    def add_tool_from_dict(self, tool_data: Dict[str, Any], request_id: Optional[str] = None) -> Optional[Tool]:
        """
        Add a tool from a dictionary of data.

        Args:
            tool_data: Dictionary containing tool information
            request_id: Optional request ID for logging

        Returns:
            The created Tool object
        """
        rid = request_id or get_request_id()

        required_fields = ['name', 'tool_category_id', 'tool_manufacturer_id']

        # Validate required fields
        for field in required_fields:
            if field not in tool_data:
                raise ValueError(f"Required field '{field}' is missing from tool data")

        return self.add_tool(
            name=tool_data['name'],
            tool_category_id=tool_data['tool_category_id'],
            tool_manufacturer_id=tool_data['tool_manufacturer_id'],
            size=tool_data.get('size'),
            tool_type=tool_data.get('type'),
            material=tool_data.get('material'),
            description=tool_data.get('description'),
            package_ids=tool_data.get('package_ids'),
            request_id=rid
        )

    # ===================
    # UPDATE OPERATIONS
    # ===================

    @with_request_id
    def update_tool(self,
                    tool_id: int,
                    name: Optional[str] = None,
                    size: Optional[str] = None,
                    tool_type: Optional[str] = None,
                    material: Optional[str] = None,
                    description: Optional[str] = None,
                    tool_category_id: Optional[int] = None,
                    tool_manufacturer_id: Optional[int] = None,
                    package_ids: Optional[List[int]] = None,
                    request_id: Optional[str] = None) -> Optional[Tool]:
        """
        Update an existing tool.

        Args:
            tool_id: ID of the tool to update
            name: New name (if provided)
            size: New size (if provided)
            tool_type: New type (if provided)
            material: New material (if provided)
            description: New description (if provided)
            tool_category_id: New category ID (if provided)
            tool_manufacturer_id: New manufacturer ID (if provided)
            package_ids: New list of package IDs (replaces existing associations)
            request_id: Optional request ID for logging

        Returns:
            Updated Tool object if successful, None if tool not found
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                # Prepare update data
                update_data = {}
                if name is not None:
                    update_data['name'] = name
                if size is not None:
                    update_data['size'] = size
                if tool_type is not None:
                    update_data['type'] = tool_type
                if material is not None:
                    update_data['material'] = material
                if description is not None:
                    update_data['description'] = description
                if tool_category_id is not None:
                    update_data['tool_category_id'] = tool_category_id
                if tool_manufacturer_id is not None:
                    update_data['tool_manufacturer_id'] = tool_manufacturer_id

                # Update the tool
                tool = Tool.update_tool(session, tool_id, request_id=rid, **update_data)

                # Update package associations if provided
                if tool and package_ids is not None:
                    # Remove existing associations
                    session.execute(
                        tool_package_association.delete().where(
                            tool_package_association.c.tool_id == tool_id
                        )
                    )
                    # Add new associations
                    if package_ids:
                        self._add_tool_package_associations(session, tool_id, package_ids, rid)
                    session.commit()

                return tool

        except ValueError as e:
            error_id(f"Validation error updating tool: {e}", rid, exc_info=True)
            raise
        except SQLAlchemyError as e:
            error_id(f"Database error updating tool: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error updating tool: {e}", rid, exc_info=True)
            raise

    # ===================
    # DELETE OPERATIONS
    # ===================

    @with_request_id
    def delete_tool(self, tool_id: int, force: bool = False, request_id: Optional[str] = None) -> bool:
        """
        Delete a tool from the database.

        Args:
            tool_id: ID of the tool to delete
            force: If True, will delete even if tool has dependencies
            request_id: Optional request ID for logging

        Returns:
            True if deletion was successful, False if tool not found

        Raises:
            ValueError: If tool has dependencies and force=False
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                return Tool.delete_tool(session, tool_id, force, request_id=rid)

        except ValueError as e:
            error_id(f"Validation error deleting tool: {e}", rid, exc_info=True)
            raise
        except SQLAlchemyError as e:
            error_id(f"Database error deleting tool: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error deleting tool: {e}", rid, exc_info=True)
            raise

    @with_request_id
    def delete_tools_by_category(self, category_id: int, force: bool = False, request_id: Optional[str] = None) -> int:
        """
        Delete all tools in a specific category.

        Args:
            category_id: Category ID
            force: If True, will delete even if tools have dependencies
            request_id: Optional request ID for logging

        Returns:
            Number of tools deleted
        """
        rid = request_id or get_request_id()

        try:
            tools = self.get_tools_by_category(category_id, include_subcategories=False, request_id=rid)
            deleted_count = 0

            for tool in tools:
                if self.delete_tool(tool.id, force=force, request_id=rid):
                    deleted_count += 1

            info_id(f"Deleted {deleted_count} tools from category {category_id}", rid)
            return deleted_count

        except Exception as e:
            error_id(f"Error deleting tools by category: {e}", rid, exc_info=True)
            raise

    @with_request_id
    def delete_tools_by_manufacturer(self, manufacturer_id: int, force: bool = False,
                                     request_id: Optional[str] = None) -> int:
        """
        Delete all tools from a specific manufacturer.

        Args:
            manufacturer_id: Manufacturer ID
            force: If True, will delete even if tools have dependencies
            request_id: Optional request ID for logging

        Returns:
            Number of tools deleted
        """
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                tools = Tool.get_tools_by_manufacturer(session, manufacturer_id, request_id=rid)

                deleted_count = 0
                for tool in tools:
                    if self.delete_tool(tool.id, force=force, request_id=rid):
                        deleted_count += 1

                info_id(f"Deleted {deleted_count} tools from manufacturer {manufacturer_id}", rid)
                return deleted_count

        except Exception as e:
            error_id(f"Error deleting tools by manufacturer: {e}", rid, exc_info=True)
            raise

    # ===================
    # UTILITY METHODS
    # ===================

    def _add_tool_package_associations(self, session, tool_id: int, package_ids: List[int], request_id: str):
        """Add tool-package associations."""
        for package_id in package_ids:
            # Validate package exists
            package = session.query(ToolPackage).filter(ToolPackage.id == package_id).first()
            if not package:
                raise ValueError(f"Tool package with ID {package_id} does not exist")

            # Add association
            association = tool_package_association.insert().values(
                tool_id=tool_id,
                package_id=package_id,
                quantity=1  # Default quantity
            )
            session.execute(association)

    def _check_tool_dependencies(self, session, tool_id: int, request_id: str) -> List[str]:
        """Check if a tool has dependencies that would prevent deletion."""
        dependencies = []

        # Check tool packages
        package_count = session.query(func.count()).select_from(
            tool_package_association
        ).filter(tool_package_association.c.tool_id == tool_id).scalar()
        if package_count > 0:
            dependencies.append(f"{package_count} package associations")

        # Check tool images
        image_count = session.query(ToolImageAssociation).filter(
            ToolImageAssociation.tool_id == tool_id
        ).count()
        if image_count > 0:
            dependencies.append(f"{image_count} image associations")

        # Check tool positions
        position_count = session.query(ToolPositionAssociation).filter(
            ToolPositionAssociation.tool_id == tool_id
        ).count()
        if position_count > 0:
            dependencies.append(f"{position_count} position associations")

        return dependencies

    # ===================
    # STATISTICS AND REPORTING
    # ===================

    @with_request_id
    def get_tool_statistics(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive statistics about tools in the database."""
        rid = request_id or get_request_id()

        try:
            with self.db_config.main_session() as session:
                stats = {}

                # Total tool count
                stats['total_tools'] = session.query(Tool).count()

                # Tools by category
                category_stats = session.query(
                    ToolCategory.name,
                    func.count(Tool.id).label('count')
                ).join(Tool).group_by(ToolCategory.name).all()
                stats['tools_by_category'] = {name: count for name, count in category_stats}

                # Tools by manufacturer
                manufacturer_stats = session.query(
                    ToolManufacturer.name,
                    func.count(Tool.id).label('count')
                ).join(Tool).group_by(ToolManufacturer.name).all()
                stats['tools_by_manufacturer'] = {name: count for name, count in manufacturer_stats}

                # Tools by type
                type_stats = session.query(
                    Tool.type,
                    func.count(Tool.id).label('count')
                ).filter(Tool.type.isnot(None)).group_by(Tool.type).all()
                stats['tools_by_type'] = {tool_type or 'Unknown': count for tool_type, count in type_stats}

                # Tools by material
                material_stats = session.query(
                    Tool.material,
                    func.count(Tool.id).label('count')
                ).filter(Tool.material.isnot(None)).group_by(Tool.material).all()
                stats['tools_by_material'] = {material or 'Unknown': count for material, count in material_stats}

                info_id(f"Generated tool statistics: {stats['total_tools']} total tools", rid)
                return stats

        except SQLAlchemyError as e:
            error_id(f"Database error generating tool statistics: {e}", rid, exc_info=True)
            raise
        except Exception as e:
            error_id(f"Unexpected error generating tool statistics: {e}", rid, exc_info=True)
            raise


# ===========================================
# CONVENIENCE FUNCTIONS
# ===========================================

def create_tool_manager(db_config: DatabaseConfig = None) -> ToolManager:
    """Create a new ToolManager instance."""
    return ToolManager(db_config)


def get_default_tool_manager() -> ToolManager:
    """Get a default ToolManager instance with standard database config."""
    return ToolManager(DatabaseConfig())

