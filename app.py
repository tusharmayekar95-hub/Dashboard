import re
import numpy as np
import pandas as pd
import streamlit as st
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
# ⚠️  COLUMN CONFIG — CHECK / EDIT THESE ⚠️
# =====================================================
SALES_DATE_COL = "Date"
SALES_STORE_COL = "Store"
SALES_CITY_COL = "City"
SALES_INVOICE_COL = "Invoice No"
SALES_NET_COL = "Net Amount"
SALES_QTY_COL = "Qty"
SALES_NAME_COL = "Customer Name"
SALES_PHONE_COL = "Mobile Number"

WALKIN_DATE_COL = "Date"
WALKIN_STORE_COL = "Store"
WALKIN_NAME_COL = "Customer Name"
WALKIN_PHONE_COL = "Mobile Number"

SALES_CATEGORY_COL = "Product Category"
SALES_COLLECTION_COL = "Collection"
SALES_PRICEBAND_COL = "Price band"

# =====================================================
# LIMECHAT CONFIGURATION
# =====================================================
LIMECHAT_SHEET_ID = "1Io2bxAJxWhm2KhdpQSrHE8WFAefbjrlmrIOlhwIGfc8"
LIMECHAT_GID = "0"

LIMECHAT_DATE_COL = "Date"
LIMECHAT_PHONE_COL = "Phone Number"
LIMECHAT_INBOX_COL = "Inbox Name"
LIMECHAT_AGENT_COL = "Current Agent"
LIMECHAT_CONTACT_BLOCKS_COL = "Contact Message Blocks"
LIMECHAT_MAIN_TAG_COL = "Main Tag"
LIMECHAT_TICKET_COL = "Ticket ID"  # auto-detected below; metrics using it degrade gracefully if missing

LIMECHAT_L1_COL = "Level 1 Tags (Main)"
LIMECHAT_L2_COL = "Level 2 Tags"
LIMECHAT_L3_COL = "Level 3 Tags"
LIMECHAT_LEAD_QUALITY_COL = "Custom Lead Quality"

LIMECHAT_JUNK_TAG = "junk"

ASSOC_KEYWORDS = [
    "associate", "executive", "salesperson", "sales person",
    "staff", "employee", "sold by", "sales rep", "advisor",
]
NAME_KEYWORDS = ["customer name", "cust name", "client name", " name"]
PHONE_KEYWORDS = ["mobile", "phone", "contact no", "contact number", "whatsapp"]

CR = 10_000_000  # 1 Crore

# =====================================================
# THEME
# =====================================================
NAVY = "#5C1A2B"
NAVY_SOFT = "#7A2E3F"
GOLD = "#C9A227"
GOLD_SOFT = "#E3C567"
GRAY = "#A08972"
GRAY_LIGHT = "#EDE3D8"
BG = "#FBF7F0"
CARD_BG = "#FFFFFF"
TEXT_MUTED = "#7A6A5D"
GOOD = "#2F7D4F"
BAD = "#B3413A"
FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

st.markdown(
    f"""
    <style>
        .stApp {{ background-color: {BG}; }}
        h1, h2, h3, h4 {{ font-family: {FONT}; color: {NAVY}; }}
        .exec-header {{
            background: linear-gradient(120deg, {NAVY} 0%, {NAVY_SOFT} 100%);
            border-radius: 16px; padding: 26px 30px; margin-bottom: 20px;
            box-shadow: 0 6px 18px rgba(16, 36, 62, 0.18);
        }}
        .exec-header h1 {{ color: white; margin: 0; font-size: 26px; font-weight: 700; }}
        .exec-header p {{ color: {GOLD_SOFT}; margin: 4px 0 0 0; font-size: 12.5px;
            letter-spacing: 0.5px; text-transform: uppercase; }}
        .filter-pills {{ margin-top: 12px; }}
        .filter-pill {{
            display: inline-block; background: rgba(255,255,255,0.10); color: white;
            border: 1px solid rgba(255,255,255,0.25); border-radius: 999px;
            padding: 4px 14px; font-size: 12px; margin: 2px 6px 2px 0; font-family: {FONT};
        }}
        .filter-pill b {{ color: {GOLD_SOFT}; }}
        .kpi-card {{
            background: {CARD_BG}; border-radius: 14px; padding: 14px 16px 12px 16px;
            box-shadow: 0 2px 10px rgba(16, 36, 62, 0.06); border-left: 4px solid {GOLD};
            min-height: 96px; display: flex; flex-direction: column; justify-content: center;
        }}
        .kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 22px rgba(16,36,62,0.14); }}
        .kpi-icon {{ font-size: 16px; margin-bottom: 2px; }}
        .kpi-label {{ font-family: {FONT}; font-size: 10.5px; font-weight: 600; letter-spacing: 0.5px;
            text-transform: uppercase; color: {TEXT_MUTED}; margin-bottom: 2px; }}
        .kpi-value {{ font-family: {FONT}; font-size: 20px; font-weight: 700; color: {NAVY}; line-height: 1.15; }}
        .kpi-delta {{ font-size: 11.5px; font-weight: 600; margin-top: 2px; }}
        .section-kicker {{ font-family: {FONT}; font-size: 12px; font-weight: 700; letter-spacing: 1px;
            text-transform: uppercase; color: {GOLD}; margin: 14px 0 4px 0; }}
        .stTabs [data-baseweb="tab"] {{ font-family: {FONT}; font-weight: 600; color: {TEXT_MUTED}; padding: 8px 16px; }}
        .stTabs [aria-selected="true"] {{ color: {NAVY} !important; border-bottom: 3px solid {GOLD} !important; }}
        section[data-testid="stSidebar"] {{ background-color: {NAVY}; }}
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{ color: #F3E9DD !important; }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important; border-radius: 10px !important; border: 1px solid {GRAY_LIGHT} !important; }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] * {{ color: {NAVY} !important; fill: {NAVY} !important; }}
        section[data-testid="stSidebar"] button {{
            background-color: rgba(255,255,255,0.08) !important; border: 1px solid {GOLD_SOFT} !important;
            color: {GOLD_SOFT} !important; border-radius: 10px !important; font-weight: 600 !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def render_kpi(col, icon, label, value, delta=None, delta_suffix="vs last year"):
    if delta is not None:
        if delta == "N/A":
            color = TEXT_MUTED
        elif str(delta).strip().startswith("-"):
            color = BAD
        else:
            color = GOOD
        delta_html = f'<div class="kpi-delta" style="color:{color}">{delta} {delta_suffix}</div>'
    else:
        delta_html = '<div class="kpi-delta">&nbsp;</div>'
    col.markdown(
        f"""<div class="kpi-card"><div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{delta_html}</div>""",
        unsafe_allow_html=True,
    )


def style_fig(fig, height=380, show_legend=None, category_count=0):
    fig.update_layout(
        template="plotly_white", font=dict(family=FONT, size=12, color=TEXT_MUTED),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10), height=height,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family=FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    if show_legend is not None:
        fig.update_layout(showlegend=show_legend)
    tickangle = -45 if category_count > 8 else 0
    fig.update_xaxes(showgrid=False, showline=True, linecolor=GRAY_LIGHT, tickfont=dict(size=11), tickangle=tickangle)
    fig.update_yaxes(showgrid=True, gridcolor="#EFEDE8", zeroline=False, tickfont=dict(size=11))
    if category_count > 8:
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=90))
    return fig


def highlight_top(fig, values, top_color=GOLD, base_color=NAVY_SOFT):
    if len(values) == 0:
        return fig
    peak = max(values)
    fig.update_traces(marker_color=[top_color if v == peak else base_color for v in values], marker_line_width=0)
    return fig


def to_cr(series):
    return series / CR


def fmt_money(v):
    return f"₹{v:,.0f}" if pd.notna(v) else "N/A"


def fmt_pct(v):
    return f"{v:.1f}%" if pd.notna(v) else "N/A"


# =====================================================
# SHEET IDs
# =====================================================
SALES_SHEET_ID = "18pTb4qEZe4HtioClGzUGtZwvfY7wVs-4yT-PSgZinps"
SALES_GID = "2003103498"
WALKINS_SHEET_ID = "1BT9XC4oIpgTotOGoVOSUTGoR5Je3gmePifYhRqgGSI4"
WALKINS_GID = "2003103498"
TARGETS_SHEET_ID = "1VIvFZkAezRoQzqny-EE8-QMbzLCBsWlOtPnIaFbpQAA"
TARGETS_GID = "0"


def _get_worksheet(spreadsheet, gid):
    try:
        return spreadsheet.get_worksheet_by_id(int(gid))
    except Exception:
        for ws in spreadsheet.worksheets():
            if str(ws.id) == str(gid):
                return ws
    return spreadsheet.sheet1


def _melt_targets(df):
    df = df.copy()
    store_col = df.columns[0]
    df = df.rename(columns={store_col: "Store"})
    df["Store"] = df["Store"].astype(str).str.strip()
    df = df[~df["Store"].str.upper().isin(["TOTAL", "GRAND TOTAL", ""])]
    month_cols = [c for c in df.columns if c != "Store" and str(c).strip().lower() != "total"]
    melted = df.melt(id_vars=["Store"], value_vars=month_cols, var_name="Month_Label", value_name="Target")
    melted["Month_Label"] = melted["Month_Label"].astype(str).str.strip()
    melted["Target"] = pd.to_numeric(melted["Target"], errors="coerce").fillna(0)
    melted["_ParsedMonth"] = pd.to_datetime(melted["Month_Label"], format="%b-%y", errors="coerce")
    melted = melted.dropna(subset=["_ParsedMonth"])
    melted["Month_Sort"] = melted["_ParsedMonth"].dt.strftime("%Y-%m")
    return melted[["Store", "Month_Label", "Month_Sort", "Target"]]


def _clean_team_targets(df):
    """Team Target tab: Store Name | Agent Name | Target | Month-YY.
    Returns None (not a warning) if the structure doesn't match — st.warning
    should never be called from inside a @st.cache_data function, so the
    caller decides whether/how to surface that."""
    df = df.copy()
    rename_map = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("store name", "store"):
            rename_map[c] = "Store"
        elif cl in ("agent name", "agent"):
            rename_map[c] = "Agent"
        elif cl == "target":
            rename_map[c] = "Target"
        elif cl in ("month-yy", "month", "month_label", "month-year"):
            rename_map[c] = "Month_Label"
    df = df.rename(columns=rename_map)
    required = {"Store", "Agent", "Target", "Month_Label"}
    if not required.issubset(df.columns):
        return None

    df["Store"] = df["Store"].astype(str).str.strip()
    df["Agent"] = df["Agent"].astype(str).str.strip()
    df["Month_Label"] = df["Month_Label"].astype(str).str.strip()
    df["Target"] = pd.to_numeric(df["Target"], errors="coerce").fillna(0)
    df = df[(df["Agent"] != "") & (df["Agent"].str.lower() != "nan")]
    df["_ParsedMonth"] = pd.to_datetime(df["Month_Label"], format="%b-%y", errors="coerce")
    df = df.dropna(subset=["_ParsedMonth"])
    df["Month_Sort"] = df["_ParsedMonth"].dt.strftime("%Y-%m")
    return df[["Store", "Agent", "Month_Label", "Month_Sort", "Target"]]


@st.cache_data(ttl=300)
def load_data():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )

    client = gspread.authorize(creds)

    sales_ss = client.open_by_key(SALES_SHEET_ID)
    walkins_ss = client.open_by_key(WALKINS_SHEET_ID)
    targets_ss = client.open_by_key(TARGETS_SHEET_ID)
    limechat_ss = client.open_by_key(LIMECHAT_SHEET_ID)

    sales_ws = _get_worksheet(sales_ss, SALES_GID)
    walkins_ws = _get_worksheet(walkins_ss, WALKINS_GID)
    targets_ws = _get_worksheet(targets_ss, TARGETS_GID)
    limechat_ws = _get_worksheet(limechat_ss, LIMECHAT_GID)

    sales = get_as_dataframe(sales_ws, evaluate_formulas=True)
    walkins = get_as_dataframe(walkins_ws, evaluate_formulas=True)
    targets_raw = get_as_dataframe(targets_ws, evaluate_formulas=True)
    limechat = get_as_dataframe(limechat_ws, evaluate_formulas=True)

    sales = sales.dropna(how="all").dropna(axis=1, how="all")
    walkins = walkins.dropna(how="all").dropna(axis=1, how="all")
    targets_raw = targets_raw.dropna(how="all").dropna(axis=1, how="all")
    limechat = limechat.dropna(how="all").dropna(axis=1, how="all")

    # ---- Sales dates ----
    sales[SALES_DATE_COL] = pd.to_datetime(sales[SALES_DATE_COL], errors="coerce")
    sales["Year"] = sales[SALES_DATE_COL].dt.year
    sales["Month"] = sales[SALES_DATE_COL].dt.month
    sales["Month_Label"] = sales[SALES_DATE_COL].dt.strftime("%b-%y")
    sales["Month_Sort"] = sales[SALES_DATE_COL].dt.strftime("%Y-%m")
    sales["Date_Str"] = sales[SALES_DATE_COL].dt.strftime("%d-%b-%Y")

    # ---- Walk-in dates ----
    walkins[WALKIN_DATE_COL] = pd.to_datetime(walkins[WALKIN_DATE_COL], errors="coerce")
    walkins["Year"] = walkins[WALKIN_DATE_COL].dt.year
    walkins["Month"] = walkins[WALKIN_DATE_COL].dt.month
    walkins["Month_Label"] = walkins[WALKIN_DATE_COL].dt.strftime("%b-%y")
    walkins["Month_Sort"] = walkins[WALKIN_DATE_COL].dt.strftime("%Y-%m")
    walkins["Date_Str"] = walkins[WALKIN_DATE_COL].dt.strftime("%d-%b-%Y")

    # ---- LimeChat dates ----
    limechat[LIMECHAT_DATE_COL] = pd.to_datetime(limechat[LIMECHAT_DATE_COL], errors="coerce")
    limechat["Year"] = limechat[LIMECHAT_DATE_COL].dt.year
    limechat["Month"] = limechat[LIMECHAT_DATE_COL].dt.month
    limechat["Month_Label"] = limechat[LIMECHAT_DATE_COL].dt.strftime("%b-%y")
    limechat["Month_Sort"] = limechat[LIMECHAT_DATE_COL].dt.strftime("%Y-%m")
    limechat["Date_Str"] = limechat[LIMECHAT_DATE_COL].dt.strftime("%d-%b-%Y")

    # ---- LimeChat phone normalization ----
    limechat["Customer_Key"] = limechat[LIMECHAT_PHONE_COL].apply(_normalize_phone)
    limechat["Phone_Status"] = np.where(limechat["Customer_Key"].str.len() >= 10, "Valid", "Invalid")

    # ---- LimeChat New/Repeat: identified by phone, computed within Inbox+Agent ----
    limechat["New/Repeat"] = None
    valid_phone_mask = limechat["Customer_Key"].ne("")
    first_month = (
        limechat[valid_phone_mask]
        .groupby([LIMECHAT_INBOX_COL, LIMECHAT_AGENT_COL, "Customer_Key"])["Month_Sort"]
        .min()
        .reset_index()
        .rename(columns={"Month_Sort": "First_Month"})
    )
    limechat = limechat.merge(first_month, on=[LIMECHAT_INBOX_COL, LIMECHAT_AGENT_COL, "Customer_Key"], how="left")
    limechat.loc[limechat["Month_Sort"] == limechat["First_Month"], "New/Repeat"] = "New"
    limechat.loc[limechat["Month_Sort"] > limechat["First_Month"], "New/Repeat"] = "Repeat"
    limechat.drop(columns=["First_Month"], inplace=True, errors="ignore")

    # ---- LimeChat interaction status (Contact Message Blocks >= 3) ----
    limechat[LIMECHAT_CONTACT_BLOCKS_COL] = pd.to_numeric(limechat[LIMECHAT_CONTACT_BLOCKS_COL], errors="coerce").fillna(0)
    limechat["Interaction_Status"] = np.where(limechat[LIMECHAT_CONTACT_BLOCKS_COL] >= 3, "Interacted", "Non Interacted")
    limechat["Main_Tag_Clean"] = limechat[LIMECHAT_MAIN_TAG_COL].astype(str).str.strip().str.lower()
    limechat["Is_Junk"] = limechat["Main_Tag_Clean"] == LIMECHAT_JUNK_TAG

    targets = _melt_targets(targets_raw)

    # ---- Team Target lives on its OWN tab, not the Store Targets pivot ----
    team_targets = pd.DataFrame(columns=["Store", "Agent", "Month_Label", "Month_Sort", "Target"])
    try:
        team_target_ws = targets_ss.worksheet("Team Target")
        team_targets_raw = get_as_dataframe(team_target_ws, evaluate_formulas=True)
        team_targets_raw = team_targets_raw.dropna(how="all").dropna(axis=1, how="all")
        cleaned = _clean_team_targets(team_targets_raw)
        if cleaned is not None:
            team_targets = cleaned
    except gspread.exceptions.WorksheetNotFound:
        pass

    return sales, walkins, targets, team_targets, limechat


def _autodetect_col(columns, keywords, exclude=None):
    exclude = exclude or []
    for c in columns:
        cl = str(c).lower()
        if any(ex in cl for ex in exclude):
            continue
        if any(k in cl for k in keywords):
            return c
    return None


def _resolve_col(df, configured_name, keywords, exclude=None):
    if configured_name in df.columns:
        return configured_name
    return _autodetect_col(df.columns, keywords, exclude)


def _find_column_ci(df, name):
    if name in df.columns:
        return name
    target = name.strip().lower()
    for c in df.columns:
        if str(c).strip().lower() == target:
            return c
    return None


def _normalize_phone(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\D", "", str(x))


def _normalize_name(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip().upper()


def build_customer_key(df, name_col, phone_col):
    if phone_col and phone_col in df.columns:
        phone = df[phone_col].apply(_normalize_phone)
    else:
        phone = pd.Series([""] * len(df), index=df.index)
    if name_col and name_col in df.columns:
        name = df[name_col].apply(_normalize_name)
    else:
        name = pd.Series([""] * len(df), index=df.index)

    key = phone.where(phone != "", "NAME::" + name)
    key = key.where(key != "NAME::", None)
    key = key.where(key.notna() & (key != ""), None)
    return key


def build_conversion_key(df, store_col, month_col, name_col, phone_col):
    """Sales Conversion key = StoreName|Month-YY|Number (falls back to Name if Number missing)."""
    store = df[store_col].astype(str).str.strip().str.upper()
    month = df[month_col].astype(str).str.strip()
    if phone_col and phone_col in df.columns:
        number = df[phone_col].apply(_normalize_phone)
    else:
        number = pd.Series([""] * len(df), index=df.index)
    if name_col and name_col in df.columns:
        name = df[name_col].apply(_normalize_name)
    else:
        name = pd.Series([""] * len(df), index=df.index)
    identifier = number.where(number != "", name)
    key = store + "|" + month + "|" + identifier
    key = key.where(identifier != "", None)
    return key


def conversion_metrics_by(walkins_df, sales_df, group_col):
    """Sales Conversion Count = unique Walk-in Conversion_Keys also found in Sales Conversion_Keys.
    Sales Conversion % = Sales Conversion Count / Total Unique Walkin."""
    if walkins_df.empty or group_col not in walkins_df.columns:
        return pd.DataFrame(columns=[group_col, "Total_Unique_Walkin", "Sales_Conversion_Count", "Conversion %"])
    sales_keys = set(sales_df["Conversion_Key"].dropna()) if not sales_df.empty else set()
    w = walkins_df.copy()
    w["_Matched"] = w["Conversion_Key"].isin(sales_keys)

    total = w.groupby(group_col)["Customer_Key"].nunique().rename("Total_Unique_Walkin")
    matched = w[w["_Matched"]].groupby(group_col)["Conversion_Key"].nunique().rename("Sales_Conversion_Count")
    out = pd.concat([total, matched], axis=1).reset_index()
    out["Total_Unique_Walkin"] = out["Total_Unique_Walkin"].fillna(0)
    out["Sales_Conversion_Count"] = out["Sales_Conversion_Count"].fillna(0)
    out["Conversion %"] = out.apply(
        lambda r: round(r["Sales_Conversion_Count"] / r["Total_Unique_Walkin"] * 100, 1) if r["Total_Unique_Walkin"] > 0 else None,
        axis=1,
    )
    return out


def tag_new_repeat(df, store_col, key_col, month_sort_col):
    df = df.copy()
    valid_mask = df[key_col].notna()
    if not valid_mask.any():
        df["New/Repeat"] = None
        return df
    first_month = (
        df[valid_mask]
        .groupby([store_col, key_col])[month_sort_col]
        .min()
        .rename("First_Month")
        .reset_index()
    )
    df = df.merge(first_month, on=[store_col, key_col], how="left")
    df["New/Repeat"] = None
    is_new = valid_mask & (df[month_sort_col] == df["First_Month"])
    is_repeat = valid_mask & (df[month_sort_col] > df["First_Month"])
    df.loc[is_new, "New/Repeat"] = "New"
    df.loc[is_repeat, "New/Repeat"] = "Repeat"
    df = df.drop(columns=["First_Month"])
    return df


def tag_sales_walkin_conversion(walkins_df, sales_df, walk_key_col, sales_key_col, walk_date_col, sales_date_col):
    wdf = walkins_df.copy()
    if sales_df.empty or wdf.empty:
        wdf["Sales_Walkin_Tag"] = "Not Converted"
        return wdf
    sdf = sales_df[[sales_key_col, sales_date_col]].dropna(subset=[sales_key_col]).copy()
    sdf["Day"] = sdf[sales_date_col].dt.date
    sdf = sdf[[sales_key_col, "Day"]].drop_duplicates()
    sdf["_matched"] = "Converted"
    sdf = sdf.rename(columns={sales_key_col: walk_key_col})

    wdf["Day"] = wdf[walk_date_col].dt.date
    wdf = wdf.merge(sdf, on=[walk_key_col, "Day"], how="left")
    wdf["Sales_Walkin_Tag"] = wdf["_matched"].fillna("Not Converted")
    wdf = wdf.drop(columns=["_matched", "Day"])
    return wdf


def tag_limechat_conversion(limechat_df, sales_df, sales_phone_col):
    """Marks a LimeChat row 'Converted' if that phone number (LimeChat's
    Phone Number, matched against Sales' Mobile Number) bought in Sales
    within the same month as the chat. Set-based lookup — O(n), not a
    per-row scan of the Sales table."""
    ldf = limechat_df.copy()
    if sales_df.empty or ldf.empty or not sales_phone_col or sales_phone_col not in sales_df.columns:
        ldf["Sales_Conversion"] = "Not Converted"
        return ldf
    sdf = sales_df[[sales_phone_col, "Month_Sort"]].copy()
    sdf["_Phone"] = sdf[sales_phone_col].apply(_normalize_phone)
    sdf = sdf[sdf["_Phone"] != ""]
    sales_lookup = set(zip(sdf["_Phone"], sdf["Month_Sort"]))
    ldf["Sales_Conversion"] = [
        "Converted" if (p, m) in sales_lookup else "Not Converted"
        for p, m in zip(ldf["Customer_Key"], ldf["Month_Sort"])
    ]
    return ldf


try:
    sales, walkins, targets, team_targets, limechat = load_data()
except Exception as e:
    st.error(
        f"Could not load data: {e}\n\n"
        "Check that:\n"
        "1. `.streamlit/secrets.toml` has a `[gcp_service_account]` section.\n"
        "2. All sheets (Sales, Walk-ins, Targets, LimeChat) are shared with the service account's email.\n"
        "3. The sheet IDs / gid values at the top of the file are correct."
    )
    st.stop()

# ---- resolve name / phone columns (configured name, else auto-detect) ----
sales_name_col = _resolve_col(sales, SALES_NAME_COL, NAME_KEYWORDS, exclude=["store", "associate"])
sales_phone_col = _resolve_col(sales, SALES_PHONE_COL, PHONE_KEYWORDS)
walkin_name_col = _resolve_col(walkins, WALKIN_NAME_COL, NAME_KEYWORDS, exclude=["store", "associate"])
walkin_phone_col = _resolve_col(walkins, WALKIN_PHONE_COL, PHONE_KEYWORDS)

category_col = _find_column_ci(sales, SALES_CATEGORY_COL)
collection_col = _find_column_ci(sales, SALES_COLLECTION_COL)
priceband_col = _find_column_ci(sales, SALES_PRICEBAND_COL)
ticket_col = _find_column_ci(limechat, LIMECHAT_TICKET_COL)  # None if the sheet doesn't have this column

missing_cols_warning = []
if not sales_name_col and not sales_phone_col:
    missing_cols_warning.append("Sales sheet: no Name/Mobile Number column found.")
if not walkin_name_col and not walkin_phone_col:
    missing_cols_warning.append("Walk-in sheet: no Name/Mobile Number column found.")
if not collection_col:
    missing_cols_warning.append(f"Sales sheet: no '{SALES_COLLECTION_COL}' column found — check SALES_COLLECTION_COL.")
if not priceband_col:
    missing_cols_warning.append(f"Sales sheet: no '{SALES_PRICEBAND_COL}' column found — check SALES_PRICEBAND_COL.")
if not category_col:
    missing_cols_warning.append(f"Sales sheet: no '{SALES_CATEGORY_COL}' column found — check SALES_CATEGORY_COL.")
if team_targets.empty:
    missing_cols_warning.append("Team Target tab: not found, empty, or missing Store/Agent/Target/Month-YY columns.")

# ---- build unique customer keys ----
sales["Customer_Key"] = build_customer_key(sales, sales_name_col, sales_phone_col)
walkins["Customer_Key"] = build_customer_key(walkins, walkin_name_col, walkin_phone_col)

# ---- Sales Conversion key: StoreName|Month-YY|Number (falls back to Name if Number missing) ----
sales["Conversion_Key"] = build_conversion_key(sales, SALES_STORE_COL, "Month_Label", sales_name_col, sales_phone_col)
walkins["Conversion_Key"] = build_conversion_key(walkins, WALKIN_STORE_COL, "Month_Label", walkin_name_col, walkin_phone_col)

# ---- New/Repeat tagging (MoM, per store, based on customer key) ----
sales = tag_new_repeat(sales, SALES_STORE_COL, "Customer_Key", "Month_Sort")
walkins = tag_new_repeat(walkins, WALKIN_STORE_COL, "Customer_Key", "Month_Sort")

# ---- Sales_Walkin Tag: walk-in converted if matched in Sales same day ----
walkins = tag_sales_walkin_conversion(
    walkins, sales, "Customer_Key", "Customer_Key", WALKIN_DATE_COL, SALES_DATE_COL
)

# ---- LimeChat → Sales conversion: LimeChat Phone Number vs Sales Mobile Number, same month ----
limechat = tag_limechat_conversion(limechat, sales, sales_phone_col)

sales_assoc_candidates = [c for c in sales.columns if any(k in str(c).lower() for k in ASSOC_KEYWORDS)]
walkin_assoc_candidates = [c for c in walkins.columns if any(k in str(c).lower() for k in ASSOC_KEYWORDS)]

# =====================================================
# SIDEBAR — FILTERS
# =====================================================
st.sidebar.markdown("## 💎 Tyaani Analytics")
st.sidebar.caption("Filter the dashboard")

if missing_cols_warning:
    for w in missing_cols_warning:
        st.sidebar.warning(f"⚠️ {w}")

all_stores = sorted(sales[SALES_STORE_COL].dropna().unique().tolist())
selected_stores = st.sidebar.multiselect("Store", all_stores, default=[], placeholder="All stores")

store_scoped_sales = sales[sales[SALES_STORE_COL].isin(selected_stores)] if selected_stores else sales
month_lookup = (
    store_scoped_sales[["Month_Label", "Month_Sort"]].dropna().drop_duplicates().sort_values("Month_Sort")
)
all_months = month_lookup["Month_Label"].tolist()
selected_months = st.sidebar.multiselect("Month (Month-YY)", all_months, default=[], placeholder="All months")

month_scoped_sales = store_scoped_sales[store_scoped_sales["Month_Label"].isin(selected_months)] if selected_months else store_scoped_sales
date_lookup = (
    month_scoped_sales[[SALES_DATE_COL, "Date_Str"]].dropna().drop_duplicates().sort_values(SALES_DATE_COL)
)
all_dates = date_lookup["Date_Str"].tolist()
selected_dates = st.sidebar.multiselect("Date", all_dates, default=[], placeholder="All dates")

date_scoped_sales = month_scoped_sales[month_scoped_sales["Date_Str"].isin(selected_dates)] if selected_dates else month_scoped_sales

if collection_col:
    collection_options = sorted(date_scoped_sales[collection_col].dropna().unique().tolist())
    selected_collections = st.sidebar.multiselect("Collection", collection_options, default=[], placeholder="All collections")
else:
    selected_collections = []

collection_scoped_sales = (
    date_scoped_sales[date_scoped_sales[collection_col].isin(selected_collections)]
    if (collection_col and selected_collections) else date_scoped_sales
)

if priceband_col:
    priceband_options = sorted(collection_scoped_sales[priceband_col].dropna().unique().tolist())
    selected_pricebands = st.sidebar.multiselect("Price Band", priceband_options, default=[], placeholder="All price bands")
else:
    selected_pricebands = []

all_limechat_inboxes = sorted(limechat[LIMECHAT_INBOX_COL].dropna().unique().tolist())
selected_limechat_inboxes = st.sidebar.multiselect("LimeChat Inbox", all_limechat_inboxes, default=[], placeholder="All Inboxes")

all_limechat_agents = sorted(limechat[LIMECHAT_AGENT_COL].dropna().unique().tolist())
selected_limechat_agents = st.sidebar.multiselect("LimeChat Agent", all_limechat_agents, default=[], placeholder="All Agents")

store_display = ", ".join(selected_stores) if selected_stores else "All"
month_display = ", ".join(selected_months) if selected_months else "All"
date_display = ", ".join(selected_dates) if selected_dates else "All"
collection_display = ", ".join(selected_collections) if selected_collections else "All"
priceband_display = ", ".join(selected_pricebands) if selected_pricebands else "All"

st.sidebar.markdown("---")
st.sidebar.caption(f"Sales rows loaded: {len(sales):,}")
st.sidebar.caption(f"Walk-in rows loaded: {len(walkins):,}")
st.sidebar.caption(f"Target rows loaded: {len(targets):,}")
st.sidebar.caption(f"Team Target rows loaded: {len(team_targets):,}")
st.sidebar.caption(f"LimeChat rows loaded: {len(limechat):,}")
st.sidebar.caption("Data auto-refreshes every 5 min.")
if st.sidebar.button("🔄 Refresh data now"):
    st.cache_data.clear()
    st.rerun()


def apply_filters(df, store_col, date_str_col="Date_Str"):
    out = df.copy()
    if selected_stores:
        out = out[out[store_col].isin(selected_stores)]
    if selected_months:
        out = out[out["Month_Label"].isin(selected_months)]
    if selected_dates:
        out = out[out[date_str_col].isin(selected_dates)]
    if collection_col and collection_col in out.columns and selected_collections:
        out = out[out[collection_col].isin(selected_collections)]
    if priceband_col and priceband_col in out.columns and selected_pricebands:
        out = out[out[priceband_col].isin(selected_pricebands)]
    return out


filtered_sales = apply_filters(sales, SALES_STORE_COL)
filtered_walkins = apply_filters(walkins, WALKIN_STORE_COL)

# ---- LimeChat filters ----
filtered_limechat = limechat.copy()
if selected_months:
    filtered_limechat = filtered_limechat[filtered_limechat["Month_Label"].isin(selected_months)]
if selected_dates:
    filtered_limechat = filtered_limechat[filtered_limechat["Date_Str"].isin(selected_dates)]
if selected_limechat_inboxes:
    filtered_limechat = filtered_limechat[filtered_limechat[LIMECHAT_INBOX_COL].isin(selected_limechat_inboxes)]
if selected_limechat_agents:
    filtered_limechat = filtered_limechat[filtered_limechat[LIMECHAT_AGENT_COL].isin(selected_limechat_agents)]

# =====================================================
# GROUP-LEVEL METRIC BUILDERS
# =====================================================
def sales_metrics_by(df, group_col, targets_df=None, target_group_col=None):
    if df.empty or group_col not in df.columns:
        return pd.DataFrame()

    out = df.groupby(group_col).agg(
        Revenue=(SALES_NET_COL, "sum"),
        Unique_Invoice=(SALES_INVOICE_COL, "nunique"),
        Qty=(SALES_QTY_COL, "sum"),
    ).reset_index()
    out["ATV"] = out["Revenue"] / out["Unique_Invoice"].replace(0, np.nan)
    out["UPT"] = out["Qty"] / out["Unique_Invoice"].replace(0, np.nan)

    uc = df.groupby(group_col)["Customer_Key"].nunique().rename("Unique_Customer")
    out = out.merge(uc, on=group_col, how="left")

    nr = df.dropna(subset=["New/Repeat"]).groupby([group_col, "New/Repeat"])["Customer_Key"].nunique().unstack(fill_value=0)
    for c in ["New", "Repeat"]:
        if c not in nr.columns:
            nr[c] = 0
    nr = nr.rename(columns={"New": "New_Customer_Count", "Repeat": "Repeat_Customer_Count"}).reset_index()
    out = out.merge(nr, on=group_col, how="left")
    out["New_Customer_Count"] = out["New_Customer_Count"].fillna(0)
    out["Repeat_Customer_Count"] = out["Repeat_Customer_Count"].fillna(0)
    tot_nr = out["New_Customer_Count"] + out["Repeat_Customer_Count"]
    out["New %"] = (out["New_Customer_Count"] / tot_nr.replace(0, np.nan) * 100).round(1)
    out["Repeat %"] = (out["Repeat_Customer_Count"] / tot_nr.replace(0, np.nan) * 100).round(1)

    rev_nr = df.dropna(subset=["New/Repeat"]).groupby([group_col, "New/Repeat"])[SALES_NET_COL].sum().unstack(fill_value=0)
    for c in ["New", "Repeat"]:
        if c not in rev_nr.columns:
            rev_nr[c] = 0
    rev_nr = rev_nr.rename(columns={"New": "Revenue_From_New", "Repeat": "Revenue_From_Repeat"}).reset_index()
    out = out.merge(rev_nr, on=group_col, how="left")

    tcol = target_group_col or group_col
    if targets_df is not None and not targets_df.empty and tcol in targets_df.columns:
        tgt = targets_df.groupby(tcol)["Target"].sum().reset_index().rename(columns={tcol: group_col})
        out = out.merge(tgt, on=group_col, how="left")
    else:
        out["Target"] = 0
    out["Target"] = out["Target"].fillna(0)
    out["Ach %"] = out.apply(lambda r: round(r["Revenue"] / r["Target"] * 100, 1) if r["Target"] > 0 else None, axis=1)
    out["Shortfall"] = out["Target"] - out["Revenue"]

    return out


def walkin_metrics_by(df, group_col):
    if df.empty or group_col not in df.columns:
        return pd.DataFrame()
    tot = df.groupby(group_col)["Customer_Key"].nunique().rename("Total_Unique_Walkin").reset_index()
    nr = df.dropna(subset=["New/Repeat"]).groupby([group_col, "New/Repeat"])["Customer_Key"].nunique().unstack(fill_value=0)
    for c in ["New", "Repeat"]:
        if c not in nr.columns:
            nr[c] = 0
    nr = nr.rename(columns={"New": "New_Walkin", "Repeat": "Repeat_Walkin"}).reset_index()
    out = tot.merge(nr, on=group_col, how="left")
    out["New_Walkin"] = out["New_Walkin"].fillna(0)
    out["Repeat_Walkin"] = out["Repeat_Walkin"].fillna(0)
    tot_nr = out["New_Walkin"] + out["Repeat_Walkin"]
    out["New Walkin %"] = (out["New_Walkin"] / tot_nr.replace(0, np.nan) * 100).round(1)
    out["Repeat Walkin %"] = (out["Repeat_Walkin"] / tot_nr.replace(0, np.nan) * 100).round(1)
    return out


def build_store_table(sales_df, walkins_df, targets_df):
    s = sales_metrics_by(sales_df, SALES_STORE_COL, targets_df)
    w = walkin_metrics_by(walkins_df, WALKIN_STORE_COL)
    if s.empty:
        return s
    if not w.empty:
        w = w.rename(columns={WALKIN_STORE_COL: SALES_STORE_COL})[[SALES_STORE_COL, "Total_Unique_Walkin"]]
        s = s.merge(w, on=SALES_STORE_COL, how="left")
    else:
        s["Total_Unique_Walkin"] = 0
    s["Total_Unique_Walkin"] = s["Total_Unique_Walkin"].fillna(0)

    # ---- Conversion %: StoreName|Month-YY|Number-or-Name key matched between Walk-in and Sales ----
    conv = conversion_metrics_by(walkins_df, sales_df, WALKIN_STORE_COL)
    if not conv.empty:
        conv = conv.rename(columns={WALKIN_STORE_COL: SALES_STORE_COL})[[SALES_STORE_COL, "Conversion %"]]
        s = s.drop(columns=["Conversion %"], errors="ignore").merge(conv, on=SALES_STORE_COL, how="left")
    else:
        s["Conversion %"] = None

    return s.sort_values("Revenue", ascending=False)


def format_sales_table(df, group_col):
    d = df.copy()
    d = d.rename(columns={
        group_col: group_col, "Revenue": "Revenue", "Unique_Invoice": "Unique Invoice",
        "Unique_Customer": "Unique Customer", "New_Customer_Count": "New Customer Count",
        "Repeat_Customer_Count": "Repeat Customer Count", "Revenue_From_New": "Revenue From New Customer",
        "Revenue_From_Repeat": "Revenue From Repeat Customer", "Total_Unique_Walkin": "Total Walkin",
    })
    for col in ["Revenue", "Target", "Shortfall", "Revenue From New Customer", "Revenue From Repeat Customer"]:
        if col in d.columns:
            d[col] = d[col].apply(fmt_money)
    for col in ["Ach %", "New %", "Repeat %", "Conversion %"]:
        if col in d.columns:
            d[col] = d[col].apply(fmt_pct)
    if "ATV" in d.columns:
        d["ATV"] = d["ATV"].apply(lambda v: f"₹{v:,.0f}" if pd.notna(v) else "N/A")
    if "UPT" in d.columns:
        d["UPT"] = d["UPT"].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "N/A")
    cols_order = [c for c in [
        group_col, "Target", "Revenue", "Ach %", "Shortfall", "Unique Invoice", "ATV", "UPT",
        "Total Walkin", "Unique Customer", "Conversion %", "New Customer Count", "Repeat Customer Count",
        "New %", "Repeat %", "Revenue From New Customer", "Revenue From Repeat Customer",
    ] if c in d.columns]
    return d[cols_order]


def format_walkin_table(df, group_col):
    d = df.copy()
    d = d.rename(columns={"Total_Unique_Walkin": "Total Unique Walkin", "New_Walkin": "New Walkin",
                           "Repeat_Walkin": "Repeat Walkin"})
    cols_order = [c for c in [group_col, "Total Unique Walkin", "New Walkin", "Repeat Walkin",
                               "New Walkin %", "Repeat Walkin %"] if c in d.columns]
    return d[cols_order]


def product_metrics_by(df, group_col):
    if df.empty or not group_col or group_col not in df.columns:
        return pd.DataFrame()

    scoped = df.dropna(subset=[group_col])
    if scoped.empty:
        return pd.DataFrame()

    out = scoped.groupby(group_col).agg(
        Revenue=(SALES_NET_COL, "sum"),
        Unique_Invoice=(SALES_INVOICE_COL, "nunique"),
        Qty=(SALES_QTY_COL, "sum"),
    ).reset_index()
    out["ATV"] = out["Revenue"] / out["Unique_Invoice"].replace(0, np.nan)
    out["UPT"] = out["Qty"] / out["Unique_Invoice"].replace(0, np.nan)

    uc = scoped.groupby(group_col)["Customer_Key"].nunique().rename("Unique_Customer")
    out = out.merge(uc, on=group_col, how="left")

    nr = scoped.dropna(subset=["New/Repeat"]).groupby([group_col, "New/Repeat"])["Customer_Key"].nunique().unstack(fill_value=0)
    for c in ["New", "Repeat"]:
        if c not in nr.columns:
            nr[c] = 0
    nr = nr.rename(columns={"New": "New_Customer_Count", "Repeat": "Repeat_Customer_Count"}).reset_index()
    out = out.merge(nr, on=group_col, how="left")
    out["New_Customer_Count"] = out["New_Customer_Count"].fillna(0)
    out["Repeat_Customer_Count"] = out["Repeat_Customer_Count"].fillna(0)
    tot_nr = out["New_Customer_Count"] + out["Repeat_Customer_Count"]
    out["New %"] = (out["New_Customer_Count"] / tot_nr.replace(0, np.nan) * 100).round(1)
    out["Repeat %"] = (out["Repeat_Customer_Count"] / tot_nr.replace(0, np.nan) * 100).round(1)

    total_rev = out["Revenue"].sum()
    out["Revenue Share %"] = (out["Revenue"] / total_rev * 100).round(1) if total_rev > 0 else None

    return out.sort_values("Revenue", ascending=False)


def format_product_table(df, group_col):
    d = df.copy()
    d = d.rename(columns={
        "Unique_Invoice": "Unique Invoice", "Unique_Customer": "Unique Customer",
        "New_Customer_Count": "New Customer Count", "Repeat_Customer_Count": "Repeat Customer Count",
        "Qty": "Qty Sold",
    })
    d["Revenue"] = d["Revenue"].apply(fmt_money)
    d["ATV"] = d["ATV"].apply(lambda v: f"₹{v:,.0f}" if pd.notna(v) else "N/A")
    d["UPT"] = d["UPT"].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "N/A")
    for col in ["New %", "Repeat %", "Revenue Share %"]:
        if col in d.columns:
            d[col] = d[col].apply(fmt_pct)
    cols_order = [c for c in [
        group_col, "Revenue", "Revenue Share %", "Unique Invoice", "ATV", "UPT", "Qty Sold",
        "Unique Customer", "New Customer Count", "Repeat Customer Count", "New %", "Repeat %",
    ] if c in d.columns]
    return d[cols_order]


def crosstab_counts(df, group_col, split_col, id_col, new_label="New", repeat_label="Repeat"):
    """Fast, correct replacement for the old per-row lambda pattern: one
    vectorized groupby+unstack instead of scanning the whole frame per group."""
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, new_label, repeat_label])
    ct = df.dropna(subset=[split_col]).groupby([group_col, split_col])[id_col].nunique().unstack(fill_value=0)
    for c in [new_label, repeat_label]:
        if c not in ct.columns:
            ct[c] = 0
    return ct.reset_index()[[group_col, new_label, repeat_label]]


# =====================================================
# GLOBAL KPI CALCULATIONS (current filter scope)
# =====================================================
relevant_months = sorted(filtered_sales["Month_Label"].dropna().unique().tolist()) or all_months
target_scope = targets.copy()

if selected_stores:
    target_scope = target_scope[target_scope["Store"].isin(selected_stores)]
if relevant_months:
    target_scope = target_scope[target_scope["Month_Label"].isin(relevant_months)]

period_target = target_scope["Target"].sum()
net_sales = filtered_sales[SALES_NET_COL].sum()
total_invoices = filtered_sales[SALES_INVOICE_COL].nunique()
atv = net_sales / total_invoices if total_invoices > 0 else 0
upt = filtered_sales[SALES_QTY_COL].sum() / total_invoices if total_invoices > 0 else 0

if period_target > 0:
    achievement_display = fmt_pct(net_sales / period_target * 100)
    surplus = net_sales - period_target
    shortfall_display = f"{'+₹' if surplus >= 0 else '-₹'}{abs(surplus):,.0f}"
    target_display = fmt_money(period_target)
else:
    achievement_display, shortfall_display, target_display = "N/A", "N/A", "N/A"

unique_customers = filtered_sales["Customer_Key"].nunique()
total_walkins_kpi = filtered_walkins["Customer_Key"].nunique()

# ---- Sales Conversion Count/%: StoreName|Month-YY|Number-or-Name key matched between Walk-in and Sales ----
_sales_conversion_keys_kpi = set(filtered_sales["Conversion_Key"].dropna())
sales_conversion_count = filtered_walkins[
    filtered_walkins["Conversion_Key"].isin(_sales_conversion_keys_kpi)
]["Conversion_Key"].nunique()
conversion_pct = sales_conversion_count / total_walkins_kpi * 100 if total_walkins_kpi > 0 else 0

new_customer_count = filtered_sales[filtered_sales["New/Repeat"] == "New"]["Customer_Key"].nunique()
repeat_customer_count = filtered_sales[filtered_sales["New/Repeat"] == "Repeat"]["Customer_Key"].nunique()
tot_nr = new_customer_count + repeat_customer_count
new_pct = new_customer_count / tot_nr * 100 if tot_nr > 0 else 0
repeat_pct = repeat_customer_count / tot_nr * 100 if tot_nr > 0 else 0

revenue_from_new = filtered_sales[filtered_sales["New/Repeat"] == "New"][SALES_NET_COL].sum()
revenue_from_repeat = filtered_sales[filtered_sales["New/Repeat"] == "Repeat"][SALES_NET_COL].sum()

converted_walkins = filtered_walkins[filtered_walkins["Sales_Walkin_Tag"] == "Converted"]["Customer_Key"].nunique()

walkin_new = filtered_walkins[filtered_walkins["New/Repeat"] == "New"]["Customer_Key"].nunique()
walkin_repeat = filtered_walkins[filtered_walkins["New/Repeat"] == "Repeat"]["Customer_Key"].nunique()
walkin_tot_nr = walkin_new + walkin_repeat
walkin_new_pct = walkin_new / walkin_tot_nr * 100 if walkin_tot_nr > 0 else 0
walkin_repeat_pct = walkin_repeat / walkin_tot_nr * 100 if walkin_tot_nr > 0 else 0

yoy_display = "N/A"
if len(selected_months) == 1:
    cur = pd.to_datetime(selected_months[0], format="%b-%y")
    prior_df = sales[(sales["Month"] == cur.month) & (sales["Year"] == cur.year - 1)]
    if selected_stores:
        prior_df = prior_df[prior_df[SALES_STORE_COL].isin(selected_stores)]
    last_year_sales = prior_df[SALES_NET_COL].sum()
    if last_year_sales > 0:
        yoy_display = f"{(net_sales - last_year_sales) / last_year_sales * 100:+.1f}%"

# ---- LimeChat KPIs ----
limechat_valid = filtered_limechat[filtered_limechat["Customer_Key"] != ""]
limechat_unique_customers = limechat_valid["Customer_Key"].nunique()
limechat_new_customers = limechat_valid[limechat_valid["New/Repeat"] == "New"]["Customer_Key"].nunique()
limechat_repeat_customers = limechat_valid[limechat_valid["New/Repeat"] == "Repeat"]["Customer_Key"].nunique()
limechat_total_nr = limechat_new_customers + limechat_repeat_customers
limechat_new_pct = limechat_new_customers / limechat_total_nr * 100 if limechat_total_nr > 0 else 0
limechat_repeat_pct = limechat_repeat_customers / limechat_total_nr * 100 if limechat_total_nr > 0 else 0

limechat_valid_phone_count = filtered_limechat[filtered_limechat["Phone_Status"] == "Valid"]["Customer_Key"].nunique()
limechat_invalid_phone_count = filtered_limechat[filtered_limechat["Phone_Status"] == "Invalid"].shape[0]

limechat_non_junk = filtered_limechat[~filtered_limechat["Is_Junk"]]
limechat_interacted = limechat_non_junk[limechat_non_junk["Interaction_Status"] == "Interacted"]["Customer_Key"].nunique()
limechat_non_interacted = limechat_non_junk[limechat_non_junk["Interaction_Status"] == "Non Interacted"]["Customer_Key"].nunique()
limechat_interaction_total = limechat_interacted + limechat_non_interacted
limechat_interacted_pct = limechat_interacted / limechat_interaction_total * 100 if limechat_interaction_total > 0 else 0
limechat_non_interacted_pct = limechat_non_interacted / limechat_interaction_total * 100 if limechat_interaction_total > 0 else 0

# ---- LimeChat → Sales conversion (by phone number, same month) ----
limechat_converted = filtered_limechat[filtered_limechat["Sales_Conversion"] == "Converted"]["Customer_Key"].nunique()
limechat_conversion_pct = limechat_converted / limechat_unique_customers * 100 if limechat_unique_customers > 0 else 0

# =====================================================
# HEADER
# =====================================================
st.markdown(
    f"""
    <div class="exec-header">
        <h1>💎 Tyaani Jewellery — Executive Dashboard</h1>
        <p>Performance overview across stores, months & sales associates</p>
        <div class="filter-pills">
            <span class="filter-pill">Store: <b>{store_display}</b></span>
            <span class="filter-pill">Month: <b>{month_display}</b></span>
            <span class="filter-pill">Date: <b>{date_display}</b></span>
            <span class="filter-pill">Collection: <b>{collection_display}</b></span>
            <span class="filter-pill">Price Band: <b>{priceband_display}</b></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# KPI CARDS
# =====================================================
st.markdown('<div class="section-kicker">Sales Key Metrics</div>', unsafe_allow_html=True)
r1 = st.columns(4)
render_kpi(r1[0], "🎯", "Target", target_display)
render_kpi(r1[1], "💎", "Revenue", fmt_money(net_sales), yoy_display)
render_kpi(r1[2], "🏆", "Ach %", achievement_display)
render_kpi(r1[3], "⚖️", "Shortfall", shortfall_display)

r2 = st.columns(4)
render_kpi(r2[0], "🧾", "Unique Invoice", f"{total_invoices:,}")
render_kpi(r2[1], "💳", "ATV", fmt_money(atv))
render_kpi(r2[2], "📦", "UPT", f"{upt:.2f}")
render_kpi(r2[3], "🔄", "Sales_Walkin Tag (Converted)", f"{converted_walkins:,}")

r3 = st.columns(4)
render_kpi(r3[0], "🚶", "Total Walkin", f"{total_walkins_kpi:,}")
render_kpi(r3[1], "👤", "Unique Customer", f"{unique_customers:,}")
render_kpi(r3[2], "🎯", "Conversion %", fmt_pct(conversion_pct))
render_kpi(r3[3], "🆕", "New %", fmt_pct(new_pct))

r4 = st.columns(4)
render_kpi(r4[0], "🆕", "New Customer Count", f"{new_customer_count:,}")
render_kpi(r4[1], "🔁", "Repeat Customer Count", f"{repeat_customer_count:,}")
render_kpi(r4[2], "🔁", "Repeat %", fmt_pct(repeat_pct))
render_kpi(r4[3], "💰", "Revenue From New", fmt_money(revenue_from_new))

r5 = st.columns(4)
render_kpi(r5[0], "💰", "Revenue From Repeat", fmt_money(revenue_from_repeat))

st.markdown('<div class="section-kicker">Walkin Key Metrics</div>', unsafe_allow_html=True)
w1 = st.columns(4)
render_kpi(w1[0], "🚶", "Total Unique Walkin", f"{total_walkins_kpi:,}")
render_kpi(w1[1], "🆕", "New Walkin", f"{walkin_new:,}")
render_kpi(w1[2], "🔁", "Repeat Walkin", f"{walkin_repeat:,}")
render_kpi(w1[3], "📊", "New Walkin %", fmt_pct(walkin_new_pct))
w2 = st.columns(4)
render_kpi(w2[0], "📊", "Repeat Walkin %", fmt_pct(walkin_repeat_pct))

st.markdown("---")

# =====================================================
# TABS
# =====================================================
tab_trends, tab_sales, tab_walkin, tab_limechat, tab_product, tab_yoy, tab_raw = st.tabs(
    [
        "📈 Trends Charts",
        "🏬 Sales Tab",
        "🚶 Walkin Tab",
        "💬 LimeChat Tab",
        "🏷️ Product Mix",
        "📆 Same Month Vs Last Yr",
        "📄 Raw Data"
    ]
)

# ---------------- TRENDS CHARTS ----------------
# Kept lean: only the two core trend lines. The "New vs Repeat" 3-key
# groupby was dropped per request — it's the heaviest of the three and
# least essential; New/Repeat splits are already available store-wise
# and associate-wise in the Sales/Walkin tabs.
with tab_trends:
    trend_sales = sales[sales[SALES_STORE_COL].isin(selected_stores)] if selected_stores else sales
    trend_walk = walkins[walkins[WALKIN_STORE_COL].isin(selected_stores)] if selected_stores else walkins

    st.markdown('<div class="section-kicker">Sales Trend</div>', unsafe_allow_html=True)
    m_sales = trend_sales.groupby(["Month_Sort", "Month_Label"], as_index=False)[SALES_NET_COL].sum().sort_values("Month_Sort")
    m_sales["Net Sales (₹ Cr)"] = to_cr(m_sales[SALES_NET_COL])
    if not m_sales.empty:
        fig = px.area(m_sales, x="Month_Label", y="Net Sales (₹ Cr)", markers=True)
        fig.update_traces(line_color=NAVY, fillcolor="rgba(92,26,43,0.10)", marker=dict(color=GOLD, size=7))
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(style_fig(fig, show_legend=False, category_count=len(m_sales)), use_container_width=True)
    else:
        st.info("No sales data for this selection.")

    st.markdown('<div class="section-kicker">Walkin Trend</div>', unsafe_allow_html=True)
    m_walk = trend_walk.groupby(["Month_Sort", "Month_Label"], as_index=False)["Customer_Key"].nunique().sort_values("Month_Sort").rename(columns={"Customer_Key": "Unique Walk-ins"})
    if not m_walk.empty:
        fig2 = px.area(m_walk, x="Month_Label", y="Unique Walk-ins", markers=True)
        fig2.update_traces(line_color=NAVY, fillcolor="rgba(92,26,43,0.10)", marker=dict(color=GOLD, size=7))
        fig2.update_layout(hovermode="x unified")
        st.plotly_chart(style_fig(fig2, show_legend=False, category_count=len(m_walk)), use_container_width=True)
    else:
        st.info("No walk-in data for this selection.")

# ---------------- SALES TAB ----------------
with tab_sales:
    st.markdown('<div class="section-kicker">Store Wise Table Format</div>', unsafe_allow_html=True)
    store_table = build_store_table(filtered_sales, filtered_walkins, target_scope)
    if store_table.empty:
        st.info("No sales data for this selection.")
    else:
        st.dataframe(format_sales_table(store_table, SALES_STORE_COL), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-kicker">Sales Associate Table Format</div>', unsafe_allow_html=True)
    if not sales_assoc_candidates:
        st.warning("Couldn't find a Sales Associate column. Columns available: " + ", ".join(map(str, sales.columns)))
    else:
        assoc_col = (
            sales_assoc_candidates[0] if len(sales_assoc_candidates) == 1
            else st.selectbox("Sales Associate column", sales_assoc_candidates, key="sales_assoc_pick")
        )
        assoc_targets = team_targets.rename(columns={"Agent": assoc_col})
        assoc_scope = assoc_targets.copy()
        if selected_stores:
            assoc_scope = assoc_scope[assoc_scope["Store"].isin(selected_stores)]
        if relevant_months:
            assoc_scope = assoc_scope[assoc_scope["Month_Label"].isin(relevant_months)]
        assoc_table = sales_metrics_by(filtered_sales.dropna(subset=[assoc_col]), assoc_col, assoc_scope, target_group_col=assoc_col)
        if not assoc_table.empty:
            walk_assoc_col = (
                walkin_assoc_candidates[0] if len(walkin_assoc_candidates) == 1
                else (st.selectbox("Walk-in Associate column", walkin_assoc_candidates, key="walk_assoc_pick") if walkin_assoc_candidates else None)
            )
            if walk_assoc_col:
                w_assoc = walkin_metrics_by(filtered_walkins.dropna(subset=[walk_assoc_col]), walk_assoc_col)
                w_assoc = w_assoc.rename(columns={walk_assoc_col: assoc_col})[[assoc_col, "Total_Unique_Walkin"]] if not w_assoc.empty else pd.DataFrame(columns=[assoc_col, "Total_Unique_Walkin"])
                assoc_table = assoc_table.merge(w_assoc, on=assoc_col, how="left")
                assoc_table["Total_Unique_Walkin"] = assoc_table["Total_Unique_Walkin"].fillna(0)

                # ---- Conversion %: StoreName|Month-YY|Number-or-Name key matched between Walk-in and Sales ----
                conv_assoc = conversion_metrics_by(
                    filtered_walkins.dropna(subset=[walk_assoc_col]), filtered_sales, walk_assoc_col
                )
                if not conv_assoc.empty:
                    conv_assoc = conv_assoc.rename(columns={walk_assoc_col: assoc_col})[[assoc_col, "Conversion %"]]
                    assoc_table = assoc_table.drop(columns=["Conversion %"], errors="ignore").merge(
                        conv_assoc, on=assoc_col, how="left"
                    )
                else:
                    assoc_table["Conversion %"] = None
            assoc_table = assoc_table.sort_values("Revenue", ascending=False)
            st.dataframe(format_sales_table(assoc_table, assoc_col), use_container_width=True, hide_index=True)
        else:
            st.info("No associate-level sales data for this selection.")

# ---------------- WALKIN TAB ----------------
with tab_walkin:
    st.markdown('<div class="section-kicker">Store Wise Table Format</div>', unsafe_allow_html=True)
    w_store_table = walkin_metrics_by(filtered_walkins, WALKIN_STORE_COL)
    if w_store_table.empty:
        st.info("No walk-in data for this selection.")
    else:
        st.dataframe(format_walkin_table(w_store_table.sort_values("Total_Unique_Walkin", ascending=False), WALKIN_STORE_COL),
                     use_container_width=True, hide_index=True)

    st.markdown('<div class="section-kicker">Sales Associate Table Format</div>', unsafe_allow_html=True)
    if not walkin_assoc_candidates:
        st.warning("Couldn't find a Sales Associate column in Walk-ins. Columns available: " + ", ".join(map(str, walkins.columns)))
    else:
        w_assoc_col = (
            walkin_assoc_candidates[0] if len(walkin_assoc_candidates) == 1
            else st.selectbox("Walk-in Associate column", walkin_assoc_candidates, key="walk_assoc_pick_2")
        )
        w_assoc_table = walkin_metrics_by(filtered_walkins.dropna(subset=[w_assoc_col]), w_assoc_col)
        if not w_assoc_table.empty:
            w_assoc_table = w_assoc_table.sort_values("Total_Unique_Walkin", ascending=False)
            st.dataframe(format_walkin_table(w_assoc_table, w_assoc_col), use_container_width=True, hide_index=True)
        else:
            st.info("No associate-level walk-in data for this selection.")

# ---------------- LIMECHAT TAB ----------------
with tab_limechat:
    st.markdown('<div class="section-kicker">LimeChat Key Metrics</div>', unsafe_allow_html=True)
    lc1 = st.columns(4)
    render_kpi(lc1[0], "👤", "Unique Customers", f"{limechat_unique_customers:,}")
    render_kpi(lc1[1], "🆕", "New Customers", f"{limechat_new_customers:,}")
    render_kpi(lc1[2], "🔁", "Repeat Customers", f"{limechat_repeat_customers:,}")
    render_kpi(lc1[3], "📊", "New %", fmt_pct(limechat_new_pct))

    lc2 = st.columns(4)
    render_kpi(lc2[0], "📞", "Valid Phone #s", f"{limechat_valid_phone_count:,}")
    render_kpi(lc2[1], "🚫", "Invalid Phone #s", f"{limechat_invalid_phone_count:,}")
    render_kpi(lc2[2], "💬", "Interacted %", fmt_pct(limechat_interacted_pct))
    render_kpi(lc2[3], "👀", "Non Interacted %", fmt_pct(limechat_non_interacted_pct))

    lc3 = st.columns(2)
    render_kpi(lc3[0], "🛍️", "Converted to Sale", f"{limechat_converted:,}")
    render_kpi(lc3[1], "🎯", "Conversion %", fmt_pct(limechat_conversion_pct))
    st.caption("Conversion = LimeChat Phone Number matched against Sales Mobile Number, same month.")

    st.markdown("---")

    # ---- Inbox-wise performance (vectorized — replaces the old per-group lambda scan) ----
    st.markdown('<div class="section-kicker">Inbox Wise Performance</div>', unsafe_allow_html=True)
    inbox_customers = filtered_limechat.groupby(LIMECHAT_INBOX_COL)["Customer_Key"].nunique().rename("Unique_Customers")
    inbox_nr = crosstab_counts(filtered_limechat, LIMECHAT_INBOX_COL, "New/Repeat", "Customer_Key")
    inbox_summary = inbox_nr.merge(inbox_customers, on=LIMECHAT_INBOX_COL, how="left")
    inbox_summary = inbox_summary.rename(columns={"New": "New_Customers", "Repeat": "Repeat_Customers"})
    tot = inbox_summary["New_Customers"] + inbox_summary["Repeat_Customers"]
    inbox_summary["New %"] = (inbox_summary["New_Customers"] / tot.replace(0, np.nan) * 100).round(1)
    inbox_summary["Repeat %"] = (inbox_summary["Repeat_Customers"] / tot.replace(0, np.nan) * 100).round(1)
    if ticket_col:
        tix = filtered_limechat.groupby(LIMECHAT_INBOX_COL)[ticket_col].nunique().rename("Total_Tickets")
        inbox_summary = inbox_summary.merge(tix, on=LIMECHAT_INBOX_COL, how="left")
    st.dataframe(inbox_summary.sort_values("Unique_Customers", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- Agent-wise performance (vectorized) ----
    st.markdown('<div class="section-kicker">Agent Wise Performance</div>', unsafe_allow_html=True)
    agent_customers = filtered_limechat.groupby(LIMECHAT_AGENT_COL)["Customer_Key"].nunique().rename("Unique_Customers")
    agent_interaction = crosstab_counts(filtered_limechat, LIMECHAT_AGENT_COL, "Interaction_Status", "Customer_Key",
                                         new_label="Interacted", repeat_label="Non Interacted")
    agent_summary = agent_interaction.merge(agent_customers, on=LIMECHAT_AGENT_COL, how="left")
    agent_tot = agent_summary["Interacted"] + agent_summary["Non Interacted"]
    agent_summary["Interacted %"] = (agent_summary["Interacted"] / agent_tot.replace(0, np.nan) * 100).round(1)
    agent_summary["Non Interacted %"] = (agent_summary["Non Interacted"] / agent_tot.replace(0, np.nan) * 100).round(1)
    if ticket_col:
        atix = filtered_limechat.groupby(LIMECHAT_AGENT_COL)[ticket_col].nunique().rename("Total_Tickets")
        agent_summary = agent_summary.merge(atix, on=LIMECHAT_AGENT_COL, how="left")
    st.dataframe(agent_summary.sort_values("Unique_Customers", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- Tag analysis ----
    st.markdown('<div class="section-kicker">Lead Quality & Tag Analysis</div>', unsafe_allow_html=True)
    tag_columns = [LIMECHAT_MAIN_TAG_COL, LIMECHAT_L1_COL, LIMECHAT_L2_COL, LIMECHAT_L3_COL, LIMECHAT_LEAD_QUALITY_COL]
    for tag_col in tag_columns:
        if tag_col not in filtered_limechat.columns:
            continue
        st.markdown(f"##### {tag_col}")
        agg_kwargs = {"Unique_Customers": ("Customer_Key", "nunique")}
        if ticket_col:
            agg_kwargs["Total_Tickets"] = (ticket_col, "nunique")
        tag_summary = filtered_limechat.groupby(tag_col).agg(**agg_kwargs).reset_index().sort_values("Unique_Customers", ascending=False)
        st.dataframe(tag_summary, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- Interaction summary (junk excluded) ----
    st.markdown('<div class="section-kicker">Interaction Summary — Junk Excluded</div>', unsafe_allow_html=True)
    interaction_summary = limechat_non_junk.groupby("Interaction_Status")["Customer_Key"].nunique().rename("Unique_Customers").reset_index()
    interaction_summary["Percentage"] = (interaction_summary["Unique_Customers"] / interaction_summary["Unique_Customers"].sum() * 100).round(1)
    st.dataframe(interaction_summary, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown('<div class="section-kicker">LimeChat Raw Data</div>', unsafe_allow_html=True)
    st.dataframe(filtered_limechat, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download Filtered LimeChat CSV",
        data=filtered_limechat.to_csv(index=False).encode("utf-8"),
        file_name="filtered_limechat.csv",
        mime="text/csv"
    )

# ---------------- PRODUCT MIX ----------------
with tab_product:
    st.caption("Respects the Store, Month, Date, Collection and Price Band filters in the sidebar.")

    def _render_product_section(title, col):
        st.markdown(f'<div class="section-kicker">{title}</div>', unsafe_allow_html=True)
        if not col:
            st.warning("Couldn't find this column in the Sales sheet. Available columns: " + ", ".join(map(str, sales.columns)))
            return
        tbl = product_metrics_by(filtered_sales, col)
        if tbl.empty:
            st.info("No data for this selection.")
            return
        st.dataframe(format_product_table(tbl, col), use_container_width=True, hide_index=True)

    _render_product_section("By Collection", collection_col)
    st.markdown("---")
    _render_product_section("By Product Category", category_col)
    st.markdown("---")
    _render_product_section("By Price Band", priceband_col)

# ---------------- SAME MONTH VS LAST YEAR ----------------
with tab_yoy:
    st.markdown('<div class="section-kicker">Same Month vs Last Year — Store Wise</div>', unsafe_allow_html=True)
    st.caption("Select one or more months in the sidebar. Each is compared to the same month last year.")

    if not selected_months:
        st.info("👈 Select at least one month in the sidebar to see this comparison.")
    else:
        for m_label in selected_months:
            cur = pd.to_datetime(m_label, format="%b-%y")
            prior_label = pd.Timestamp(year=cur.year - 1, month=cur.month, day=1).strftime("%b-%y")

            this_sales = sales[(sales["Month"] == cur.month) & (sales["Year"] == cur.year)]
            last_sales = sales[(sales["Month"] == cur.month) & (sales["Year"] == cur.year - 1)]
            this_walk = walkins[(walkins["Month"] == cur.month) & (walkins["Year"] == cur.year)]
            last_walk = walkins[(walkins["Month"] == cur.month) & (walkins["Year"] == cur.year - 1)]
            if selected_stores:
                this_sales = this_sales[this_sales[SALES_STORE_COL].isin(selected_stores)]
                last_sales = last_sales[last_sales[SALES_STORE_COL].isin(selected_stores)]
                this_walk = this_walk[this_walk[WALKIN_STORE_COL].isin(selected_stores)]
                last_walk = last_walk[last_walk[WALKIN_STORE_COL].isin(selected_stores)]

            this_targets = targets[targets["Month_Label"] == m_label]
            last_targets = targets[targets["Month_Label"] == prior_label]

            this_tbl = build_store_table(this_sales, this_walk, this_targets)
            last_tbl = build_store_table(last_sales, last_walk, last_targets)

            st.markdown(f"##### {m_label} vs {prior_label}")
            if this_tbl.empty and last_tbl.empty:
                st.info("No data for this month in either year.")
                continue

            this_fmt = format_sales_table(this_tbl, SALES_STORE_COL) if not this_tbl.empty else pd.DataFrame()
            last_fmt = format_sales_table(last_tbl, SALES_STORE_COL) if not last_tbl.empty else pd.DataFrame()

            c1, c2 = st.columns(2)
            with c1:
                st.caption(m_label)
                st.dataframe(this_fmt, use_container_width=True, hide_index=True)
            with c2:
                st.caption(prior_label)
                st.dataframe(last_fmt, use_container_width=True, hide_index=True)

            if not this_tbl.empty or not last_tbl.empty:
                chart_df = pd.DataFrame({
                    "Period": [m_label, prior_label],
                    "Net Sales (₹ Cr)": [
                        to_cr(this_tbl["Revenue"].sum()) if not this_tbl.empty else 0,
                        to_cr(last_tbl["Revenue"].sum()) if not last_tbl.empty else 0,
                    ],
                })
                fig = px.bar(chart_df, x="Period", y="Net Sales (₹ Cr)", color="Period", text_auto=".2f",
                             color_discrete_map={m_label: GOLD, prior_label: NAVY_SOFT})
                st.plotly_chart(style_fig(fig, show_legend=False, height=300), use_container_width=True)
            st.markdown("---")

# ---------------- RAW DATA ----------------
with tab_raw:
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