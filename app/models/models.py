from datetime import datetime
import uuid
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.mysql import CHAR, DECIMAL
from sqlalchemy.orm import relationship
from ..extensions import db

Base = db.Model


# ---------------------------
# Users
# ---------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255))  # hashed password
    created_at = Column(DateTime, default=datetime.utcnow)

    comparisons = relationship("Comparison", back_populates="user")

    def to_dict(self, include_comparisons=False):
        data = {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat()
        }
        if include_comparisons:
            data["comparisons"] = [cmp.to_dict() for cmp in self.comparisons]
        return data


# ---------------------------
# Reference Tables
# ---------------------------
class Brand(Base):
    __tablename__ = "brands"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)

    bikes = relationship("Bike", back_populates="brand")

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Source(Base):
    __tablename__ = "sources"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    importer = Column(String(255))
    domain = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    listings = relationship("BikeListing", back_populates="source")
    images = relationship("BikeImage", back_populates="source")

    def to_dict(self):
        return {"id": self.id, "importer": self.importer, "domain": self.domain}


# ---------------------------
# Core Bike Tables
# ---------------------------
class Bike(Base):
    __tablename__ = "bikes"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(CHAR(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    brand_id = Column(BigInteger, ForeignKey("brands.id"))
    model = Column(String(255), nullable=False)
    year = Column(Integer)
    category = Column(String(50))
    sub_category = Column(String(50))
    style = Column(String(50))
    fork_length = Column(String(50))  # Fork length/travel
    description = Column(Text)
    slug = Column(String(255), unique=True)  # SEO-friendly slug
    main_image_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column[datetime](DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("brand_id", "model", "year"),)

    brand = relationship("Brand", back_populates="bikes")
    listings = relationship("BikeListing", back_populates="bike", cascade="all, delete-orphan")
    standardized_specs = relationship("BikeSpecStd", back_populates="bike", cascade="all, delete-orphan")
    images = relationship("BikeImage", back_populates="bike", cascade="all, delete-orphan")
    compare_count = relationship("CompareCount", uselist=False, back_populates="bike")

    def to_dict(self, include_specs=True, include_prices=True, include_images=True, flat_format=True):
        """
        Convert bike to dictionary format
        
        Args:
            include_specs: Include specification data
            include_prices: Include pricing data
            include_images: Include image data
            flat_format: If True, returns template-compatible flat format.
                        If False, returns clean nested format.
        """
        if flat_format:
            return self._to_dict_flat(include_specs, include_prices, include_images)
        else:
            return self._to_dict_nested(include_specs, include_prices, include_images)
    
    def _to_dict_nested(self, include_specs, include_prices, include_images):
        """Clean nested format for API/modern usage"""
        data = {
            "id": self.uuid,  # Use UUID as external ID
            "internal_id": self.id,  # Bigint for internal use
            "brand": self.brand.name if self.brand else None,
            "model": self.model,
            "year": self.year,
            "category": self.category,
            "sub_category": self.sub_category,
            "style": self.style,
            "description": self.description,
            "slug": self.slug,
            "main_image_url": self.main_image_url,
        }

        if include_specs:
            data["specs"] = {spec.spec_name: spec.spec_value for spec in self.standardized_specs}

        if include_prices:
            data["prices"] = [price.to_dict() for listing in self.listings for price in listing.prices]

        if include_images:
            data["images"] = [img.to_dict() for img in sorted(self.images, key=lambda x: (not x.is_main, x.position))]

        return data
    
    def _to_dict_flat(self, include_specs, include_prices, include_images):
        """Flat format for template compatibility (mimics old SQLite structure)"""
        # Basic fields with template-compatible names
        data = {
            'id': self.uuid,  # UUID as external ID
            'firm': self.brand.name if self.brand else None,  # 'firm' = brand
            'model': str(self.model) if self.model else None,
            'year': str(self.year) if self.year else None,
            'image_url': str(self.main_image_url) if self.main_image_url else None,
            'sub_category': str(self.sub_category) if self.sub_category else None,
            'category': str(self.category) if self.category else None,
            'style': str(self.style) if self.style else None,
            'fork_length': str(self.fork_length) if self.fork_length else None,
        }
        
        # Get price and product_url from latest listing
        if self.listings and include_prices:
            latest_listing = self.listings[0]
            data['product_url'] = latest_listing.product_url
            
            if latest_listing.prices:
                latest_price = latest_listing.prices[-1]
                data['price'] = str(latest_price.original_price) if latest_price.original_price else None
                data['disc_price'] = str(latest_price.disc_price) if latest_price.disc_price else None
            else:
                data['price'] = None
                data['disc_price'] = None
        else:
            data['product_url'] = None
            data['price'] = None
            data['disc_price'] = None
        
        # Include RAW specs from bike_specs_raw table (via listings)
        if include_specs and self.listings:
            # Get raw specs from the first listing
            if self.listings[0].raw_specs:
                for raw_spec in self.listings[0].raw_specs:
                    # Use the raw spec key and value directly
                    if raw_spec.spec_value_raw:
                        data[raw_spec.spec_key_raw] = raw_spec.spec_value_raw
        
        # Gallery images as JSON string (template compatible)
        if include_images and self.images:
            import json
            gallery_urls = [img.image_url for img in sorted(self.images, key=lambda x: (not x.is_main, x.position))]
            data['gallery_images_urls'] = json.dumps(gallery_urls) if gallery_urls else None
        else:
            data['gallery_images_urls'] = None
        
        return data


class BikeListing(Base):
    __tablename__ = "bike_listings"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bike_id = Column(BigInteger, ForeignKey("bikes.id", ondelete="CASCADE"))
    source_id = Column(BigInteger, ForeignKey("sources.id"))
    product_url = Column(String(500), nullable=False)  # Required - unique per source
    availability = Column(Boolean, default=True)
    stock = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("source_id", "product_url"),)

    bike = relationship("Bike", back_populates="listings")
    source = relationship("Source", back_populates="listings")
    prices = relationship("BikePrice", back_populates="listing", cascade="all, delete-orphan")
    raw_specs = relationship("BikeSpecRaw", back_populates="listing", cascade="all, delete-orphan")

    def to_dict(self, include_prices=True):
        data = {
            "id": self.id,
            "product_url": self.product_url,
            "availability": self.availability,
            "stock": self.stock,
            "source": self.source.domain if self.source else None,
        }
        if include_prices:
            data["prices"] = [p.to_dict() for p in self.prices]
        return data


class BikePrice(Base):
    __tablename__ = "bike_prices"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    listing_id = Column(BigInteger, ForeignKey("bike_listings.id", ondelete="CASCADE"))
    original_price = Column(DECIMAL(10, 2), nullable=True)  # Original price from JSON
    disc_price = Column(DECIMAL(10, 2), nullable=True)  # Discounted price from JSON
    currency = Column(String(10), default="ILS")
    scraped_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("BikeListing", back_populates="prices")

    def to_dict(self):
        return {
            "id": self.id,
            "original_price": str(self.original_price) if self.original_price else None,
            "disc_price": str(self.disc_price) if self.disc_price else None,
            "currency": self.currency,
            "scraped_at": self.scraped_at.isoformat()
        }


# ---------------------------
# Specs Tables
# ---------------------------
class BikeSpecRaw(Base):
    __tablename__ = "bike_specs_raw"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    listing_id = Column(BigInteger, ForeignKey("bike_listings.id", ondelete="CASCADE"))
    spec_key_raw = Column(String(255), nullable=False)
    spec_value_raw = Column(Text, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("BikeListing", back_populates="raw_specs")

    def to_dict(self):
        return {
            "spec_key_raw": self.spec_key_raw,
            "spec_value_raw": self.spec_value_raw,
            "scraped_at": self.scraped_at.isoformat()
        }


class BikeSpecStd(Base):
    __tablename__ = "bike_specs_std"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bike_id = Column(BigInteger, ForeignKey("bikes.id", ondelete="CASCADE"))
    spec_name = Column(String(100), nullable=False)
    spec_value = Column(Text)
    spec_numeric = Column(DECIMAL(10, 3), nullable=True)
    spec_unit = Column(String(20), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("bike_id", "spec_name"),)

    bike = relationship("Bike", back_populates="standardized_specs")

    def to_dict(self):
        return {
            "spec_name": self.spec_name,
            "spec_value": self.spec_value,
            "spec_numeric": str(self.spec_numeric) if self.spec_numeric else None,
            "spec_unit": self.spec_unit
        }


# ---------------------------
# Images
# ---------------------------
class BikeImage(Base):
    __tablename__ = "bike_images"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bike_id = Column(BigInteger, ForeignKey("bikes.id", ondelete="CASCADE"))
    source_id = Column(BigInteger, ForeignKey("sources.id"))
    image_url = Column(String(500), nullable=False)  # Optimized for MySQL utf8mb4 unique index
    is_main = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    local_url = Column(Text)
    content_hash = Column(String(64))
    downloaded_at = Column(DateTime)

    __table_args__ = (UniqueConstraint("bike_id", "image_url"),)

    bike = relationship("Bike", back_populates="images")
    source = relationship("Source", back_populates="images")

    def to_dict(self):
        return {
            "url": self.image_url,
            "is_main": self.is_main,
            "position": self.position,
            "local_url": self.local_url
        }


# ---------------------------
# Comparisons & Counts
# ---------------------------
class CompareCount(Base):
    __tablename__ = "compare_counts"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bike_id = Column(BigInteger, ForeignKey("bikes.id", ondelete="CASCADE"), unique=True)
    count = Column(Integer, default=0)

    bike = relationship("Bike", back_populates="compare_count")

    def to_dict(self):
        return {"bike_id": self.bike_id, "count": self.count}


class Comparison(Base):
    __tablename__ = "comparisons"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    slug = Column(String(500), unique=True)
    bike_ids = Column(Text)  # JSON array of bike IDs
    comparison_data = Column(Text)  # JSON from ChatGPT
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="comparisons")

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "bike_ids": self.bike_ids,
            "comparison_data": self.comparison_data,
            "created_at": self.created_at.isoformat(),
            "user": self.user.email if self.user else None
        }


# ---------------------------
# Lead Tables
# ---------------------------
class AvailabilityLead(Base):
    __tablename__ = "availability_leads"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    city = Column(String(255), nullable=False)
    bike_model = Column(String(500))
    bike_id = Column(String(36))  # UUID of the bike
    importer = Column(String(500))  # Importer information
    preferred_size = Column(String(50))  # Height in cm
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "city": self.city,
            "bike_model": self.bike_model,
            "bike_id": self.bike_id,
            "importer": self.importer,
            "preferred_size": self.preferred_size,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ContactLead(Base):
    __tablename__ = "contact_leads"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))  # For test ride form
    message = Column(Text)
    form_type = Column(String(50), default="contact")  # "contact" or "test_ride"
    model = Column(String(500))  # For test ride form
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "message": self.message,
            "form_type": self.form_type,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

