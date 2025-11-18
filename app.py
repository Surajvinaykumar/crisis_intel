import streamlit as st
st.set_page_config(page_title="Crisis Response Intelligence", layout="wide")

import os
from datetime import datetime, timedelta
import pandas as pd
import joblib
import folium
from streamlit_folium import folium_static
from dotenv import load_dotenv
import altair as alt

from src import db
from src import risk
from src.fetchers import eonet
from src.models.train_baseline import train_model

load_dotenv()

# Using EONET as the only data source
SELECTED_SOURCES = ["EONET"]

# Event type color mapping for map markers
TYPE_COLORS = {
    "Wildfires": "red",
    "Sea and Lake Ice": "blue",
    "Volcanoes": "green",
    "Severe Storms": "pink",
}

MODEL_PATH = "artifacts/baseline_crisis_lr.joblib"

def init_session_state():
    """Initialize session state variables."""
    if "ml_scores" not in st.session_state:
        st.session_state.ml_scores = {}

def fetch_data():
    """Fetch data from EONET."""
    all_events = []

    with st.spinner("Fetching NASA EONET events..."):
        try:
            eonet_events = eonet.fetch_events()
            all_events.extend(eonet_events)
            st.success(f"Fetched {len(eonet_events)} NASA EONET events")
        except Exception as ex:
            st.error(f"EONET fetch failed: {ex}")

    if all_events:
        db.upsert_events(all_events)
        st.success(f"Total events fetched and stored: {len(all_events)}")
    else:
        st.warning("No events fetched")

def filter_events(events, start_date, end_date, hours_back):
    """Apply filters to events."""
    if not events:
        return []

    df = pd.DataFrame(events)

    # Convert updated_at to datetime (with coerce for missing/invalid dates)
    df["updated_dt"] = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)

    # Only EONET events (filter by source)
    df = df[df["source"] == "EONET"]

    # Date range filter - KEEP rows with NaT (missing dates) so they aren't dropped
    if start_date and end_date:
        start_dt = pd.Timestamp(start_date, tz="UTC")
        end_dt = pd.Timestamp(end_date, tz="UTC") + timedelta(days=1)
        df = df[df["updated_dt"].isna() | ((df["updated_dt"] >= start_dt) & (df["updated_dt"] < end_dt))]

    # Last N hours filter - KEEP rows with NaT (missing dates)
    if hours_back > 0:
        cutoff = pd.Timestamp.now(tz='UTC') - timedelta(hours=hours_back)
        df = df[df["updated_dt"].isna() | (df["updated_dt"] >= cutoff)]

    return df.to_dict("records")

def render_map(events):
    """Render Folium map with events."""
    if not events:
        st.info("No events to display on map")
        return

    events_with_coords = [
        e for e in events
        if e.get("lat") is not None
        and e.get("lon") is not None
        and not pd.isna(e.get("lat"))
        and not pd.isna(e.get("lon"))
    ]

    if not events_with_coords:
        st.info("No events with coordinates to display on map")
        return

    avg_lat = sum(e["lat"] for e in events_with_coords) / len(events_with_coords)
    avg_lon = sum(e["lon"] for e in events_with_coords) / len(events_with_coords)

    if pd.isna(avg_lat) or pd.isna(avg_lon):
        st.info("Unable to calculate map center coordinates")
        return

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=4)

    # Color-code markers by event type
    for event in events_with_coords:
        event_type = str(event.get('type', '')).strip()
        color = TYPE_COLORS.get(event_type, "gray")  # default to gray for unknown types

        ml_risk = event.get("ml_risk")
        priority = event.get("priority_score", 0.0)

        loc_method = event.get('loc_method', 'N/A')
        loc_confidence = event.get('loc_confidence', 0.0)
        loc_notes = event.get('loc_notes', '')

        popup_text = f"""
        <b>{event.get('title', 'Untitled')}</b><br>
        Source: NASA EONET<br>
        Type: {event_type or 'N/A'}<br>
        Severity: {event.get('severity', 'N/A')}<br>
        Updated: {event.get('updated_display', event.get('updated_at', 'N/A'))}<br>
        Location: {loc_method} ({loc_confidence:.0%})<br>
        {loc_notes}<br>
        ML Risk: {ml_risk if ml_risk is not None else 'N/A'}<br>
        Priority Score: {priority:.2f}
        """

        folium.CircleMarker(
            location=[event["lat"], event["lon"]],
            radius=3,  # smaller dots
            popup=folium.Popup(popup_text, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.9
        ).add_to(m)

    # Event type legend
    legend_html = """
    <div style="
    position: fixed;
    bottom: 20px; left: 20px; z-index: 9999;
    background: white; padding: 8px 10px; border: 1px solid #ccc;
    font-size: 13px; line-height: 1.4; box-shadow: 0 1px 4px rgba(0,0,0,0.2);
    ">
    <b>Event Type Legend</b><br/>
    <span style="display:inline-block;width:10px;height:10px;background:red;margin-right:6px;border:1px solid #444;"></span> Wildfires<br/>
    <span style="display:inline-block;width:10px;height:10px;background:blue;margin-right:6px;border:1px solid #444;"></span> Sea and Lake Ice<br/>
    <span style="display:inline-block;width:10px;height:10px;background:green;margin-right:6px;border:1px solid #444;"></span> Volcanoes<br/>
    <span style="display:inline-block;width:10px;height:10px;background:pink;margin-right:6px;border:1px solid #444;"></span> Severe Storms<br/>
    <span style="display:inline-block;width:10px;height:10px;background:gray;margin-right:6px;border:1px solid #444;"></span> Other
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium_static(m, width=1200, height=600)

def main():
    init_session_state()
    db.init_db()

    st.title("Crisis Response Intelligence")
    st.markdown("Real-time crisis monitoring from NASA EONET with ML risk prediction")

    st.sidebar.header("Data Source")
    st.sidebar.write("Using: NASA Natural Events (EONET)")

    st.sidebar.header("Filters")
    start_date = st.sidebar.date_input("Start date", value=datetime.now() - timedelta(days=30))
    end_date = st.sidebar.date_input("End date", value=datetime.now())

    hours_back = st.sidebar.slider("Last N hours (0 = disabled)", 0, 168, 0)

    st.sidebar.header("Actions")

    if st.sidebar.button("Fetch data"):
        fetch_data()

    if st.sidebar.button("Train ML model (tiny)"):
        with st.spinner("Training model..."):
            try:
                result = train_model(MODEL_PATH)
                st.success(f"Model trained successfully!")
                st.json(result)
            except Exception as e:
                st.error(f"Training failed: {e}")

    if st.sidebar.button("Score events (ML)"):
        events = db.read_events()
        if not events:
            st.warning("No events in database to score")
        elif not os.path.exists(MODEL_PATH):
            st.error("Model not found. Please train model first.")
        else:
            with st.spinner("Scoring events..."):
                scored_events = risk.score_events(events, MODEL_PATH)
                st.session_state.ml_scores = {e["id"]: {"ml_risk": e.get("ml_risk"), "priority_score": e.get("priority_score", 0.0)} for e in scored_events}
                st.success(f"Scored {len(scored_events)} events")

    st.sidebar.header("Code Base")
    st.sidebar.markdown("[GitHub Repository](https://github.com/Surajvinaykumar/crisis_intel/tree/main)")
    st.sidebar.caption("Made by Suraj Vinaykumar")

    st.header("Crisis Events")

    events = db.read_events()

    # Diagnostic: show DB counts by source
    if events:
        events_df = pd.DataFrame(events)
        db_counts = events_df["source"].value_counts().to_dict()
        st.caption(f"DB counts by source: {', '.join(f'{k}:{v}' for k, v in db_counts.items())}")

    for event in events:
        if event["id"] in st.session_state.ml_scores:
            event["ml_risk"] = st.session_state.ml_scores[event["id"]]["ml_risk"]
            event["priority_score"] = st.session_state.ml_scores[event["id"]]["priority_score"]
        else:
            event["ml_risk"] = None
            event["priority_score"] = 0.0

    filtered_events = filter_events(events, start_date, end_date, hours_back)

    # Diagnostic: show filtered counts by source
    if filtered_events:
        filtered_df = pd.DataFrame(filtered_events)
        filtered_counts = filtered_df["source"].value_counts().to_dict()
        st.caption(f"Filtered counts by source: {', '.join(f'{k}:{v}' for k, v in filtered_counts.items())}")

        # Show mappable events (with coordinates)
        mappable = filtered_df.dropna(subset=["lat", "lon"])
        if not mappable.empty:
            mappable_counts = mappable["source"].value_counts().to_dict()
            st.caption(f"Mappable (with coordinates): {', '.join(f'{k}:{v}' for k, v in mappable_counts.items())}")

    st.write(f"**Total events:** {len(filtered_events)}")

    if filtered_events:
        display_df = pd.DataFrame(filtered_events)

        # All events are from EONET, display as "NASA EONET"
        display_df["source"] = "NASA EONET"

        display_df["updated_dt"] = pd.to_datetime(display_df["updated_at"], errors="coerce", utc=True)
        display_df["updated_display"] = display_df["updated_dt"].dt.strftime("%b %d, %Y %I:%M %p UTC")

        for i, row in display_df.iterrows():
            if i < len(filtered_events):
                filtered_events[i]["updated_display"] = row["updated_display"]

        columns_to_show = ["id", "source", "type", "title", "severity", "lat", "lon", "loc_method", "loc_confidence", "updated_display"]
        if "ml_risk" in display_df.columns:
            columns_to_show.append("ml_risk")
        if "priority_score" in display_df.columns:
            columns_to_show.append("priority_score")

        display_df = display_df[[col for col in columns_to_show if col in display_df.columns]]

        if "priority_score" in display_df.columns:
            display_df["priority_score"] = (display_df["priority_score"] * 100).round(2).astype(str) + "%"

        st.dataframe(display_df, use_container_width=True)
        st.caption("All times shown in UTC")

        # --- Layout: Map (left) and Bar Chart (right)
        left_col, right_col = st.columns([3, 2], gap="medium")

        with left_col:
            st.markdown("### Event Map")
            render_map(filtered_events)

        with right_col:
            st.markdown("### Events by Type")

            # Prepare counts by event type for the bar chart
            df_counts = pd.DataFrame(filtered_events)
            if not df_counts.empty and "type" in df_counts.columns:
                df_types = (
                    df_counts.assign(type=df_counts["type"].fillna("Unknown").astype(str))
                    .groupby("type", as_index=False)
                    .size()
                    .rename(columns={"size": "count"})
                    .sort_values("count", ascending=False)
                )

                # Limit to top 12 event types for readability
                df_types = df_types.head(12)

                # Define a colorful categorical palette
                domain = df_types["type"].tolist()
                palette = [
                    "#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#8c564b",
                    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#ff7f0e",
                    "#1b9e77", "#d95f02"
                ]
                range_ = (palette + ["#7f7f7f"] * len(domain))[:len(domain)]

                chart = (
                    alt.Chart(df_types)
                    .mark_bar()
                    .encode(
                        x=alt.X("type:N", title="Event type", sort="-y"),
                        y=alt.Y("count:Q", title="Event count"),
                        color=alt.Color("type:N", scale=alt.Scale(domain=domain, range=range_), legend=None),
                        tooltip=[
                            alt.Tooltip("type:N", title="Type"),
                            alt.Tooltip("count:Q", title="Events")
                        ]
                    )
                    .properties(height=320)
                )

                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No events to summarize")
    else:
        st.info("No events match the current filters")

if __name__ == "__main__":
    main()
