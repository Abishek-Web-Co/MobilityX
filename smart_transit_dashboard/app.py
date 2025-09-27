import streamlit as st
import pandas as pd
import pydeck as pdk
import time
from math import radians, sin, cos, sqrt, atan2

# Import all our data handling functions
from data_handler import get_live_data, get_all_stops, predict_delay

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
st.title("Smart Commute NYC 🚌🚇")

if live_df.empty or stops_df.empty:
    st.error("Error: Could not fetch transit data.")
else:
    live_df = live_df.dropna(subset=['latitude', 'longitude', 'route_id'])
    live_df['color'] = live_df.get('delay', pd.Series(0)).apply(get_color_by_delay)
    
    is_subway = live_df['route_id'].str.len() <= 2
    subway_df = live_df[is_subway]
    bus_df = live_df[~is_subway]
    
    # --- Sidebar ---
    st.sidebar.title("Controls & Analytics")
    st.sidebar.info(f"Tracking **{len(bus_df)}** buses and **{len(subway_df)}** subways.")
    
    with st.sidebar.expander("🔮 Delay Predictor"):
        route_list_pred = sorted(bus_df['route_id'].unique().tolist())
        selected_route_pred = st.selectbox("Select a Bus Route:", route_list_pred, key="pred_route")
        selected_hour = st.slider("Select Hour of Day (24-hr format):", 0, 23, int(time.strftime("%H")))
        
        predicted_delay_sec = predict_delay(selected_hour)
        predicted_delay_min = predicted_delay_sec / 60
        st.metric(
            label=f"Predicted Delay for Route {selected_route_pred} at {selected_hour}:00",
            value=f"~{predicted_delay_min:.1f} minutes"
        )

    with st.sidebar.expander("📍 Trip Planner"):
        stop_names = [""] + sorted(stops_df['stop_name'].unique().tolist())
        start_stop_name = st.selectbox("Start Stop:", stop_names, key="start_stop")
        end_stop_name = st.selectbox("End Stop:", stop_names, key="end_stop")

    with st.sidebar.expander("🗺️ Map Filters", expanded=True):
        show_buses = st.checkbox("Show Buses", value=True)
        show_subways = st.checkbox("Show Subways", value=True)
        show_stops = st.checkbox("Show Bus Stops")
        route_list = ["All Routes"] + sorted(bus_df['route_id'].unique().tolist())
        selected_route = st.selectbox("Filter Bus Route:", route_list)

    with st.sidebar.expander("🔎 Find Nearest Stops"):
        default_lat = live_df['latitude'].mean()
        default_lon = live_df['longitude'].mean()
        lat_input = st.number_input("Enter Latitude:", value=default_lat, format="%.6f")
        lon_input = st.number_input("Enter Longitude:", value=default_lon, format="%.6f")
        find_button = st.button("Find!")

    with st.sidebar.expander("📊 Live Analytics"):
        st.write("Top 10 Busiest Bus Routes")
        route_counts = bus_df['route_id'].value_counts().nlargest(10)
        st.bar_chart(route_counts)

    # --- Main Area ---
    if start_stop_name and end_stop_name:
        st.header("Commute Recommendation")
        start_stop = stops_df[stops_df['stop_name'] == start_stop_name].iloc[0]
        end_stop = stops_df[stops_df['stop_name'] == end_stop_name].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚌 Bus vs. 🚇 Subway")
            st.metric(label="Bus Est. Time", value="~30-40 Mins")
            st.metric(label="Bus Fare", value="$2.90")
            st.markdown("---")
            st.metric(label="Subway Est. Time", value="~20-25 Mins")
            st.metric(label="Subway Fare", value="$2.90")
        with col2:
            st.subheader("🚗 Ride-Share (Estimate)")
            distance = haversine_distance(start_stop['stop_lat'], start_stop['stop_lon'], end_stop['stop_lat'], end_stop['stop_lon'])
            est_time_mins = int((distance * 1.4 / 20) * 60)
            est_cost_usd = distance * 1.4 * 1.50
            st.metric(label="Est. Time", value=f"~{est_time_mins}-{est_time_mins + 5} Mins")
            st.metric(label="Est. Cost", value=f"${est_cost_usd:.2f}")
        st.markdown("---")

    # Map Display
    st.header("Live Transit Map")
    
    if selected_route != "All Routes":
        display_bus_df = bus_df[bus_df['route_id'] == selected_route]
    else:
        display_bus_df = bus_df
    
    layers = [
        pdk.Layer("TileLayer", data="https://a.tile.openstreetmap.org/carto/dark_matter/{z}/{x}/{y}.png", opacity=0.8)
    ]
    if show_buses:
        layers.append(pdk.Layer('ScatterplotLayer', data=display_bus_df, get_position='[longitude, latitude]',
                                get_color='color', get_radius=80, pickable=True))
    if show_subways:
        layers.append(pdk.Layer('ScatterplotLayer', data=subway_df, get_position='[longitude, latitude]',
                                get_color='[0, 128, 255, 180]', get_radius=100, pickable=True))
    if show_stops:
        layers.append(pdk.Layer('ScatterplotLayer', data=stops_df, get_position='[stop_lon, stop_lat]',
                                get_color='[200, 200, 200, 100]', get_radius=15))

    view_state = pdk.ViewState(latitude=live_df['latitude'].mean(), longitude=live_df['longitude'].mean(), zoom=11, pitch=50)
    tooltip = {"html": "<b>ID:</b> {vehicle_id}<br/><b>Route:</b> {route_id}<br/><b>Delay:</b> {delay} seconds"}
    r = pdk.Deck(layers=layers, initial_view_state=view_state, tooltip=tooltip)
    st.pydeck_chart(r, use_container_width=True)

    if find_button:
        st.header("Nearest Bus Stops")
        stops_df['distance_km'] = stops_df.apply(
            lambda row: haversine_distance(lat_input, lon_input, row['stop_lat'], row['stop_lon']), axis=1)
        nearest_stops = stops_df.nsmallest(5, 'distance_km')
        st.dataframe(nearest_stops[['stop_name', 'distance_km']].style.format({'distance_km': '{:.2f} km'}))

