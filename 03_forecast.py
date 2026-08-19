from pathlib import Path
import pandas as pd, numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error

BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs"
w=pd.read_csv(OUT/'weekly_sku_demand_clean.csv',parse_dates=['week_start'])
sku=pd.read_csv(BASE/'raw/sku_master.csv',usecols=['sku_id','category'])
# Complete weekly panel
weeks=pd.date_range(w.week_start.min(),w.week_start.max(),freq='7D')
skus=sku[['sku_id','category']].drop_duplicates()
mi=pd.MultiIndex.from_product([weeks,skus.sku_id],names=['week_start','sku_id'])
panel=mi.to_frame(index=False).merge(w[['week_start','sku_id','units_sold','revenue']],on=['week_start','sku_id'],how='left')
panel['units_sold']=panel['units_sold'].fillna(0.0)
panel['revenue']=panel['revenue'].fillna(0.0)
panel=panel.merge(sku,on='sku_id',how='left')
panel['week_of_year']=panel.week_start.dt.isocalendar().week.astype(int)
panel['month']=panel.week_start.dt.month
panel['sin52']=np.sin(2*np.pi*panel.week_of_year/52)
panel['cos52']=np.cos(2*np.pi*panel.week_of_year/52)
panel['category_code']=panel.category.astype('category').cat.codes.astype('int16')
panel=panel.sort_values(['sku_id','week_start']).reset_index(drop=True)
for lag in [1,2,4,13,26,52]:
 panel[f'lag{lag}']=panel.groupby('sku_id').units_sold.shift(lag)
for win in [4,13,52]:
 panel[f'roll{win}']=panel.groupby('sku_id').units_sold.shift(1).rolling(win,min_periods=win).mean().reset_index(level=0,drop=True)
features=['lag1','lag2','lag4','lag13','lag26','lag52','roll4','roll13','roll52','sin52','cos52','category_code']
panel=panel.dropna(subset=features).reset_index(drop=True)

def wape(y,p):
 den=np.abs(y).sum(); return np.abs(y-p).sum()/den if den else np.nan

def recursive_predict(train, cutoff, horizon=8):
 hist=train[['week_start','sku_id','units_sold','category_code']].copy()
 future_dates=pd.date_range(cutoff+pd.Timedelta(days=7),periods=horizon,freq='7D')
 preds=[]
 model=lgb.LGBMRegressor(objective='regression_l1',n_estimators=350,learning_rate=0.05,num_leaves=31,subsample=0.8,colsample_bytree=0.9,random_state=42,n_jobs=-1,verbosity=-1)
 X=train[features]; y=train.units_sold
 model.fit(X,y,categorical_feature=['category_code'])
 # dictionaries per sku for recent history
 bysku={k: g.units_sold.tolist() for k,g in train.groupby('sku_id',sort=False)}
 cat=dict(zip(train.sku_id,train.category_code))
 for d in future_dates:
  rows=[]
  weekno=int(d.isocalendar().week); s52=np.sin(2*np.pi*weekno/52); c52=np.cos(2*np.pi*weekno/52)
  for sid,histvals in bysku.items():
   def lag(n): return histvals[-n] if len(histvals)>=n else 0.0
   vals=histvals[-52:]
   r4=np.mean(vals[-4:]) if len(vals)>=4 else np.mean(vals) if vals else 0
   r13=np.mean(vals[-13:]) if len(vals)>=13 else np.mean(vals) if vals else 0
   r52=np.mean(vals) if len(vals)>=52 else np.mean(vals) if vals else 0
   rows.append([lag(1),lag(2),lag(4),lag(13),lag(26),lag(52),r4,r13,r52,s52,c52,cat[sid],sid,d])
  fx=pd.DataFrame(rows,columns=features+['sku_id','week_start'])
  pred=np.clip(model.predict(fx[features]),0,None)
  fx['prediction']=pred
  preds.append(fx[['week_start','sku_id','prediction']])
  for sid,p in zip(fx.sku_id, pred): bysku[sid].append(float(p))
 return pd.concat(preds,ignore_index=True)

# Rolling-origin folds with an 8-week horizon
fold_cutoffs=[pd.Timestamp('2025-08-04'),pd.Timestamp('2025-10-06'),pd.Timestamp('2025-11-03')]
metrics=[]; all_preds=[]
for cutoff in fold_cutoffs:
 train=panel[panel.week_start<=cutoff].copy()
 test_dates=pd.date_range(cutoff+pd.Timedelta(days=7),periods=8,freq='7D')
 test=panel[panel.week_start.isin(test_dates)][['week_start','sku_id','units_sold']].copy()
 pred=recursive_predict(train,cutoff,8)
 merged=test.merge(pred,on=['week_start','sku_id'],how='left')
 # seasonal naive = same SKU 52 weeks earlier
 lag52=panel[['week_start','sku_id','units_sold']].copy(); lag52['week_start']=lag52.week_start+pd.Timedelta(weeks=52); lag52=lag52.rename(columns={'units_sold':'naive52'})
 merged=merged.merge(lag52,on=['week_start','sku_id'],how='left')
 merged['naive52']=merged['naive52'].fillna(0)
 metrics.append({'fold_cutoff':cutoff.date(),'horizon_weeks':8,'model_wape':wape(merged.units_sold,merged.prediction),'seasonal_naive_wape':wape(merged.units_sold,merged.naive52),'model_mae':mean_absolute_error(merged.units_sold,merged.prediction),'naive_mae':mean_absolute_error(merged.units_sold,merged.naive52)})
 merged['fold_cutoff']=cutoff; all_preds.append(merged)
 print(metrics[-1],flush=True)

m=pd.DataFrame(metrics); m.to_csv(OUT/'forecast_backtest_metrics.csv',index=False)
p=pd.concat(all_preds,ignore_index=True); p.to_csv(OUT/'forecast_backtest_predictions.csv',index=False)
# Final 8-week forecast from latest complete week
cutoff=panel.week_start.max(); train=panel.copy(); final=recursive_predict(train,cutoff,8)
final.to_csv(OUT/'forecast_next_8_weeks.csv',index=False)
print('\nFINAL METRICS\n',m.to_string(index=False))
print('\nAVERAGE',m[['model_wape','seasonal_naive_wape']].mean())
