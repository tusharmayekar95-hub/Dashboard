import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime


def calculate_kpis(df_sales: pd.DataFrame, df_walkin: pd.DataFrame) -> dict:
    """
    Computes all standard KPIs for Tyaani Jewellery dashboard on unique customers.
    Returns a dictionary of calculated metrics.
    """
    kpis = {}

    # 1. Sales-based metrics
    if not df_sales.empty:
        net_sales = df_sales['net_amount'].sum()
        gross_sales = df_sales['gross_amount'].sum()
        total_discount = df_sales['discount'].sum()
        invoices = df_sales['invoice_number'].nunique()
        total_qty = df_sales['quantity'].sum()

        cust_col = 'cleaned_mobile' if 'cleaned_mobile' in df_sales.columns else 'customer_key'
        unique_customers = df_sales[cust_col].nunique()

        if 'New_Repeat' in df_sales.columns:
            repeat_customers = df_sales[df_sales['New_Repeat'] == 'Repeat'][cust_col].nunique()
            repeat_revenue = df_sales[df_sales['New_Repeat'] == 'Repeat']['net_amount'].sum()
        else:
            cust_counts = df_sales.groupby(cust_col)['invoice_number'].nunique()
            repeat_cust_keys = cust_counts[cust_counts >= 2].index
            repeat_customers = len(repeat_cust_keys)
            repeat_revenue = df_sales[df_sales[cust_col].isin(repeat_cust_keys)]['net_amount'].sum()

        average_bill = net_sales / invoices if invoices > 0 else 0.0
        repeat_pct = (repeat_customers / unique_customers * 100) if unique_customers > 0 else 0.0
        upt = total_qty / invoices if invoices > 0 else 0.0
    else:
        net_sales = 0.0
        gross_sales = 0.0
        total_discount = 0.0
        invoices = 0
        total_qty = 0
        unique_customers = 0
        repeat_customers = 0
        repeat_revenue = 0.0
        average_bill = 0.0
        repeat_pct = 0.0
        upt = 0.0

    # 2. Walkin-based metrics
    if not df_walkin.empty:
        total_walkins = len(df_walkin)

        wk_cust_col = 'cleaned_mobile' if 'cleaned_mobile' in df_walkin.columns else 'walkin_customer_key'
        unique_walkins = df_walkin[wk_cust_col].nunique()

        purchased_count = df_walkin[df_walkin['purpose'].str.lower() == 'purchased'][wk_cust_col].nunique()

        not_purchased = len(df_walkin[df_walkin['purpose'].str.lower() == 'not purchased'])
        adv_booking = len(df_walkin[df_walkin['purpose'].str.lower() == 'advanced booking'])
        repair = len(df_walkin[df_walkin['purpose'].str.lower() == 'repair'])

        if 'New_Repeat' in df_walkin.columns:
            repeat_walkins = df_walkin[df_walkin['New_Repeat'] == 'Repeat'][wk_cust_col].nunique()
        else:
            repeat_walkins = 0

        conversion_pct = (purchased_count / unique_walkins * 100) if unique_walkins > 0 else 0.0
        repeat_walkins_pct = (repeat_walkins / unique_walkins * 100) if unique_walkins > 0 else 0.0
    else:
        total_walkins = 0
        unique_walkins = 0
        purchased_count = 0
        not_purchased = 0
        adv_booking = 0
        repair = 0
        repeat_walkins = 0
        conversion_pct = 0.0
        repeat_walkins_pct = 0.0

    kpis.update({
        'net_sales': net_sales,
        'gross_sales': gross_sales,
        'discount': total_discount,
        'invoices': invoices,
        'total_quantity': total_qty,
        'unique_customers': unique_customers,
        'repeat_customers': repeat_customers,
        'repeat_revenue': repeat_revenue,
        'average_bill': average_bill,
        'repeat_pct': repeat_pct,
        'upt': upt,
        'total_walkins': total_walkins,
        'unique_walkins': unique_walkins,
        'purchased_walkins': purchased_count,
        'not_purchased_walkins': not_purchased,
        'advanced_booking_walkins': adv_booking,
        'repair_walkins': repair,
        'repeat_walkins': repeat_walkins,
        'repeat_walkins_pct': repeat_walkins_pct,
        'conversion_pct': conversion_pct
    })

    return kpis


def calculate_ty_ly_comparison(df_sales_raw: pd.DataFrame, df_walkin_raw: pd.DataFrame) -> dict:
    """
    Computes TY (This Year) and LY (Last Year) metrics for Like-to-Like comparison.
    Applies all active non-year sidebar filters to both TY and LY datasets.
    """
    sel_years = st.session_state.get('sel_years', None)
    sel_months = st.session_state.get('sel_months', None)
    sel_cities = st.session_state.get('sel_cities', None)
    sel_stores = st.session_state.get('sel_stores', None)
    sel_categories = st.session_state.get('sel_categories', None)
    sel_collections = st.session_state.get('sel_collections', None)
    sel_execs = st.session_state.get('sel_execs', None)

    def apply_non_date_filters(df):
        if df.empty:
            return df
        filtered = df.copy()
        if sel_cities:
            filtered = filtered[filtered['city'].isin(sel_cities)]
        if sel_stores:
            filtered = filtered[filtered['store'].isin(sel_stores)]
        if sel_categories:
            filtered = filtered[filtered['category'].isin(sel_categories)]
        if sel_collections:
            filtered = filtered[filtered['collection'].isin(sel_collections)]
        if sel_execs and 'sales_executive' in filtered.columns:
            filtered = filtered[filtered['sales_executive'].isin(sel_execs)]
        return filtered

    sales_base = apply_non_date_filters(df_sales_raw)
    walkin_base = apply_non_date_filters(df_walkin_raw)

    available_years = set()
    if not sales_base.empty:
        available_years.update(sales_base['date'].dt.year.dropna().unique())
    if not walkin_base.empty:
        available_years.update(walkin_base['date'].dt.year.dropna().unique())

    available_years = sorted(list(available_years))
    if not available_years:
        available_years = [datetime.now().year]

    if sel_years:
        ty_years = [int(y) for y in sel_years]
    else:
        ty_years = [max(available_years)]

    ly_years = [y - 1 for y in ty_years]

    # Month name → integer map for fast integer-based filtering (avoids per-row strftime)
    _MONTH_NAME_TO_INT = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }

    def filter_time(df, years):
        if df.empty:
            return df
        df_y = df[df['date'].dt.year.isin(years)]
        if sel_months:
            month_ints = {_MONTH_NAME_TO_INT[m] for m in sel_months if m in _MONTH_NAME_TO_INT}
            df_y = df_y[df_y['date'].dt.month.isin(month_ints)]
        return df_y

    sales_ty = filter_time(sales_base, ty_years)
    sales_ly = filter_time(sales_base, ly_years)

    walkin_ty = filter_time(walkin_base, ty_years)
    walkin_ly = filter_time(walkin_base, ly_years)

    kpis_ty = calculate_kpis(sales_ty, walkin_ty)
    kpis_ly = calculate_kpis(sales_ly, walkin_ly)

    def pct_change(ty_val, ly_val):
        if ly_val == 0:
            return 0.0 if ty_val == 0 else 100.0
        return ((ty_val - ly_val) / ly_val) * 100

    def abs_change(ty_val, ly_val):
        return ty_val - ly_val

    comparison = {
        'ty': kpis_ty,
        'ly': kpis_ly,
        'deltas': {
            'net_sales_pct': pct_change(kpis_ty['net_sales'], kpis_ly['net_sales']),
            'gross_sales_pct': pct_change(kpis_ty['gross_sales'], kpis_ly['gross_sales']),
            'discount_pct': pct_change(kpis_ty['discount'], kpis_ly['discount']),
            'invoices_pct': pct_change(kpis_ty['invoices'], kpis_ly['invoices']),
            'unique_customers_pct': pct_change(kpis_ty['unique_customers'], kpis_ly['unique_customers']),
            'total_walkins_pct': pct_change(kpis_ty['total_walkins'], kpis_ly['total_walkins']),
            'unique_walkins_pct': pct_change(kpis_ty['unique_walkins'], kpis_ly['unique_walkins']),
            'conversion_pct_diff': abs_change(kpis_ty['conversion_pct'], kpis_ly['conversion_pct']),
            'average_bill_pct': pct_change(kpis_ty['average_bill'], kpis_ly['average_bill']),
            'repeat_pct_diff': abs_change(kpis_ty['repeat_pct'], kpis_ly['repeat_pct']),
            'upt_pct': pct_change(kpis_ty['upt'], kpis_ly['upt']),
        }
    }
    return comparison


def calculate_mom_growth(df_sales: pd.DataFrame) -> tuple:
    """
    Calculates Month-over-Month sales growth.
    Returns: (growth_percentage, current_month_name, prior_month_name)
    """
    if df_sales.empty:
        return 0.0, "N/A", "N/A"

    monthly_sales = df_sales.set_index('date').resample('ME')['net_amount'].sum().reset_index()
    if len(monthly_sales) < 2:
        return 0.0, "N/A", "N/A"

    last_row = monthly_sales.iloc[-1]
    prior_row = monthly_sales.iloc[-2]

    cur_sales = last_row['net_amount']
    prev_sales = prior_row['net_amount']

    cur_month = last_row['date'].strftime('%b %Y')
    prev_month = prior_row['date'].strftime('%b %Y')

    if prev_sales == 0:
        return 0.0, cur_month, prev_month

    growth = ((cur_sales - prev_sales) / prev_sales) * 100
    return growth, cur_month, prev_month


def generate_ai_insights(df_sales: pd.DataFrame, df_walkin: pd.DataFrame) -> dict:
    """
    Generates rule-based business insights mimicking an AI analyst.
    Reads latest filtered DataFrames and outputs top performance summaries.
    """
    insights = {}

    # 1. Sales Performance Insights
    if not df_sales.empty:
        store_rev = df_sales.groupby('store')['net_amount'].sum()
        insights['highest_performing_store'] = store_rev.idxmax()
        insights['highest_performing_store_val'] = store_rev.max()

        insights['lowest_performing_store'] = store_rev.idxmin()
        insights['lowest_performing_store_val'] = store_rev.min()

        collection_rev = df_sales.groupby('collection')['net_amount'].sum()
        insights['best_collection'] = collection_rev.idxmax()
        insights['best_collection_val'] = collection_rev.max()

        insights['worst_collection'] = collection_rev.idxmin()
        insights['worst_collection_val'] = collection_rev.min()

        city_rev = df_sales.groupby('city')['net_amount'].sum()
        insights['highest_revenue_city'] = city_rev.idxmax()
        insights['highest_revenue_city_val'] = city_rev.max()

        exec_rev = df_sales.groupby('sales_executive')['net_amount'].sum()
        insights['top_performing_exec'] = exec_rev.idxmax()
        insights['top_performing_exec_val'] = exec_rev.max()

        # Highest average-bill store — vectorized: one agg, no per-group lambda
        store_bill_agg = df_sales.groupby('store').agg(
            _rev=('net_amount', 'sum'),
            _inv=('invoice_number', 'nunique')
        )
        store_bill_agg['_atv'] = store_bill_agg['_rev'] / store_bill_agg['_inv'].replace(0, float('nan'))
        store_bill = store_bill_agg['_atv'].dropna()
        insights['highest_average_bill_store'] = store_bill.idxmax()
        insights['highest_average_bill_store_val'] = store_bill.max()

        mom_growth, cur_m, prev_m = calculate_mom_growth(df_sales)
        insights['mom_growth_pct'] = mom_growth
        insights['mom_growth_current'] = cur_m
        insights['mom_growth_prior'] = prev_m
    else:
        for key in ['highest_performing_store', 'lowest_performing_store', 'best_collection',
                    'worst_collection', 'highest_revenue_city', 'top_performing_exec',
                    'highest_average_bill_store', 'mom_growth_current', 'mom_growth_prior']:
            insights[key] = "N/A"
        for key in ['highest_performing_store_val', 'lowest_performing_store_val', 'best_collection_val',
                    'worst_collection_val', 'highest_revenue_city_val', 'top_performing_exec_val',
                    'highest_average_bill_store_val', 'mom_growth_pct']:
            insights[key] = 0.0

    # 2. Walkin & Conversion Insights
    if not df_walkin.empty:
        # Highest Conversion Store — vectorized: count purchased & total per store
        wk_cust_col = 'cleaned_mobile' if 'cleaned_mobile' in df_walkin.columns else 'walkin_customer_key'
        purchased_mask = df_walkin['purpose'].str.lower() == 'purchased'
        unique_purchased = (
            df_walkin[purchased_mask]
            .groupby('store')[wk_cust_col].nunique()
            .rename('_purchased')
        )
        unique_total = df_walkin.groupby('store')[wk_cust_col].nunique().rename('_total')
        store_conv_df = pd.concat([unique_total, unique_purchased], axis=1).fillna(0)
        store_conv = (store_conv_df['_purchased'] / store_conv_df['_total'].replace(0, float('nan'))).dropna()
        if not store_conv.empty:
            insights['highest_conversion_store'] = store_conv.idxmax()
            insights['highest_conversion_store_val'] = store_conv.max() * 100
        else:
            insights['highest_conversion_store'] = "N/A"
            insights['highest_conversion_store_val'] = 0.0
    else:
        insights['highest_conversion_store'] = "N/A"
        insights['highest_conversion_store_val'] = 0.0

    # 3. Repeat Purchase Insights
    if not df_sales.empty:
        # Repeat customer percentage per store — vectorized: no per-group lambda
        cust_col = 'cleaned_mobile' if 'cleaned_mobile' in df_sales.columns else 'customer_key'
        total_per_store = df_sales.groupby('store')[cust_col].nunique().rename('_total')
        if 'New_Repeat' in df_sales.columns:
            repeat_per_store = (
                df_sales[df_sales['New_Repeat'] == 'Repeat']
                .groupby('store')[cust_col].nunique()
                .rename('_repeat')
            )
        else:
            cust_inv = df_sales.groupby(['store', cust_col])['invoice_number'].nunique()
            repeat_per_store = (
                cust_inv[cust_inv >= 2]
                .groupby(level='store').count()
                .rename('_repeat')
            )
        store_repeat_df = pd.concat([total_per_store, repeat_per_store], axis=1).fillna(0)
        store_repeat = (store_repeat_df['_repeat'] / store_repeat_df['_total'].replace(0, float('nan'))).dropna()
        if not store_repeat.empty:
            insights['highest_repeat_store'] = store_repeat.idxmax()
            insights['highest_repeat_store_val'] = store_repeat.max() * 100
        else:
            insights['highest_repeat_store'] = "N/A"
            insights['highest_repeat_store_val'] = 0.0
    else:
        insights['highest_repeat_store'] = "N/A"
        insights['highest_repeat_store_val'] = 0.0

    return insights
