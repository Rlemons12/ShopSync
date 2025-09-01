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


# ===========================================
# MODULE EXPORTS
# ===========================================

__all__ = [
    # Models
    'Tool',
    'ToolCategory',
    'ToolManufacturer',
    'ToolPackage',
    'ToolImageAssociation',
    'ToolPositionAssociation',

    # Manager
    'ToolManager',

    # Convenience functions
    'create_tool_manager',
    'get_default_tool_manager',

    # Association table
    'tool_package_association',
]