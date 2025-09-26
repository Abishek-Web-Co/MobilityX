import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2

# --- This is the correct, direct URL for live NYC Bus Data ---
REALTIME_FEED_URL = "http://gtfsrt.prod.obanyc.com/vehiclePositions.pb"


def get_live_data(feed_url):
    """
    Fetches and parses live GTFS-Realtime data from NYC MTA.
    """
    print("Attempting to fetch live data from NYC...")
    try:
        feed = gtfs_realtime_pb2.FeedMessage()
        
        response = requests.get(feed_url, timeout=20)
        response.raise_for_status() # Raise an exception for bad status codes
        
        feed.ParseFromString(response.content)
        
        bus_data = []
        for entity in feed.entity:
            if entity.HasField('vehicle'):
                bus_data.append({
                    'vehicle_id': entity.vehicle.vehicle.id,
                    'route_id': entity.vehicle.trip.route_id,
                    'latitude': entity.vehicle.position.latitude,
                    'longitude': entity.vehicle.position.longitude,
                })
                
        df = pd.DataFrame(bus_data)
        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

# This block lets us test it
if __name__ == "__main__":
    live_bus_df = get_live_data(REALTIME_FEED_URL)
    
    if not live_bus_df.empty:
        print("\n✅ Success! Fetched live NYC bus data.")
        print(f"Number of active buses: {len(live_bus_df)}")
        print(live_bus_df.head())
    else:
        print("\n❌ Failed to fetch data. Make sure your URL is correct and you have an internet connection.")