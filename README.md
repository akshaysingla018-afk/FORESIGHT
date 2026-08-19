# FORESIGHT - Retail Demand Forecasting and Inventory Risk Analytics

## Project Overview

FORESIGHT is an end-to-end retail analytics and decision-support solution designed to forecast SKU-level demand and identify inventory risks.

The project includes:

- Reproducible data ingestion and cleaning
- Exploratory data analysis
- Weekly SKU-level demand forecasting
- Seasonal-naive baseline comparison
- Rolling-origin backtesting
- WAPE-based model evaluation
- Inventory risk scoring
- Reorder and markdown recommendations
- Interactive Streamlit dashboard
- FastAPI scoring service

## Business Objective

The solution helps retail decision-makers identify:

1. Products likely to face stockouts
2. Products with excess inventory
3. SKUs that should be reordered
4. SKUs that should be marked down or cleared
5. Potential sales value at risk
6. Capital tied up in excess inventory

## Dataset

The supplied synthetic retail dataset contains:

- 5,000 SKUs
- 30 stores
- 10,000 customers
- 100 promotions
- 10M+ transaction records
- Inventory snapshots
- SKU/product master data
- Inventory risk flags

The clean transaction history is used for demand forecasting. The supplied anomaly flags are retained for inventory-risk evaluation.

## Project Workflow

Raw Retail Data
    |
    v
D1 - Data Pipeline and Cleaning
    |
    v
D2 - Exploratory Data Analysis
    |
    v
D3 - Demand Forecasting
    |
    v
D4 - Inventory Risk Scoring
    |
    v
D5 - Interactive Dashboard
    |
    v
D6 - FastAPI Scoring Service

## D1 - Data Pipeline and Cleaning

The large transaction dataset is processed in chunks to avoid loading the complete dataset into memory.

Results:

- 10 transaction-data chunks processed
- 1,033,143 weekly SKU observations created
- 5,000 SKUs
- 21,228 inventory records
- 30 stores
- 10,000 customers
- 100 promotions
- No invalid SKU/store foreign-key matches

Outputs:

- weekly_sku_demand_clean.csv
- inventory_by_sku.csv
- anomaly_flags.csv
- data_quality_report.csv

## D2 - Exploratory Data Analysis

The EDA stage examined demand trends, weekly demand patterns, top-selling SKUs, slow-moving products and data-quality issues.

Results:

- Top 20 SKUs identified
- 400 slow-moving SKUs flagged

## D3 - Demand Forecasting

An 8-week SKU-level demand forecasting model was developed.

Three rolling-origin backtesting folds were evaluated.

| Metric | Forecast Model | Seasonal Naive |
| --- | ---: | ---: |
| Average WAPE | 27.37% | 36.20% |

The forecasting model achieved approximately 24.4% lower WAPE than the seasonal-naive baseline.

Forecast output:

- forecast_next_8_weeks.csv

## D4 - Inventory Risk Scoring

The risk engine combines:

- 8-week demand forecast
- Stock on hand
- Reorder point
- Safety stock
- Product price
- Product cost

Risk actions:

| Action | SKU Count |
| --- | ---: |
| Markdown / clear | 2,785 |
| Reorder now | 1,814 |
| Watch / volatile | 217 |
| Healthy | 184 |
| Total | 5,000 |

Business impact:

- Sales at Risk: approximately INR 199.07M
- Capital Locked: approximately INR 1.131B

Risk outputs:

- sku_risk_scoring.csv
- risk_action_summary.csv
- risk_impact_summary.csv

## D5 - Interactive Dashboard

The Streamlit dashboard provides:

- Executive KPI cards
- Sales at Risk
- Capital Locked
- Reorder Now count
- Risk-action distribution
- Prioritised SKU decision list
- Forecast and risk information
- SKU selection

Run locally:

    streamlit run app.py

The dashboard normally runs at:

    http://localhost:8501

## D6 - FastAPI Scoring Service

The project includes a FastAPI scoring service.

Run locally:

    uvicorn api:app --reload

Health endpoint:

    GET /health

SKU scoring endpoint:

    GET /score/{sku_id}

Example:

    GET /score/SKU04321

The scoring endpoint returns:

- SKU ID
- 8-week forecast
- Stock on hand
- Recommended action
- Sales at risk
- Capital locked
- Weekly forecast values

## Key Business Findings

The analysis identifies a significant inventory imbalance across the SKU portfolio.

1,814 SKUs are classified as Reorder Now.

2,785 SKUs are classified as Markdown / clear.

The risk engine estimates approximately:

- INR 199.07M in sales at risk
- INR 1.131B in capital locked

## Modelling Notes

The supplied inventory snapshot does not contain separate on-order quantity or lead-time fields.

Therefore, the risk logic uses:

- 8-week planning horizon
- Current stock on hand
- Reorder point
- Safety stock
- Forecast demand

No unavailable fields are fabricated.

The forecast dates correspond to the modelling horizon generated from the supplied dataset.

## Technology Stack

- Python
- Pandas
- NumPy
- LightGBM
- Scikit-learn
- Matplotlib
- Streamlit
- FastAPI
- Uvicorn

## Project Structure

FORESIGHT/
|
+-- archive/
|   +-- retail_clean_dataset/
|   +-- retail_contaminated_dataset/
|
+-- outputs/
|
+-- 01_data_pipeline.py
+-- 02_eda.py
+-- 03_forecast.py
+-- 04_risk_scoring.py
+-- app.py
+-- api.py
+-- requirements.txt
+-- README.md
+-- .gitignore

## How to Run

Create the virtual environment:

    python -m venv .venv

Activate it on Windows:

    .venv\Scripts\activate

Install dependencies:

    pip install -r requirements.txt

Run the pipeline:

    python 01_data_pipeline.py

Run EDA:

    python 02_eda.py

Run forecasting:

    python 03_forecast.py

Run risk scoring:

    python 04_risk_scoring.py

Launch the dashboard:

    streamlit run app.py

Launch the API:

    uvicorn api:app --reload

## Author

Akshay Singla

M.Sc. Statistics
Panjab University