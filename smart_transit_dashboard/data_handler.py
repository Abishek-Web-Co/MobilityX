import streamlit as st
import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
import time

# --- URLs for live data feeds ---
POSITIONS_URL = "http://gtfsrt.prod.obanyc.com/vehiclePositions.pb"
TRIP_UPDATES_URL = "http://gtfsrt.prod.obanyc.com/tripUpdates.pb"

# Using cache for the stops data so we only read the local file once
@st.cache_data
def get_all_stops():
    """
    Reads the local stops.txt file.
    """
    print("Reading local bus stop data...")
    try:
        # Read the local CSV file directly
        stops_df = pd.read_csv("stops.txt")
        return stops_df[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']]
    except FileNotFoundError:
        print("Error: stops.txt not found! Make sure you've downloaded it.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error reading stops data: {e}")
        return pd.DataFrame()


def get_live_data():
    """
    Fetches and merges both vehicle positions and trip updates.
    """
    print(f"Fetching new data at {time.strftime('%X')}")
    try:
        # Fetch Vehicle Positions
        positions_feed = gtfs_realtime_pb2.FeedMessage()
        positions_response = requests.get(POSITIONS_URL, timeout=20)
        positions_response.raise_for_status()
        positions_feed.ParseFromString(positions_response.content)
        positions_df = pd.DataFrame([{
            'trip_id': entity.vehicle.trip.trip_id,
            'route_id': entity.vehicle.trip.route_id,
            'vehicle_id': entity.vehicle.vehicle.id,
            'latitude': entity.vehicle.position.latitude,
            'longitude': entity.vehicle.position.longitude,
        } for entity in positions_feed.entity if entity.HasField('vehicle')])

        # Fetch Trip Updates (for delay info)
        updates_feed = gtfs_realtime_pb2.FeedMessage()
        updates_response = requests.get(TRIP_UPDATES_URL, timeout=20)
        updates_response.raise_for_status()
        updates_feed.ParseFromString(updates_response.content)
        updates_df = pd.DataFrame([{
            'trip_id': entity.trip_update.trip.trip_id,
            'delay': entity.trip_update.stop_time_update[0].arrival.delay,
        } for entity in updates_feed.entity if entity.HasField('trip_update') and entity.trip_update.stop_time_update])

        # Merge the two datasets
        if not positions_df.empty and not updates_df.empty:
            merged_df = pd.merge(positions_df, updates_df, on='trip_id', how='left')
            return merged_df
        else:
            return positions_df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching live data: {e}")
        return pd.DataFrame()