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
    
    # Expected columns: Date, Sales, Category, Region
    required_cols = ['Date', 'Sales']
    if not all(col in df.columns for col in required_cols):
        raise HTTPException(status_code=400, detail="Dataset must contain 'Date' and 'Sales' columns.")
    
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
    
    # Aggregation for forecasting (monthly)
    monthly_sales = df.groupby('Month_Year')['Sales'].sum().reset_index()
    monthly_sales['Date_Index'] = np.arange(len(monthly_sales))
    
    # Machine Learning - Linear Regression
    if len(monthly_sales) < 3:
        raise HTTPException(status_code=400, detail="Not enough data points to forecast. Please provide at least 3 months of data.")
        
    X = monthly_sales[['Date_Index']]
    y = monthly_sales['Sales']
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict past to calculate accuracy (R-squared proxy for simple LR)
    score = model.score(X, y)
    accuracy = round(max(0.0, score * 100), 2)  # Cap min at 0%
    
    # Forecast next 6 months
    last_index = monthly_sales['Date_Index'].max()
    future_X = pd.DataFrame({'Date_Index': np.arange(last_index + 1, last_index + 7)})
    future_predictions = model.predict(future_X)
    
    # Generate future periods
    last_period = pd.Period(monthly_sales['Month_Year'].iloc[-1], freq='M')
    future_periods = [(last_period + i).astype(str) for i in range(1, 7)]
    
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
    
    # Category Insights
    category_insights = {}
    if 'Category' in df.columns:
        cat_sales = df.groupby('Category')['Sales'].sum().sort_values(ascending=False)
        category_insights = cat_sales.head(5).to_dict()
        
    # Region insights if available
    region_insights = {}
    if 'Region' in df.columns:
        reg_sales = df.groupby('Region')['Sales'].sum().sort_values(ascending=False)
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
