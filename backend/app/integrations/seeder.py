"""
Database Seeder for data.gov.in API

Seeds the database with real commodities, mandis, and price history
from the Ministry of Agriculture's open data portal.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models import Commodity, Mandi
from app.models.price_history import PriceHistory
from app.integrations.data_gov_client import DataGovClient, get_data_gov_client

logger = logging.getLogger(__name__)


# Mapping of commodity names to categories
COMMODITY_CATEGORIES = {
    # Grains & Cereals
    "Wheat": "Grains", "Rice": "Grains", "Paddy": "Grains", "Paddy(Dhan)": "Grains",
    "Maize": "Grains", "Bajra": "Grains", "Jowar": "Grains", "Sorghum": "Grains",
    "Barley(Jau)": "Grains", "Barley": "Grains", "Ragi": "Grains",
    
    # Pulses
    "Arhar (Tur/Red Gram)": "Pulses", "Arhar Dal": "Pulses", "Tur": "Pulses",
    "Moong": "Pulses", "Moong Dal": "Pulses", "Green Gram (Moong)": "Pulses",
    "Urad": "Pulses", "Urad Dal": "Pulses", "Black Gram (Urd Beans)": "Pulses",
    "Chana": "Pulses", "Gram Dal": "Pulses", "Bengal Gram(Gram)": "Pulses",
    "Masoor": "Pulses", "Masoor Dal": "Pulses", "Lentil (Masur)": "Pulses",
    
    # Oilseeds
    "Groundnut": "Oilseeds", "Mustard": "Oilseeds", "Mustard Oil": "Oilseeds",
    "Soyabean": "Oilseeds", "Soybean": "Oilseeds", "Sunflower": "Oilseeds",
    "Sesamum(Sesame,Gingelly,Til)": "Oilseeds", "Castor Seed": "Oilseeds",
    "Copra": "Oilseeds", "Coconut": "Oilseeds", "Cotton": "Cash Crops",
    
    # Vegetables
    "Tomato": "Vegetables", "Potato": "Vegetables", "Onion": "Vegetables",
    "Brinjal": "Vegetables", "Cabbage": "Vegetables", "Cauliflower": "Vegetables",
    "Carrot": "Vegetables", "Beans": "Vegetables", "Peas Wet": "Vegetables",
    "Lady Finger": "Vegetables", "Bitter Gourd": "Vegetables", "Bottle Gourd": "Vegetables",
    "Pumpkin": "Vegetables", "Cucumber": "Vegetables", "Spinach": "Vegetables",
    "Green Chilli": "Vegetables", "Capsicum": "Vegetables", "Raddish": "Vegetables",
    "Drumstick": "Vegetables", "Methi": "Vegetables", "Coriander": "Vegetables",
    
    # Fruits
    "Apple": "Fruits", "Banana": "Fruits", "Mango": "Fruits", "Grapes": "Fruits",
    "Orange": "Fruits", "Papaya": "Fruits", "Pomegranate": "Fruits",
    "Watermelon": "Fruits", "Guava": "Fruits", "Lemon": "Fruits", "Lime": "Fruits",
    
    # Spices
    "Chillies": "Spices", "Dry Chillies": "Spices", "Red Chillies": "Spices",
    "Turmeric": "Spices", "Turmeric (Whole)": "Spices", "Ginger": "Spices",
    "Garlic": "Spices", "Coriander Seed": "Spices", "Cumin Seed": "Spices",
    "Fennel Seed": "Spices", "Fenugreek Seed": "Spices", "Black Pepper": "Spices",
    "Ajwan": "Spices", "Cardamom": "Spices", "Cloves": "Spices",
    
    # Sugar & Jaggery
    "Sugar": "Sugar", "Jaggery": "Sugar", "Gur": "Sugar", "Sugarcane": "Cash Crops",
    
    # Others
    "Tea": "Beverages", "Coffee": "Beverages",
}


def get_commodity_category(commodity_name: str) -> str:
    """Get category for a commodity, defaulting to 'Other' if unknown."""
    return COMMODITY_CATEGORIES.get(commodity_name, "Other")


def get_commodity_unit(commodity_name: str) -> str:
    """Get unit for a commodity. Most are per quintal (100kg)."""
    return "quintal"


class DatabaseSeeder:
    """Seeds database with real data from data.gov.in API."""
    
    def __init__(self, db: Session, client: Optional[DataGovClient] = None):
        self.db = db
        self.client = client or get_data_gov_client()
        
        # Caches for lookup
        self._commodity_cache: dict[str, Commodity] = {}
        self._mandi_cache: dict[str, Mandi] = {}
    
    def preload_caches(self) -> None:
        """Load all existing commodities and mandis into in-memory caches.

        Eliminates per-record SELECT queries during seeding.
        """
        for c in self.db.query(Commodity).all():
            self._commodity_cache[c.name] = c

        for m in self.db.query(Mandi).all():
            key = f"{m.name}|{m.district}|{m.state}"
            self._mandi_cache[key] = m

        logger.info(
            "Pre-loaded caches: %d commodities, %d mandis",
            len(self._commodity_cache),
            len(self._mandi_cache),
        )

    def seed_all(
        self,
        limit: Optional[int] = None,
        records: Optional[list[dict]] = None,
    ):
        """
        Seed all data from API.

        Args:
            limit: Optional limit on records to process (for testing)
            records: Pre-fetched records to seed. When provided, skips API fetch.
        """
        logger.info("Starting database seed from data.gov.in...")

        if records is None:
            # Fetch from API only when no pre-fetched records provided
            if limit:
                data = self.client.fetch_prices(limit=limit)
                records = data.get("records", [])
            else:
                records = self.client.fetch_all_prices()

        logger.info(f"Processing {len(records)} records...")

        # Pre-load existing DB entities into caches to avoid per-record SELECTs
        self.preload_caches()

        # Run the three seeding passes
        self.seed_records(records)

        logger.info("Database seed complete!")

    def seed_records(self, records: list[dict]) -> None:
        """Seed pre-fetched records into the database.

        Assumes caches have been pre-loaded via preload_caches().
        Use this for per-date incremental seeding where caches persist
        across multiple calls.
        """
        self._seed_commodities(records)
        self._seed_mandis(records)
        self._seed_prices(records)
    
    def _seed_commodities(self, records: list[dict]):
        """Extract and create unique commodities."""
        commodity_names = set()
        for r in records:
            name = r.get("commodity", "").strip()
            if name:
                commodity_names.add(name)
        
        logger.info(f"Seeding {len(commodity_names)} commodities...")
        
        created = 0
        for name in sorted(commodity_names):
            if name in self._commodity_cache:
                continue
            
            commodity = Commodity(
                id=uuid4(),
                name=name,
                name_local=name,  # Use same name for now
                category=get_commodity_category(name),
                unit=get_commodity_unit(name),
                is_active=True,
            )
            self.db.add(commodity)
            self._commodity_cache[name] = commodity
            created += 1
        
        self.db.commit()
        logger.info(f"Created {created} new commodities")
    
    def _seed_mandis(self, records: list[dict]):
        """Extract and create unique mandis (markets)."""
        mandis_data = {}
        
        for r in records:
            market_name = r.get("market", "").strip()
            if not market_name:
                continue
            
            state = r.get("state", "").strip()
            district = r.get("district", "").strip()
            
            # Unique key for mandi
            key = f"{market_name}|{district}|{state}"
            
            if key not in mandis_data:
                mandis_data[key] = {
                    "name": market_name,
                    "state": state,
                    "district": district,
                }
        
        logger.info(f"Seeding {len(mandis_data)} mandis...")

        created = 0

        for key, data in mandis_data.items():
            if key in self._mandi_cache:
                continue

            # Generate market code from name
            market_code = "".join(
                c for c in data["name"].upper() if c.isalnum()
            )[:10] + str(uuid4())[:4].upper()

            mandi = Mandi(
                id=uuid4(),
                name=data["name"],
                market_code=market_code,
                state=data["state"],
                district=data["district"],
                address=f"{data['name']}, {data['district']}, {data['state']}",
                latitude=None,
                longitude=None,
                is_active=True,
            )
            self.db.add(mandi)
            self._mandi_cache[key] = mandi
            created += 1

        self.db.commit()
        logger.info(
            f"Created {created} new mandis (geocoding deferred to background job)"
        )
    
    def _seed_prices(self, records: list[dict]):
        """Create price history records."""
        logger.info(f"Seeding {len(records)} price records...")
        
        created = 0
        skipped = 0
        
        # Cache to track processed records within this transaction
        # Key: (commodity_id, mandi_name, price_date)
        # Value: PriceHistory object
        record_cache = {}
        
        for r in records:
            commodity_name = r.get("commodity", "").strip()
            market_name = r.get("market", "").strip()
            state = r.get("state", "").strip()
            district = r.get("district", "").strip()
            
            if not commodity_name or not market_name:
                skipped += 1
                continue
            
            # Look up commodity
            commodity = self._commodity_cache.get(commodity_name)
            if not commodity:
                commodity = self.db.query(Commodity).filter(
                    Commodity.name == commodity_name
                ).first()
                if commodity:
                    self._commodity_cache[commodity_name] = commodity
            
            if not commodity:
                skipped += 1
                continue
            
            # Look up mandi
            mandi_key = f"{market_name}|{district}|{state}"
            mandi = self._mandi_cache.get(mandi_key)
            if not mandi:
                mandi = self.db.query(Mandi).filter(
                    Mandi.name == market_name,
                    Mandi.district == district,
                ).first()
                if mandi:
                    self._mandi_cache[mandi_key] = mandi
            
            if not mandi:
                skipped += 1
                continue
            
            # Parse date
            arrival_date_dt = self.client.parse_arrival_date(r.get("arrival_date", ""))
            if not arrival_date_dt:
                arrival_date_dt = datetime.now()
            
            # Convert to date object for model/key
            arrival_date = arrival_date_dt.date()
            
            # Get prices
            min_price = float(r.get("min_price", 0) or 0)
            max_price = float(r.get("max_price", 0) or 0)
            modal_price = float(r.get("modal_price", 0) or 0)
            
            # Unique Key for this price record
            # Note: unique constraint is on (commodity_id, mandi_name, price_date)
            record_key = (commodity.id, mandi.name, arrival_date)
            
            # Check cache first (deduplication within batch)
            price_history = record_cache.get(record_key)
            
            if price_history:
                # We already processed this exact record in this batch
                # Keep the latest values (last writer wins)
                price_history.min_price = min_price
                price_history.max_price = max_price
                price_history.modal_price = modal_price
                continue

            # Check for existing price record in DB
            existing = self.db.query(PriceHistory).filter(
                PriceHistory.commodity_id == commodity.id,
                PriceHistory.mandi_name == mandi.name,
                PriceHistory.price_date == arrival_date,
            ).first()
            
            if existing:
                # Check if prices have changed
                prices_changed = (
                    existing.min_price != min_price or
                    existing.max_price != max_price or
                    existing.modal_price != modal_price
                )
                
                if prices_changed:
                    # Prices changed - update the existing record for this date
                    # This keeps one record per date but with the latest values
                    existing.min_price = min_price
                    existing.max_price = max_price
                    existing.modal_price = modal_price
                    existing.updated_at = datetime.now()  # Track when it was updated
                
                # Add to cache so we don't query DB again for this key
                record_cache[record_key] = existing
            else:
                # Create new record for this date
                price_history = PriceHistory(
                    id=uuid4(),
                    commodity_id=commodity.id,
                    mandi_id=mandi.id,
                    mandi_name=mandi.name,
                    min_price=min_price,
                    max_price=max_price,
                    modal_price=modal_price,
                    price_date=arrival_date,
                )
                self.db.add(price_history)
                record_cache[record_key] = price_history
                created += 1
            
            # Commit in batches (clearing cache is unsafe if we rely on it preventing duplicates across batches?
            # No, cache must persist across batches if we want to dedupe globally.
            # But the UNIQUE constraint is global.
            # If we commit, the object is in DB. Next time cache miss -> DB query -> Found -> Update. Safe.
            # BUT if duplicate comes in NEXT batch, cache miss -> DB query -> Found -> Update.
            # So clearing cache is fine IF we query DB on cache miss.
            # For performance, keeping cache is better, but memory usage? 6000 records * small object. Fine.
            # "created" counter usage for commit:
            if created > 0 and created % 500 == 0:
                self.db.commit()
                logger.info(f"Progress: {created} prices created...")
        
        self.db.commit()
        logger.info(f"Created {created} price records (skipped {skipped})")


def seed_from_api(limit: Optional[int] = None):
    """
    Main entry point to seed database from API.
    
    Args:
        limit: Optional limit on records (for testing)
    """
    db = SessionLocal()
    try:
        seeder = DatabaseSeeder(db)
        seeder.seed_all(limit=limit)
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    seed_from_api(limit=limit)
