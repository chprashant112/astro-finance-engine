import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import swisseph as swe
import pandas as pd
import datetime

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Astro-Finance Correlation", layout="wide")

col1, col2 = st.columns([3, 1])
with col1:
    st.title("🪐 Astro-Finance Engine: Nifty 50 vs Navagrahas")
    st.markdown("Use the **vertical crosshair** to map exact dates. Use the **Box/Lasso tool** to select dates for your report.")

# --- VEDIC ASTROLOGY MATHEMATICAL CONSTANTS ---
RASHIS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 
    'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]

NAKSHATRA_LORDS = [
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury'
]

PLANET_MAP = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
    'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER, 'Venus': swe.VENUS,
    'Saturn': swe.SATURN, 'Rahu': swe.TRUE_NODE 
}

PLANET_COLORS = {
    'Sun': '#FFD700', 'Moon': '#00FFFF', 'Mars': '#FF4500', # Moon changed to Cyan for visibility
    'Mercury': '#32CD32', 'Jupiter': '#FFA500', 'Venus': '#FF69B4', 
    'Saturn': '#8A2BE2', 'Rahu': '#A52A2A', 'Ketu': '#808080'
}

# --- SIDEBAR (LEFT PANEL) ---
st.sidebar.header("⚙️ Dashboard Controls")

st.sidebar.subheader("1. Chart & Timeframe Settings")
timeframe = st.sidebar.radio("Select Interval:", options=['1h (Hourly)', '1d (Daily)', '1wk (Weekly)'], index=1)
yf_interval_map = {'1h (Hourly)': '1h', '1d (Daily)': '1d', '1wk (Weekly)': '1wk'}
interval = yf_interval_map[timeframe]

start_date = st.sidebar.date_input("Start Date", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())

st.sidebar.subheader("2. Astrological Metrics")
y_axis_metric = st.sidebar.selectbox(
    "Select Y-Axis Scale:",
    options=['Padas (1-108)', 'Degrees (0-360°)', 'Nakshatras (1-27)', 'Zodiac Signs (1-12)']
)

plot_style = st.sidebar.radio(
    "Planetary Plot Style:",
    options=['Stepped Line (Best for boundaries)', 'Smooth Line', 'Dots Only'],
    index=0
)

st.sidebar.subheader("3. Filter Planets")
selected_planets = st.sidebar.multiselect(
    "Visible Navagrahas:",
    options=['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'],
    default=['Saturn', 'Jupiter', 'Rahu'] 
)

# --- DATA PROCESSING & ASTRONOMICAL CALCULATIONS ---
@st.cache_data(ttl=3600)
def get_nifty_data(start, end, invl):
    df = yf.download("^NSEI", start=start, end=end, interval=invl, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.index.tz is not None:
        df.index = df.index.tz_convert('UTC').tz_localize(None)
    return df

def append_planet_data(df, planets_to_calc):
    data = df.copy()
    for planet in planets_to_calc:
        if planet == 'Ketu': continue
        planet_id = PLANET_MAP[planet]
        degrees, padas, nakshatras, signs = [], [], [], []
        
        for dt in data.index:
            hour_fraction = dt.hour + (dt.minute / 60.0)
            jd = swe.julday(dt.year, dt.month, dt.day, hour_fraction)
            pos, _ = swe.calc_ut(jd, planet_id)
            deg = pos[0]
            
            degrees.append(deg)
            padas.append(int(deg / (360/108)) + 1)
            nakshatras.append(int(deg / (360/27)) + 1)
            signs.append(int(deg / 30) + 1)
            
        data[f'{planet}_Degree'] = degrees
        data[f'{planet}_Pada'] = padas
        data[f'{planet}_Nakshatra'] = nakshatras
        data[f'{planet}_Sign'] = signs
        
    if 'Ketu' in planets_to_calc:
        if 'Rahu' not in planets_to_calc:
            rahu_degs = []
            for dt in data.index:
                jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + (dt.minute/60.0))
                pos, _ = swe.calc_ut(jd, PLANET_MAP['Rahu'])
                rahu_degs.append(pos[0])
            data['Rahu_Degree_Temp'] = rahu_degs
            ketu_deg = (data['Rahu_Degree_Temp'] + 180) % 360
            data.drop(columns=['Rahu_Degree_Temp'], inplace=True)
        else:
            ketu_deg = (data['Rahu_Degree'] + 180) % 360
            
        data['Ketu_Degree'] = ketu_deg
        data['Ketu_Pada'] = ketu_deg.apply(lambda x: int(x / (360/108)) + 1)
        data['Ketu_Nakshatra'] = ketu_deg.apply(lambda x: int(x / (360/27)) + 1)
        data['Ketu_Sign'] = ketu_deg.apply(lambda x: int(x / 30) + 1)
        
    return data

def get_astrological_info(absolute_pada):
    pada_idx = int(absolute_pada) - 1 
    nakshatra_idx = pada_idx // 4
    pada_num = (pada_idx % 4) + 1
    d1_idx = pada_idx // 9       
    d9_idx = pada_idx % 12       
    
    return {
        'Absolute_Pada': absolute_pada,
        'Nakshatra': NAKSHATRAS[nakshatra_idx],
        'Pada (1 to 4)': pada_num,
        'D1_Rashi (Sign)': RASHIS[d1_idx],
        'D9_Navamsa': RASHIS[d9_idx],
        'Nakshatra_Lord': NAKSHATRA_LORDS[nakshatra_idx % 9]
    }

def generate_report(selected_dates, final_df, active_planets):
    report_rows = []
    for date_str in selected_dates:
        dt = pd.to_datetime(date_str)
        if dt in final_df.index:
            row_data = final_df.loc[dt]
            nifty_price = row_data['Close']
            
            for planet in active_planets:
                pada_col = f"{planet}_Pada"
                if pada_col in row_data:
                    abs_pada = int(row_data[pada_col])
                    astro_data = get_astrological_info(abs_pada)
                    
                    report_rows.append({
                        'Date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'Nifty_Close': round(float(nifty_price), 2),
                        'Planet': planet,
                        'Degree': round(float(row_data[f"{planet}_Degree"]), 2),
                        **astro_data
                    })
    return pd.DataFrame(report_rows)

# --- CHART RENDERING & INTERACTIVE SELECTION ---
if start_date >= end_date:
    st.error("Error: End date must fall after start date.")
else:
    with st.spinner("Crunching Astronomical & Financial Data..."):
        nifty_df = get_nifty_data(start_date, end_date, interval)
        
        if not nifty_df.empty and len(selected_planets) > 0:
            final_df = append_planet_data(nifty_df, selected_planets)
            
            # --- MAPPING UI SELECTION TO DATAFRAME COLUMNS ---
            metric_col_map = {
                'Padas (1-108)': '_Pada',
                'Degrees (0-360°)': '_Degree',
                'Nakshatras (1-27)': '_Nakshatra',
                'Zodiac Signs (1-12)': '_Sign'
            }
            y_col_suffix = metric_col_map[y_axis_metric]
            
            # 1. Build the Plotly Chart
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.65, 0.35] 
            )

            fig.add_trace(go.Candlestick(
                x=final_df.index, open=final_df['Open'], high=final_df['High'],
                low=final_df['Low'], close=final_df['Close'], name="Nifty 50"
            ), row=1, col=1)

            # Determine Plot Style
            if plot_style == 'Stepped Line (Best for boundaries)':
                plot_mode = 'lines'
                line_shape = 'hv' # Horizontal then vertical steps
            elif plot_style == 'Smooth Line':
                plot_mode = 'lines+markers'
                line_shape = 'linear'
            else:
                plot_mode = 'markers'
                line_shape = 'linear'

            for planet in selected_planets:
                # Bundle all data for the universal hover tooltip
                custom_data = final_df[[
                    f'{planet}_Degree', f'{planet}_Nakshatra', f'{planet}_Sign', f'{planet}_Pada'
                ]].values

                fig.add_trace(go.Scatter(
                    x=final_df.index, y=final_df[f'{planet}{y_col_suffix}'],
                    mode=plot_mode, name=planet,
                    line_shape=line_shape,
                    customdata=custom_data,
                    hovertemplate=(
                        f"<b>{planet}</b><br>"
                        "Degree: %{customdata[0]:.2f}°<br>"
                        "Nakshatra: %{customdata[1]}<br>"
                        "Sign: %{customdata[2]}<br>"
                        "Pada: %{customdata[3]}<extra></extra>"
                    ),
                    marker=dict(color=PLANET_COLORS[planet], size=5),
                    line=dict(color=PLANET_COLORS[planet], width=2),
                    opacity=0.85
                ), row=2, col=1)

            # Chart Layout Config
            fig.update_layout(
                height=850, template='plotly_dark', hovermode='x unified', 
                xaxis_rangeslider_visible=False, margin=dict(l=50, r=50, t=30, b=50),
                dragmode='zoom' 
            )
            
            # Make X-axis dynamically adjust its intervals when zoomed
            fig.update_xaxes(
                showspikes=True, spikemode='across', spikesnap='cursor',
                showline=True, showgrid=True, spikecolor="rgba(255, 255, 255, 0.6)", 
                spikethickness=2, spikedash='dash',
                tickmode='auto', nticks=15, # Forces granular ticks upon zooming
                rangeslider=dict(visible=True), row=2, col=1 
            )
            
            fig.update_yaxes(title_text="Nifty 50 Price", showgrid=True, tickmode='auto', row=1, col=1)
            
            # Set dynamic Y-axis range based on selected metric
            if y_axis_metric == 'Degrees (0-360°)': y_range = [0, 360]
            elif y_axis_metric == 'Nakshatras (1-27)': y_range = [0, 28]
            elif y_axis_metric == 'Zodiac Signs (1-12)': y_range = [0, 13]
            else: y_range = [0, 109]
            
            fig.update_yaxes(title_text=y_axis_metric, range=y_range, showgrid=True, tickmode='auto', nticks=15, row=2, col=1)

            # 2. Render Chart
            chart_selection = st.plotly_chart(
                fig, 
                use_container_width=True, 
                on_select="rerun", 
                selection_mode=('points', 'box', 'lasso')
            )

            # 3. Process the Selected Dates for the Report
            selected_dates_from_chart = []
            if chart_selection and "selection" in chart_selection:
                points = chart_selection["selection"].get("points", [])
                for p in points:
                    x_val = p.get("x")
                    if x_val and x_val not in selected_dates_from_chart:
                        selected_dates_from_chart.append(x_val)
            
            # 4. Update Sidebar dynamically based on selection
            st.sidebar.markdown("---")
            st.sidebar.subheader("4. 📥 Generate Detail Report")
            
            if len(selected_dates_from_chart) > 0:
                st.sidebar.success(f"✅ {len(selected_dates_from_chart)} points selected!")
                report_df = generate_report(selected_dates_from_chart, final_df, selected_planets)
                st.sidebar.dataframe(report_df.head(3)) 
                
                csv_data = report_df.to_csv(index=False).encode('utf-8')
                st.sidebar.download_button(
                    label="⬇️ Download Selected Data (CSV)",
                    data=csv_data, file_name="Astro_Analysis_Custom.csv", mime="text/csv"
                )
            else:
                st.sidebar.info("Awaiting selection... Use the Box Select tool on the chart.")
                
        elif nifty_df.empty:
            st.warning("No data found for the selected dates.")
        else:
            st.info("Select at least one planet to begin.")