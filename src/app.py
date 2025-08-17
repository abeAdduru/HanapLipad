import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

from .amadeus_client import AmadeusClient

# --- 1. APP INITIALIZATION & CONFIG ---
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Ensure the instance folder exists and set an absolute path for the database
# This is the most reliable way to configure the database path.
try:
    os.makedirs(app.instance_path)
except OSError:
    pass
db_path = os.path.join(app.instance_path, 'flights.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- 2. DATABASE MODELS ---
class FlightPrice(db.Model):
    """Stores flight price data points for a specific date."""
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(10), nullable=False)
    destination = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    oneway_price = db.Column(db.Float)
    roundtrip_price = db.Column(db.Float)
    roundtrip_return_date = db.Column(db.Date)
    airline = db.Column(db.String(80))
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('origin', 'destination', 'date', name='_origin_dest_date_uc'),)

class Subscription(db.Model):
    """Stores user email subscriptions."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    destination = db.Column(db.String(10), nullable=False)


# --- 3. HELPER FUNCTIONS ---
def get_airline_info(api_response):
    """Extracts airline name and price from the Amadeus API response."""
    if not api_response or not api_response.get('data'):
        return None, None
    try:
        data = api_response['data'][0]
        carrier_code = data['itineraries'][0]['segments'][0]['carrierCode']
        airline_name = api_response['dictionaries']['carriers'][carrier_code]
        price = float(data['price']['total'])
        return airline_name, price
    except (KeyError, IndexError):
        return None, None


# --- 4. API ROUTES (VIEWS) ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/cheapest-flights")
def get_cheapest_flights():
    """API endpoint with caching to get the cheapest flights."""
    start_date_str = request.args.get('startDate')
    end_date_str = request.args.get('endDate')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    amadeus = AmadeusClient()
    origins = ['HND', 'NRT']
    destinations = ['SIN', 'MNL']
    results = {}
    freshness_limit = datetime.utcnow() - timedelta(hours=12)

    with app.app_context():
        for dest in destinations:
            cached_flights = db.session.query(FlightPrice).filter(
                FlightPrice.destination == dest,
                FlightPrice.date.between(start_date, end_date),
                FlightPrice.scanned_at > freshness_limit
            ).all()

            cached_dates = {flight.date for flight in cached_flights}
            all_dates_in_range = {start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)}
            missing_dates = all_dates_in_range - cached_dates
            
            if missing_dates:
                print(f"INFO: For {dest}, found {len(cached_dates)} cached dates. Fetching {len(missing_dates)} missing dates from API.")
                for date_to_scan in sorted(list(missing_dates)):
                    cheapest_oneway_price, cheapest_roundtrip_price = float('inf'), float('inf')
                    best_oneway_origin, best_roundtrip_origin = None, None
                    best_oneway_airline, best_roundtrip_airline = None, None
                    return_date = date_to_scan + timedelta(days=7)

                    for origin in origins:
                        oneway_response = amadeus.search_flights(origin, dest, date_to_scan.strftime('%Y-%m-%d'))
                        airline_name, price = get_airline_info(oneway_response)
                        if airline_name and price < cheapest_oneway_price:
                            cheapest_oneway_price, best_oneway_airline, best_oneway_origin = price, airline_name, origin
                        
                        roundtrip_response = amadeus.search_roundtrip_flights(origin, dest, date_to_scan.strftime('%Y-%m-%d'), return_date.strftime('%Y-%m-%d'))
                        airline_name, price = get_airline_info(roundtrip_response)
                        if airline_name and price < cheapest_roundtrip_price:
                            cheapest_roundtrip_price, best_roundtrip_airline, best_roundtrip_origin = price, airline_name, origin
                    
                    if best_oneway_origin or best_roundtrip_origin:
                        new_flight_price = FlightPrice(
                            origin=best_oneway_origin or best_roundtrip_origin,
                            destination=dest, date=date_to_scan,
                            oneway_price=cheapest_oneway_price if best_oneway_origin else None,
                            roundtrip_price=cheapest_roundtrip_price if best_roundtrip_origin else None,
                            roundtrip_return_date=return_date if best_roundtrip_origin else None,
                            airline=best_oneway_airline or best_roundtrip_airline,
                            scanned_at=datetime.utcnow()
                        )
                        db.session.merge(new_flight_price)
                db.session.commit()

            final_flights = db.session.query(FlightPrice).filter(
                FlightPrice.destination == dest,
                FlightPrice.date.between(start_date, end_date)
            ).all()
            
            cheapest_oneway = min(final_flights, key=lambda x: x.oneway_price if x.oneway_price is not None else float('inf'), default=None)
            cheapest_roundtrip = min(final_flights, key=lambda x: x.roundtrip_price if x.roundtrip_price is not None else float('inf'), default=None)

            results[dest] = {
                'oneWay': {
                    'price': cheapest_oneway.oneway_price, 'date': cheapest_oneway.date.isoformat(), 
                    'origin': cheapest_oneway.origin, 'airline': cheapest_oneway.airline
                } if cheapest_oneway and cheapest_oneway.oneway_price is not None else None,
                'roundTrip': {
                    'price': cheapest_roundtrip.roundtrip_price, 'date': cheapest_roundtrip.date.isoformat(), 
                    'returnDate': cheapest_roundtrip.roundtrip_return_date.isoformat() if cheapest_roundtrip.roundtrip_return_date else None, 
                    'origin': cheapest_roundtrip.origin, 'airline': cheapest_roundtrip.airline
                } if cheapest_roundtrip and cheapest_roundtrip.roundtrip_price is not None else None
            }
    return jsonify(results)


# --- 5. CORE LOGIC (for manage.py) ---
def scan_and_save_flights():
    """Scans flights for the next 30 days and saves them to the database cache."""
    print("--- Starting daily flight scan to populate cache ---")
    amadeus = AmadeusClient()
    if not amadeus.token:
        print("Aborting scan due to Amadeus connection issue.")
        return

    destinations = ['SIN', 'MNL']
    origins = ['HND', 'NRT']
    start_date = datetime.now().date()
    
    with app.app_context():
        for i in range(30):
            date_to_scan = start_date + timedelta(days=i + 1)
            print(f"\nScanning for date: {date_to_scan.strftime('%Y-%m-%d')}")
            
            for dest in destinations:
                cheapest_oneway_price, cheapest_roundtrip_price = float('inf'), float('inf')
                best_origin, best_oneway_airline, best_roundtrip_airline = None, None, None
                return_date = date_to_scan + timedelta(days=7)

                for origin in origins:
                    oneway_response = amadeus.search_flights(origin, dest, date_to_scan.strftime('%Y-%m-%d'))
                    airline_name, price = get_airline_info(oneway_response)
                    if airline_name and price < cheapest_oneway_price:
                        cheapest_oneway_price, best_oneway_airline, best_origin = price, airline_name, origin

                    roundtrip_response = amadeus.search_roundtrip_flights(origin, dest, date_to_scan.strftime('%Y-%m-%d'), return_date.strftime('%Y-%m-%d'))
                    airline_name, price = get_airline_info(roundtrip_response)
                    if airline_name and price < cheapest_roundtrip_price:
                        cheapest_roundtrip_price, best_roundtrip_airline = price, airline_name
                        best_origin = origin if not best_origin else best_origin

                if best_origin:
                    new_flight_price = FlightPrice(
                        origin=best_origin, destination=dest, date=date_to_scan,
                        oneway_price=cheapest_oneway_price if cheapest_oneway_price != float('inf') else None,
                        roundtrip_price=cheapest_roundtrip_price if cheapest_roundtrip_price != float('inf') else None,
                        roundtrip_return_date=return_date if cheapest_roundtrip_price != float('inf') else None,
                        airline=best_oneway_airline or best_roundtrip_airline,
                        scanned_at=datetime.utcnow()
                    )
                    db.session.merge(new_flight_price)
        
        db.session.commit()
    print("\n--- Flight scan finished. Cache is populated. ---")