from app.database.session import SessionLocal
from app.models import Commodity, PriceHistory
from datetime import datetime, timedelta

db = SessionLocal()
start_date = datetime.now().date() - timedelta(days=14)

commodities_to_check = ['Broken Rice', 'Coca', 'Black Gram Dal (Urd Dal)']

for name in commodities_to_check:
    commodity = db.query(Commodity).filter(Commodity.name.ilike(f'%{name}%')).first()
    if commodity:
        count = db.query(PriceHistory).filter(
            PriceHistory.commodity_id == commodity.id,
            PriceHistory.price_date >= start_date
        ).count()
        print(f'{name}: {count} price records in last 14 days (ID: {commodity.id})')
    else:
        print(f'{name}: NOT FOUND in database')

db.close()
