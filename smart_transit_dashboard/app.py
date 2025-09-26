import streamlit as st
import pandas as pd
import pydeck as pdk

# Import our data handling function
from data_handler import get_live_data, REALTIME_FEED_URL

# --- Page Configuration ---
st.set_page_config(page_title="Real-Time Transit Dashboard", layout="wide")

# --- Main Dashboard ---
st.title("Real-Time NYC Bus Tracker 🚌")

df = get_live_data(REALTIME_FEED_URL)

if df.empty:
    st.error("Error: Could not fetch live bus data.")
else:
    df = df.dropna(subset=['latitude', 'longitude'])

    # --- Sidebar Filters ---
    st.sidebar.success(f"{len(df)} buses are currently active.")
    
    # Get a unique list of routes for the dropdown
    route_list = ["All Routes"] + sorted(df['route_id'].unique().tolist())
    # Create the dropdown menu
    selected_route = st.sidebar.selectbox("Filter by Route:", route_list)

    # Filter the data if a specific route is chosen
    if selected_route != "All Routes":
        df = df[df['route_id'] == selected_route]

    st.sidebar.header("About")
    st.sidebar.info("This dashboard displays real-time NYC bus locations.")

    # --- Create the Map ---
    view_state = pdk.ViewState(
        latitude=df['latitude'].mean(), 
        longitude=df['longitude'].mean(), 
        zoom=11, # Slightly more zoomed in
        pitch=50,
    )

    tile_layer = pdk.Layer("TileLayer", data="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", opacity=0.8)

    bus_layer = pdk.Layer(
        'ScatterplotLayer',
        data=df,
        get_position='[longitude, latitude]',
        get_color='[255, 40, 40, 180]',
        get_radius=80, # Made the buses a bit bigger
        pickable=True,
    )

    tooltip = {"html": "<b>Bus ID:</b> {vehicle_id}<br/><b>Route:</b> {route_id}"}

    r = pdk.Deck(layers=[tile_layer, bus_layer], initial_view_state=view_state, tooltip=tooltip)
    
    # --- Display the Map ---
    st.pydeck_chart(r)