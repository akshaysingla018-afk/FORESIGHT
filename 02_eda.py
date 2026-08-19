from pathlib import Path
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent; OUT=BASE/'outputs'; PLOTS=OUT/'plots'; PLOTS.mkdir(exist_ok=True)
w=pd.read_csv(OUT/'weekly_sku_demand_clean.csv',parse_dates=['week_start'])
flags=pd.read_csv(OUT/'anomaly_flags.csv')
trend=w.groupby('week_start',as_index=False).agg(units_sold=('units_sold','sum'),revenue=('revenue','sum'),active_skus=('sku_id','nunique'))
trend.to_csv(OUT/'eda_weekly_trend.csv',index=False)
top=w.groupby('sku_id',as_index=False).agg(units_sold=('units_sold','sum'),revenue=('revenue','sum')).sort_values('revenue',ascending=False).head(20); top.to_csv(OUT/'eda_top_20_skus.csv',index=False)
last=w.week_start.max(); recent=w[w.week_start>last-pd.Timedelta(weeks=13)]
recent_d=recent.groupby('sku_id',as_index=False).agg(recent_units=('units_sold','sum'),recent_revenue=('revenue','sum'))
slow=flags[flags.flag.eq('SLOW_MOVER')].merge(recent_d,on='sku_id',how='left').fillna({'recent_units':0,'recent_revenue':0}); slow.to_csv(OUT/'eda_slow_movers.csv',index=False)
w['week_of_year']=w.week_start.dt.isocalendar().week.astype(int)
season=w.groupby('week_of_year',as_index=False).agg(total_units=('units_sold','sum'),avg_sku_week_units=('units_sold','mean')); season.to_csv(OUT/'eda_week_of_year.csv',index=False)
plt.figure(figsize=(10,4)); plt.plot(trend.week_start,trend.units_sold); plt.title('Weekly Units Sold'); plt.xlabel('Week'); plt.ylabel('Units'); plt.tight_layout(); plt.savefig(PLOTS/'weekly_units_trend.png',dpi=150); plt.close()
plt.figure(figsize=(10,4)); plt.plot(season.week_of_year,season.total_units); plt.title('Demand Seasonality by Week of Year'); plt.xlabel('ISO Week'); plt.ylabel('Units'); plt.tight_layout(); plt.savefig(PLOTS/'weekly_seasonality.png',dpi=150); plt.close()
plt.figure(figsize=(10,6)); q=top.sort_values('revenue'); plt.barh(q.sku_id,q.revenue); plt.title('Top 20 SKUs by Revenue'); plt.xlabel('Revenue'); plt.tight_layout(); plt.savefig(PLOTS/'top20_revenue.png',dpi=150); plt.close()
print(f'D2 complete: {len(slow)} flagged slow movers; {len(top)} top SKUs.')
