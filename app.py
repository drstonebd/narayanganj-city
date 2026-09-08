import os
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="Narayanganj Weather AI",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# PROJECT CONFIG
# ==========================================================

CITY = "Narayanganj"
COUNTRY = "Bangladesh"

LAT = 23.6238
LON = 90.5000

TIMEZONE = "Asia/Dhaka"


# ==========================================================
# HTML HELPER
# ==========================================================

def render_html(content: str):
    """Render HTML safely across Streamlit versions."""
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


# ==========================================================
# SECRET HELPER
# ==========================================================

def get_secret(name: str, default: str = "") -> str:
    """Read a secret from Streamlit secrets, then environment."""
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


TOMTOM_API_KEY = get_secret("TOMTOM_API_KEY", "")


# ==========================================================
# WEATHER API
# ==========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
            "visibility",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "visibility",
            "uv_index",
        ]),
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "sunrise",
            "sunset",
            "uv_index_max",
            "precipitation_probability_max",
            "precipitation_sum",
        ]),
        "timezone": TIMEZONE,
        "forecast_days": 7,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


# ==========================================================
# TOMTOM TRAFFIC API
# ==========================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_traffic():
    """
    Fetch a live traffic flow segment near Narayanganj.

    The API key is read from .streamlit/secrets.toml:
        TOMTOM_API_KEY = "YOUR_NEW_KEY"
    """

    if not TOMTOM_API_KEY:
        return None, "TOMTOM_API_KEY is not configured."

    url = (
        "https://api.tomtom.com/"
        "traffic/services/4/"
        "flowSegmentData/absolute/10/json"
    )

    params = {
        "point": f"{LAT},{LON}",
        "unit": "KMPH",
        "key": TOMTOM_API_KEY,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=12,
        )

        response.raise_for_status()
        return response.json(), ""

    except requests.HTTPError as error:
        status = getattr(error.response, "status_code", "unknown")
        return None, f"TomTom HTTP error: {status}"

    except requests.RequestException as error:
        return None, f"TomTom connection error: {error}"

    except Exception as error:
        return None, f"TomTom error: {error}"


# ==========================================================
# WEATHER DESCRIPTION
# ==========================================================

def weather_info(code):
    weather = {
        0: ("☀️", "Clear sky"),
        1: ("🌤️", "Mainly clear"),
        2: ("⛅", "Partly cloudy"),
        3: ("☁️", "Overcast"),
        45: ("🌫️", "Fog"),
        48: ("🌫️", "Rime fog"),
        51: ("🌦️", "Light drizzle"),
        53: ("🌦️", "Drizzle"),
        55: ("🌧️", "Heavy drizzle"),
        56: ("🌧️", "Freezing drizzle"),
        57: ("🌧️", "Heavy freezing drizzle"),
        61: ("🌦️", "Light rain"),
        63: ("🌧️", "Rain"),
        65: ("🌧️", "Heavy rain"),
        66: ("🌧️", "Freezing rain"),
        67: ("🌧️", "Heavy freezing rain"),
        71: ("🌨️", "Light snow"),
        73: ("🌨️", "Snow"),
        75: ("❄️", "Heavy snow"),
        77: ("❄️", "Snow grains"),
        80: ("🌦️", "Rain showers"),
        81: ("🌧️", "Rain showers"),
        82: ("⛈️", "Heavy rain showers"),
        85: ("🌨️", "Snow showers"),
        86: ("❄️", "Heavy snow showers"),
        95: ("⛈️", "Thunderstorm"),
        96: ("⛈️", "Thunderstorm + hail"),
        99: ("⛈️", "Heavy thunderstorm + hail"),
    }

    try:
        code = int(code)
    except Exception:
        code = 0

    return weather.get(code, ("🌤️", "Unknown"))


# ==========================================================
# SAFE NUMBER
# ==========================================================

def safe_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ==========================================================
# LOAD WEATHER
# ==========================================================

try:
    data = get_weather()
except Exception as error:
    st.error("Weather API connection failed.")
    st.code(str(error))
    st.info(
        "Internet connection এবং Open-Meteo API check করে "
        "আবার Run করুন।"
    )
    st.stop()


current = data.get("current", {})
hourly = data.get("hourly", {})
daily = data.get("daily", {})


# ==========================================================
# CURRENT WEATHER
# ==========================================================

temperature = round(
    safe_number(current.get("temperature_2m"))
)

feels_like = round(
    safe_number(current.get("apparent_temperature"))
)

humidity = round(
    safe_number(current.get("relative_humidity_2m"))
)

wind = round(
    safe_number(current.get("wind_speed_10m"))
)

wind_direction = round(
    safe_number(current.get("wind_direction_10m"))
)

pressure = round(
    safe_number(current.get("surface_pressure"))
)

visibility = round(
    safe_number(current.get("visibility")) / 1000,
    1,
)

rain = safe_number(current.get("precipitation"))

weather_icon, weather_text = weather_info(
    current.get("weather_code", 0)
)


# ==========================================================
# UV INDEX
# ==========================================================

uv = 0.0

try:
    current_hour = str(current.get("time", ""))[:13]

    for i, item_time in enumerate(hourly.get("time", [])):
        if str(item_time).startswith(current_hour):
            uv = safe_number(hourly["uv_index"][i])
            break

    if uv == 0 and daily.get("uv_index_max"):
        uv = safe_number(daily["uv_index_max"][0])

except Exception:
    if daily.get("uv_index_max"):
        uv = safe_number(daily["uv_index_max"][0])


# ==========================================================
# UPDATED TIME
# ==========================================================

try:
    updated_dt = datetime.fromisoformat(
        current["time"]
    )
    updated_time = updated_dt.strftime("%I:%M %p").lstrip("0")
except Exception:
    updated_time = "--"


# ==========================================================
# TRAFFIC
# ==========================================================

traffic_data, traffic_error = get_traffic()

traffic_speed = None
traffic_free_speed = None
traffic_ratio = None
traffic_status = "API NOT CONFIGURED"


if traffic_data:
    try:
        flow = traffic_data.get("flowSegmentData", {})

        traffic_speed = safe_number(
            flow.get("currentSpeed"),
            None,
        )

        traffic_free_speed = safe_number(
            flow.get("freeFlowSpeed"),
            None,
        )

        if (
            traffic_speed is not None
            and traffic_free_speed
            and traffic_free_speed > 0
        ):
            traffic_ratio = (
                traffic_speed / traffic_free_speed
            )

            if traffic_ratio >= 0.85:
                traffic_status = "FREE FLOW"
            elif traffic_ratio >= 0.60:
                traffic_status = "MODERATE"
            elif traffic_ratio >= 0.35:
                traffic_status = "HEAVY"
            else:
                traffic_status = "JAM"
        else:
            traffic_status = "UNAVAILABLE"

    except Exception:
        traffic_status = "UNAVAILABLE"

elif TOMTOM_API_KEY:
    traffic_status = "UNAVAILABLE"


# ==========================================================
# TRAFFIC LINE
# ==========================================================

def add_traffic_line(map_object):
    """Add TomTom road segment to a Folium map if available."""

    if not traffic_data:
        return

    try:
        coordinates = (
            traffic_data
            .get("flowSegmentData", {})
            .get("coordinates", {})
            .get("coordinate", [])
        )

        line = [
            (
                item["latitude"],
                item["longitude"],
            )
            for item in coordinates
            if "latitude" in item and "longitude" in item
        ]

        if not line:
            return

        if traffic_ratio is None:
            line_color = "blue"
        elif traffic_ratio >= 0.85:
            line_color = "green"
        elif traffic_ratio >= 0.60:
            line_color = "orange"
        else:
            line_color = "red"

        popup_text = (
            f"Traffic: "
            f"{traffic_speed:.0f} km/h"
            if traffic_speed is not None
            else "Traffic data"
        )

        folium.PolyLine(
            line,
            color=line_color,
            weight=7,
            opacity=0.9,
            popup=popup_text,
        ).add_to(map_object)

    except Exception:
        pass


# ==========================================================
# GLOBAL CSS
# ==========================================================

render_html(
    """
<style>
@import url(
'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap'
);

:root {
    --bg: #060a0f;
    --panel: rgba(18,25,33,.72);
    --border: rgba(255,255,255,.095);
    --text: #f5f7fa;
    --muted: #85919f;
    --blue: #55b8ff;
    --cyan: #6de7ff;
    --green: #63e6a3;
}

.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(36,125,190,.20), transparent 32%),
        radial-gradient(circle at 90% 10%, rgba(91,68,170,.16), transparent 30%),
        radial-gradient(circle at 50% 100%, rgba(20,100,125,.12), transparent 38%),
        #060a0f !important;
    color: var(--text);
}

html, body, [class*="css"] {
    font-family: "Space Grotesk", "Inter", sans-serif !important;
}

.block-container {
    max-width: 1600px !important;
    padding: 20px 28px 30px 28px !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1016, #060a0f) !important;
    border-right: 1px solid rgba(255,255,255,.07);
}

section[data-testid="stSidebar"] > div {
    padding-top: 22px;
}

.side-logo {
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto;
    border-radius: 17px;
    font-size: 26px;
    background: linear-gradient(145deg, rgba(255,255,255,.12), rgba(255,255,255,.035));
    border: 1px solid rgba(255,255,255,.10);
}

.side-brand {
    text-align: center;
    margin-top: 10px;
    font-size: 10px;
    letter-spacing: 3px;
    color: #7d8996;
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
}

.dashboard-title {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -1.2px;
}

.dashboard-subtitle {
    margin-top: 3px;
    color: var(--muted);
    font-size: 11px;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 8px 13px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    color: #7cf0ad;
    background: rgba(65,220,135,.075);
    border: 1px solid rgba(65,220,135,.20);
}

.live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #54e994;
    box-shadow: 0 0 12px #54e994;
}

.weather-card {
    min-height: 290px;
    padding: 27px;
    border-radius: 25px;
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 90% 20%, rgba(45,157,230,.26), transparent 33%),
        radial-gradient(circle at 30% 100%, rgba(38,105,140,.14), transparent 40%),
        rgba(17,25,33,.74);
    border: 1px solid var(--border);
    box-shadow: 0 25px 70px rgba(0,0,0,.30);
    backdrop-filter: blur(25px);
}

.weather-location {
    color: #84909d;
    font-size: 11px;
}

.weather-main {
    display: flex;
    align-items: center;
    gap: 18px;
    margin-top: 20px;
}

.weather-icon {
    font-size: 72px;
    line-height: 1;
}

.temperature {
    font-size: 67px;
    line-height: .9;
    font-weight: 700;
    letter-spacing: -4px;
}

.temperature-unit {
    font-size: 23px;
    color: #8d9aa7;
    vertical-align: top;
}

.weather-condition {
    margin-top: 16px;
    font-size: 14px;
    font-weight: 500;
}

.feels-like {
    margin-top: 6px;
    color: #768391;
    font-size: 10px;
}

.weather-footer {
    position: absolute;
    bottom: 22px;
    left: 27px;
    right: 27px;
    display: flex;
    justify-content: space-between;
    color: #687583;
    font-size: 9px;
}

.section-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    color: #dbe2e9;
    font-size: 13px;
    font-weight: 600;
}

.section-caption {
    color: #626f7c;
    font-size: 9px;
}

.stat-card {
    min-height: 105px;
    padding: 16px;
    border-radius: 18px;
    background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(255,255,255,.025));
    border: 1px solid rgba(255,255,255,.075);
}

.stat-name {
    color: #7f8c99;
    font-size: 9px;
}

.stat-value {
    margin-top: 10px;
    font-size: 21px;
    font-weight: 700;
}

.stat-description {
    margin-top: 5px;
    color: #596673;
    font-size: 8px;
}

.forecast-card, .workflow-card {
    padding: 13px 15px;
    margin-bottom: 7px;
    border-radius: 16px;
    background: rgba(255,255,255,.037);
    border: 1px solid rgba(255,255,255,.06);
}

.forecast-row {
    display: grid;
    grid-template-columns: 72px 38px 1fr 45px;
    align-items: center;
}

.forecast-day {
    color: #9ba6b1;
    font-size: 10px;
}

.forecast-icon {
    font-size: 19px;
}

.forecast-temp {
    text-align: center;
    font-size: 11px;
    font-weight: 600;
}

.forecast-rain {
    text-align: right;
    color: #5f9bbd;
    font-size: 9px;
}

.workflow-row {
    display: grid;
    grid-template-columns: 48px 1fr 105px;
    gap: 12px;
    align-items: center;
}

.workflow-number {
    color: #61c7ff;
    font-size: 11px;
    font-weight: 700;
}

.workflow-name {
    font-size: 11px;
    font-weight: 600;
}

.workflow-detail {
    margin-top: 3px;
    color: #687583;
    font-size: 8px;
}

.status-ready {
    text-align: right;
    color: #65e5a1;
    font-size: 8px;
    font-weight: 700;
}

.terminal {
    padding: 18px;
    border-radius: 18px;
    background: #03070a;
    border: 1px solid rgba(255,255,255,.08);
    color: #a8e8c5;
    font-family: monospace;
    font-size: 11px;
    line-height: 1.8;
    overflow-x: auto;
}

.traffic-card {
    padding: 20px;
    border-radius: 20px;
    background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(255,255,255,.025));
    border: 1px solid rgba(255,255,255,.075);
}

.stButton > button, .stLinkButton > a {
    width: 100%;
    border-radius: 12px !important;
    background: rgba(255,255,255,.055) !important;
    border: 1px solid rgba(255,255,255,.09) !important;
    color: #d7e0e8 !important;
    font-family: "Space Grotesk", sans-serif !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

#MainMenu, footer {
    visibility: hidden;
}
</style>
"""
)


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    render_html(
        """
        <div class="side-logo">🌦️</div>
        <div class="side-brand">WEATHER AI</div>
        """
    )

    st.markdown("### Navigation")

    page = st.radio(
        "Navigation",
        [
            "Weather",
            "Map",
            "Traffic",
            "Project Workflow",
            "System",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### Weather Layers")

    precipitation_layer = st.checkbox("🌧️ Precipitation")
    clouds_layer = st.checkbox("☁️ Clouds")
    wind_layer = st.checkbox("💨 Wind")
    temperature_layer = st.checkbox("🌡️ Temperature", value=True)
    traffic_layer = st.checkbox("🚗 Traffic")

    st.markdown("---")
    st.caption("Narayanganj Smart Weather")
    st.caption("Live weather intelligence")
    st.caption("Asia / Dhaka")
    st.caption("Open-Meteo data")

    st.markdown("---")

    if st.button("↻ Refresh Weather", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ==========================================================
# GLOBAL HEADER
# ==========================================================

render_html(
    f"""
    <div class="dashboard-header">
        <div>
            <div class="dashboard-title">
                Narayanganj Weather
            </div>
            <div class="dashboard-subtitle">
                AI weather intelligence • live atmospheric conditions •
                Narayanganj, Bangladesh
            </div>
        </div>

        <div class="live-pill">
            <span class="live-dot"></span>
            LIVE • {escape(updated_time)}
        </div>
    </div>
    """
)


# ==========================================================
# WEATHER PAGE
# ==========================================================

if page == "Weather":

    weather_col, stats_col = st.columns(
        [0.82, 1.48],
        gap="medium",
    )

    with weather_col:
        render_html(
            f"""
            <div class="weather-card">
                <div class="weather-location">
                    📍 {CITY}, {COUNTRY}
                </div>

                <div class="weather-main">
                    <div class="weather-icon">{weather_icon}</div>
                    <div>
                        <div class="temperature">
                            {temperature}
                            <span class="temperature-unit">°C</span>
                        </div>
                    </div>
                </div>

                <div class="weather-condition">
                    {escape(weather_text)}
                </div>

                <div class="feels-like">
                    Feels like {feels_like}°C
                </div>

                <div class="weather-footer">
                    <span>Updated {escape(updated_time)}</span>
                    <span>Asia/Dhaka</span>
                </div>
            </div>
            """
        )

    with stats_col:
        render_html(
            """
            <div class="section-title">
                <span>Today's Highlights</span>
                <span class="section-caption">Atmospheric data</span>
            </div>
            """
        )

        row1 = st.columns(3)

        sunrise_text = "--"
        sunset_text = "--"

        try:
            sunrise_text = datetime.fromisoformat(
                daily["sunrise"][0]
            ).strftime("%I:%M %p").lstrip("0")

            sunset_text = datetime.fromisoformat(
                daily["sunset"][0]
            ).strftime("%I:%M %p").lstrip("0")
        except Exception:
            pass

        stats_1 = [
            (
                "💨 Wind Status",
                f"{wind} km/h",
                f"Direction {wind_direction}°",
            ),
            (
                "☀️ UV Index",
                f"{uv:.1f}",
                "Current UV level",
            ),
            (
                "🌅 Sunrise",
                sunrise_text,
                f"Sunset {sunset_text}",
            ),
        ]

        for column, stat in zip(row1, stats_1):
            with column:
                render_html(
                    f"""
                    <div class="stat-card">
                        <div class="stat-name">{stat[0]}</div>
                        <div class="stat-value">{stat[1]}</div>
                        <div class="stat-description">{stat[2]}</div>
                    </div>
                    """
                )

        row2 = st.columns(3)

        stats_2 = [
            ("💧 Humidity", f"{humidity}%", "Relative humidity"),
            ("👁️ Visibility", f"{visibility} km", "Atmospheric visibility"),
            ("🌧️ Precipitation", f"{rain:.1f} mm", "Current precipitation"),
        ]

        for column, stat in zip(row2, stats_2):
            with column:
                render_html(
                    f"""
                    <div class="stat-card">
                        <div class="stat-name">{stat[0]}</div>
                        <div class="stat-value">{stat[1]}</div>
                        <div class="stat-description">{stat[2]}</div>
                    </div>
                    """
                )

    forecast_col, map_col = st.columns(
        [0.82, 1.48],
        gap="medium",
    )

    with forecast_col:
        render_html(
            """
            <div class="section-title">
                <span>7 Days Forecast</span>
                <span class="section-caption">Narayanganj</span>
            </div>
            """
        )

        for i in range(min(7, len(daily.get("time", [])))):
            date = datetime.fromisoformat(daily["time"][i])

            day_name = (
                "Today"
                if i == 0
                else date.strftime("%a")
            )

            ficon, _ = weather_info(
                daily["weather_code"][i]
            )

            high = round(
                safe_number(
                    daily["temperature_2m_max"][i]
                )
            )

            low = round(
                safe_number(
                    daily["temperature_2m_min"][i]
                )
            )

            rain_probability = round(
                safe_number(
                    daily["precipitation_probability_max"][i]
                )
            )

            render_html(
                f"""
                <div class="forecast-card">
                    <div class="forecast-row">
                        <div class="forecast-day">{day_name}</div>
                        <div class="forecast-icon">{ficon}</div>
                        <div class="forecast-temp">
                            {high}° / {low}°
                        </div>
                        <div class="forecast-rain">
                            💧 {rain_probability}%
                        </div>
                    </div>
                </div>
                """
            )

    with map_col:
        render_html(
            """
            <div class="section-title">
                <span>Weather Condition Map</span>
                <span class="section-caption">OpenStreetMap • No map key required</span>
            </div>
            """
        )

        weather_map = folium.Map(
            location=[LAT, LON],
            zoom_start=11,
            tiles="OpenStreetMap",
            control_scale=True,
        )

        folium.Marker(
            [LAT, LON],
            tooltip="Narayanganj",
            popup=folium.Popup(
                f"""
                <b>Narayanganj Weather</b><br>
                Temperature: {temperature}°C<br>
                Condition: {escape(weather_text)}<br>
                Humidity: {humidity}%<br>
                Wind: {wind} km/h
                """,
                max_width=280,
            ),
            icon=folium.Icon(
                color="blue",
                icon="cloud",
                prefix="fa",
            ),
        ).add_to(weather_map)

        if temperature_layer:
            folium.Circle(
                [LAT, LON],
                radius=6000,
                color="#45b8ff",
                fill=True,
                fill_color="#45b8ff",
                fill_opacity=0.08,
                weight=1,
                popup=f"Temperature: {temperature}°C",
            ).add_to(weather_map)

        if precipitation_layer and rain > 0:
            folium.Circle(
                [LAT, LON],
                radius=3500,
                color="#4e9dff",
                fill=True,
                fill_color="#4e9dff",
                fill_opacity=0.20,
                popup=f"Precipitation: {rain:.1f} mm",
            ).add_to(weather_map)

        if wind_layer:
            folium.CircleMarker(
                [LAT, LON],
                radius=10,
                color="#63e6a3",
                fill=True,
                fill_opacity=0.30,
                popup=f"Wind: {wind} km/h",
            ).add_to(weather_map)

        if clouds_layer:
            folium.Circle(
                [LAT, LON],
                radius=8000,
                color="#9c9c9c",
                fill=True,
                fill_color="#9c9c9c",
                fill_opacity=0.06,
                popup="Cloud coverage",
            ).add_to(weather_map)

        if traffic_layer:
            add_traffic_line(weather_map)

        st_folium(
            weather_map,
            width=None,
            height=390,
            returned_objects=[],
            key="weather-map",
        )

    render_html(
        """
        <div class="section-title">
            <span>🚀 Project Workflow</span>
            <span class="section-caption">
                Linux → Localhost → GitHub → Free Cloud
            </span>
        </div>

        <div class="workflow-card">
            <div class="workflow-row">
                <div class="workflow-number">01–05</div>
                <div>
                    <div class="workflow-name">Linux + Python Environment</div>
                    <div class="workflow-detail">
                        Linux → Python → venv → pip → dependencies
                    </div>
                </div>
                <div class="status-ready">✓ READY</div>
            </div>
        </div>

        <div class="workflow-card">
            <div class="workflow-row">
                <div class="workflow-number">06–10</div>
                <div>
                    <div class="workflow-name">Weather AI Application</div>
                    <div class="workflow-detail">
                        API → UI → Map → Forecast → Localhost
                    </div>
                </div>
                <div class="status-ready">✓ READY</div>
            </div>
        </div>

        <div class="workflow-card">
            <div class="workflow-row">
                <div class="workflow-number">11–15</div>
                <div>
                    <div class="workflow-name">GitHub + Free Hosting</div>
                    <div class="workflow-detail">
                        Git → GitHub → Cloud → Secrets → Public URL
                    </div>
                </div>
                <div class="status-ready">✓ READY</div>
            </div>
        </div>
        """
    )


# ==========================================================
# MAP PAGE
# ==========================================================

elif page == "Map":

    render_html(
        """
        <div class="dashboard-title">🗺️ Narayanganj Weather Map</div>
        <div class="dashboard-subtitle">
            Interactive map • OpenStreetMap • No map API key required
        </div>
        """
    )

    st.write("")

    full_map = folium.Map(
        location=[LAT, LON],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.Marker(
        [LAT, LON],
        tooltip="Narayanganj",
        popup=(
            f"Narayanganj<br>"
            f"{temperature}°C<br>"
            f"{escape(weather_text)}"
        ),
        icon=folium.Icon(
            color="blue",
            icon="cloud",
            prefix="fa",
        ),
    ).add_to(full_map)

    folium.Circle(
        [LAT, LON],
        radius=6000,
        color="#45b8ff",
        fill=True,
        fill_color="#45b8ff",
        fill_opacity=0.08,
    ).add_to(full_map)

    if traffic_layer:
        add_traffic_line(full_map)

    st_folium(
        full_map,
        width=None,
        height=650,
        returned_objects=[],
        key="full-map",
    )


# ==========================================================
# TRAFFIC PAGE
# ==========================================================

elif page == "Traffic":

    render_html(
        """
        <div class="dashboard-title">
            🚗 Narayanganj Traffic Intelligence
        </div>
        <div class="dashboard-subtitle">
            TomTom traffic flow monitoring
        </div>
        """
    )

    st.write("")

    traffic_1, traffic_2, traffic_3 = st.columns(3)

    with traffic_1:
        value = (
            f"{traffic_speed:.0f} km/h"
            if traffic_speed is not None
            else "NOT SET"
        )

        render_html(
            f"""
            <div class="traffic-card">
                <div class="stat-name">🚦 CURRENT SPEED</div>
                <div class="stat-value">{value}</div>
                <div class="stat-description">
                    Live traffic segment speed
                </div>
            </div>
            """
        )

    with traffic_2:
        render_html(
            f"""
            <div class="traffic-card">
                <div class="stat-name">🚥 TRAFFIC STATUS</div>
                <div class="stat-value">{traffic_status}</div>
                <div class="stat-description">
                    Traffic intelligence status
                </div>
            </div>
            """
        )

    with traffic_3:
        value = (
            f"{traffic_free_speed:.0f} km/h"
            if traffic_free_speed is not None
            else "NOT SET"
        )

        render_html(
            f"""
            <div class="traffic-card">
                <div class="stat-name">🛣️ FREE FLOW SPEED</div>
                <div class="stat-value">{value}</div>
                <div class="stat-description">
                    Reference road speed
                </div>
            </div>
            """
        )

    st.write("")

    if not TOMTOM_API_KEY:
        st.warning(
            "Live Traffic চালু করতে .streamlit/secrets.toml-এ "
            "TOMTOM_API_KEY দিতে হবে।"
        )
    elif traffic_error:
        st.error(
            "TomTom Traffic API থেকে data পাওয়া যায়নি।"
        )
        st.caption(traffic_error)

    traffic_map = folium.Map(
        location=[LAT, LON],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.Marker(
        [LAT, LON],
        tooltip="Narayanganj Traffic",
        popup=f"Traffic: {traffic_status}",
        icon=folium.Icon(
            color="red",
            icon="car",
            prefix="fa",
        ),
    ).add_to(traffic_map)

    add_traffic_line(traffic_map)

    st_folium(
        traffic_map,
        width=None,
        height=560,
        returned_objects=[],
        key="traffic-map",
    )


# ==========================================================
# PROJECT WORKFLOW
# ==========================================================

elif page == "Project Workflow":

    render_html(
        """
        <div class="dashboard-title">🚀 Project Build Workflow</div>
        <div class="dashboard-subtitle">
            Linux থেকে শুরু করে Free Hosting পর্যন্ত পুরো project lifecycle
        </div>
        """
    )

    st.write("")

    workflow = [
        ("01", "Linux Setup", "Linux environment ready", "✓ READY"),
        ("02", "Python Setup", "Python 3 + pip installed", "✓ READY"),
        ("03", "Virtual Environment", "python3 -m venv venv", "✓ READY"),
        ("04", "Project Folder", "narayanganj-smart-city", "✓ READY"),
        ("05", "Dependencies", "Streamlit + Requests + Folium", "✓ READY"),
        ("06", "Weather API", "Open-Meteo integration", "✓ READY"),
        ("07", "Weather Engine", "Current weather + forecast", "✓ READY"),
        ("08", "Modern AI UI", "Glassmorphism + Space Grotesk", "✓ READY"),
        ("09", "Interactive Map", "OpenStreetMap + Folium", "✓ READY"),
        ("10", "Localhost", "streamlit run app.py", "✓ READY"),
        ("11", "Git Repository", "git init + commit", "✓ READY"),
        ("12", "GitHub", "Push project to GitHub", "✓ READY"),
        ("13", "Free Hosting", "Streamlit Community Cloud", "✓ READY"),
        ("14", "Cloud Secrets", "TOMTOM_API_KEY if required", "✓ READY"),
        ("15", "Public URL", "Your app.streamlit.app", "✓ READY"),
    ]

    for number, name, detail, status in workflow:
        render_html(
            f"""
            <div class="workflow-card">
                <div class="workflow-row">
                    <div class="workflow-number">{number}</div>
                    <div>
                        <div class="workflow-name">{name}</div>
                        <div class="workflow-detail">{detail}</div>
                    </div>
                    <div class="status-ready">{status}</div>
                </div>
            </div>
            """
        )

    st.write("")

    render_html(
        """
        <div class="section-title">
            <span>💻 LINUX SETUP</span>
            <span class="section-caption">Terminal</span>
        </div>

        <div class="terminal">
$ sudo apt update<br>
$ sudo apt install -y python3 python3-pip python3-venv git<br><br>
$ cd ~/narayanganj-smart-city<br><br>
$ python3 -m venv venv<br>
$ source venv/bin/activate<br><br>
$ python -m pip install --upgrade pip<br>
$ pip install -r requirements.txt<br><br>
$ streamlit run app.py
        </div>
        """
    )

    st.write("")

    render_html(
        """
        <div class="section-title">
            <span>📁 PROJECT STRUCTURE</span>
            <span class="section-caption">GitHub ready</span>
        </div>

        <div class="terminal">
narayanganj-smart-city/<br>
├── app.py<br>
├── requirements.txt<br>
├── .gitignore<br>
├── README.md<br>
├── venv/<br>
└── .streamlit/<br>
&nbsp;&nbsp;&nbsp;&nbsp;└── secrets.toml
        </div>
        """
    )

    st.write("")

    render_html(
        """
        <div class="section-title">
            <span>🔐 TOMTOM SECRET</span>
            <span class="section-caption">Never commit this file</span>
        </div>

        <div class="terminal">
.streamlit/secrets.toml<br><br>
TOMTOM_API_KEY = "YOUR_NEW_ROTATED_KEY"
        </div>
        """
    )

    st.write("")

    render_html(
        """
        <div class="section-title">
            <span>🐙 GIT + GITHUB</span>
        </div>

        <div class="terminal">
$ git init<br>
$ git add .<br>
$ git commit -m "Narayanganj Weather AI"<br>
$ git branch -M main<br>
$ git remote add origin https://github.com/YOUR_USERNAME/narayanganj-smart-city.git<br>
$ git push -u origin main
        </div>
        """
    )

    st.write("")

    render_html(
        """
        <div class="section-title">
            <span>☁️ FREE HOSTING</span>
            <span class="section-caption">Streamlit Community Cloud</span>
        </div>
        """
    )

    st.link_button(
        "🚀 Open Streamlit Community Cloud",
        "https://share.streamlit.io/",
        use_container_width=True,
    )

    render_html(
        """
        <div class="workflow-card">
            <div class="workflow-name">1. GitHub Repository</div>
            <div class="workflow-detail">
                GitHub repository connect করুন
            </div>
        </div>

        <div class="workflow-card">
            <div class="workflow-name">2. Create App</div>
            <div class="workflow-detail">
                Repository → main → app.py
            </div>
        </div>

        <div class="workflow-card">
            <div class="workflow-name">3. Python Version</div>
            <div class="workflow-detail">
                Python 3.12 ব্যবহার করুন
            </div>
        </div>

        <div class="workflow-card">
            <div class="workflow-name">4. Secrets</div>
            <div class="workflow-detail">
                Cloud Secrets-এ TOMTOM_API_KEY দিন
            </div>
        </div>

        <div class="workflow-card">
            <div class="workflow-name">5. Deploy</div>
            <div class="workflow-detail">
                Deploy করার পরে public Streamlit URL পাবেন
            </div>
        </div>
        """
    )

    st.write("")

    render_html(
        """
        <div class="section-title">
            <span>✅ COMPLETE PROJECT FLOW</span>
        </div>

        <div class="terminal">
Linux<br>
↓<br>
Python<br>
↓<br>
Virtual Environment<br>
↓<br>
requirements.txt<br>
↓<br>
app.py<br>
↓<br>
Open-Meteo API<br>
↓<br>
TomTom Traffic API<br>
↓<br>
Modern AI UI<br>
↓<br>
OpenStreetMap<br>
↓<br>
Streamlit Localhost<br>
↓<br>
Git → GitHub<br>
↓<br>
Streamlit Community Cloud<br>
↓<br>
Cloud Secrets<br>
↓<br>
✓ PROJECT READY
        </div>
        """
    )


# ==========================================================
# SYSTEM
# ==========================================================

elif page == "System":

    render_html(
        """
        <div class="dashboard-title">⚙️ System Status</div>
        <div class="dashboard-subtitle">Project components</div>
        """
    )

    st.write("")

    traffic_system_status = (
        "Connected"
        if traffic_data
        else ("Configured" if TOMTOM_API_KEY else "Optional")
    )

    system = [
        ("✓", "Python", "Running"),
        ("✓", "Streamlit", "Running"),
        ("✓", "Open-Meteo API", "Connected"),
        ("✓", "Weather Engine", "Connected"),
        ("✓", "Narayanganj Map", "Ready"),
        ("✓", "OpenStreetMap", "Connected"),
        ("✓", "7-Day Forecast", "Ready"),
        ("✓", "Glass UI", "Enabled"),
        ("✓", "AI Font", "Space Grotesk"),
        ("✓", "Project Workflow", "Enabled"),
        ("✓", "Traffic API", traffic_system_status),
        ("✓", "GitHub", "Ready"),
        ("✓", "Free Cloud", "Ready"),
        ("✓", "Public URL", "Ready"),
    ]

    for icon, name, status in system:
        render_html(
            f"""
            <div class="forecast-card">
                <div class="forecast-row">
                    <div class="forecast-day">{icon}</div>
                    <div>{name}</div>
                    <div class="forecast-temp">{status}</div>
                    <div class="forecast-rain">•</div>
                </div>
            </div>
            """
        )


# ==========================================================
# FOOTER
# ==========================================================

render_html(
    """
    <div style="
        text-align:center;
        padding:25px 0 5px 0;
        color:#4e5b68;
        font-size:9px;
    ">
        Narayanganj Weather AI
        • Live Weather Intelligence
        • Bangladesh
        • OpenStreetMap
        • ✓ READY
    </div>
    """
)
