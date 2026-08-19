from fastapi import FastAPI, HTTPException
from pathlib import Path
import pandas as pd
app=FastAPI(title='FORESIGHT Scoring Service',version='1.0')
BASE=Path(__file__).resolve().parent; OUT=BASE/'outputs'
risk=pd.read_csv(OUT/'sku_risk_scoring.csv'); fc=pd.read_csv(OUT/'forecast_next_8_weeks.csv')
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/score/{sku_id}')
def score(sku_id:str):
    r=risk[risk.sku_id.eq(sku_id)]
    if r.empty: raise HTTPException(404,'SKU not found')
    f=fc[fc.sku_id.eq(sku_id)].sort_values('week_start')
    row=r.iloc[0]
    return {'sku_id':sku_id,'forecast_8w_units':float(row.forecast_8w_units),'stock_on_hand':float(row.stock_on_hand),'action':row.action,'sales_at_risk':float(row.sales_at_risk),'capital_locked':float(row.capital_locked),'forecast':f[['week_start','prediction']].to_dict('records')}
