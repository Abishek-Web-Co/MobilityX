import streamlit as st
import pandas as pd
import pydeck as pdk
import time
from math import radians, sin, cos, sqrt, atan2

# Import our data handling functions
from data_handler import get_live_data, get_all_stops

# --- Page Configuration ---
st.set_page_config(page_title="Smart Commute Dashboard", layout="wide")

# --- Helper Functions ---
def get_color_by_delay(delay):
    if pd.isna(delay) or delay <= 0: return [0, 255, 0, 180]
    elif 0 < delay <= 300: return [255, 165, 0, 180]
    else: return [255, 40, 40, 180]

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dLat, dLon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# --- Load Data ---
live_df = get_live_data()
stops_df = get_all_stops()

# --- Main App ---
st.title("Smart Commute NYC 🚌")

if live_df.empty or stops_df.empty:
    st.error("Error: Could not fetch transit data.")
else:
    live_df = live_df.dropna(subset=['latitude', 'longitude', 'route_id'])
    live_df['color'] = live_df.get('delay', pd.Series(0)).apply(get_color_by_delay)
    
    # --- Sidebar ---
    st.sidebar.title("Controls & Analytics")
    st.sidebar.info(f"**{len(live_df)}** buses are currently active.")
    
    with st.sidebar.expander("📍 Trip Planner"):
        stop_names = [""] + sorted(stops_df['stop_name'].unique().tolist())
        start_stop_name = st.selectbox("Start Stop:", stop_names, key="start_stop")
        end_stop_name = st.selectbox("End Stop:", stop_names, key="end_stop")

    with st.sidebar.expander("🗺️ Map Filters"):
        show_stops = st.checkbox("Show All Bus Stops")
        route_list = ["All Routes"] + sorted(live_df['route_id'].unique().tolist())
        selected_route = st.selectbox("Filter by Route:", route_list)

    with st.sidebar.expander("🔎 Find Nearest Stops"):
        default_lat = live_df['latitude'].mean()
        default_lon = live_df['longitude'].mean()
        lat_input = st.number_input("Enter Latitude:", value=default_lat, format="%.6f")
        lon_input = st.number_input("Enter Longitude:", value=default_lon, format="%.6f")
        find_button = st.button("Find!")

    with st.sidebar.expander("📊 Live Analytics"):
        st.write("Top 10 Busiest Routes")
        route_counts = live_df['route_id'].value_counts().nlargest(10)
        st.bar_chart(route_counts)

    # --- Main Area ---
    # Display Trip Planner results if stops are selected
    if start_stop_name and end_stop_name:
        st.header("Commute Recommendation")
        start_stop = stops_df[stops_df['stop_name'] == start_stop_name].iloc[0]
        end_stop = stops_df[stops_df['stop_name'] == end_stop_name].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚌 Public Transit")
            st.info("Route logic would appear here.")
            st.metric(label="Est. Time", value="~25-35 Mins")
        with col2:
            st.subheader("🚗 Private Ride-Share")
            distance = haversine_distance(start_stop['stop_lat'], start_stop['stop_lon'], end_stop['stop_lat'], end_stop['stop_lon'])
            est_time_mins = int((distance * 1.4 / 20) * 60)
            est_cost_usd = distance * 1.4 * 1.50
            st.metric(label="Est. Time", value=f"~{est_time_mins}-{est_time_mins + 5} Mins")
            st.metric(label="Est. Cost", value=f"${est_cost_usd:.2f}")
        st.markdown("---")

    # Map Display
    st.header("Live Transit Map")
    
    # Filter and setup map layers
    if selected_route != "All Routes": display_df = live_df[live_df['route_id'] == selected_route]
    else: display_df = live_df
    layers = [pdk.Layer("TileLayer", data="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", opacity=0.8),
              pdk.Layer('ScatterplotLayer', data=display_df, get_position='[longitude, latitude]',
                        get_color='color', get_radius=80, pickable=True)]
    if show_stops:
        layers.append(pdk.Layer('ScatterplotLayer', data=stops_df, get_position='[stop_lon, stop_lat]',
                                get_color='[200, 200, 200, 100]', get_radius=15))

    view_state = pdk.ViewState(latitude=lat_input, longitude=lon_input, zoom=12, pitch=50)
    tooltip = {"html": "<b>Bus ID:</b> {vehicle_id}<br/><b>Route:</b> {route_id}<br/><b>Delay:</b> {delay} seconds"}
    r = pdk.Deck(layers=layers, initial_view_state=view_state, tooltip=tooltip)
    st.pydeck_chart(r, use_container_width=True)

    # Display Nearest Stops if button is clicked
    if find_button:
        st.header("Nearest Bus Stops")
        stops_df['distance_km'] = stops_df.apply(
            lambda row: haversine_distance(lat_input, lon_input, row['stop_lat'], row['stop_lon']),
            axis=1
        )
        nearest_stops = stops_df.nsmallest(5, 'distance_km')
        st.dataframe(nearest_stops[['stop_name', 'distance_km']].style.format({'distance_km': '{:.2f} km'}))