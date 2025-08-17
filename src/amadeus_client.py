import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AmadeusClient:
    """
    A client to interact with the Amadeus Flight Search API.
    """
    def __init__(self):
        self.client_id = os.getenv("AMADEUS_API_KEY")
        self.client_secret = os.getenv("AMADEUS_API_SECRET")
        
        # --- ADD THESE TWO LINES FOR DEBUGGING ---
        print(f"🔑 Loaded Key: {self.client_id}")
        print(f"🤫 Loaded Secret: {self.client_secret}")
        # ------------------------------------------

        self.base_url = "https://test.api.amadeus.com" # Use production URL for real data
        self.token = self._get_access_token()

    def _get_access_token(self):
        """Fetches a new access token from Amadeus."""
        url = f"{self.base_url}/v1/security/oauth2/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status() # Raise an exception for bad status codes
            print("Successfully obtained Amadeus access token.")
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            print(f"Error getting access token: {e}")
            return None

    def search_flights(self, origin, destination, departure_date):
        """
        Searches for the cheapest flight on a given date.
        
        Args:
            origin (str): IATA code for the origin airport (e.g., "HND").
            destination (str): IATA code for the destination airport (e.g., "SIN").
            departure_date (str): Date in "YYYY-MM-DD" format.
            
        Returns:
            dict: The flight offer data or None if an error occurs.
        """
        if not self.token:
            print("Cannot search flights without an access token.")
            return None

        url = f"{self.base_url}/v2/shopping/flight-offers"
        headers = {'Authorization': f'Bearer {self.token}'}
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': 1,
            'nonStop': 'true', # Let's search for non-stop flights to keep it simple
            'currencyCode': 'JPY',
            'max': 1 # We only need the cheapest one
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            print(f"Successfully fetched flights for {origin} to {destination} on {departure_date}.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching flights: {e}")
            # If the token expired, you might need to refresh it here.
            # For simplicity, we'll assume it's valid for now.
            return None
   
    def search_roundtrip_flights(self, origin, destination, departure_date, return_date):
        """
        Searches for the cheapest round-trip flight.
        """
        if not self.token:
            print("Cannot search flights without an access token.")
            return None

        url = f"{self.base_url}/v2/shopping/flight-offers"
        headers = {'Authorization': f'Bearer {self.token}'}
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'returnDate': return_date, # Key difference for round trips
            'adults': 1,
            'nonStop': 'true',
            'currencyCode': 'JPY',
            'max': 1
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            print(f"Successfully fetched round-trip for {origin}-{destination} on {departure_date} to {return_date}.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching round-trip flights: {e}")
            return None

# Example usage (for testing)
if __name__ == '__main__':
    client = AmadeusClient()
    if client.token:
        # Search for a flight tomorrow (replace with your desired date)
        from datetime import date, timedelta
        tomorrow = date.today() + timedelta(days=1)
        flights = client.search_flights("HND", "SIN", tomorrow.strftime("%Y-%m-%d"))
        if flights:
            price = flights[0]['price']['total']
            print(f"Cheapest flight found: {price} JPY")