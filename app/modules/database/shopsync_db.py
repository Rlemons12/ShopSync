
# Main Tables
class SiteLocation(Base):
    __tablename__ = 'site_location'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    room_number = Column(String, nullable=False)
    site_area = Column(String, nullable=False)

    position = relationship('Position', back_populates="site_location")

    @classmethod
    @with_request_id
    def add_site_location(cls, session, title, room_number, site_area, request_id=None):
        """
        Add a new site location to the database.

        Args:
            session: SQLAlchemy database session
            title (str): Title of the site location
            room_number (str): Room number of the site location
            site_area (str): Site area of the site location
            request_id (str, optional): Unique identifier for the request

        Returns:
            SiteLocation: The newly created site location object
        """
        new_site_location = cls(
            title=title,
            room_number=room_number,
            site_area=site_area
        )

        session.add(new_site_location)
        session.commit()

        logger.info(f"Created new site location: '{title}' in room {room_number}, area {site_area}")
        return new_site_location

    @classmethod
    @with_request_id
    def delete_site_location(cls, session, site_location_id, request_id=None):
        """
        Delete a site location from the database.

        Args:
            session: SQLAlchemy database session
            site_location_id (int): ID of the site location to delete
            request_id (str, optional): Unique identifier for the request

        Returns:
            bool: True if deletion was successful, False if site location not found
        """
        site_location = session.query(cls).filter(cls.id == site_location_id).first()

        if site_location:
            session.delete(site_location)
            session.commit()
            logger.info(f"Deleted site location ID {site_location_id}")
            return True
        else:
            logger.warning(f"Failed to delete site location ID {site_location_id} - not found")
            return False

    @classmethod
    @with_request_id
    def find_related_entities(cls, session, identifier, is_id=True, request_id=None):
        """
        Find all related entities for a site location.

        Args:
            session: SQLAlchemy database session
            identifier: Either site location ID (int) or title (str)
            is_id (bool): If True, identifier is an ID, otherwise it's a title
            request_id (str, optional): Unique identifier for the request

        Returns:
            dict: Dictionary containing:
                - 'site_location': The found site location object
                - 'downward': Dictionary containing:
                    - 'positions': List of all positions at this site location
        """
        # Find the site location
        if is_id:
            site_location = session.query(cls).filter(cls.id == identifier).first()
        else:
            site_location = session.query(cls).filter(cls.title == identifier).first()

        if not site_location:
            logger.warning(f"Site location not found for identifier: {identifier}")
            return None

        # Going downward in the hierarchy
        downward = {
            'positions': site_location.position
        }

        logger.info(f"Found related entities for site location ID {site_location.id}")
        return {
            'site_location': site_location,
            'downward': downward
        }

    @classmethod
    @with_request_id
    def find_or_create(cls, session, title, room_number="Unknown", site_area="General", request_id=None):
        """
        Find a SiteLocation by title, or create it if it doesn't exist.

        Args:
            session: SQLAlchemy database session
            title (str): Title of the site location
            room_number (str): Room number (default "Unknown")
            site_area (str): Site area (default "General")
            request_id (str, optional): Unique identifier for the request

        Returns:
            SiteLocation: The found or newly created site location object
        """
        site_location = session.query(cls).filter_by(title=title).first()

        if site_location:
            logger.info(f"Found existing site location '{title}'", extra={'request_id': request_id})
        else:
            site_location = cls(
                title=title,
                room_number=room_number,
                site_area=site_area
            )
            session.add(site_location)
            session.commit()
            logger.info(f"Created new site location '{title}' with room '{room_number}' and area '{site_area}'",
                        extra={'request_id': request_id})

        return site_location

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

    area = relationship("Area", back_populates="position")
    equipment_group = relationship("EquipmentGroup", back_populates="position")
    model = relationship("Model", back_populates="position")
    asset_number = relationship("AssetNumber", back_populates="position")
    location = relationship("Location", back_populates="position")
    """bill_of_material = relationship("BillOfMaterial", back_populates="position")"""
    part_position_image = relationship("PartsPositionImageAssociation", back_populates="position")
    image_position_association = relationship("ImagePositionAssociation", back_populates="position")
    drawing_position = relationship("DrawingPositionAssociation", back_populates="position")
    problem_position = relationship("ProblemPositionAssociation", back_populates="position")
    completed_document_position_association = relationship("CompletedDocumentPositionAssociation", back_populates="position")
    site_location = relationship("SiteLocation", back_populates="position")
    position_tasks = relationship("TaskPositionAssociation", back_populates="position", cascade="all, delete-orphan")
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
        Search for corresponding Position IDs based on the provided filters with request ID logging.

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
            session = DatabaseConfig().get_main_session()

        # Log input parameters with request ID
        logging.info(
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
            logging.info(f"[{request_id}] Retrieved {len(position_ids)} Position IDs")
            return position_ids

        except SQLAlchemyError as e:
            # Log any errors encountered during the query
            logging.error(
                f"[{request_id}] Error in get_corresponding_position_ids: {str(e)}",
                exc_info=True
            )
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
        debug_id(f"Filtering Positions with filters: {filters}", request_id=g.request_id)

        try:
            # Query the Position table based on the filters
            query = session.query(Position).filter_by(**filters)

            # Log the query execution
            info_id(f"Executing query for positions with {len(filters)} filters.", request_id=g.request_id)

            # Return the positions matching the filter
            positions = query.all()

            # Log the result
            info_id(f"Retrieved {len(positions)} positions.", request_id=g.request_id)
            return positions

        except SQLAlchemyError as e:
            # Log any errors encountered during the query
            error_id(f"Error in _get_positions_by_hierarchy: {str(e)}", exc_info=True, request_id=g.request_id)
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
                # Loop through the found results to build a structured list with detailed logging.
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
    def add_container(cls, session: Session, position_id: int, code: str, name: str, description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        obj = cls(position_id=position_id, code=code, name=name, description=(description or "").strip() or None)
        session.add(obj)
        try:
            session.commit()
            logger.info(f"Created Container '{code}' on position {position_id}", extra={'request_id': request_id} if request_id else None)
            return obj
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create Container", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def delete_container(cls, session: Session, container_id: int, request_id=None) -> bool:
        obj = session.get(cls, container_id)
        if not obj:
            logger.warning(f"Container {container_id} not found", extra={'request_id': request_id} if request_id else None)
            return False
        session.delete(obj)
        try:
            session.commit()
            logger.info(f"Deleted Container {container_id}", extra={'request_id': request_id} if request_id else None)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete Container", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def find_or_create(cls, session: Session, position_id: int, code: str, name: str, description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        existing = session.execute(
            select(cls).where(cls.position_id == position_id, cls.code == code)
        ).scalar_one_or_none()
        if existing:
            logger.info(f"Found Container '{code}' on position {position_id}", extra={'request_id': request_id} if request_id else None)
            return existing
        return cls.add_container(session, position_id, code, name, description=description, request_id=request_id)

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
    container_id = Column(Integer, ForeignKey("container.id", ondelete="CASCADE"), nullable=True)  # shelf can be directly on equipment (no container)
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
    def add_shelf(cls, session: Session, position_id: int, code: str, name: str, container_id: int | None = None, description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        obj = cls(position_id=position_id, container_id=container_id, code=code, name=name, description=(description or "").strip() or None)
        session.add(obj)
        try:
            session.commit()
            where = f"container={container_id}" if container_id else "no-container"
            logger.info(f"Created Shelf '{code}' on position {position_id} ({where})", extra={'request_id': request_id} if request_id else None)
            return obj
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create Shelf", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def delete_shelf(cls, session: Session, shelf_id: int, request_id=None) -> bool:
        obj = session.get(cls, shelf_id)
        if not obj:
            logger.warning(f"Shelf {shelf_id} not found", extra={'request_id': request_id} if request_id else None)
            return False
        session.delete(obj)
        try:
            session.commit()
            logger.info(f"Deleted Shelf {shelf_id}", extra={'request_id': request_id} if request_id else None)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete Shelf", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def find_or_create(cls, session: Session, position_id: int, code: str, name: str, container_id: int | None = None, description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        existing = session.execute(
            select(cls).where(
                cls.position_id == position_id,
                cls.container_id.is_(container_id) if container_id is None else cls.container_id == container_id,
                cls.code == code,
            )
        ).scalar_one_or_none()
        if existing:
            logger.info(f"Found Shelf '{code}' on position {position_id}", extra={'request_id': request_id} if request_id else None)
            return existing
        return cls.add_shelf(session, position_id, code, name, container_id=container_id, description=description, request_id=request_id)

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, shelf_id: int, request_id=None):
        obj = session.execute(
            select(cls).options(joinedload(cls.drawers)).where(cls.id == shelf_id)
        ).scalar_one_or_none()
        if not obj:
            logger.warning(f"Shelf {shelf_id} not found", extra={'request_id': request_id} if request_id else None)
            return None
        return {"shelf": obj, "downward": {"drawers": obj.drawers}}

class Drawer(Base):
    __tablename__ = "drawer"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("position.id", ondelete="CASCADE"), nullable=False)
    shelf_id = Column(Integer, ForeignKey("shelf.id", ondelete="CASCADE"), nullable=True)  # drawer can be directly on equipment (no shelf)
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
    def add_drawer(cls, session: Session, position_id: int, code: str, name: str, shelf_id: int | None = None, description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        obj = cls(position_id=position_id, shelf_id=shelf_id, code=code, name=name, description=(description or "").strip() or None)
        session.add(obj)
        try:
            session.commit()
            where = f"shelf={shelf_id}" if shelf_id else "no-shelf"
            logger.info(f"Created Drawer '{code}' on position {position_id} ({where})", extra={'request_id': request_id} if request_id else None)
            return obj
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create Drawer", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def delete_drawer(cls, session: Session, drawer_id: int, request_id=None) -> bool:
        obj = session.get(cls, drawer_id)
        if not obj:
            logger.warning(f"Drawer {drawer_id} not found", extra={'request_id': request_id} if request_id else None)
            return False
        session.delete(obj)
        try:
            session.commit()
            logger.info(f"Deleted Drawer {drawer_id}", extra={'request_id': request_id} if request_id else None)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete Drawer", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def find_or_create(cls, session: Session, position_id: int, code: str, name: str, shelf_id: int | None = None, description: str = None, request_id=None):
        code, name = cls._norm(code, name)
        existing = session.execute(
            select(cls).where(
                cls.position_id == position_id,
                cls.shelf_id.is_(shelf_id) if shelf_id is None else cls.shelf_id == shelf_id,
                cls.code == code,
            )
        ).scalar_one_or_none()
        if existing:
            logger.info(f"Found Drawer '{code}' on position {position_id}", extra={'request_id': request_id} if request_id else None)
            return existing
        return cls.add_drawer(session, position_id, code, name, shelf_id=shelf_id, description=description, request_id=request_id)

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, drawer_id: int, request_id=None):
        obj = session.execute(
            select(cls).options(joinedload(cls.slots)).where(cls.id == drawer_id)
        ).scalar_one_or_none()
        if not obj:
            logger.warning(f"Drawer {drawer_id} not found", extra={'request_id': request_id} if request_id else None)
            return None
        return {"drawer": obj, "downward": {"slots": obj.slots}}

class DrawerSlot(Base):
    """
    A specific "position in drawer" — you can address by a label or row/column.
    Attach parts to a slot via your own association table if needed.
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

    @classmethod
    @with_request_id
    def add_slot(cls, session: Session, drawer_id: int, *, slot_label: str | None = None, row_index: int | None = None, col_index: int | None = None, note: str | None = None, request_id=None):
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
            logger.info(f"Created DrawerSlot '{where}' in drawer {drawer_id}", extra={'request_id': request_id} if request_id else None)
            return obj
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create DrawerSlot", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def delete_slot(cls, session: Session, slot_id: int, request_id=None) -> bool:
        obj = session.get(cls, slot_id)
        if not obj:
            logger.warning(f"DrawerSlot {slot_id} not found", extra={'request_id': request_id} if request_id else None)
            return False
        session.delete(obj)
        try:
            session.commit()
            logger.info(f"Deleted DrawerSlot {slot_id}", extra={'request_id': request_id} if request_id else None)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete DrawerSlot", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def find_or_create(cls, session: Session, drawer_id: int, *, slot_label: str | None = None, row_index: int | None = None, col_index: int | None = None, note: str | None = None, request_id=None):
        if slot_label:
            existing = session.execute(
                select(cls).where(cls.drawer_id == drawer_id, cls.slot_label == slot_label.strip())
            ).scalar_one_or_none()
            if existing:
                return existing
        # For row/col addressing we don’t enforce uniqueness here, but you can add a UNIQUE on (drawer_id,row_index,col_index) if you want strict grid semantics.
        return cls.add_slot(session, drawer_id, slot_label=slot_label, row_index=row_index, col_index=col_index, note=note, request_id=request_id)

    @classmethod
    @with_request_id
    def find_related_entities(cls, session: Session, slot_id: int, request_id=None):
        obj = session.get(cls, slot_id)
        if not obj:
            logger.warning(f"DrawerSlot {slot_id} not found", extra={'request_id': request_id} if request_id else None)
            return None
        # Add any “downward” relations here if you later link parts or images to a slot
        return {"drawer_slot": obj, "downward": {}}

class Part(Base):
    __tablename__ = "part"

    id          = Column(Integer, primary_key=True)
    sku         = Column(String, nullable=False, unique=True)   # natural key
    name        = Column(String, nullable=False)
    description = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    unit_of_measure = Column(String, nullable=True)  # e.g., "ea", "box", "ft"

    # Link to stock records; no problem/task relationships here
    inventories = relationship(
        "Inventory",
        back_populates="part",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_part_name", "name"),
    )

    # ------------- helpers -------------
    @staticmethod
    def _norm(sku: str, name: str) -> tuple[str, str]:
        s = (sku or "").strip()
        n = (name or "").strip()
        if not s or not n:
            raise ValueError("sku and name are required.")
        return s, n

    # ------------- API -------------
    @classmethod
    @with_request_id
    def find_or_create(cls, session: Session, *, sku: str, name: str, description: Optional[str]=None,
                       manufacturer: Optional[str]=None, unit_of_measure: Optional[str]=None, request_id=None) -> "Part":
        sku, name = cls._norm(sku, name)
        existing = session.execute(select(cls).where(cls.sku == sku)).scalar_one_or_none()
        if existing:
            logger.info(f"Found Part sku={sku}", extra={'request_id': request_id} if request_id else None)
            return existing
        obj = cls(
            sku=sku, name=name,
            description=(description or "").strip() or None,
            manufacturer=(manufacturer or "").strip() or None,
            unit_of_measure=(unit_of_measure or "").strip() or None,
        )
        session.add(obj)
        try:
            session.commit()
            logger.info(f"Created Part sku={sku}", extra={'request_id': request_id} if request_id else None)
            return obj
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to create Part", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def delete_part(cls, session: Session, part_id: int, request_id=None) -> bool:
        obj = session.get(cls, part_id)
        if not obj:
            logger.warning(f"Part id={part_id} not found", extra={'request_id': request_id} if request_id else None)
            return False
        session.delete(obj)
        try:
            session.commit()
            logger.info(f"Deleted Part id={part_id}", extra={'request_id': request_id} if request_id else None)
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to delete Part", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    def search(cls, session: Session, q: str, limit: int = 50) -> list["Part"]:
        if not q:
            return []
        like = f"%{q.strip()}%"
        stmt = (
            select(cls)
            .where((cls.sku.ilike(like)) | (cls.name.ilike(like)))  # type: ignore[attr-defined]
            .order_by(cls.sku.asc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

class Inventory(Base):
    """
    Stock record: how much of a Part exists at a given storage node (e.g., a specific slot).
    Works with the polymorphic StorageNode design:
        Inventory.part_id -> Part.id
        Inventory.storage_node_id -> StorageNode.id
    """
    __tablename__ = "inventory"

    id               = Column(Integer, primary_key=True)
    part_id          = Column(Integer, ForeignKey("part.id", ondelete="CASCADE"), nullable=False)
    storage_node_id  = Column(Integer, ForeignKey("storage_node.id", ondelete="CASCADE"), nullable=False)
    quantity         = Column(Integer, nullable=False, default=0)

    part         = relationship("Part", back_populates="inventories")
    storage_node = relationship("StorageNode")  # no back_populates needed unless you want it

    __table_args__ = (
        UniqueConstraint("part_id", "storage_node_id", name="uq_inventory_part_node"),
        Index("ix_inventory_node", "storage_node_id"),
    )

    # -------- adjustments / transfers --------
    @classmethod
    @with_request_id
    def adjust(cls, session: Session, *, part_id: int, storage_node_id: int, delta: int, request_id=None) -> "Inventory":
        """
        Add/remove quantity at a node (positive delta adds, negative removes).
        """
        if delta == 0:
            raise ValueError("delta must be non-zero.")
        row = session.execute(
            select(cls).where(cls.part_id == part_id, cls.storage_node_id == storage_node_id)
        ).scalar_one_or_none()

        if row:
            new_qty = (row.quantity or 0) + delta
            if new_qty < 0:
                raise ValueError(f"Insufficient stock (have {row.quantity}, need {-delta}).")
            row.quantity = new_qty
        else:
            if delta < 0:
                raise ValueError("Cannot create inventory with negative quantity.")
            row = cls(part_id=part_id, storage_node_id=storage_node_id, quantity=delta)
            session.add(row)

        try:
            session.commit()
            logger.info(
                f"Adjusted stock part={part_id} node={storage_node_id} by {delta} → qty={row.quantity}",
                extra={'request_id': request_id} if request_id else None,
            )
            return row
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to adjust inventory", extra={'request_id': request_id} if request_id else None)
            raise

    @classmethod
    @with_request_id
    def transfer(cls, session: Session, *, part_id: int, from_node_id: int, to_node_id: int, qty: int, request_id=None) -> tuple["Inventory","Inventory"]:
        """
        Move qty of a part from one node to another.
        """
        if qty <= 0:
            raise ValueError("qty must be positive.")

        # decrement source
        src = session.execute(
            select(cls).where(cls.part_id == part_id, cls.storage_node_id == from_node_id)
        ).scalar_one_or_none()
        if not src or (src.quantity or 0) < qty:
            have = src.quantity if src else 0
            raise ValueError(f"Insufficient stock at source (have {have}, need {qty}).")
        src.quantity = src.quantity - qty

        # increment dest
        dst = session.execute(
            select(cls).where(cls.part_id == part_id, cls.storage_node_id == to_node_id)
        ).scalar_one_or_none()
        if dst:
            dst.quantity = (dst.quantity or 0) + qty
        else:
            dst = cls(part_id=part_id, storage_node_id=to_node_id, quantity=qty)
            session.add(dst)

        try:
            session.commit()
            logger.info(
                f"Transferred part={part_id} qty={qty} from node={from_node_id} to node={to_node_id}",
                extra={'request_id': request_id} if request_id else None,
            )
            return src, dst
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Failed to transfer inventory", extra={'request_id': request_id} if request_id else None)
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
    drawing_problem  = relationship("DrawingProblemAssociation",    back_populates="drawing")
    drawing_task     = relationship("DrawingTaskAssociation",       back_populates="drawing")
    drawing_part     = relationship("DrawingPartAssociation",       back_populates="drawing")

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



