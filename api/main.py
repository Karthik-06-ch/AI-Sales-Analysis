import io
import pandas as pd
import numpy as np
import zipfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sklearn.linear_model import LinearRegression
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Smart Sales Forecasting System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ForecastResponse(BaseModel):
    insights: Dict[str, Any]
    predictions: List[Dict[str, Any]]
    historical: List[Dict[str, Any]]
    accuracy: float
    total_sales: float
    predicted_revenue: float
    seasonal_trends: Dict[str, Any]
    category_insights: Dict[str, Any]

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Sales Forecasting API"}

@app.post("/api/forecast", response_model=ForecastResponse)
async def upload_and_forecast(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.xlsx', '.xls', '.zip')):
        raise HTTPException(status_code=400, detail="Only CSV, Excel, or ZIP files are allowed.")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(contents)) as z:
                dataset_filename = next((name for name in z.namelist() if name.endswith(('.csv', '.xlsx', '.xls')) and not name.startswith('__MACOSX')), None)
                if not dataset_filename:
                    raise HTTPException(status_code=400, detail="No valid dataset (.csv, .xlsx) found in the ZIP file.")
                
                with z.open(dataset_filename) as f:
                    file_bytes = f.read()
                    if dataset_filename.endswith('.csv'):
                        df = pd.read_csv(io.BytesIO(file_bytes))
                    else:
                        df = pd.read_excel(io.BytesIO(file_bytes))
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
    try:
        # 1. Target Column Detection
        target_col = None
        for col in df.columns:
            if col.lower() in ['sales', 'revenue', 'total', 'amount', 'profit', 'quantity', 'price']:
                target_col = col
                break
                
        if not target_col:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                target_col = numeric_cols[-1]

        if not target_col:
            raise HTTPException(status_code=400, detail="Could not detect a numeric target column (e.g., Sales, Price) in the dataset.")

        df = df.rename(columns={target_col: 'Sales'})
        df['Sales'] = df['Sales'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df['Sales'] = pd.to_numeric(df['Sales'], errors='coerce')
        
        # Drop rows where target is NaN before date processing
        df = df.dropna(subset=['Sales'])
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="Target column contained no valid numbers.")

        # 2. Robust Date Column Detection
        date_col = None
        for col in df.columns:
            if col == 'Sales':
                continue
            # Look for explicit names first, then check if they actually parse
            if 'date' in col.lower() or 'time' in col.lower() or 'month' in col.lower() or 'year' in col.lower():
                parsed = pd.to_datetime(df[col].dropna().head(20), errors='coerce')
                if parsed.notna().sum() > 0:
                    date_col = col
                    break
        
        # Fallback if no named column worked
        if not date_col:
            for col in df.columns:
                if col == 'Sales':
                    continue
                parsed = pd.to_datetime(df[col].dropna().head(20), errors='coerce')
                if parsed.notna().sum() > 5: # Needs at least a few valid dates to be trusted
                    date_col = col
                    break

        if date_col:
            df = df.rename(columns={date_col: 'Date'})
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            if len(df) == 0:
                # If we dropped everything, fallback to dummy
                date_col = None

        if not date_col:
            # Fallback: No valid date column found. Generate sequential daily dates so forecasting can still run on the sequence!
            start_date = pd.Timestamp.now() - pd.DateOffset(days=len(df))
            df['Date'] = pd.date_range(start=start_date, periods=len(df), freq='D')

        df = df.sort_values('Date')

        # Determine aggregation frequency
        date_min = df['Date'].min()
        date_max = df['Date'].max()
        time_span_days = (date_max - date_min).days

        freq = 'D' if time_span_days <= 90 else 'M'
            
        df['Month_Year'] = df['Date'].dt.to_period(freq)
        
        # Aggregation for forecasting
        monthly_sales = df.groupby('Month_Year')['Sales'].sum().reset_index()
        
        if len(monthly_sales) < 3:
            if len(df) < 3:
                raise HTTPException(status_code=400, detail="Dataset has fewer than 3 rows. Cannot generate a trend forecast.")
            
            # Artificial spread for snapshot datasets (e.g. all rows have the same date)
            days_spread = min(30, len(df))
            df['Date_Group'] = np.linspace(0, days_spread - 1, len(df)).astype(int)
            start_date = pd.Timestamp.now() - pd.DateOffset(days=days_spread)
            df['Date'] = start_date + pd.to_timedelta(df['Date_Group'], unit='D')
            df['Month_Year'] = df['Date'].dt.to_period('D')
            monthly_sales = df.groupby('Month_Year')['Sales'].sum().reset_index()
            freq = 'D'
            
        monthly_sales['Date_Index'] = np.arange(len(monthly_sales))
            
        X = monthly_sales[['Date_Index']]
        y = monthly_sales['Sales']
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict past to calculate accuracy (R-squared proxy for simple LR)
        score = model.score(X, y)
        accuracy = round(max(0.0, score * 100), 2)  # Cap min at 0%
        
        # Forecast next 6 periods
        last_index = monthly_sales['Date_Index'].max()
        future_X = pd.DataFrame({'Date_Index': np.arange(last_index + 1, last_index + 7)})
        future_predictions = model.predict(future_X)
        
        # Generate future periods
        last_period = monthly_sales['Month_Year'].iloc[-1]
        future_periods = [str(last_period + i) for i in range(1, 7)]
        
        # Convert periods to strings for JSON serialization
        monthly_sales['Month_Year'] = monthly_sales['Month_Year'].astype(str)
        
        predictions_list = [
            {"Month_Year": future_periods[i], "Predicted_Sales": float(future_predictions[i])}
            for i in range(len(future_periods))
        ]
        
        historical_list = monthly_sales[['Month_Year', 'Sales']].to_dict(orient='records')
        
        # Additional Analytics
        total_sales = float(df['Sales'].sum())
        predicted_revenue = float(sum(future_predictions))
        
        # Seasonal Trends (by Month Name)
        df['Month_Name'] = df['Date'].dt.month_name()
        seasonal = df.groupby('Month_Name')['Sales'].sum().to_dict()
        
        # Category Insights & Region Insights
        category_insights = {}
        region_insights = {}
        
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        categorical_cols = [c for c in categorical_cols if c not in ['Date', 'Month_Year', 'Month_Name'] and df[c].nunique() < 50]
        
        if len(categorical_cols) > 0:
            cat_col = categorical_cols[0]
            cat_sales = df.groupby(cat_col)['Sales'].sum().sort_values(ascending=False)
            category_insights = cat_sales.head(5).to_dict()
            
        if len(categorical_cols) > 1:
            reg_col = categorical_cols[1]
            reg_sales = df.groupby(reg_col)['Sales'].sum().sort_values(ascending=False)
            region_insights = reg_sales.head(5).to_dict()
        
        # Smart Alerts / AI Recommendations
        recent_trend = future_predictions[0] - monthly_sales['Sales'].iloc[-1]
        recommendation = "Demand is expected to grow. Stock up on inventory." if recent_trend > 0 else "Demand shows a slight decline. Optimize your marketing spend and run targeted promotions."
        
        insights = {
            "recommendation": recommendation,
            "top_category": list(category_insights.keys())[0] if category_insights else "N/A",
            "top_region": list(region_insights.keys())[0] if region_insights else "N/A"
        }

        return ForecastResponse(
            insights=insights,
            predictions=predictions_list,
            historical=historical_list,
            accuracy=accuracy,
            total_sales=total_sales,
            predicted_revenue=predicted_revenue,
            seasonal_trends=seasonal,
            category_insights=category_insights
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Processing Error: {str(err)}. Ensure your dataset has valid date and numeric target columns.")
