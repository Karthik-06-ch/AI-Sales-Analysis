# Smart Sales Forecasting System

An AI-powered web application for business analytics, consumer purchasing trend analysis, and automated sales prediction. Designed with a modern, high-contrast, professional "startup SaaS" dashboard UI.

## Features

- **AI-Powered Forecasting**: Uses Scikit-learn's `LinearRegression` machine learning model to predict the next 6 months of sales trajectories.
- **Data Upload**: Seamlessly drag & drop or select `.csv`, `.xlsx`, or `.zip` files containing historical sales data. Auto-extracts datasets from ZIP archives.
- **Dynamic Visualizations**: Beautiful, interactive charts using `recharts`. Features area charts for historical vs. predicted growth, and bar charts for seasonal trend analysis.
- **Analytics Dashboard**: Tracks Total Historical Sales, Predicted Revenue, Forecast Accuracy, and custom AI Insights generated based on current trends.
- **Downloadable Reports**: Export generated forecasts as a CSV directly from the dashboard.
- **High-Contrast Dark Theme**: Aesthetic interface with glassmorphism panels, vivid accent colors, and optimal readability.

## Tech Stack

- **Frontend**: React, Vite, Vanilla CSS, Recharts, Lucide Icons, Axios.
- **Backend**: Python, FastAPI, Pandas, Scikit-learn, Uvicorn.
- **Machine Learning**: Linear Regression for trend prediction.

## Running Locally

To run the application locally, you can use the included quick-start script.

### Using the Batch Script (Windows)

1. Double-click the `run.bat` file in the project root.
2. Two terminal windows will open (one for the React frontend, one for the FastAPI backend).
3. Wait about 5-10 seconds for the servers to boot.
4. Navigate to `http://localhost:5173` in your browser.

### Manual Setup

If you prefer to run it manually:

**1. Start the Backend:**
```bash
cd api
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt # (or install fastapi uvicorn pandas scikit-learn python-multipart openpyxl)
uvicorn main:app --reload
```

**2. Start the Frontend:**
```bash
# In the root folder
npm install
npm run dev
```

## Dataset Format

Your dataset must include at least two columns:
- `Date`: The historical date of the sale (e.g., `YYYY-MM-DD`).
- `Sales`: The numerical value of the sales or revenue.

*Additional columns like `Category` and `Region` are supported and will generate extra insights.*
