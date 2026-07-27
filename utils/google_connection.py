import os
import json
import logging
import pandas as pd
import numpy as np
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Column aliases for flexible column mapping from Google Sheets
COLUMN_ALIASES = {
    'date': ['date', 'invoice date', 'sales date', 'transaction date', 'walkin date', 'walk-in date', 'datetime', 'day', 'time'],
    'invoice_number': ['invoice number', 'invoice no', 'invoice_no', 'invoice id', 'bill no', 'bill number', 'invoice_number'],
    'customer_key': ['customer key', 'customer id', 'customer_id', 'customer_key', 'overall customer key', 'walkin customer key', 'walk-in customer key', 'phone', 'mobile', 'customer phone', 'customer name', 'cust key'],
    'store': ['store', 'store name', 'branch', 'outlet', 'location'],
    'city': ['city', 'town', 'region'],
    'category': ['category', 'product category', 'item category', 'type', 'product type'],
    'collection': ['collection', 'range', 'design collection', 'line', 'collection name'],
    'sales_executive': ['sales executive', 'executive', 'sales rep', 'rep', 'staff', 'salesperson', 'met by', 'handled by', 'executive name'],
    'quantity': ['quantity', 'qty', 'units', 'pieces', 'pcs', 'number of items'],
    'gross_amount': ['gross amount', 'gross sales', 'gross_amount', 'subtotal', 'gross value', 'gross amt', 'gross'],
    'discount': ['discount', 'discount amount', 'discount_amount', 'disc', 'discount value', 'discount amt'],
    'net_amount': ['net amount', 'net sales', 'net_amount', 'total amount', 'total', 'sales amount', 'net value', 'net amt', 'net']
}

def map_columns(df: pd.DataFrame, is_sales: bool = True) -> pd.DataFrame:
    """
    Map DataFrame columns to standard names using defined aliases.
    """
    df = df.copy()
    orig_cols = {col: str(col).strip().lower() for col in df.columns}
    rename_dict = {}

    for standard_name, aliases in COLUMN_ALIASES.items():
        if not is_sales and standard_name in ['invoice_number', 'gross_amount', 'discount', 'net_amount', 'quantity']:
            continue
        for orig_col, norm_col in orig_cols.items():
            if norm_col in aliases:
                rename_dict[orig_col] = standard_name
                break

    df.rename(columns=rename_dict, inplace=True)
    return df


def _vectorized_clean_phone(series: pd.Series) -> pd.Series:
    """
    Vectorized phone number cleaner — replaces the old per-row apply().
    Processes an entire Series at once using pandas string methods:
      - Strips whitespace, removes null sentinels → 'Unknown'
      - Strips trailing '.0' (float artefact from pandas)
      - Extracts digits; handles Indian (10/11/12-digit) and international formats.
    ~10-50× faster than the equivalent row-wise apply() on real data.
    """
    s = series.astype(str).str.strip()

    null_sentinel = {'nan', 'none', 'unknown', 'unknown_cust', '', 'nat'}
    s = s.where(~s.str.lower().isin(null_sentinel), other='')

    trailing_dot_zero = s.str.endswith('.0')
    s = s.where(~trailing_dot_zero, other=s.str[:-2])

    has_plus = s.str.startswith('+')

    digits = s.str.replace(r'\D', '', regex=True)
    digit_len = digits.str.len()

    result = pd.Series('Unknown', index=series.index, dtype=str)

    mask_10 = digit_len == 10
    result = result.where(~mask_10, other=digits)

    mask_12_91 = (digit_len == 12) & digits.str.startswith('91')
    result = result.where(~mask_12_91, other=digits.str[-10:])

    mask_11_0 = (digit_len == 11) & digits.str.startswith('0')
    result = result.where(~mask_11_0, other=digits.str[-10:])

    handled = mask_10 | mask_12_91 | mask_11_0
    intl_mask = ~handled & (digit_len > 0)
    result = result.where(~(intl_mask & has_plus), other='+' + digits)
    result = result.where(~(intl_mask & ~has_plus), other=digits)

    still_unknown = (result == 'Unknown') & (s != '')
    result = result.where(~still_unknown, other=s)

    result = result.where(s != '', other='Unknown')
    return result


def clean_phone_number(val, default_cust_id):
    """
    Single-value wrapper around _vectorized_clean_phone.
    Kept for any caller that still uses the scalar form.
    For bulk use, call _vectorized_clean_phone(series) directly.
    """
    return _vectorized_clean_phone(pd.Series([val])).iloc[0]


def clean_data(df: pd.DataFrame, is_sales: bool = True) -> pd.DataFrame:
    """
    Cleans the input DataFrame: converts dates, fills missing values, converts types.
    """
    if df.empty:
        return df

    df = map_columns(df, is_sales=is_sales)

    # 1. Clean Date Column
    if 'date' in df.columns:
        df['date'] = df['date'].astype(str).str.strip()
        df = df[df['date'].str.len() > 0]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['date'] = df['date'].ffill().bfill()
        if df['date'].isnull().all():
            df['date'] = datetime.now()
    else:
        df['date'] = datetime.now()

    df['Month-YY'] = df['date'].dt.strftime('%b-%y')

    # 2. Clean Text Columns
    text_cols = ['store', 'city', 'category', 'collection', 'sales_executive']
    cust_col = 'customer_key' if is_sales else 'walkin_customer_key'

    if not is_sales:
        if 'walkin_customer_key' not in df.columns and 'customer_key' in df.columns:
            df['walkin_customer_key'] = df['customer_key']
        if 'purpose' not in df.columns:
            purpose_aliases = ['purpose', 'status', 'type', 'walk-in purpose', 'activity']
            for col in df.columns:
                if str(col).strip().lower() in purpose_aliases:
                    df.rename(columns={col: 'purpose'}, inplace=True)
                    break
        if 'purpose' in df.columns:
            text_cols.append('purpose')
        else:
            df['purpose'] = 'Not Purchased'
            text_cols.append('purpose')

    # Basic text cleaning — fully vectorized, no per-row apply
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            null_sentinel = {'', 'nan', 'none', 'unknown', 'nat'}
            df[col] = df[col].where(
                ~df[col].str.lower().isin(null_sentinel), other='Unknown'
            )
            # .str.title() is vectorized C-level; much faster than apply(lambda)
            not_unknown = df[col] != 'Unknown'
            df.loc[not_unknown, col] = df.loc[not_unknown, col].str.title()
        else:
            df[col] = 'Unknown'

    # Clean the Customer Mobile — vectorized, no per-row apply
    if cust_col in df.columns:
        df['cleaned_mobile'] = _vectorized_clean_phone(df[cust_col])
    else:
        df['cleaned_mobile'] = 'Unknown'

    df['Store Name|Month-YY|Mobile number'] = (
        df['store'].astype(str) + "|" + df['Month-YY'].astype(str) + "|" + df['cleaned_mobile'].astype(str)
    )

    # Calculate New_Repeat column based on chronological customer history
    df.sort_values(by='date', inplace=True)
    df.reset_index(drop=True, inplace=True)

    min_dates = df.groupby('cleaned_mobile')['date'].min().reset_index()
    min_dates.rename(columns={'date': 'first_date'}, inplace=True)

    df = pd.merge(df, min_dates, on='cleaned_mobile', how='left')

    df['first_period'] = df['first_date'].dt.to_period('M')
    df['current_period'] = df['date'].dt.to_period('M')

    df['New_Repeat'] = np.where(df['current_period'] == df['first_period'], 'New', 'Repeat')

    df.drop(columns=['first_date', 'first_period', 'current_period'], errors='ignore', inplace=True)

    # 3. Clean Numeric Columns (Sales only)
    if is_sales:
        num_cols = {
            'quantity': 1,
            'gross_amount': 0.0,
            'discount': 0.0,
            'net_amount': 0.0
        }
        for col, default in num_cols.items():
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(default)
            else:
                df[col] = default

        df['quantity'] = df['quantity'].abs().astype(int)
        df['gross_amount'] = df['gross_amount'].abs()
        df['discount'] = df['discount'].abs()

        zero_net = df['net_amount'] == 0.0
        df.loc[zero_net, 'net_amount'] = (
            df.loc[zero_net, 'gross_amount'] - df.loc[zero_net, 'discount']
        ).clip(lower=0)

    # Already sorted above; no need to sort+reset again.
    return df


@st.cache_data(ttl=3600)  # Cache synthetic data for 1 hour — avoids re-generation on page switches
def generate_synthetic_data():
    """
    Generates high-fidelity mock data representing a luxury jewellery brand's transactions.
    Generates about 2,500 sales records and 3,500 walk-in records spanning the last 2.5 years.
    """
    logger.info("Generating high-fidelity synthetic data for Tyaani Jewellery.")
    np.random.seed(42)

    stores = ["Mumbai (Bandra)", "Delhi (Mehrauli)", "Hyderabad (Banjara Hills)", "Bengaluru (Infantry Road)", "Pune (Koregaon Park)"]
    cities_map = {
        "Mumbai (Bandra)": "Mumbai",
        "Delhi (Mehrauli)": "Delhi",
        "Hyderabad (Banjara Hills)": "Hyderabad",
        "Bengaluru (Infantry Road)": "Bengaluru",
        "Pune (Koregaon Park)": "Pune"
    }

    categories = ["Necklace", "Earrings", "Rings", "Bangles", "Pendants", "Chokers"]
    collections = ["Polki", "Jadau", "Diamond", "Gold", "Victorian"]

    execs = {
        "Mumbai (Bandra)": ["Amit Sharma", "Neha Gupta", "Vikram Singh"],
        "Delhi (Mehrauli)": ["Priya Patel", "Rohan Mehta", "Sanjay Kumar"],
        "Hyderabad (Banjara Hills)": ["Ananya Rao", "Kriti Verma", "Siddharth Joshi"],
        "Bengaluru (Infantry Road)": ["Deepak Reddy", "Meera Nair", "Rahul Dev"],
        "Pune (Koregaon Park)": ["Aditya Joshi", "Tanvi Shah", "Gaurav More"]
    }

    customer_keys = [f"TY-{np.random.randint(10000, 99999)}" for _ in range(800)]

    # 1. Generate Sales
    sales_rows = []
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 7, 16)
    days = (end_date - start_date).days

    invoice_seq = 50001

    for day in range(days):
        current_date = start_date + timedelta(days=day)
        month = current_date.month
        season_multiplier = 1.0
        if month in [10, 11]:
            season_multiplier = 1.8
        elif month in [12, 1, 2]:
            season_multiplier = 1.4
        elif month in [6, 7]:
            season_multiplier = 0.7

        num_sales = int(np.random.poisson(3 * season_multiplier))

        for _ in range(num_sales):
            store = np.random.choice(stores)
            city = cities_map[store]
            sales_exec = np.random.choice(execs[store])
            cust_key = np.random.choice(customer_keys)

            if np.random.rand() < 0.25:
                cust_key = np.random.choice(customer_keys[:100])

            category = np.random.choice(categories)
            collection = np.random.choice(collections)
            qty = int(np.random.choice([1, 2, 3], p=[0.8, 0.15, 0.05]))

            base_prices = {
                "Necklace": np.random.uniform(150000, 800000),
                "Chokers": np.random.uniform(300000, 1200000),
                "Earrings": np.random.uniform(50000, 250000),
                "Rings": np.random.uniform(40000, 180000),
                "Bangles": np.random.uniform(100000, 450000),
                "Pendants": np.random.uniform(30000, 150000)
            }

            gross = round(base_prices[category] * qty, 2)
            discount_rate = np.random.choice([0.0, 0.05, 0.10, 0.15], p=[0.4, 0.3, 0.2, 0.1])
            discount = round(gross * discount_rate, 2)
            net = round(gross - discount, 2)

            invoice_num = f"INV-{invoice_seq}"
            invoice_seq += 1

            sales_rows.append({
                "date": current_date + timedelta(hours=np.random.randint(10, 20)),
                "invoice_number": invoice_num,
                "customer_key": cust_key,
                "store": store,
                "city": city,
                "category": category,
                "collection": collection,
                "sales_executive": sales_exec,
                "quantity": qty,
                "gross_amount": gross,
                "discount": discount,
                "net_amount": net
            })

    df_sales = pd.DataFrame(sales_rows)

    # 2. Generate Walkins
    # Pre-build a date → customer_keys lookup dict so the inner loop does an O(1)
    # dict.get() instead of scanning the entire df_sales DataFrame per day.
    sales_by_date: dict = df_sales.groupby(df_sales['date'].dt.date)['customer_key'].apply(list).to_dict()

    walkin_rows = []
    walkin_cust_keys = customer_keys + [f"TY-WK-{np.random.randint(10000, 99999)}" for _ in range(1200)]

    for day in range(days):
        current_date = start_date + timedelta(days=day)
        month = current_date.month
        season_multiplier = 1.0
        if month in [10, 11]:
            season_multiplier = 1.6
        elif month in [12, 1, 2]:
            season_multiplier = 1.3
        elif month in [6, 7]:
            season_multiplier = 0.8

        num_walkins = int(np.random.poisson(5 * season_multiplier))

        # O(1) lookup — replaces the full DataFrame filter that ran every iteration
        day_sales_keys = sales_by_date.get(current_date.date(), [])

        for _ in range(num_walkins):
            store = np.random.choice(stores)
            city = cities_map[store]
            sales_exec = np.random.choice(execs[store])
            cust_key = np.random.choice(walkin_cust_keys)

            purpose = np.random.choice(
                ["Purchased", "Not Purchased", "Advanced Booking", "Repair"],
                p=[0.38, 0.45, 0.10, 0.07]
            )

            # Link 'Purchased' walk-ins to a real sales customer key for that day
            if purpose == "Purchased" and day_sales_keys:
                cust_key = np.random.choice(day_sales_keys)

            walkin_rows.append({
                "date": current_date + timedelta(hours=np.random.randint(10, 20)),
                "walkin_customer_key": cust_key,
                "store": store,
                "city": city,
                "category": np.random.choice(categories),
                "collection": np.random.choice(collections),
                "sales_executive": sales_exec,
                "purpose": purpose
            })

    df_walkin = pd.DataFrame(walkin_rows)

    return clean_data(df_sales, is_sales=True), clean_data(df_walkin, is_sales=False)


def authenticate_google_sheets():
    """
    Attempts to authenticate with Google Sheets API.
    Returns gspread client or None.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # 1. Try Streamlit Secrets
    if "gcp_service_account" in st.secrets:
        try:
            logger.info("Authenticating using Streamlit Secrets...")
            secret_val = st.secrets["gcp_service_account"]
            # Support both raw JSON string and native TOML table formats
            creds_dict = json.loads(secret_val) if isinstance(secret_val, str) else dict(secret_val)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Streamlit secrets authentication failed: {e}")

    # 2. Try Local File service_account.json
    local_creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "service_account.json")
    if os.path.exists(local_creds_path):
        try:
            logger.info("Authenticating using local service_account.json...")
            creds = Credentials.from_service_account_file(local_creds_path, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Local credentials file authentication failed: {e}")

    # 3. Try generic credentials.json
    generic_creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials.json")
    if os.path.exists(generic_creds_path):
        try:
            logger.info("Authenticating using local credentials.json...")
            creds = Credentials.from_service_account_file(generic_creds_path, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Local generic credentials file authentication failed: {e}")

    logger.warning("No valid Google credentials source found.")
    return None


@st.cache_data(ttl=300)  # Caches data for 5 minutes (TTL) to balance speed and freshness
def fetch_live_data(sheet_name: str = "Tyaani"):
    """
    Connects to Google Sheets and fetches 'Sales' and 'Walkin' sheets.
    If fails, returns None.
    """
    client = authenticate_google_sheets()
    if not client:
        raise ConnectionError("Google Sheets Service Account authentication failed. No credentials found.")

    try:
        logger.info(f"Connecting to Google Sheet named '{sheet_name}'...")
        spreadsheet = client.open(sheet_name)

        try:
            sales_sheet = spreadsheet.worksheet("Sales")
            sales_data = sales_sheet.get_all_records()
            df_sales = pd.DataFrame(sales_data)
        except Exception as e:
            logger.error(f"Failed to read 'Sales' worksheet: {e}")
            raise ValueError(f"Could not read 'Sales' worksheet: {e}")

        try:
            walkin_sheet = spreadsheet.worksheet("Walkin")
            walkin_data = walkin_sheet.get_all_records()
            df_walkin = pd.DataFrame(walkin_data)
        except Exception as e:
            logger.error(f"Failed to read 'Walkin' worksheet: {e}")
            raise ValueError(f"Could not read 'Walkin' worksheet: {e}")

        df_sales_clean = clean_data(df_sales, is_sales=True)
        df_walkin_clean = clean_data(df_walkin, is_sales=False)

        return df_sales_clean, df_walkin_clean

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Google Sheet named '{sheet_name}' not found. Verify service account access.")
        raise FileNotFoundError(f"Spreadsheet '{sheet_name}' not found. Share it with your Service Account.")
    except Exception as e:
        logger.error(f"Unexpected error loading from Google Sheets: {e}")
        raise e


def load_data():
    """
    Main entry point for dashboard pages to obtain data.
    Will attempt to load live Google Sheets data.
    If fails or is not set up, returns high-fidelity demo data and sets connection state.
    """
    if 'connection_status' not in st.session_state:
        st.session_state['connection_status'] = "Initializing..."
        st.session_state['connection_error'] = None

    try:
        df_sales, df_walkin = fetch_live_data("Tyaani")
        st.session_state['connection_status'] = "LIVE"
        st.session_state['connection_error'] = None
        return df_sales, df_walkin
    except Exception as e:
        st.session_state['connection_status'] = "DEMO"
        st.session_state['connection_error'] = str(e)
        logger.info(f"Fallback to Demo Mode: {e}")

        if 'synthetic_sales' not in st.session_state or 'synthetic_walkin' not in st.session_state:
            s_sales, s_walkin = generate_synthetic_data()
            st.session_state['synthetic_sales'] = s_sales
            st.session_state['synthetic_walkin'] = s_walkin

        return st.session_state['synthetic_sales'], st.session_state['synthetic_walkin']


def force_refresh_data():
    """
    Clears Streamlit cache to force reload the Google Sheets data.
    """
    st.cache_data.clear()
    if 'synthetic_sales' in st.session_state:
        del st.session_state['synthetic_sales']
    if 'synthetic_walkin' in st.session_state:
        del st.session_state['synthetic_walkin']
    logger.info("Cleared Streamlit caches to force data reload.")
