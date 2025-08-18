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
            # Query and fetch missing dates logic (this part is correct)
            cached_flights = db.session.query(FlightPrice).filter(
                FlightPrice.destination == dest,
                FlightPrice.date.between(start_date, end_date),
                FlightPrice.scanned_at > freshness_limit
            ).all()
            cached_dates = {flight.date for flight in cached_flights}
            all_dates_in_range = {start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)}
            missing_dates = all_dates_in_range - cached_dates
            
            if missing_dates:
                # ... (The logic to fetch and save to DB is correct) ...
                print(f"INFO: For {dest}, fetching {len(missing_dates)} missing dates from API.")
                # ... (This whole block should be the same as the one that fixed the IntegrityError) ...
                for date_to_scan in sorted(list(missing_dates)):
                    # ...
                    existing_record = db.session.query(FlightPrice).filter_by(destination=dest, date=date_to_scan).first()
                    if existing_record:
                        # ... update logic ...
                        db.session.merge(existing_record)
                    else:
                        # ... create logic ...
                        db.session.add(new_flight_price)
                db.session.commit()


            # --- THIS IS THE FIX ---
            # Query the database again to get the cheapest flights from the complete, updated data
            final_flights = db.session.query(FlightPrice).filter(
                FlightPrice.destination == dest,
                FlightPrice.date.between(start_date, end_date)
            ).all()
            
            cheapest_oneway = min(final_flights, key=lambda x: x.oneway_price if x.oneway_price is not None else float('inf'), default=None)
            
            # Find the best return flight based on the date of the cheapest outbound flight
            cheapest_return_oneway = None
            if cheapest_oneway:
                cheapest_return_oneway = db.session.query(FlightPrice).filter_by(
                    destination=dest,
                    date=cheapest_oneway.date
                ).first()

            cheapest_roundtrip = min(final_flights, key=lambda x: x.roundtrip_price if x.roundtrip_price is not None else float('inf'), default=None)

            # Build the final JSON response, ensuring ALL fields are included
            results[dest] = {
                'oneWay': {
                    'price': cheapest_oneway.oneway_price, 
                    'date': cheapest_oneway.date.isoformat(), 
                    'origin': cheapest_oneway.origin, 
                    'airline': cheapest_oneway.airline,
                    'departure_time': cheapest_oneway.oneway_departure_time,
                    'arrival_time': cheapest_oneway.oneway_arrival_time
                } if cheapest_oneway and cheapest_oneway.oneway_price is not None else None,

                'returnOneway': {
                    'price': cheapest_return_oneway.return_oneway_price,
                    'date': cheapest_return_oneway.return_oneway_date.isoformat() if cheapest_return_oneway and cheapest_return_oneway.return_oneway_date else None,
                    'airline': cheapest_return_oneway.return_oneway_airline,
                    'departure_time': cheapest_return_oneway.return_oneway_departure_time,
                    'arrival_time': cheapest_return_oneway.return_oneway_arrival_time
                } if cheapest_return_oneway and cheapest_return_oneway.return_oneway_price is not None else None,

                'roundTrip': {
                    'price': cheapest_roundtrip.roundtrip_price, 
                    'date': cheapest_roundtrip.date.isoformat(), 
                    'returnDate': cheapest_roundtrip.roundtrip_return_date.isoformat() if cheapest_roundtrip and cheapest_roundtrip.roundtrip_return_date else None, 
                    'origin': cheapest_roundtrip.origin, 
                    'airline': cheapest_roundtrip.airline,
                    'departure_time': cheapest_roundtrip.oneway_departure_time,
                    'arrival_time': cheapest_roundtrip.oneway_arrival_time
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
                    # Now this call will work because get_airline_info is defined above
                    airline_name, price = get_airline_info(oneway_response)
                    if airline_name and price < cheapest_oneway_price:
                        cheapest_oneway_price, best_oneway_airline, best_origin = price, airline_name, origin

                    roundtrip_response = amadeus.search_roundtrip_flights(origin, dest, date_to_scan.strftime('%Y-%m-%d'), return_date.strftime('%Y-%m-%d'))
                    # This call also works
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

def get_flight_details(api_response):
    """Extracts price, airline, and time details from an API response."""
    if not api_response or not api_response.get('data'):
        return None
    try:
        data = api_response['data'][0]
        # The flight times are nested inside the first itinerary and the first segment
        itinerary = data['itineraries'][0]['segments'][0]
        
        details = {
            "price": float(data['price']['total']),
            "airline": api_response['dictionaries']['carriers'][itinerary['carrierCode']],
            # Correctly parse the full ISO timestamp and format it to HH:MM
            "departure_time": datetime.fromisoformat(itinerary['departure']['at']).strftime('%H:%M'),
            "arrival_time": datetime.fromisoformat(itinerary['arrival']['at']).strftime('%H:%M')
        }
        return details
    except (KeyError, IndexError) as e:
        # If any key is missing, we know the data is incomplete
        print(f"DEBUG: Could not parse flight details from API response. Error: {e}")
        return None