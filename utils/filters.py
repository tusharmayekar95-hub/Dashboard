import pandas as pd
import streamlit as st

def get_unique_options(df_sales: pd.DataFrame, df_walkin: pd.DataFrame, column: str, is_date: bool = False, date_part: str = None) -> list:
    """
    Combines values from both Sales and Walkin dataframes to generate unique filter options.
    """
    options = set()

    def extract_values(df):
        if df.empty or column not in df.columns:
            return
        if is_date:
            if date_part == 'year':
                options.update(df['date'].dt.year.dropna().unique())
            elif date_part == 'month_name':
                options.update(df['date'].dt.strftime('%B').dropna().unique())
        else:
            options.update(df[column].dropna().unique())

    extract_values(df_sales)
    extract_values(df_walkin)

    sorted_options = sorted(list(options))

    if is_date and date_part == 'month_name':
        month_order = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        sorted_options = [m for m in month_order if m in options]

    return [str(opt) for opt in sorted_options]


def render_sidebar_filters(df_sales: pd.DataFrame, df_walkin: pd.DataFrame):
    """
    Renders sidebar filters for Year, Month, Store, City, Category, Collection, and Sales Executive.
    Returns filtered df_sales and df_walkin.
    """
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding-bottom: 20px;">
            <h2 style="color: #D4AF37; margin-bottom: 5px; font-weight: 700;">TYAANI</h2>
            <p style="color: #6B7280; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0;">Jewellery Analytics</p>
        </div>
        <hr style="border-top: 1px solid rgba(212, 175, 55, 0.15); margin-top: 0; margin-bottom: 20px;">
        """,
        unsafe_allow_html=True
    )

    st.sidebar.subheader("Dashboard Filters")

    years = get_unique_options(df_sales, df_walkin, 'date', is_date=True, date_part='year')
    months = get_unique_options(df_sales, df_walkin, 'date', is_date=True, date_part='month_name')
    stores = get_unique_options(df_sales, df_walkin, 'store')
    cities = get_unique_options(df_sales, df_walkin, 'city')
    categories = get_unique_options(df_sales, df_walkin, 'category')
    collections = get_unique_options(df_sales, df_walkin, 'collection')
    execs = get_unique_options(df_sales, df_walkin, 'sales_executive')

    def create_multiselect(label, options):
        options_with_all = ["All"] + options
        selected = st.sidebar.multiselect(label, options=options_with_all, default=["All"])
        if not selected or "All" in selected:
            return None
        return selected

    sel_years = create_multiselect("Year", years)
    sel_months = create_multiselect("Month", months)
    sel_cities = create_multiselect("City", cities)
    sel_stores = create_multiselect("Store", stores)
    sel_categories = create_multiselect("Category", categories)
    sel_collections = create_multiselect("Collection", collections)
    sel_execs = create_multiselect("Sales Executive", execs)

    st.session_state['sel_years'] = sel_years
    st.session_state['sel_months'] = sel_months
    st.session_state['sel_cities'] = sel_cities
    st.session_state['sel_stores'] = sel_stores
    st.session_state['sel_categories'] = sel_categories
    st.session_state['sel_collections'] = sel_collections
    st.session_state['sel_execs'] = sel_execs

    # Map month names → integers once, so the filter uses .dt.month (int) comparison
    # instead of .dt.strftime('%B') (string formatting per row) — much faster.
    _MONTH_NAME_TO_INT = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }

    def apply_filters(df, is_sales=True):
        if df.empty:
            return df

        # Skip copy entirely when no filter is active
        any_filter = any([
            sel_years, sel_months, sel_cities, sel_stores,
            sel_categories, sel_collections, sel_execs,
        ])
        if not any_filter:
            return df

        filtered_df = df.copy()

        if sel_years:
            year_ints = [int(y) for y in sel_years]
            filtered_df = filtered_df[filtered_df['date'].dt.year.isin(year_ints)]

        if sel_months:
            # Integer month comparison — avoids per-row strftime string formatting
            month_ints = {_MONTH_NAME_TO_INT[m] for m in sel_months if m in _MONTH_NAME_TO_INT}
            filtered_df = filtered_df[filtered_df['date'].dt.month.isin(month_ints)]

        if sel_cities and 'city' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['city'].isin(sel_cities)]

        if sel_stores and 'store' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['store'].isin(sel_stores)]

        if sel_categories and 'category' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['category'].isin(sel_categories)]

        if sel_collections and 'collection' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['collection'].isin(sel_collections)]

        exec_col = 'sales_executive'
        if sel_execs and exec_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[exec_col].isin(sel_execs)]

        return filtered_df

    filtered_sales = apply_filters(df_sales, is_sales=True)
    filtered_walkin = apply_filters(df_walkin, is_sales=False)

    st.sidebar.markdown(
        f"""
        <div style="margin-top: 30px; padding: 15px; background-color: rgba(214,175,55,0.04); border-radius: 8px; border: 1px solid rgba(214,175,55,0.15);">
            <div style="font-size: 0.75rem; color: #6B7280; text-transform: uppercase; font-weight: 600;">Active Filter Summary</div>
            <div style="font-size: 0.85rem; margin-top: 5px;">Sales Rows: <b>{len(filtered_sales):,}</b></div>
            <div style="font-size: 0.85rem;">Walkins Rows: <b>{len(filtered_walkin):,}</b></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    return filtered_sales, filtered_walkin
