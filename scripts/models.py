from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class Bike(Base):
    __tablename__ = 'bikes'
    
    id = Column(String(255), primary_key=True)
    firm = Column(String(255))
    model = Column(String(255))
    year = Column(Integer)
    price = Column(String(255))
    disc_price = Column(String(255))
    image_url = Column(String(500))
    product_url = Column(String(500))
    frame = Column(String(255))
    motor = Column(String(255))
    battery = Column(String(255))
    fork = Column(String(255))
    rear_shox = Column(String(255))
    
    
    # Additional standardized fields
    stem = Column(String(255))
    handelbar = Column(String(255))
    front_brake = Column(String(255))
    rear_brake = Column(String(255))
    shifter = Column(String(255))
    rear_der = Column(String(255))
    cassette = Column(String(255))
    chain = Column(String(255))
    crank_set = Column(String(255))
    front_wheel = Column(String(255))
    rear_wheel = Column(String(255))
    rims = Column(String(255))
    front_axle = Column(String(255))
    rear_axle = Column(String(255))
    spokes = Column(String(255))
    tubes = Column(String(255))
    front_tire = Column(String(255))
    rear_tire = Column(String(255))
    saddle = Column(String(255))
    seat_post = Column(String(255))
    clamp = Column(String(255))
    charger = Column(String(255))
    wheel_size = Column(String(255))
    headset = Column(String(255))
    brake_lever = Column(String(255))
    screen = Column(String(255))
    extras = Column(String(255))
    pedals = Column(String(255))
    bb = Column(String(255))
    gear_count = Column(String(255))
    
    # Additional fields
    weight = Column(String(255))
    size = Column(String(255))
    hub = Column(String(255))
    brakes = Column(String(255))
    tires = Column(String(255))

class Comparison(Base):
    __tablename__ = 'comparisons'
    
    id = Column(Integer, primary_key=True)
    slug = Column(String(500), unique=True)  # SEO-friendly URL slug
    bike_ids = Column(Text)  # JSON array of bike IDs: ["id1", "id2", "id3", "id4"]
    comparison_data = Column(Text)  # JSON output from ChatGPT API with structure:
    # {
    #   "intro": "פתיח ידידותי בעברית...",
    #   "recommendation": "הסבר בהרחבה מהו הדגם המומלץ...",
    #   "bikes": [
    #     {
    #       "name": "שם הדגם",
    #       "pros": ["יתרון 1", "יתרון 2"],
    #       "cons": ["חסרון 1", "חסרון 2"],
    #       "best_for": "הסבר בהרחבה מיהו הרוכב..."
    #     }
    #   ],
    #   "expert_tip": "טיפ מעניין, מצחיק, חשוב..."
    # }
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def get_bike_ids(self):
        """Get list of bike IDs from JSON string"""
        import json
        try:
            return json.loads(self.bike_ids)
        except:
            return []
    
    def get_comparison_data(self):
        """Get comparison data from JSON string"""
        import json
        try:
            return json.loads(self.comparison_data)
        except:
            return {}
    
    def set_bike_ids(self, bike_id_list):
        """Set bike IDs as JSON string"""
        import json
        self.bike_ids = json.dumps(bike_id_list)
    
    def set_comparison_data(self, data_dict):
        """Set comparison data as JSON string"""
        import json
        self.comparison_data = json.dumps(data_dict)
    
    def generate_slug(self, bike_ids_list, session=None):
        """Generate SEO-friendly slug from bike IDs using firm, model, year"""
        import re
        
        if not bike_ids_list:
            return f'comparison-{self.id}'
        
        bike_slugs = []
        
        # If session is provided, get bike details from database
        if session:
            from scripts.models import Bike
            for bike_id in bike_ids_list:
                bike = session.query(Bike).filter_by(id=bike_id).first()
                if bike:
                    # Create slug: firm-model-year
                    firm = bike.firm or ''
                    model = bike.model or ''
                    year = bike.year or ''
                    
                    # Clean and combine
                    firm_clean = re.sub(r'[^\w\s-]', '', firm).strip()
                    model_clean = re.sub(r'[^\w\s-]', '', model).strip()
                    
                    # Create bike slug
                    bike_parts = []
                    if firm_clean:
                        bike_parts.append(firm_clean.lower().replace(' ', '-'))
                    if model_clean:
                        bike_parts.append(model_clean.lower().replace(' ', '-'))
                    if year:
                        bike_parts.append(str(year))
                    
                    if bike_parts:
                        bike_slugs.append('-'.join(bike_parts))
        
        # Fallback if no session or bike details
        if not bike_slugs:
            bike_slugs = bike_ids_list
        
        # Create final slug: bike1-vs-bike2-vs-bike3
        return '-vs-'.join(bike_slugs)
    
    def get_intro(self):
        """Get the intro text from comparison data"""
        data = self.get_comparison_data()
        return data.get('intro', '')
    
    def get_recommendation(self):
        """Get the recommendation text from comparison data"""
        data = self.get_comparison_data()
        return data.get('recommendation', '')
    
    def get_bikes_comparison(self):
        """Get the bikes array from comparison data"""
        data = self.get_comparison_data()
        return data.get('bikes', [])
    
    def get_expert_tip(self):
        """Get the expert tip from comparison data"""
        data = self.get_comparison_data()
        return data.get('expert_tip', '')


class CompareCount(Base):
    __tablename__ = 'compare_counts'
    
    id = Column(Integer, primary_key=True)
    bike_id = Column(String(255), ForeignKey('bikes.id'), unique=True)
    count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    bike = relationship("Bike")


# Database setup
def get_database_url():
    """Get absolute path to the emtb.db file inside /app directory"""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'emtb.db')
    return f"sqlite:///{db_path}"


def init_db():
    """Initialize the database"""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)

def get_session():
    """Get a database session"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session() 