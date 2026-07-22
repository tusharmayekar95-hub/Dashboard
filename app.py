import streamlit as st
import pandas as pd
import plotly.express as px
import gspread

from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Tyaani Jewellery Analytics",
    page_icon="💎",
    layout="wide"
)


# ============================================================
# BRAND THEME
# ============================================================

NAVY = "#5C1A2B"
NAVY_SOFT = "#7A2E3F"
GOLD = "#C9A227"
GOLD_SOFT = "#E3C567"

BG = "#FBF7F0"
CARD_BG = "#FFFFFF"

TEXT = "#2E1B1F"
TEXT_MUTED = "#7A6A5D"

GOOD = "#2F7D4F"
BAD = "#B3413A"

FONT = "'Segoe UI', Arial, sans-serif"


# ============================================================
# GLOBAL CSS
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {BG};
    }}

    h1, h2, h3, h4 {{
        color: {NAVY};
    }}

    /* HEADER */

    .main-header {{
        background: linear-gradient(
            120deg,
            {NAVY},
            {NAVY_SOFT}
        );

        padding: 24px 30px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.10);
    }}

    .main-header h1 {{
        color: white;
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }}

    .main-header p {{
        color: {GOLD_SOFT};
        margin-top: 5px;
        font-size: 13px;
    }}


    /* SECTION TITLE */

    .section-title {{
        color: {NAVY};
        font-size: 17px;
        font-weight: 700;
        border-bottom: 2px solid {GOLD};
        padding-bottom: 6px;
        margin-top: 20px;
        margin-bottom: 12px;
    }}


    /* KPI CARD */

    .kpi-card {{
        background: {CARD_BG};
        padding: 15px;
        border-radius: 12px;
        border-left: 4px solid {GOLD};
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        min-height: 105px;
        margin-bottom: 10px;
    }}

    .kpi-label {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .kpi-value {{
        color: {NAVY};
        font-size: 23px;
        font-weight: 700;
        margin-top: 6px;
    }}


    /* SIDEBAR */

    section[data-testid="stSidebar"] {{
        background-color: {NAVY};
    }}

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {{
        color: white !important;
    }}


    /* TABS */

    .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# KPI CARD FUNCTION
# ============================================================

def render_kpi(col, label, value):

    col.markdown(
        f"""
        <div class="kpi-card">

            <div class="kpi-label">
                {label}
            </div>

            <div class="kpi-value">
                {value}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================

SALES_SHEET_ID = "18pTb4qEZe4HtioClGzUGtZwvfY7wVs-4yT-PSgZinps"
SALES_GID = "2003103498"

WALKINS_SHEET_ID = "1BT9XC4oIpgTotOGoVOSUTGoR5Je3gmePifYhRqgGSI4"
WALKINS_GID = "2003103498"

TARGETS_SHEET_ID = "1VIvFZkAezRoQzqny-EE8-QMbzLCBsWlOtPnIaFbpQAA"
TARGETS_GID = "0"


# ============================================================
# HELPER FUNCTION
# ============================================================

def get_worksheet_by_gid(spreadsheet, gid):

    try:

        return spreadsheet.get_worksheet_by_id(
            int(gid)
        )

    except Exception:

        for ws in spreadsheet.worksheets():

            if str(ws.id) == str(gid):

                return ws

        return spreadsheet.sheet1


# ============================================================
# MOBILE NUMBER NORMALIZATION
# ============================================================

def normalize_mobile(value):

    """
    Standardizes Indian mobile numbers.

    Examples:

    9876543210
    +91 9876543210
    +919876543210
    09876543210
    98765 43210
    987-654-3210

    All become:

    9876543210
    """

    if pd.isna(value):

        return pd.NA


    value = str(value).strip()


    # Remove Excel decimal format

    if value.endswith(".0"):

        value = value[:-2]


    # Keep only digits

    digits = "".join(

        character

        for character in value

        if character.isdigit()

    )


    # Empty value

    if digits == "":

        return pd.NA


    # ========================================================
    # COUNTRY CODE 91
    # ========================================================

    # Example:
    #
    # 919876543210
    # +919876543210
    #

    if len(digits) == 12 and digits.startswith("91"):

        digits = digits[2:]


    # ========================================================
    # LEADING ZERO
    # ========================================================

    # Example:
    #
    # 09876543210
    #

    if len(digits) == 11 and digits.startswith("0"):

        digits = digits[1:]


    # ========================================================
    # VALID INDIAN MOBILE NUMBER
    # ========================================================

    if (

        len(digits) == 10

        and

        digits[0] in "6789"

    ):

        return digits


    # Invalid mobile number

    return pd.NA


# ============================================================
# CREATE CUSTOMER KEY
# ============================================================

def create_customer_key(df):

    df = df.copy()


    # ========================================================
    # NORMALIZE MOBILE
    # ========================================================

    df["Mobile_Normalized"] = (

        df["Mobile Number"]

        .apply(normalize_mobile)

    )


    # ========================================================
    # NORMALIZE NAME
    # ========================================================

    df["Name_Normalized"] = (

        df["Customer Name"]

        .astype("string")

        .str.upper()

        .str.strip()

        .str.replace(
            r"\s+",
            " ",
            regex=True
        )

    )


    # Remove invalid names

    df["Name_Normalized"] = (

        df["Name_Normalized"]

        .replace(

            [

                "",

                "NAN",

                "NONE",

                "NULL",

                "NA",

                "N/A"

            ],

            pd.NA

        )

    )


    # ========================================================
    # CUSTOMER KEY
    # ========================================================

    # MOBILE HAS PRIORITY
    #
    # If mobile exists:
    #
    # MOBILE_9876543210
    #
    # If mobile does not exist:
    #
    # NAME_RAHUL SHARMA
    #

    df["Customer_Key"] = pd.NA


    # Mobile available

    mobile_mask = (

        df["Mobile_Normalized"]

        .notna()

    )


    df.loc[mobile_mask, "Customer_Key"] = (

        "MOBILE_"

        +

        df.loc[
            mobile_mask,
            "Mobile_Normalized"
        ]

    )


    # Name fallback

    name_mask = (

        df["Customer_Key"].isna()

        &

        df["Name_Normalized"].notna()

    )


    df.loc[name_mask, "Customer_Key"] = (

        "NAME_"

        +

        df.loc[
            name_mask,
            "Name_Normalized"
        ]

    )


    # Completely unknown customer

    df["Customer_Key"] = (

        df["Customer_Key"]

        .fillna("UNKNOWN_CUSTOMER")

    )


    return df


# ============================================================
# NEW / REPEAT CUSTOMER LOGIC
# ============================================================

def calculate_new_repeat(df):

    df = df.copy()


    # ========================================================
    # FIRST PURCHASE MONTH
    #
    # Store + Customer
    #
    # The customer can be New in one store
    # and Repeat in another store.
    # ========================================================

    first_purchase = (

        df

        .groupby(

            [

                "Store",

                "Customer_Key"

            ]

        )[

            "Month_Sort"

        ]

        .min()

        .reset_index()

        .rename(

            columns={

                "Month_Sort":

                "First_Purchase_Month"

            }

        )

    )


    # ========================================================
    # MERGE FIRST PURCHASE MONTH
    # ========================================================

    df = df.merge(

        first_purchase,

        on=[

            "Store",

            "Customer_Key"

        ],

        how="left"

    )


    # ========================================================
    # NEW / REPEAT
    # ========================================================

    # Same month as first purchase = New
    #
    # Later month = Repeat
    #

    df["New_Repeat"] = "New"


    repeat_mask = (

        df["Month_Sort"]

        >

        df["First_Purchase_Month"]

    )


    df.loc[

        repeat_mask,

        "New_Repeat"

    ] = "Repeat"


    return df


# ============================================================
# PREPARE TARGET DATA
# ============================================================

def prepare_targets(targets):

    targets = targets.copy()


    # First column is Store

    targets = targets.rename(

        columns={

            targets.columns[0]:

            "Store"

        }

    )


    targets["Store"] = (

        targets["Store"]

        .astype(str)

        .str.strip()

    )


    # Remove total rows

    targets = targets[

        ~

        targets["Store"]

        .str.upper()

        .isin(

            [

                "TOTAL",

                "GRAND TOTAL",

                ""

            ]

        )

    ]


    # Month columns

    month_columns = [

        column

        for column in targets.columns

        if (

            column != "Store"

            and

            str(column)

            .strip()

            .lower()

            != "total"

        )

    ]


    # Wide to long

    targets = targets.melt(

        id_vars=[

            "Store"

        ],

        value_vars=month_columns,

        var_name="Month_Label",

        value_name="Target"

    )


    targets["Month_Label"] = (

        targets["Month_Label"]

        .astype(str)

        .str.strip()

    )


    targets["Target"] = pd.to_numeric(

        targets["Target"],

        errors="coerce"

    ).fillna(0)


    # Validate month

    targets["_ParsedMonth"] = pd.to_datetime(

        targets["Month_Label"],

        format="%b-%y",

        errors="coerce"

    )


    targets = targets.dropna(

        subset=[

            "_ParsedMonth"

        ]

    )


    return targets[

        [

            "Store",

            "Month_Label",

            "Target"

        ]

    ]


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data(ttl=300)
def load_data():


    # ========================================================
    # GOOGLE CREDENTIALS
    # ========================================================

    credentials = Credentials.from_service_account_info(

        st.secrets["gcp_service_account"],

        scopes=[

            "https://www.googleapis.com/auth/spreadsheets.readonly"

        ]

    )


    client = gspread.authorize(

        credentials

    )


    # ========================================================
    # OPEN SPREADSHEETS
    # ========================================================

    sales_ss = client.open_by_key(

        SALES_SHEET_ID

    )


    walkins_ss = client.open_by_key(

        WALKINS_SHEET_ID

    )


    targets_ss = client.open_by_key(

        TARGETS_SHEET_ID

    )


    # ========================================================
    # OPEN WORKSHEETS
    # ========================================================

    sales_ws = get_worksheet_by_gid(

        sales_ss,

        SALES_GID

    )


    walkins_ws = get_worksheet_by_gid(

        walkins_ss,

        WALKINS_GID

    )


    targets_ws = get_worksheet_by_gid(

        targets_ss,

        TARGETS_GID

    )


    # ========================================================
    # READ DATA
    # ========================================================

    sales = get_as_dataframe(

        sales_ws,

        evaluate_formulas=True

    )


    walkins = get_as_dataframe(

        walkins_ws,

        evaluate_formulas=True

    )


    targets = get_as_dataframe(

        targets_ws,

        evaluate_formulas=True

    )


    # ========================================================
    # REMOVE EMPTY ROWS / COLUMNS
    # ========================================================

    sales = (

        sales

        .dropna(how="all")

        .dropna(axis=1, how="all")

    )


    walkins = (

        walkins

        .dropna(how="all")

        .dropna(axis=1, how="all")

    )


    targets = (

        targets

        .dropna(how="all")

        .dropna(axis=1, how="all")

    )


    # ========================================================
    # SALES DATE FIELDS
    # ========================================================

    sales["Date"] = pd.to_datetime(

        sales["Date"],

        errors="coerce"

    )


    sales["Month_Sort"] = (

        sales["Date"]

        .dt.to_period("M")

        .astype(str)

    )


    sales["Month_Label"] = (

        sales["Date"]

        .dt.strftime("%b-%y")

    )


    sales["Year"] = (

        sales["Date"]

        .dt.year

    )


    sales["Month"] = (

        sales["Date"]

        .dt.month

    )


    # ========================================================
    # WALK-IN DATE FIELDS
    # ========================================================

    walkins["Date"] = pd.to_datetime(

        walkins["Date"],

        errors="coerce"

    )


    walkins["Month_Sort"] = (

        walkins["Date"]

        .dt.to_period("M")

        .astype(str)

    )


    walkins["Month_Label"] = (

        walkins["Date"]

        .dt.strftime("%b-%y")

    )


    walkins["Year"] = (

        walkins["Date"]

        .dt.year

    )


    walkins["Month"] = (

        walkins["Date"]

        .dt.month

    )


    # ========================================================
    # NUMERIC COLUMNS
    # ========================================================

    sales["Net Amount"] = pd.to_numeric(

        sales["Net Amount"],

        errors="coerce"

    ).fillna(0)


    sales["Qty"] = pd.to_numeric(

        sales["Qty"],

        errors="coerce"

    ).fillna(0)


    # ========================================================
    # CREATE CUSTOMER KEY
    # ========================================================

    sales = create_customer_key(

        sales

    )


    walkins = create_customer_key(

        walkins

    )


    # ========================================================
    # CALCULATE NEW / REPEAT
    # ========================================================

    sales = calculate_new_repeat(

        sales

    )


    walkins = calculate_new_repeat(

        walkins

    )


    # ========================================================
    # SALES-WALKIN MATCHING
    # ========================================================

    # Sales transaction key:
    #
    # Store
    # Date
    # Customer Key
    #

    sales_match_keys = (

        sales

        [

            [

                "Store",

                "Date",

                "Customer_Key"

            ]

        ]

        .drop_duplicates()

    )


    sales_match_keys[

        "Sales_Walkin_Tag"

    ] = "Converted"


    # Match Walk-in to Sales

    walkins = walkins.merge(

        sales_match_keys,

        on=[

            "Store",

            "Date",

            "Customer_Key"

        ],

        how="left"

    )


    walkins["Sales_Walkin_Tag"] = (

        walkins["Sales_Walkin_Tag"]

        .fillna("Not Converted")

    )


    # ========================================================
    # TARGETS
    # ========================================================

    targets = prepare_targets(

        targets

    )


    return (

        sales,

        walkins,

        targets

    )


# ============================================================
# LOAD DATA
# ============================================================

try:

    sales, walkins, targets = load_data()

except Exception as error:

    st.error(

        f"""
        Data loading failed.

        Error:
        {error}

        Please check:

        1. Google Sheet IDs
        2. GID values
        3. Service account credentials
        4. Required column names
        """

    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(

    "## 💎 Tyaani Analytics"

)


st.sidebar.markdown(

    "### Filters"

)


# ============================================================
# STORE FILTER
# ============================================================

stores = sorted(

    sales["Store"]

    .dropna()

    .unique()

    .tolist()

)


selected_stores = st.sidebar.multiselect(

    "Store",

    stores,

    default=[],

    help="Leave blank for all stores"

)


# ============================================================
# MONTH FILTER
# ============================================================

month_lookup = (

    sales

    [

        [

            "Month_Label",

            "Month_Sort"

        ]

    ]

    .drop_duplicates()

    .sort_values(

        "Month_Sort"

    )

)


months = (

    month_lookup

    ["Month_Label"]

    .tolist()

)


selected_months = st.sidebar.multiselect(

    "Month-YY",

    months,

    default=[],

    help="Leave blank for all months"

)


# ============================================================
# DATE LEVEL FILTER
# ============================================================

available_dates = sorted(

    sales["Date"]

    .dropna()

    .dt.date

    .unique()

    .tolist()

)


selected_dates = st.sidebar.multiselect(

    "Date Level",

    available_dates,

    default=[],

    help="Leave blank for all dates"

)


# ============================================================
# REFRESH BUTTON
# ============================================================

if st.sidebar.button(

    "🔄 Refresh Data"

):

    st.cache_data.clear()

    st.rerun()


# ============================================================
# APPLY FILTERS
# ============================================================

def apply_filters(df):

    result = df.copy()


    if selected_stores:

        result = result[

            result["Store"]

            .isin(

                selected_stores

            )

        ]


    if selected_months:

        result = result[

            result["Month_Label"]

            .isin(

                selected_months

            )

        ]


    if selected_dates:

        result = result[

            result["Date"]

            .dt.date

            .isin(

                selected_dates

            )

        ]


    return result


filtered_sales = apply_filters(

    sales

)


filtered_walkins = apply_filters(

    walkins

)


# ============================================================
# HEADER
# ============================================================

store_text = (

    ", ".join(selected_stores)

    if selected_stores

    else

    "All Stores"

)


month_text = (

    ", ".join(selected_months)

    if selected_months

    else

    "All Months"

)


st.markdown(

    f"""

    <div class="main-header">

        <h1>
            💎 Tyaani Jewellery Analytics
        </h1>

        <p>
            Sales • Walk-in • Customer • Conversion Performance
        </p>

        <p>
            Store: {store_text}
            &nbsp; | &nbsp;
            Month: {month_text}
        </p>

    </div>

    """,

    unsafe_allow_html=True

)


# ============================================================
# TARGET CALCULATION
# ============================================================

target_scope = targets.copy()


if selected_stores:

    target_scope = target_scope[

        target_scope["Store"]

        .isin(

            selected_stores

        )

    ]


if selected_months:

    target_scope = target_scope[

        target_scope["Month_Label"]

        .isin(

            selected_months

        )

    ]


period_target = target_scope[

    "Target"

].sum()


# ============================================================
# SALES KPI CALCULATIONS
# ============================================================

revenue = filtered_sales[

    "Net Amount"

].sum()


unique_invoice = filtered_sales[

    "Invoice No"

].nunique()


total_qty = filtered_sales[

    "Qty"

].sum()


atv = (

    revenue

    /

    unique_invoice

    if unique_invoice > 0

    else 0

)


upt = (

    total_qty

    /

    unique_invoice

    if unique_invoice > 0

    else 0

)


unique_customer = filtered_sales[

    "Customer_Key"

].nunique()


new_customer = filtered_sales[

    filtered_sales["New_Repeat"]

    ==

    "New"

][

    "Customer_Key"

].nunique()


repeat_customer = filtered_sales[

    filtered_sales["New_Repeat"]

    ==

    "Repeat"

][

    "Customer_Key"

].nunique()


customer_total = (

    new_customer

    +

    repeat_customer

)


new_percentage = (

    new_customer

    /

    customer_total

    *

    100

    if customer_total > 0

    else 0

)


repeat_percentage = (

    repeat_customer

    /

    customer_total

    *

    100

    if customer_total > 0

    else 0

)


revenue_new_customer = filtered_sales[

    filtered_sales["New_Repeat"]

    ==

    "New"

][

    "Net Amount"

].sum()


revenue_repeat_customer = filtered_sales[

    filtered_sales["New_Repeat"]

    ==

    "Repeat"

][

    "Net Amount"

].sum()


# ============================================================
# WALK-IN KPI CALCULATIONS
# ============================================================

total_walkin = filtered_walkins[

    "Customer_Key"

].nunique()


new_walkin = filtered_walkins[

    filtered_walkins["New_Repeat"]

    ==

    "New"

][

    "Customer_Key"

].nunique()


repeat_walkin = filtered_walkins[

    filtered_walkins["New_Repeat"]

    ==

    "Repeat"

][

    "Customer_Key"

].nunique()


converted_walkin = filtered_walkins[

    filtered_walkins[

        "Sales_Walkin_Tag"

    ]

    ==

    "Converted"

][

    "Customer_Key"

].nunique()


# Conversion is:
#
# Unique Customers / Total Unique Walk-ins
#

conversion_percentage = (

    unique_customer

    /

    total_walkin

    *

    100

    if total_walkin > 0

    else 0

)


new_walkin_percentage = (

    new_walkin

    /

    total_walkin

    *

    100

    if total_walkin > 0

    else 0

)


repeat_walkin_percentage = (

    repeat_walkin

    /

    total_walkin

    *

    100

    if total_walkin > 0

    else 0

)


# ============================================================
# TARGET CALCULATIONS
# ============================================================

achievement_percentage = (

    revenue

    /

    period_target

    *

    100

    if period_target > 0

    else 0

)


shortfall = (

    period_target

    -

    revenue

)


# ============================================================
# SALES KEY METRICS
# ============================================================

st.markdown(

    '<div class="section-title">Sales Key Metrics</div>',

    unsafe_allow_html=True

)


row1 = st.columns(4)


render_kpi(

    row1[0],

    "Target",

    f"₹{period_target:,.0f}"

)


render_kpi(

    row1[1],

    "Revenue",

    f"₹{revenue:,.0f}"

)


render_kpi(

    row1[2],

    "Achievement %",

    f"{achievement_percentage:.1f}%"

)


render_kpi(

    row1[3],

    "Shortfall",

    f"₹{shortfall:,.0f}"

)


row2 = st.columns(4)


render_kpi(

    row2[0],

    "Unique Invoice",

    f"{unique_invoice:,}"

)


render_kpi(

    row2[1],

    "ATV",

    f"₹{atv:,.0f}"

)


render_kpi(

    row2[2],

    "UPT",

    f"{upt:.2f}"

)


render_kpi(

    row2[3],

    "Sales-Walkin Converted",

    f"{converted_walkin:,}"

)


row3 = st.columns(4)


render_kpi(

    row3[0],

    "Total Walk-in",

    f"{total_walkin:,}"

)


render_kpi(

    row3[1],

    "Unique Customer",

    f"{unique_customer:,}"

)


render_kpi(

    row3[2],

    "Conversion %",

    f"{conversion_percentage:.1f}%"

)


render_kpi(

    row3[3],

    "Repeat %",

    f"{repeat_percentage:.1f}%"

)


row4 = st.columns(4)


render_kpi(

    row4[0],

    "New Customer",

    f"{new_customer:,}"

)


render_kpi(

    row4[1],

    "Repeat Customer",

    f"{repeat_customer:,}"

)


render_kpi(

    row4[2],

    "New %",

    f"{new_percentage:.1f}%"

)


render_kpi(

    row4[3],

    "Revenue New Customer",

    f"₹{revenue_new_customer:,.0f}"

)


row5 = st.columns(2)


render_kpi(

    row5[0],

    "Revenue Repeat Customer",

    f"₹{revenue_repeat_customer:,.0f}"

)


render_kpi(

    row5[1],

    "Revenue per Customer",

    (

        f"₹{revenue / unique_customer:,.0f}"

        if unique_customer > 0

        else "₹0"

    )

)


# ============================================================
# WALK-IN KEY METRICS
# ============================================================

st.markdown(

    '<div class="section-title">Walk-in Key Metrics</div>',

    unsafe_allow_html=True

)


walkin_row1 = st.columns(3)


render_kpi(

    walkin_row1[0],

    "Total Unique Walk-in",

    f"{total_walkin:,}"

)


render_kpi(

    walkin_row1[1],

    "New Walk-in",

    f"{new_walkin:,}"

)


render_kpi(

    walkin_row1[2],

    "Repeat Walk-in",

    f"{repeat_walkin:,}"

)


walkin_row2 = st.columns(2)


render_kpi(

    walkin_row2[0],

    "New Walk-in %",

    f"{new_walkin_percentage:.1f}%"

)


render_kpi(

    walkin_row2[1],

    "Repeat Walk-in %",

    f"{repeat_walkin_percentage:.1f}%"

)


# ============================================================
# TABS
# ============================================================

tab_trends, tab_sales, tab_walkin, tab_yoy, tab_raw = st.tabs(

    [

        "📈 Trends",

        "💰 Sales",

        "🚶 Walk-in",

        "📊 Same Month vs Last Year",

        "📄 Raw Data"

    ]

)


# ============================================================
# TAB 1 — TRENDS
# ============================================================

with tab_trends:


    st.subheader(

        "Sales Trend"

    )


    trend_sales = sales.copy()


    if selected_stores:

        trend_sales = trend_sales[

            trend_sales["Store"]

            .isin(

                selected_stores

            )

        ]


    monthly_sales = (

        trend_sales

        .groupby(

            [

                "Month_Sort",

                "Month_Label"

            ]

        )[

            "Net Amount"

        ]

        .sum()

        .reset_index()

        .sort_values(

            "Month_Sort"

        )

    )


    if not monthly_sales.empty:


        fig_sales = px.line(

            monthly_sales,

            x="Month_Label",

            y="Net Amount",

            markers=True,

            title="Monthly Revenue Trend"

        )


        fig_sales.update_layout(

            yaxis_title="Revenue",

            xaxis_title="Month"

        )


        st.plotly_chart(

            fig_sales,

            use_container_width=True

        )


    else:

        st.info(

            "No sales data available."

        )


    # --------------------------------------------------------
    # WALK-IN TREND
    # --------------------------------------------------------

    st.subheader(

        "Walk-in Trend"

    )


    trend_walkins = walkins.copy()


    if selected_stores:

        trend_walkins = trend_walkins[

            trend_walkins["Store"]

            .isin(

                selected_stores

            )

        ]


    monthly_walkins = (

        trend_walkins

        .groupby(

            [

                "Month_Sort",

                "Month_Label"

            ]

        )[

            "Customer_Key"

        ]

        .nunique()

        .reset_index(

            name="Walk-ins"

        )

        .sort_values(

            "Month_Sort"

        )

    )


    if not monthly_walkins.empty:


        fig_walkins = px.line(

            monthly_walkins,

            x="Month_Label",

            y="Walk-ins",

            markers=True,

            title="Monthly Walk-in Trend"

        )


        st.plotly_chart(

            fig_walkins,

            use_container_width=True

        )


    # --------------------------------------------------------
    # NEW VS REPEAT TREND
    # --------------------------------------------------------

    st.subheader(

        "New vs Repeat Customer Trend"

    )


    new_repeat_trend = (

        trend_sales

        .groupby(

            [

                "Month_Sort",

                "Month_Label",

                "New_Repeat"

            ]

        )[

            "Customer_Key"

        ]

        .nunique()

        .reset_index(

            name="Customers"

        )

        .sort_values(

            "Month_Sort"

        )

    )


    if not new_repeat_trend.empty:


        fig_new_repeat = px.line(

            new_repeat_trend,

            x="Month_Label",

            y="Customers",

            color="New_Repeat",

            markers=True,

            title="New vs Repeat Customer Trend"

        )


        st.plotly_chart(

            fig_new_repeat,

            use_container_width=True

        )


# ============================================================
# TAB 2 — SALES
# ============================================================

with tab_sales:


    st.subheader(

        "Store-wise Sales Performance"

    )


    store_sales = (

        filtered_sales

        .groupby(

            "Store"

        )

        .agg(

            Revenue=(

                "Net Amount",

                "sum"

            ),

            Unique_Invoice=(

                "Invoice No",

                "nunique"

            ),

            Qty=(

                "Qty",

                "sum"

            ),

            Unique_Customer=(

                "Customer_Key",

                "nunique"

            ),

            New_Customer=(

                "Customer_Key",

                lambda x:

                x[

                    filtered_sales.loc[

                        x.index,

                        "New_Repeat"

                    ]

                    ==

                    "New"

                ].nunique()

            ),

            Repeat_Customer=(

                "Customer_Key",

                lambda x:

                x[

                    filtered_sales.loc[

                        x.index,

                        "New_Repeat"

                    ]

                    ==

                    "Repeat"

                ].nunique()

            )

        )

        .reset_index()

    )


    store_sales["ATV"] = (

        store_sales["Revenue"]

        /

        store_sales["Unique_Invoice"]

        .replace(

            0,

            pd.NA

        )

    )


    store_sales["UPT"] = (

        store_sales["Qty"]

        /

        store_sales["Unique_Invoice"]

        .replace(

            0,

            pd.NA

        )

    )


    store_sales["New %"] = (

        store_sales["New_Customer"]

        /

        (

            store_sales["New_Customer"]

            +

            store_sales["Repeat_Customer"]

        )

        *

        100

    )


    store_sales["Repeat %"] = (

        store_sales["Repeat_Customer"]

        /

        (

            store_sales["New_Customer"]

            +

            store_sales["Repeat_Customer"]

        )

        *

        100

    )


    store_sales = store_sales.sort_values(

        "Revenue",

        ascending=False

    )


    st.dataframe(

        store_sales,

        use_container_width=True,

        hide_index=True

    )


    # --------------------------------------------------------
    # SALES BY STORE CHART
    # --------------------------------------------------------

    st.subheader(

        "Revenue by Store"

    )


    if not store_sales.empty:


        fig_store = px.bar(

            store_sales,

            x="Store",

            y="Revenue",

            text_auto=".2s",

            title="Store-wise Revenue"

        )


        st.plotly_chart(

            fig_store,

            use_container_width=True

        )


# ============================================================
# TAB 3 — WALK-IN
# ============================================================

with tab_walkin:


    st.subheader(

        "Store-wise Walk-in Performance"

    )


    walkin_store = (

        filtered_walkins

        .groupby(

            "Store"

        )

        .agg(

            Total_Walkin=(

                "Customer_Key",

                "nunique"

            ),

            New_Walkin=(

                "Customer_Key",

                lambda x:

                x[

                    filtered_walkins.loc[

                        x.index,

                        "New_Repeat"

                    ]

                    ==

                    "New"

                ].nunique()

            ),

            Repeat_Walkin=(

                "Customer_Key",

                lambda x:

                x[

                    filtered_walkins.loc[

                        x.index,

                        "New_Repeat"

                    ]

                    ==

                    "Repeat"

                ].nunique()

            ),

            Converted_Walkin=(

                "Customer_Key",

                lambda x:

                x[

                    filtered_walkins.loc[

                        x.index,

                        "Sales_Walkin_Tag"

                    ]

                    ==

                    "Converted"

                ].nunique()

            )

        )

        .reset_index()

    )


    walkin_store["Conversion %"] = (

        walkin_store["Converted_Walkin"]

        /

        walkin_store["Total_Walkin"]

        *

        100

    )


    walkin_store["New %"] = (

        walkin_store["New_Walkin"]

        /

        walkin_store["Total_Walkin"]

        *

        100

    )


    walkin_store["Repeat %"] = (

        walkin_store["Repeat_Walkin"]

        /

        walkin_store["Total_Walkin"]

        *

        100

    )


    st.dataframe(

        walkin_store,

        use_container_width=True,

        hide_index=True

    )


    # --------------------------------------------------------
    # WALK-IN CHART
    # --------------------------------------------------------

    st.subheader(

        "Walk-ins by Store"

    )


    if not walkin_store.empty:


        fig_walkin_store = px.bar(

            walkin_store,

            x="Store",

            y="Total_Walkin",

            text_auto=True,

            title="Total Unique Walk-ins by Store"

        )


        st.plotly_chart(

            fig_walkin_store,

            use_container_width=True

        )


# ============================================================
# TAB 4 — SAME MONTH VS LAST YEAR
# ============================================================

with tab_yoy:


    st.subheader(

        "Same Month vs Last Year Same Month"

    )


    if not selected_months:


        st.info(

            "Please select a Month-YY from the sidebar."

        )


    else:


        # Use the latest selected month

        selected_month = selected_months[-1]


        current_date = pd.to_datetime(

            selected_month,

            format="%b-%y"

        )


        current_month = current_date.month

        current_year = current_date.year

        previous_year = current_year - 1


        # ----------------------------------------------------
        # CURRENT YEAR
        # ----------------------------------------------------

        current_sales = sales[

            (

                sales["Month"]

                ==

                current_month

            )

            &

            (

                sales["Year"]

                ==

                current_year

            )

        ]


        # ----------------------------------------------------
        # LAST YEAR
        # ----------------------------------------------------

        last_year_sales = sales[

            (

                sales["Month"]

                ==

                current_month

            )

            &

            (

                sales["Year"]

                ==

                previous_year

            )

        ]


        # Store filter

        if selected_stores:


            current_sales = current_sales[

                current_sales["Store"]

                .isin(

                    selected_stores

                )

            ]


            last_year_sales = last_year_sales[

                last_year_sales["Store"]

                .isin(

                    selected_stores

                )

            ]


        # ----------------------------------------------------
        # KPI FUNCTION
        # ----------------------------------------------------

        def calculate_comparison_kpis(df):


            revenue_value = df[

                "Net Amount"

            ].sum()


            invoice_value = df[

                "Invoice No"

            ].nunique()


            customer_value = df[

                "Customer_Key"

            ].nunique()


            qty_value = df[

                "Qty"

            ].sum()


            atv_value = (

                revenue_value

                /

                invoice_value

                if invoice_value > 0

                else 0

            )


            upt_value = (

                qty_value

                /

                invoice_value

                if invoice_value > 0

                else 0

            )


            return {

                "Revenue":

                revenue_value,

                "Unique Invoice":

                invoice_value,

                "Unique Customer":

                customer_value,

                "Qty":

                qty_value,

                "ATV":

                atv_value,

                "UPT":

                upt_value

            }


        current_kpi = calculate_comparison_kpis(

            current_sales

        )


        last_year_kpi = calculate_comparison_kpis(

            last_year_sales

        )


        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        current_label = current_date.strftime(

            "%b %Y"

        )


        last_year_label = pd.Timestamp(

            year=previous_year,

            month=current_month,

            day=1

        ).strftime(

            "%b %Y"

        )


        comparison_df = pd.DataFrame(

            {

                "Metric": [

                    "Revenue",

                    "Unique Invoice",

                    "ATV",

                    "UPT",

                    "Unique Customer",

                    "Qty"

                ],

                current_label: [

                    current_kpi["Revenue"],

                    current_kpi["Unique Invoice"],

                    current_kpi["ATV"],

                    current_kpi["UPT"],

                    current_kpi["Unique Customer"],

                    current_kpi["Qty"]

                ],

                last_year_label: [

                    last_year_kpi["Revenue"],

                    last_year_kpi["Unique Invoice"],

                    last_year_kpi["ATV"],

                    last_year_kpi["UPT"],

                    last_year_kpi["Unique Customer"],

                    last_year_kpi["Qty"]

                ]

            }

        )


        st.dataframe(

            comparison_df,

            use_container_width=True,

            hide_index=True

        )


        # ----------------------------------------------------
        # REVENUE COMPARISON
        # ----------------------------------------------------

        chart_df = pd.DataFrame(

            {

                "Period": [

                    current_label,

                    last_year_label

                ],

                "Revenue": [

                    current_kpi["Revenue"],

                    last_year_kpi["Revenue"]

                ]

            }

        )


        fig_yoy = px.bar(

            chart_df,

            x="Period",

            y="Revenue",

            text_auto=".2s",

            title=(

                f"{current_label} vs "

                f"{last_year_label}"

            )

        )


        st.plotly_chart(

            fig_yoy,

            use_container_width=True

        )


# ============================================================
# TAB 5 — RAW DATA
# ============================================================

with tab_raw:


    st.subheader(

        "Filtered Sales Data"

    )


    st.dataframe(

        filtered_sales,

        use_container_width=True,

        hide_index=True

    )


    st.download_button(

        "⬇️ Download Sales CSV",

        data=filtered_sales.to_csv(

            index=False

        ).encode(

            "utf-8"

        ),

        file_name="filtered_sales.csv",

        mime="text/csv"

    )


    st.divider()


    st.subheader(

        "Filtered Walk-in Data"

    )


    st.dataframe(

        filtered_walkins,

        use_container_width=True,

        hide_index=True

    )


    st.download_button(

        "⬇️ Download Walk-in CSV",

        data=filtered_walkins.to_csv(

            index=False

        ).encode(

            "utf-8"

        ),

        file_name="filtered_walkins.csv",

        mime="text/csv"

    )