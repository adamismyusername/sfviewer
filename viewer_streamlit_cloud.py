"""
SurStitch for Salesforce - Streamlit Cloud Viewer
Based on ui_template.html design
Created: Sept 4, 2025

This viewer is designed to work both locally and on Streamlit Cloud
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
import random
import json

# Page config - MUST BE FIRST
st.set_page_config(
    page_title="SurStitch for Salesforce",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS that matches the HTML template
st.markdown("""
<style>
    /* Salesforce Theme Variables */
    :root {
        --sf-blue: #0176D3;
        --sf-indigo: #1B5297;
        --band-1: #E8F3FF;
        --band-1-ring: #BFD9F5;
        --band-2: #F6FAFF;
        --band-2-ring: #DFEAF8;
        --card-bd-1: #D6E7FB;
        --card-bd-2: #E6EEF9;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Remove extra padding at the top of the page */
    .block-container {
        padding-top: 0.5rem !important;
        max-width: 100%;
    }
    
    /* Reduce gap between elements */
    .stApp > div > div {
        padding-top: 0rem;
    }
    
    /* Remove the custom header styles since we're not using it */

    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 16px;
        border: 1px solid #D6E7FB;
        box-shadow: 0 1px 2px rgba(0,0,0,.06);
        padding: 12px;
        height: 100%;
    }

    .kpi-card.secondary {
        border-color: #E6EEF9;
    }

    .kpi-label {
        font-size: 11px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #1B5297;
        opacity: 0.9;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 42px;
        font-weight: 900;
        color: #0176D3;
        line-height: 1;
    }

    .kpi-value.secondary {
        font-size: 32px;
        color: #1B5297;
        font-weight: 800;
    }

    /* KPI Bands */
    .band-main {
        background: #E8F3FF;
        border: 1px solid #BFD9F5;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
    }

    .band-secondary {
        background: #F6FAFF;
        border: 1px solid #DFEAF8;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
    }

    /* Delta Chips */
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border-radius: 8px;
        padding: 4px 8px;
        font-weight: 700;
        font-size: 10px;
        margin-right: 8px;
    }

    .chip.up {
        border: 1px solid #a7f3d0;
        color: #047857;
        background: #ecfdf5;
    }

    .chip.down {
        border: 1px solid #fecaca;
        color: #b91c1c;
        background: #fef2f2;
    }

    .chip.neutral {
        border: 1px solid #e5e7eb;
        color: #374151;
        background: #f3f4f6;
    }

    /* Filters */
    .stSelectbox > div > div {
        border-radius: 12px !important;
        border-color: #e5e7eb !important;
    }

    /* Data Table Card */
    .table-card {
        background: white;
        border-radius: 20px;
        border: 1px solid #D6E7FB;
        box-shadow: 0 4px 12px rgba(0,0,0,.08);
        padding: 24px;
    }

    /* Streamlit specific adjustments */
    .stButton > button {
        border-radius: 12px;
        padding: 8px 12px;
        font-weight: 600;
    }

    /* Toggle buttons */
    .toggle-button {
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 14px;
    }

    /* Hide default Streamlit padding on some elements */
    .element-container {
        margin: 0 !important;
    }

    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'show_sparklines' not in st.session_state:
    st.session_state.show_sparklines = False
if 'show_deltas' not in st.session_state:
    st.session_state.show_deltas = False
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = None
if 'column_labels' not in st.session_state:
    st.session_state.column_labels = {}

def find_output_files():
    """Find all person_master CSV files in Output-Files directory"""
    # Try different paths for local development
    possible_paths = [
        Path("Output-Files"),  # If running from main SurStitch directory
        Path("../../Output-Files"),  # If running from UI/STREAMLIT
        Path("D:/08 - APPS & DEVELOPMENT/salesforce-data-anlayzer/SurStitch/Output-Files"),  # Absolute path
    ]
    
    for base_path in possible_paths:
        if base_path.exists():
            csv_files = list(base_path.glob("person_master_*.csv"))
            if csv_files:
                return sorted(csv_files, reverse=True)
    return []

def load_data(file_path=None, uploaded_file=None):
    """Load data from file path or uploaded file"""
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif file_path:
            df = pd.read_csv(file_path)
        else:
            return None
            
        # Ensure required columns exist
        required_cols = ['Person_UUID', 'Lead_Status', 'Lead_Source']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 'Unknown'
                
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def calculate_metrics(df):
    """Calculate all KPI metrics from dataframe"""
    if df is None or df.empty:
        return {
            'lead_count': 0,
            'l2qr_count': 0,
            'converted_count': 0,
            'lead_to_convert_pct': 0,
            'lead_to_l2qr_pct': 0,
            'l2qr_to_convert_pct': 0,
            'median_speed_to_lead': '00:00',
            'activity_count_avg': 0
        }
    
    metrics = {}
    
    # Main metrics
    metrics['lead_count'] = len(df)
    
    # Check for L2QR column
    if 'Has_L2QR' in df.columns:
        metrics['l2qr_count'] = df['Has_L2QR'].astype(str).str.lower().isin(['true', 'yes', '1']).sum()
    else:
        metrics['l2qr_count'] = 0
    
    # Check for conversion column
    if 'Is_Converted_Bool' in df.columns:
        metrics['converted_count'] = df['Is_Converted_Bool'].astype(str).str.lower().isin(['true', 'yes', '1']).sum()
    else:
        metrics['converted_count'] = 0
    
    # Calculate percentages
    if metrics['lead_count'] > 0:
        metrics['lead_to_convert_pct'] = (metrics['converted_count'] / metrics['lead_count']) * 100
        metrics['lead_to_l2qr_pct'] = (metrics['l2qr_count'] / metrics['lead_count']) * 100
    else:
        metrics['lead_to_convert_pct'] = 0
        metrics['lead_to_l2qr_pct'] = 0
    
    if metrics['l2qr_count'] > 0:
        metrics['l2qr_to_convert_pct'] = (metrics['converted_count'] / metrics['l2qr_count']) * 100
    else:
        metrics['l2qr_to_convert_pct'] = 0
    
    # Calculate median speed to lead
    if 'Speed_to_Lead' in df.columns:
        # Parse time format (HH:MM or similar)
        try:
            speed_values = df['Speed_to_Lead'].dropna()
            if not speed_values.empty:
                # Get median value
                median_val = speed_values.iloc[len(speed_values)//2]
                metrics['median_speed_to_lead'] = str(median_val)[:5]  # Keep HH:MM format
            else:
                metrics['median_speed_to_lead'] = '00:00'
        except:
            metrics['median_speed_to_lead'] = '00:00'
    else:
        metrics['median_speed_to_lead'] = '00:00'
    
    # Activity count
    if 'Activity_Count' in df.columns:
        metrics['activity_count_avg'] = df['Activity_Count'].mean()
    else:
        metrics['activity_count_avg'] = 0
    
    return metrics

def generate_sparkline_data(base_value, num_points=8):
    """Generate fake sparkline data for demo purposes"""
    points = [base_value * random.uniform(0.8, 1.2) for _ in range(num_points)]
    return points

def generate_delta(current, trend='up'):
    """Generate fake delta values for demo purposes"""
    if trend == 'up':
        dod = random.uniform(0.1, 2.0)
        wow = random.uniform(1.0, 8.0)
        mom = random.uniform(5.0, 20.0)
    elif trend == 'down':
        dod = -random.uniform(0.1, 2.0)
        wow = -random.uniform(1.0, 8.0)
        mom = -random.uniform(5.0, 20.0)
    else:
        dod = 0
        wow = random.uniform(-2.0, 2.0)
        mom = random.uniform(-5.0, 5.0)
    
    return {
        'dod': dod,
        'wow': wow,
        'mom': mom
    }

# SIDEBAR CONFIGURATION
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # File Management Section
    st.markdown("#### 📁 Data Source")
    
    # Load data early so we can check if we have data
    output_files = find_output_files()
    if output_files:
        selected_path = output_files[0]  # Default to most recent file
    else:
        selected_path = None
    
    # Try to load data from uploaded file or local file
    df = None  # Initialize df
    if 'uploaded_file' in st.session_state and st.session_state.uploaded_file:
        df = load_data(uploaded_file=st.session_state.uploaded_file)
    elif selected_path:
        df = load_data(file_path=selected_path)
    
    # File selector for local files
    if output_files:
        file_options = {f.name: f for f in output_files}
        selected_file = st.selectbox(
            "Select Local File",
            options=list(file_options.keys()),
            index=0 if file_options else None
        )
        selected_path = file_options.get(selected_file)
        # Load the selected file if it's different from what's already loaded
        if selected_path and (df is None or not st.session_state.uploaded_file):
            df = load_data(file_path=selected_path)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Or Upload CSV",
        type=['csv'],
        key="csv_uploader"
    )
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        # Load the uploaded file immediately
        df = load_data(uploaded_file=uploaded_file)
    
    st.divider()
    
    # KPI Options Section
    st.markdown("#### 📊 Display Options")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "📈 Sparklines" + (" ✓" if st.session_state.show_sparklines else ""),
            key="toggle_sparklines",
            type="primary" if st.session_state.show_sparklines else "secondary",
            use_container_width=True
        ):
            st.session_state.show_sparklines = not st.session_state.show_sparklines
    
    with col2:
        if st.button(
            "% Deltas" + (" ✓" if st.session_state.show_deltas else ""),
            key="toggle_deltas",
            type="primary" if st.session_state.show_deltas else "secondary",
            use_container_width=True
        ):
            st.session_state.show_deltas = not st.session_state.show_deltas
    
    st.divider()
    
    # Column Configuration Section
    if df is not None and not df.empty:
        st.markdown("#### 📊 Table Columns")
        
        # Initialize selected columns if not set
        if st.session_state.selected_columns is None:
            # Default columns to show
            default_cols = [
                'Lead_FirstName', 'Lead_LastName', 'Lead_Name', 'Lead_Status', 
                'Lead_Source', 'Lead_Owner_Name', 'Lead_CreatedDate', 
                'Activity_Count', 'Speed_to_Lead', 'Has_L2QR', 'Is_Converted_Bool'
            ]
            # Only include defaults that exist in the dataframe
            st.session_state.selected_columns = [col for col in default_cols if col in df.columns]
            
            # If no default columns found, take first 10 columns
            if not st.session_state.selected_columns:
                st.session_state.selected_columns = list(df.columns[:10])
        
        # Multi-select for columns
        selected_columns = st.multiselect(
            "Select columns to display",
            options=list(df.columns),
            default=st.session_state.selected_columns,
            key="column_selector"
        )
        st.session_state.selected_columns = selected_columns
        
        # Quick actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", type="secondary", use_container_width=True):
                st.session_state.selected_columns = list(df.columns)
                st.rerun()
        with col2:
            if st.button("Clear All", type="secondary", use_container_width=True):
                st.session_state.selected_columns = []
                st.rerun()
        
        # Column renaming in expander
        with st.expander("Rename Columns", expanded=False):
            if selected_columns:
                st.markdown("**Custom column labels:**")
                
                # Create input fields for each selected column
                for col in selected_columns:
                    # Get existing label or use original column name
                    current_label = st.session_state.column_labels.get(col, col)
                    new_label = st.text_input(
                        col,
                        value=current_label,
                        key=f"rename_{col}"
                    )
                    st.session_state.column_labels[col] = new_label
                
                if st.button("Reset Labels", type="secondary", use_container_width=True):
                    st.session_state.column_labels = {}
                    st.rerun()

# MAIN AREA
st.markdown("### SurStitch for Salesforce")

# Show alert only if no data is loaded from any source
if df is None or (isinstance(df, pd.DataFrame) and df.empty):
    if not output_files and not st.session_state.uploaded_file:
        st.info("No data loaded. Please upload a CSV file in the sidebar.")

# Refresh button in main area (smaller, top-right position)
col1, col2, col3 = st.columns([8, 1, 1])
with col3:
    if st.button("🔄", help="Refresh data"):
        st.rerun()

# Data is already loaded above, no need to reload unless explicitly refreshed

# Calculate metrics
metrics = calculate_metrics(df)

# Main KPIs - More compact layout
st.markdown("#### Lead Metrics")
col1, col2, col3 = st.columns(3)

with col1:
    # Put all HTML in one block to keep it contained
    card_html = f"""
    <div style="background: white; border-radius: 16px; border: 1px solid #D6E7FB; box-shadow: 0 1px 2px rgba(0,0,0,.06); padding: 12px; height: 100%;">
        <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">LEAD COUNT</div>
        <div style="font-size: 42px; font-weight: 900; color: #0176D3; line-height: 1;">{metrics["lead_count"]:,}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    if st.session_state.show_sparklines:
        # In a real app, you'd calculate actual historical data
        sparkline_data = generate_sparkline_data(metrics['lead_count'])
        st.line_chart(pd.DataFrame(sparkline_data), height=50, use_container_width=True)
    
    if st.session_state.show_deltas:
        deltas = generate_delta(metrics['lead_count'], 'up')
        delta_html = f"""
        <div style="margin-top: 8px;">
            <span class="chip up">DoD ▲ +{deltas['dod']:.1f}%</span>
            <span class="chip up">WoW ▲ +{deltas['wow']:.1f}%</span>
            <span class="chip up">MoM ▲ +{deltas['mom']:.1f}%</span>
        </div>
        """
        st.markdown(delta_html, unsafe_allow_html=True)

with col2:
    card_html = f"""
    <div style="background: white; border-radius: 16px; border: 1px solid #D6E7FB; box-shadow: 0 1px 2px rgba(0,0,0,.06); padding: 12px; height: 100%;">
        <div style="display: flex; justify-content: space-between; gap: 12px;">
            <div style="flex: 1;">
                <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">L2QR COUNT</div>
                <div style="font-size: 42px; font-weight: 900; color: #0176D3; line-height: 1;">{metrics["l2qr_count"]:,}</div>
            </div>
            <div style="flex: 1; text-align: right;">
                <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">LEAD → L2QR</div>
                <div style="font-size: 28px; font-weight: 800; color: #1B5297; line-height: 1;">{metrics["lead_to_l2qr_pct"]:.1f}%</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    if st.session_state.show_sparklines:
        sparkline_data = generate_sparkline_data(metrics['l2qr_count'])
        st.line_chart(pd.DataFrame(sparkline_data), height=50, use_container_width=True)
    
    if st.session_state.show_deltas:
        deltas = generate_delta(metrics['l2qr_count'], 'up')
        delta_html = f"""
        <div style="margin-top: 8px;">
            <span class="chip up">DoD ▲ +{deltas['dod']:.1f}%</span>
            <span class="chip up">WoW ▲ +{deltas['wow']:.1f}%</span>
            <span class="chip up">MoM ▲ +{deltas['mom']:.1f}%</span>
        </div>
        """
        st.markdown(delta_html, unsafe_allow_html=True)

with col3:
    card_html = f"""
    <div style="background: white; border-radius: 16px; border: 1px solid #D6E7FB; box-shadow: 0 1px 2px rgba(0,0,0,.06); padding: 12px; height: 100%;">
        <div style="display: flex; justify-content: space-between; gap: 10px;">
            <div style="flex: 1;">
                <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">ACCOUNTS</div>
                <div style="font-size: 42px; font-weight: 900; color: #0176D3; line-height: 1;">{metrics["converted_count"]:,}</div>
            </div>
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">LEAD → ACCOUNT</div>
                <div style="font-size: 28px; font-weight: 800; color: #1B5297; line-height: 1;">{metrics["lead_to_convert_pct"]:.2f}%</div>
            </div>
            <div style="flex: 1; text-align: right;">
                <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">L2QR → ACCOUNT</div>
                <div style="font-size: 28px; font-weight: 800; color: #1B5297; line-height: 1;">{metrics["l2qr_to_convert_pct"]:.2f}%</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    if st.session_state.show_sparklines:
        sparkline_data = generate_sparkline_data(metrics['converted_count'])
        st.line_chart(pd.DataFrame(sparkline_data), height=50, use_container_width=True)
    
    if st.session_state.show_deltas:
        deltas = generate_delta(metrics['converted_count'], 'up')
        delta_html = f"""
        <div style="margin-top: 8px;">
            <span class="chip up">DoD ▲ +{deltas['dod']:.1f}%</span>
            <span class="chip up">WoW ▲ +{deltas['wow']:.1f}%</span>
            <span class="chip up">MoM ▲ +{deltas['mom']:.1f}%</span>
        </div>
        """
        st.markdown(delta_html, unsafe_allow_html=True)


# Secondary KPIs - More compact
st.markdown("#### Calling Metrics")
col1 = st.columns(1)[0]

with col1:
    card_html = f"""
    <div style="background: white; border-radius: 16px; border: 1px solid #E6EEF9; box-shadow: 0 1px 2px rgba(0,0,0,.06); padding: 12px; height: 100%; max-width: 350px;">
        <div style="font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: #1B5297; opacity: 0.9; margin-bottom: 6px;">MEDIAN SPEED TO LEAD</div>
        <div style="font-size: 32px; font-weight: 800; color: #1B5297; line-height: 1;">{metrics["median_speed_to_lead"]}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    if st.session_state.show_sparklines:
        # For time-based metrics, show as minutes
        sparkline_data = generate_sparkline_data(1, num_points=8)  # Using 1 minute as base
        # Create a narrower chart container
        with st.container():
            col_chart, col_empty = st.columns([1, 2])
            with col_chart:
                st.line_chart(pd.DataFrame(sparkline_data), height=50, use_container_width=True)
    
    if st.session_state.show_deltas:
        deltas = generate_delta(1, 'neutral')
        delta_html = f"""
        <div style="margin-top: 8px; max-width: 400px;">
            <span class="chip neutral">DoD ■ {deltas['dod']:.1f}%</span>
            <span class="chip {"down" if deltas['wow'] < 0 else "up"}">WoW {"▼" if deltas['wow'] < 0 else "▲"} {abs(deltas['wow']):.1f}%</span>
            <span class="chip {"down" if deltas['mom'] < 0 else "up"}">MoM {"▼" if deltas['mom'] < 0 else "▲"} {abs(deltas['mom']):.1f}%</span>
        </div>
        """
        st.markdown(delta_html, unsafe_allow_html=True)

# Data Table Section
st.markdown('<div class="table-card">', unsafe_allow_html=True)
st.markdown("### Person Master Data")

if df is not None and not df.empty:
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Lead Status filter
        if 'Lead_Status' in df.columns:
            status_options = ['All'] + sorted(df['Lead_Status'].dropna().unique().tolist())
            selected_status = st.selectbox("Lead Status", status_options)
        else:
            selected_status = 'All'
    
    with col2:
        # Lead Source filter
        if 'Lead_Source' in df.columns:
            source_options = ['All'] + sorted(df['Lead_Source'].dropna().unique().tolist())
            selected_source = st.selectbox("Lead Source", source_options)
        else:
            selected_source = 'All'
    
    with col3:
        # Conversion Status filter
        conversion_options = ['All', 'Converted', 'Not Converted']
        selected_conversion = st.selectbox("Conversion Status", conversion_options)
    
    with col4:
        # Search box
        search_term = st.text_input("Search all fields...", placeholder="Enter search term")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_status != 'All' and 'Lead_Status' in df.columns:
        filtered_df = filtered_df[filtered_df['Lead_Status'] == selected_status]
    
    if selected_source != 'All' and 'Lead_Source' in df.columns:
        filtered_df = filtered_df[filtered_df['Lead_Source'] == selected_source]
    
    if selected_conversion != 'All' and 'Is_Converted_Bool' in df.columns:
        if selected_conversion == 'Converted':
            filtered_df = filtered_df[filtered_df['Is_Converted_Bool'].astype(str).str.lower().isin(['true', 'yes', '1'])]
        else:
            filtered_df = filtered_df[~filtered_df['Is_Converted_Bool'].astype(str).str.lower().isin(['true', 'yes', '1'])]
    
    if search_term:
        # Search across all string columns
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    # Stats bar
    filtered_metrics = calculate_metrics(filtered_df)
    st.markdown(f"""
    <div style="display: flex; gap: 32px; padding: 16px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; margin: 16px 0;">
        <div><b>Filtered Records:</b> {len(filtered_df):,} / {len(df):,}</div>
        <div><b>Filtered Conversion Rate:</b> {filtered_metrics['lead_to_convert_pct']:.2f}%</div>
        <div><b>Median Speed to Lead:</b> {filtered_metrics['median_speed_to_lead']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display the dataframe with selected columns and custom labels
    if st.session_state.selected_columns:
        # Create a copy of the dataframe with selected columns
        display_df = filtered_df[st.session_state.selected_columns].copy()
        
        # Rename columns based on user labels
        rename_dict = {}
        for col in st.session_state.selected_columns:
            if col in st.session_state.column_labels and st.session_state.column_labels[col]:
                rename_dict[col] = st.session_state.column_labels[col]
        
        if rename_dict:
            display_df = display_df.rename(columns=rename_dict)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400,
            hide_index=True
        )
    else:
        st.warning("No columns selected. Please select columns to display in the configuration section above.")
    
    # Export button - exports with selected columns and custom labels
    if st.session_state.selected_columns:
        export_df = filtered_df[st.session_state.selected_columns].copy()
        
        # Apply custom labels to export
        rename_dict = {}
        for col in st.session_state.selected_columns:
            if col in st.session_state.column_labels and st.session_state.column_labels[col]:
                rename_dict[col] = st.session_state.column_labels[col]
        
        if rename_dict:
            export_df = export_df.rename(columns=rename_dict)
        
        csv = export_df.to_csv(index=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Export Filtered Data (Custom Columns)",
                data=csv,
                file_name=f"surstitch_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        with col2:
            # Also offer full export
            full_csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Export All Data (All Columns)",
                data=full_csv,
                file_name=f"surstitch_full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary"
            )
else:
    st.warning("No data loaded. Please upload a CSV file or ensure Output-Files directory contains person_master CSV files.")

st.markdown('</div>', unsafe_allow_html=True)
