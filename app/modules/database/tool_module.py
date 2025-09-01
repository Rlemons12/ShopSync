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
            info_id(f