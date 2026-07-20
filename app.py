import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Tyaani Jewellery Analytics",
    page_icon="💎",
    layout="wide"
)

# =====================================================
# THEME — matched to Tyaani's brand aesthetic (deep maroon / gold / ivory,
# typical of 22KT gold Polki bridal jewellery branding). Variable names
# kept as NAVY/NAVY_SOFT for compatibility with the rest of the file —
# they now hold maroon tones instead of navy.
# =====================================================
NAVY = "#5C1A2B"        # deep maroon/wine — primary brand color
NAVY_SOFT = "#7A2E3F"    # lighter maroon — gradients, secondary elements
GOLD = "#C9A227"         # gold — unchanged, matches 22KT gold branding
GOLD_SOFT = "#E3C567"
GRAY = "#A08972"         # warm taupe (replaces cool gray)
GRAY_LIGHT = "#EDE3D8"   # warm ivory border tone
BG = "#FBF7F0"           # warm ivory page background
CARD_BG = "#FFFFFF"
TEXT_MUTED = "#7A6A5D"   # warm gray-brown (replaces cool gray)
GOOD = "#2F7D4F"
BAD = "#B3413A"

FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

# =====================================================
# GLOBAL STYLING
# =====================================================
st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {BG};
        }}
        h1, h2, h3, h4 {{
            font-family: {FONT};
            color: {NAVY};
        }}
        /* ---- Header banner ---- */
        .exec-header {{
            background: linear-gradient(120deg, {NAVY} 0%, {NAVY_SOFT} 100%);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 22px;
            box-shadow: 0 6px 18px rgba(16, 36, 62, 0.18);
        }}
        .exec-header h1 {{
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .exec-header p {{
            color: {GOLD_SOFT};
            margin: 4px 0 0 0;
            font-size: 13px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .filter-pills {{ margin-top: 14px; }}
        .filter-pill {{
            display: inline-block;
            background: rgba(255,255,255,0.10);
            color: white;
            border: 1px solid rgba(255,255,255,0.25);
            border-radius: 999px;
            padding: 4px 14px;
            font-size: 12.5px;
            margin-right: 8px;
            font-family: {FONT};
        }}
        .filter-pill b {{ color: {GOLD_SOFT}; }}

        /* ---- KPI cards ---- */
        .kpi-card {{
            background: {CARD_BG};
            border-radius: 14px;
            padding: 16px 18px 14px 18px;
            box-shadow: 0 2px 10px rgba(16, 36, 62, 0.06);
            border-left: 4px solid {GOLD};
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            min-height: 106px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .kpi-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 22px rgba(16, 36, 62, 0.14);
        }}
        .kpi-icon {{ font-size: 18px; margin-bottom: 2px; }}
        .kpi-label {{
            font-family: {FONT};
            font-size: 11.5px;
            font-weight: 600;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            color: {TEXT_MUTED};
            margin-bottom: 2px;
        }}
        .kpi-value {{
            font-family: {FONT};
            font-size: 23px;
            font-weight: 700;
            color: {NAVY};
            line-height: 1.15;
        }}
        .kpi-delta {{
            font-size: 12px;
            font-weight: 600;
            margin-top: 2px;
        }}

        /* ---- Section labels ---- */
        .section-kicker {{
            font-family: {FONT};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: {GOLD};
            margin: 4px 0 2px 0;
        }}

        /* ---- Tabs ---- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border-radius: 10px 10px 0 0;
            font-family: {FONT};
            font-weight: 600;
            color: {TEXT_MUTED};
            padding: 8px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {NAVY} !important;
            border-bottom: 3px solid {GOLD} !important;
        }}

        /* ---- Dataframes ---- */
        div[data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background-color: {NAVY};
        }}
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: #F3E9DD !important;
        }}
        section[data-testid="stSidebar"] .stSelectbox label {{
            color: {GOLD_SOFT} !important;
            font-weight: 600;
            font-size: 12.5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        /* Selectbox itself sits on a white pill — force dark, readable text there */
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important;
            border-radius: 10px !important;
            border: 1px solid {GRAY_LIGHT} !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
            color: {NAVY} !important;
            fill: {NAVY} !important;
        }}
        section[data-testid="stSidebar"] button {{
            background-color: rgba(255,255,255,0.08) !important;
            border: 1px solid {GOLD_SOFT} !important;
            color: {GOLD_SOFT} !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] button:hover {{
            background-color: rgba(201,162,39,0.18) !important;
            border-color: {GOLD} !important;
            color: white !important;
        }}
    </style>
    """,
    unsafe_allow_html=True
)


def render_kpi(col, icon, label, value, delta=None):
    """Render a custom KPI card with an optional colored delta.
    Always reserves the delta row's space so cards in the same row line up
    whether or not they carry a delta value."""
    if delta is not None:
        if delta == "N/A":
            color = TEXT_MUTED
        elif delta.strip().startswith("-"):
            color = BAD
        else:
            color = GOOD
        delta_html = f'<div class="kpi-delta" style="color:{color}">{delta} vs last year</div>'
    else:
        delta_html = '<div class="kpi-delta">&nbsp;</div>'

    col.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_fig(fig, height=400, show_legend=None, category_count=0):
    """Apply a consistent, minimal executive look to every chart.
    category_count lets bar/pie charts with many x-axis labels (e.g. 20+
    associates) auto-angle their tick labels so they don't overlap."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT, size=12.5, color=TEXT_MUTED),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
        hoverlabel=dict(bgcolor="white", font_size=12.5, font_family=FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    if show_legend is not None:
        fig.update_layout(showlegend=show_legend)
    tickangle = -45 if category_count > 8 else 0
    fig.update_xaxes(
        showgrid=False, showline=True, linecolor=GRAY_LIGHT,
        tickfont=dict(size=11.5), tickangle=tickangle,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EFEDE8", zeroline=False, tickfont=dict(size=11.5))
    if category_count > 8:
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=90))
    return fig


def highlight_top(fig, values, top_color=GOLD, base_color=NAVY_SOFT):
    """Recolor a single-series bar chart: navy bars, gold highlight on the top value."""
    if len(values) == 0:
        return fig
    peak = max(values)
    colors = [top_color if v == peak else base_color for v in values]
    fig.update_traces(marker_color=colors, marker_line_width=0)
    return fig


# =====================================================
# LOAD DATA — Google Sheets via service account (gspread)
# =====================================================
SALES_SHEET_ID = "18pTb4qEZe4HtioClGzUGtZwvfY7wVs-4yT-PSgZinps"
SALES_GID = "2003103498"

WALKINS_SHEET_ID = "1BT9XC4oIpgTotOGoVOSUTGoR5Je3gmePifYhRqgGSI4"
WALKINS_GID = "2003103498"


def _get_worksheet(spreadsheet, gid):
    """Open the exact tab matching the gid from the sheet's URL, not just the
    first tab — .sheet1 silently reads the wrong data if Sales/Walk-ins
    aren't on the first tab of their spreadsheet."""
    try:
        return spreadsheet.get_worksheet_by_id(int(gid))
    except Exception:
        for ws in spreadsheet.worksheets():
            if str(ws.id) == str(gid):
                return ws
    # Fall back to the first tab only if the gid truly can't be found
    return spreadsheet.sheet1


@st.cache_data(ttl=300)  # re-fetch from Google Sheets at most every 5 minutes
def load_data():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    client = gspread.authorize(creds)

    sales_ss = client.open_by_key(SALES_SHEET_ID)
    walkins_ss = client.open_by_key(WALKINS_SHEET_ID)

    sales_ws = _get_worksheet(sales_ss, SALES_GID)
    walkins_ws = _get_worksheet(walkins_ss, WALKINS_GID)

    sales = get_as_dataframe(sales_ws, evaluate_formulas=True)
    walkins = get_as_dataframe(walkins_ws, evaluate_formulas=True)

    # get_as_dataframe pulls in the sheet's full grid, including trailing
    # empty rows/columns beyond your actual data — drop both.
    sales = sales.dropna(how="all").dropna(axis=1, how="all")
    walkins = walkins.dropna(how="all").dropna(axis=1, how="all")

    sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce")
    sales["Year"] = sales["Date"].dt.year
    sales["Month"] = sales["Date"].dt.month
    sales["Month_Label"] = sales["Date"].dt.strftime("%b-%y")
    sales["Month_Sort"] = sales["Date"].dt.strftime("%Y-%m")

    walkins["Date"] = pd.to_datetime(walkins["Date"], errors="coerce")
    walkins["Year"] = walkins["Date"].dt.year
    walkins["Month"] = walkins["Date"].dt.month
    walkins["Month_Label"] = walkins["Date"].dt.strftime("%b-%y")
    walkins["Month_Sort"] = walkins["Date"].dt.strftime("%Y-%m")

    return sales, walkins


try:
    sales, walkins = load_data()
except Exception as e:
    st.error(
        f"Could not load data from Google Sheets: {e}\n\n"
        "Check that:\n"
        "1. `.streamlit/secrets.toml` has a `[gcp_service_account]` section "
        "with your service account's JSON key.\n"
        "2. Both sheets are shared with the service account's email "
        "(the `client_email` field in your key file) — or shared as "
        "'Anyone with the link can view'.\n"
        "3. The sheet IDs / gid values at the top of `load_data()` are correct."
    )
    st.stop()

CANDIDATE_ASSOC_KEYWORDS = [
    "associate", "executive", "salesperson", "sales person",
    "staff", "employee", "sold by", "sales rep", "advisor",
]

# =====================================================
# SIDEBAR — FILTERS (Store + Month only)
# =====================================================
st.sidebar.markdown("## 💎 Tyaani Analytics")
st.sidebar.caption("Filter the dashboard")

stores = ["All"] + sorted(sales["Store"].dropna().unique().tolist())

month_lookup = (
    sales[["Month_Label", "Month_Sort"]]
    .dropna()
    .drop_duplicates()
    .sort_values("Month_Sort")
)
months = ["All"] + month_lookup["Month_Label"].tolist()

selected_store = st.sidebar.selectbox("Store", stores)
selected_month = st.sidebar.selectbox("Month", months)

st.sidebar.markdown("---")
st.sidebar.caption(f"Sales rows loaded: {len(sales):,}")
st.sidebar.caption(f"Walk-in rows loaded: {len(walkins):,}")
st.sidebar.caption("Data auto-refreshes every 5 min.")
if st.sidebar.button("🔄 Refresh data now"):
    st.cache_data.clear()
    st.rerun()


def apply_filters(df):
    out = df.copy()
    if selected_store != "All":
        out = out[out["Store"] == selected_store]
    if selected_month != "All":
        out = out[out["Month_Label"] == selected_month]
    return out


filtered_sales = apply_filters(sales)
filtered_walkins = apply_filters(walkins)

# =====================================================
# HEADER
# =====================================================
st.markdown(
    f"""
    <div class="exec-header">
        <h1>💎 Tyaani Jewellery — Executive Dashboard</h1>
        <p>Performance overview across stores, months & sales associates</p>
        <div class="filter-pills">
            <span class="filter-pill">Store: <b>{selected_store}</b></span>
            <span class="filter-pill">Month: <b>{selected_month}</b></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =====================================================
# KPI CALCULATIONS
# =====================================================
net_sales = filtered_sales["Net Amount"].sum()
total_invoices = filtered_sales["Invoice No"].nunique()

new_customers = filtered_sales[filtered_sales["New/Repeat"] == "New"]["Helper"].nunique()
repeat_customers = filtered_sales[filtered_sales["New/Repeat"] == "Repeat"]["Helper"].nunique()

repeat_share = (
    repeat_customers / (new_customers + repeat_customers) * 100
    if (new_customers + repeat_customers) > 0 else 0
)

avg_bill = net_sales / total_invoices if total_invoices > 0 else 0

total_walkins = filtered_walkins[
    (filtered_walkins["New/Repeat"] == "New") &
    (filtered_walkins["unique cust count WRT num&Nam"] == 1)
]["Helper"].nunique()

matched_walkins = filtered_walkins[
    (filtered_walkins["Sales Matched"] == "Matched") &
    (filtered_walkins["unique cust count WRT num&Nam"] == 1)
]["Helper"].nunique()

conversion = matched_walkins / total_walkins * 100 if total_walkins > 0 else 0
upt = filtered_sales["Qty"].sum() / total_invoices if total_invoices > 0 else 0

# ---------------- YEAR ON YEAR (same month) ----------------
current_sales = net_sales
last_year_sales = 0

if selected_month != "All":
    current = pd.to_datetime(selected_month, format="%b-%y")
    current_month = current.month
    current_year = current.year
    previous_year = current_year - 1

    prior_year_df = sales[(sales["Month"] == current_month) & (sales["Year"] == previous_year)]
    if selected_store != "All":
        prior_year_df = prior_year_df[prior_year_df["Store"] == selected_store]

    last_year_sales = prior_year_df["Net Amount"].sum()

if last_year_sales > 0:
    yoy_growth = ((current_sales - last_year_sales) / last_year_sales) * 100
    yoy_display = f"{yoy_growth:+.1f}%"
else:
    yoy_display = "N/A"

# =====================================================
# KPI CARDS
# =====================================================
st.markdown('<div class="section-kicker">Key Metrics</div>', unsafe_allow_html=True)

r1 = st.columns(3)
render_kpi(r1[0], "💎", "Net Sales", f"₹{net_sales:,.0f}", yoy_display)
render_kpi(r1[1], "🧾", "Invoices", f"{total_invoices:,}")
render_kpi(r1[2], "💳", "Avg Bill", f"₹{avg_bill:,.0f}")

st.write("")

r2 = st.columns(3)
render_kpi(r2[0], "📦", "UPT", f"{upt:.2f}")
render_kpi(r2[1], "🔁", "Repeat %", f"{repeat_share:.1f}%")
render_kpi(r2[2], "🎯", "Conversion %", f"{conversion:.1f}%")

st.write("")

r3 = st.columns(3)
render_kpi(r3[0], "🚶", "Walk-ins", f"{total_walkins:,}")
render_kpi(r3[1], "🆕", "New Customers", f"{new_customers:,}")
render_kpi(r3[2], "👥", "Repeat Customers", f"{repeat_customers:,}")

st.write("")
st.markdown("---")

# =====================================================
# TABS
# =====================================================
tab_trend, tab_store, tab_month_yoy, tab_assoc, tab_data = st.tabs(
    [
        "📈 Trends",
        "🏬 Store & City Breakdown",
        "📆 Month vs Last Year",
        "🧑‍💼 Sales Associate",
        "📄 Raw Data",
    ]
)

# ---------------- TAB 1: TRENDS ----------------
with tab_trend:
    trend_source = sales.copy()
    if selected_store != "All":
        trend_source = trend_source[trend_source["Store"] == selected_store]

    st.markdown('<div class="section-kicker">Monthly Net Sales Trend</div>', unsafe_allow_html=True)
    monthly_trend = (
        trend_source.groupby(["Month_Sort", "Month_Label"], as_index=False)["Net Amount"]
        .sum()
        .sort_values("Month_Sort")
    )

    if not monthly_trend.empty:
        fig_trend = px.area(
            monthly_trend,
            x="Month_Label",
            y="Net Amount",
            markers=True,
            labels={"Month_Label": "Month", "Net Amount": "Net Sales (₹)"},
        )
        fig_trend.update_traces(
            line_color=NAVY, fillcolor="rgba(16,36,62,0.08)",
            marker=dict(color=GOLD, size=7),
        )
        fig_trend.update_layout(hovermode="x unified")
        st.plotly_chart(style_fig(fig_trend, show_legend=False), use_container_width=True)
    else:
        st.info("No sales data available for this selection.")

    st.markdown('<div class="section-kicker">Monthly Invoice Count</div>', unsafe_allow_html=True)
    monthly_invoices = (
        trend_source.groupby(["Month_Sort", "Month_Label"], as_index=False)["Invoice No"]
        .nunique()
        .sort_values("Month_Sort")
        .rename(columns={"Invoice No": "Invoices"})
    )
    if not monthly_invoices.empty:
        fig_inv = px.bar(monthly_invoices, x="Month_Label", y="Invoices", labels={"Month_Label": "Month"})
        fig_inv = highlight_top(fig_inv, monthly_invoices["Invoices"].tolist())
        st.plotly_chart(style_fig(fig_inv, show_legend=False), use_container_width=True)

# ---------------- TAB 2: STORE / CITY BREAKDOWN ----------------
with tab_store:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-kicker">Net Sales by Store</div>', unsafe_allow_html=True)
        by_store = (
            filtered_sales.groupby("Store", as_index=False)["Net Amount"]
            .sum()
            .sort_values("Net Amount", ascending=False)
        )
        if not by_store.empty:
            fig_store = px.bar(by_store, x="Store", y="Net Amount", labels={"Net Amount": "Net Sales (₹)"})
            fig_store = highlight_top(fig_store, by_store["Net Amount"].tolist())
            st.plotly_chart(
                style_fig(fig_store, show_legend=False, category_count=len(by_store)),
                use_container_width=True,
            )
        else:
            st.info("No data for this selection.")

    with col_b:
        st.markdown('<div class="section-kicker">Net Sales by City</div>', unsafe_allow_html=True)
        by_city = (
            filtered_sales.groupby("City", as_index=False)["Net Amount"]
            .sum()
            .sort_values("Net Amount", ascending=False)
        )
        if not by_city.empty:
            fig_city = px.pie(
                by_city, names="City", values="Net Amount", hole=0.55,
                color_discrete_sequence=[NAVY, GOLD, NAVY_SOFT, GOLD_SOFT, GRAY, "#8B4049", "#D9BB6F", "#B89A85"],
            )
            fig_city.update_traces(textfont_size=11.5, marker_line_width=1, marker_line_color="white")
            st.plotly_chart(style_fig(fig_city, show_legend=True), use_container_width=True)
        else:
            st.info("No data for this selection.")

    st.markdown('<div class="section-kicker">New vs Repeat Customers by Store</div>', unsafe_allow_html=True)
    if "New/Repeat" in filtered_sales.columns:
        nr_store = (
            filtered_sales.groupby(["Store", "New/Repeat"])["Helper"]
            .nunique()
            .reset_index(name="Customers")
        )
        if not nr_store.empty:
            fig_nr = px.bar(
                nr_store, x="Store", y="Customers", color="New/Repeat", barmode="group",
                color_discrete_map={"New": NAVY, "Repeat": GOLD},
            )
            st.plotly_chart(style_fig(fig_nr, show_legend=True), use_container_width=True)

# ---------------- TAB 3: MONTH VS SAME MONTH LAST YEAR ----------------
with tab_month_yoy:
    st.markdown('<div class="section-kicker">Month vs Same Month Last Year</div>', unsafe_allow_html=True)
    st.caption("Driven by the Month filter in the sidebar. Pick Apr-26 to compare it against Apr-25.")

    if selected_month == "All":
        st.info("👈 Select a specific month in the sidebar to see this comparison.")
    else:
        current = pd.to_datetime(selected_month, format="%b-%y")
        c_month, c_year = current.month, current.year
        p_year = c_year - 1
        this_label = current.strftime("%b %Y")
        last_label = pd.Timestamp(year=p_year, month=c_month, day=1).strftime("%b %Y")

        base_sales = sales.copy()
        base_walkins = walkins.copy()
        if selected_store != "All":
            base_sales = base_sales[base_sales["Store"] == selected_store]
            base_walkins = base_walkins[base_walkins["Store"] == selected_store]

        this_sales = base_sales[(base_sales["Month"] == c_month) & (base_sales["Year"] == c_year)]
        last_sales = base_sales[(base_sales["Month"] == c_month) & (base_sales["Year"] == p_year)]
        this_walk = base_walkins[(base_walkins["Month"] == c_month) & (base_walkins["Year"] == c_year)]
        last_walk = base_walkins[(base_walkins["Month"] == c_month) & (base_walkins["Year"] == p_year)]

        def compute_kpis(s_df, w_df):
            net = s_df["Net Amount"].sum()
            inv = s_df["Invoice No"].nunique()
            new_c = s_df[s_df["New/Repeat"] == "New"]["Helper"].nunique()
            rep_c = s_df[s_df["New/Repeat"] == "Repeat"]["Helper"].nunique()
            rep_share = rep_c / (new_c + rep_c) * 100 if (new_c + rep_c) > 0 else 0
            avg_bill_ = net / inv if inv > 0 else 0
            walkins_n = w_df[
                (w_df["New/Repeat"] == "New") & (w_df["unique cust count WRT num&Nam"] == 1)
            ]["Helper"].nunique()
            matched = w_df[
                (w_df["Sales Matched"] == "Matched") & (w_df["unique cust count WRT num&Nam"] == 1)
            ]["Helper"].nunique()
            conv = matched / walkins_n * 100 if walkins_n > 0 else 0
            upt_ = s_df["Qty"].sum() / inv if inv > 0 else 0
            return {
                "net": net, "inv": inv, "new_c": new_c, "rep_c": rep_c,
                "rep_share": rep_share, "avg_bill": avg_bill_,
                "walkins": walkins_n, "conv": conv, "upt": upt_,
            }

        this_kpi = compute_kpis(this_sales, this_walk)
        last_kpi = compute_kpis(last_sales, last_walk)

        def pct_delta(curr, prev):
            return f"{(curr - prev) / prev * 100:+.1f}%" if prev > 0 else "N/A"

        st.markdown(f"##### {this_label} vs {last_label}")

        r1 = st.columns(4)
        render_kpi(r1[0], "💎", "Net Sales", f"₹{this_kpi['net']:,.0f}", pct_delta(this_kpi["net"], last_kpi["net"]))
        render_kpi(r1[1], "🧾", "Invoices", f"{this_kpi['inv']:,}", pct_delta(this_kpi["inv"], last_kpi["inv"]))
        render_kpi(r1[2], "💳", "Avg Bill", f"₹{this_kpi['avg_bill']:,.0f}", pct_delta(this_kpi["avg_bill"], last_kpi["avg_bill"]))
        render_kpi(r1[3], "📦", "UPT", f"{this_kpi['upt']:.2f}", pct_delta(this_kpi["upt"], last_kpi["upt"]))

        st.write("")
        r2 = st.columns(4)
        render_kpi(r2[0], "🔁", "Repeat %", f"{this_kpi['rep_share']:.1f}%", pct_delta(this_kpi["rep_share"], last_kpi["rep_share"]))
        render_kpi(r2[1], "🎯", "Conversion %", f"{this_kpi['conv']:.1f}%", pct_delta(this_kpi["conv"], last_kpi["conv"]))
        render_kpi(r2[2], "🚶", "Walk-ins", f"{this_kpi['walkins']:,}", pct_delta(this_kpi["walkins"], last_kpi["walkins"]))
        render_kpi(r2[3], "🆕", "New Customers", f"{this_kpi['new_c']:,}", pct_delta(this_kpi["new_c"], last_kpi["new_c"]))

        st.write("")
        st.markdown('<div class="section-kicker">Side-by-Side KPI Table</div>', unsafe_allow_html=True)
        compare_df = pd.DataFrame({
            "Metric": [
                "Net Sales (₹)", "Invoices", "Avg Bill (₹)", "UPT",
                "Repeat %", "Conversion %", "Walk-ins", "New Customers", "Repeat Customers",
            ],
            this_label: [
                this_kpi["net"], this_kpi["inv"], this_kpi["avg_bill"], this_kpi["upt"],
                this_kpi["rep_share"], this_kpi["conv"], this_kpi["walkins"],
                this_kpi["new_c"], this_kpi["rep_c"],
            ],
            last_label: [
                last_kpi["net"], last_kpi["inv"], last_kpi["avg_bill"], last_kpi["upt"],
                last_kpi["rep_share"], last_kpi["conv"], last_kpi["walkins"],
                last_kpi["new_c"], last_kpi["rep_c"],
            ],
        })
        st.dataframe(compare_df, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-kicker">Net Sales Comparison</div>', unsafe_allow_html=True)
        chart_df = pd.DataFrame({
            "Period": [this_label, last_label],
            "Net Sales": [this_kpi["net"], last_kpi["net"]],
        })
        fig_month_compare = px.bar(chart_df, x="Period", y="Net Sales", color="Period", text_auto=".2s",
                                    color_discrete_map={this_label: GOLD, last_label: NAVY_SOFT})
        st.plotly_chart(style_fig(fig_month_compare, show_legend=False), use_container_width=True)

# ---------------- TAB 4: SALES ASSOCIATE DASHBOARD ----------------
with tab_assoc:
    st.markdown('<div class="section-kicker">Sales Associate Performance</div>', unsafe_allow_html=True)
    st.caption("Respects the Store and Month filters in the sidebar.")

    matching_cols = [c for c in filtered_sales.columns if any(k in c.lower() for k in CANDIDATE_ASSOC_KEYWORDS)]

    if not matching_cols:
        st.warning(
            "Couldn't automatically find a column identifying the sales associate. "
            "Your Sales sheet's columns are listed below — let me know the exact "
            "column name and I'll wire it in."
        )
        st.write(list(sales.columns))
    else:
        assoc_col = (
            matching_cols[0] if len(matching_cols) == 1
            else st.selectbox("Which column identifies the Sales Associate?", matching_cols, key="assoc_sales_col")
        )

        assoc_sales = filtered_sales.dropna(subset=[assoc_col])

        if assoc_sales.empty:
            st.info("No data for this selection.")
        else:
            summary = (
                assoc_sales.groupby(assoc_col)
                .agg(Net_Sales=("Net Amount", "sum"), Invoices=("Invoice No", "nunique"), Qty=("Qty", "sum"))
                .reset_index()
            )
            summary["Avg Bill"] = summary["Net_Sales"] / summary["Invoices"].replace(0, pd.NA)
            summary["UPT"] = summary["Qty"] / summary["Invoices"].replace(0, pd.NA)

            if "New/Repeat" in assoc_sales.columns and "Helper" in assoc_sales.columns:
                nr = (
                    assoc_sales.groupby([assoc_col, "New/Repeat"])["Helper"]
                    .nunique().unstack(fill_value=0).reset_index()
                )
                summary = summary.merge(nr, on=assoc_col, how="left")

            summary = summary.sort_values("Net_Sales", ascending=False).reset_index(drop=True)

            top_n = min(3, len(summary))
            st.markdown("##### 🏆 Top Performers")
            top_cols = st.columns(top_n)
            medals = ["🥇", "🥈", "🥉"]
            for i in range(top_n):
                row = summary.iloc[i]
                render_kpi(top_cols[i], medals[i], row[assoc_col], f"₹{row['Net_Sales']:,.0f}")

            st.write("")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="section-kicker">Net Sales by Associate</div>', unsafe_allow_html=True)
                fig_assoc_sales = px.bar(summary, x=assoc_col, y="Net_Sales", labels={"Net_Sales": "Net Sales (₹)"})
                fig_assoc_sales = highlight_top(fig_assoc_sales, summary["Net_Sales"].tolist())
                st.plotly_chart(
                    style_fig(fig_assoc_sales, show_legend=False, category_count=len(summary)),
                    use_container_width=True,
                )

            with col_b:
                st.markdown('<div class="section-kicker">Total Walk-ins by Associate</div>', unsafe_allow_html=True)
                walkin_matching_cols = [
                    c for c in filtered_walkins.columns if any(k in c.lower() for k in CANDIDATE_ASSOC_KEYWORDS)
                ]
                if not walkin_matching_cols:
                    st.info(
                        "Couldn't find a sales-associate column in the Walk-ins sheet. "
                        "Available columns are listed below."
                    )
                    st.write(list(walkins.columns))
                else:
                    walk_assoc_col = (
                        walkin_matching_cols[0] if len(walkin_matching_cols) == 1
                        else st.selectbox(
                            "Which Walk-ins column identifies the Sales Associate?",
                            walkin_matching_cols, key="assoc_walkin_col",
                        )
                    )
                    walkin_summary = (
                        filtered_walkins[
                            (filtered_walkins["New/Repeat"] == "New") &
                            (filtered_walkins["unique cust count WRT num&Nam"] == 1)
                        ]
                        .dropna(subset=[walk_assoc_col])
                        .groupby(walk_assoc_col)["Helper"]
                        .nunique()
                        .reset_index(name="Walk-ins")
                        .sort_values("Walk-ins", ascending=False)
                    )
                    if walkin_summary.empty:
                        st.info("No walk-in data for this selection.")
                    else:
                        fig_walk = px.bar(walkin_summary, x=walk_assoc_col, y="Walk-ins")
                        fig_walk = highlight_top(fig_walk, walkin_summary["Walk-ins"].tolist())
                        st.plotly_chart(
                            style_fig(fig_walk, show_legend=False, category_count=len(walkin_summary)),
                            use_container_width=True,
                        )

            st.markdown('<div class="section-kicker">Full Breakdown</div>', unsafe_allow_html=True)
            display_summary = summary.copy()
            display_summary["Net_Sales"] = display_summary["Net_Sales"].apply(lambda v: f"₹{v:,.0f}")
            display_summary["Avg Bill"] = display_summary["Avg Bill"].apply(lambda v: f"₹{v:,.0f}" if pd.notna(v) else "N/A")
            display_summary["UPT"] = display_summary["UPT"].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "N/A")
            display_summary = display_summary.rename(columns={"Net_Sales": "Net Sales"})
            st.dataframe(display_summary, use_container_width=True, hide_index=True)

# ---------------- TAB 5: RAW DATA ----------------
with tab_data:
    st.markdown('<div class="section-kicker">Sales Data</div>', unsafe_allow_html=True)
    st.dataframe(filtered_sales, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download filtered sales as CSV",
        data=filtered_sales.to_csv(index=False).encode("utf-8"),
        file_name="filtered_sales.csv",
        mime="text/csv",
    )

    st.markdown("---")

    st.markdown('<div class="section-kicker">Walk-in Data</div>', unsafe_allow_html=True)
    st.dataframe(filtered_walkins, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download filtered walk-ins as CSV",
        data=filtered_walkins.to_csv(index=False).encode("utf-8"),
        file_name="filtered_walkins.csv",
        mime="text/csv",
    )