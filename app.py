import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px
BASE=Path(__file__).resolve().parent; OUT=BASE/'outputs'
st.set_page_config(page_title='FORESIGHT Planning Dashboard',layout='wide')
@st.cache_data
def load():
    sku=pd.read_csv(BASE/'raw/sku_master.csv')
    risk=pd.read_csv(OUT/'sku_risk_scoring.csv')
    fc=pd.read_csv(OUT/'forecast_next_8_weeks.csv',parse_dates=['week_start'])
    actual=pd.read_csv(OUT/'weekly_sku_demand_clean.csv',parse_dates=['week_start'])
    return sku,risk,fc,actual
sku,risk,fc,actual=load()
st.title('FORESIGHT — Demand Forecast & Inventory Risk')
st.caption('8-week SKU-level planning view | Forecast model: LightGBM | Risk logic: transparent stockout/overstock guardrails')
cat=st.selectbox('Category',['All']+sorted(sku.category.dropna().unique().tolist()))
if cat!='All': risk=risk.merge(sku[['sku_id','category']],on='sku_id',how='left'); risk=risk[risk.category.eq(cat)]
sel=st.selectbox('SKU',['All']+sorted(risk.sku_id.unique().tolist()))
if sel!='All': risk=risk[risk.sku_id.eq(sel)]
col1,col2,col3,col4=st.columns(4)
col1.metric('SKUs in view',f'{len(risk):,}')
col2.metric('Sales at risk',f'₹{risk.sales_at_risk.sum()/1e6:.1f}M')
col3.metric('Capital locked',f'₹{risk.capital_locked.sum()/1e6:.1f}M')
col4.metric('Reorder now',f'{(risk.action=="Reorder now").sum():,}')
left,right=st.columns(2)
with left:
    st.subheader('Forecast vs Actual')
    if sel!='All':
        a=actual[actual.sku_id.eq(sel)].tail(26); f=fc[fc.sku_id.eq(sel)]
        fig=px.line(a,x='week_start',y='units_sold',title='Historical weekly demand'); st.plotly_chart(fig,use_container_width=True)
    else: st.info('Select an SKU to view its forecast history.')
with right:
    st.subheader('Risk Actions')
    fig=px.bar(risk.action.value_counts().reset_index(),x='action',y='count',title='SKUs by recommended action'); st.plotly_chart(fig,use_container_width=True)
st.subheader('Prioritised Decision List')
cols=['sku_id','sku_name','category','forecast_8w_units','stock_on_hand','sales_at_risk','capital_locked','action']
st.dataframe(risk[cols].head(50),use_container_width=True)
