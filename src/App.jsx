import { useState, useCallback } from 'react'
import { UploadCloud, TrendingUp, DollarSign, Activity, AlertCircle, BarChart3, CalendarDays } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  BarChart, Bar, AreaChart, Area
} from 'recharts'
import axios from 'axios'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      setError('')
    }
  }, [])

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError('')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first.')
      return
    }

    setLoading(true)
    setError('')
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:8000/api/forecast', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setData(response.data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'An error occurred during forecasting.')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
  }

  // Prepare chart data
  const combinedChartData = () => {
    if (!data) return []
    const hist = data.historical.map(d => ({ month: d.Month_Year, Actual: d.Sales, Predicted: null }))
    const pred = data.predictions.map(d => ({ month: d.Month_Year, Actual: null, Predicted: d.Predicted_Sales }))
    return [...hist, ...pred]
  }

  const seasonalChartData = () => {
    if (!data) return []
    return Object.keys(data.seasonal_trends).map(key => ({
      name: key,
      Sales: data.seasonal_trends[key]
    }))
  }

  const handleDownload = () => {
    if (!data) return;
    const csvRows = [
      ["Month_Year", "Predicted_Sales"]
    ];
    data.predictions.forEach(p => {
      csvRows.push([p.Month_Year, p.Predicted_Sales]);
    });
    
    const csvString = csvRows.map(row => row.join(",")).join("\n");
    const blob = new Blob([csvString], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "sales_forecast_report.csv";
    link.click();
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-container">
            <Activity className="logo-icon" />
            <h1>Smart Sales Forecasting AI</h1>
          </div>
          <div className="header-actions">
            <button className="btn-secondary">Documentation</button>
            <button className="btn-primary">Connect Data</button>
          </div>
        </div>
      </header>

      <main className="main-content">
        {!data ? (
          <div className="upload-section glass-panel">
            <h2>Upload Historical Data</h2>
            <p className="subtitle">Upload your CSV, Excel, or ZIP files containing 'Date' and 'Sales' columns to generate an AI-powered forecast. (ZIP files will be auto-extracted).</p>
            
            <div 
              className={`upload-zone ${file ? 'has-file' : ''}`}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <UploadCloud className="upload-icon" />
              <h3>{file ? file.name : "Drag & Drop your dataset or ZIP here"}</h3>
              <p>or click to browse</p>
              <input type="file" onChange={handleFileChange} accept=".csv, .xlsx, .xls, .zip" />
            </div>

            {error && <div className="error-message"><AlertCircle size={16}/> {error}</div>}
            
            <button 
              className={`btn-primary run-btn ${loading ? 'loading' : ''}`}
              onClick={handleUpload}
              disabled={loading || !file}
            >
              {loading ? 'Analyzing Data...' : 'Generate Forecast'}
            </button>

            <div className="ml-explanation">
              <BarChart3 size={20} className="icon-blue" />
              <div>
                <h4>How it works</h4>
                <p>Our system uses <strong>Linear Regression</strong>—a machine learning algorithm that models the relationship between historical dates and sales figures to project future revenue trajectories.</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="dashboard-section fade-in">
            <div className="dashboard-header">
              <div>
                <h2>Forecast Overview</h2>
                <p>AI-generated insights based on your historical data</p>
              </div>
              <button className="btn-secondary" onClick={handleDownload}>
                Download Report
              </button>
              <button className="btn-primary" onClick={() => setData(null)}>
                New Analysis
              </button>
            </div>

            <div className="metrics-grid">
              <div className="metric-card glass-panel">
                <div className="metric-header">
                  <div className="metric-icon bg-blue"><DollarSign size={20} /></div>
                  <span>Total Historical Sales</span>
                </div>
                <h3>{formatCurrency(data.total_sales)}</h3>
              </div>
              
              <div className="metric-card glass-panel">
                <div className="metric-header">
                  <div className="metric-icon bg-green"><TrendingUp size={20} /></div>
                  <span>Predicted Revenue (Next 6M)</span>
                </div>
                <h3>{formatCurrency(data.predicted_revenue)}</h3>
              </div>
              
              <div className="metric-card glass-panel">
                <div className="metric-header">
                  <div className="metric-icon bg-purple"><Activity size={20} /></div>
                  <span>Forecast Accuracy</span>
                </div>
                <h3>{data.accuracy}%</h3>
              </div>
              
              <div className="metric-card glass-panel highlight">
                <div className="metric-header">
                  <div className="metric-icon bg-gold"><AlertCircle size={20} /></div>
                  <span>AI Insight</span>
                </div>
                <p className="insight-text">{data.insights.recommendation}</p>
              </div>
            </div>

            <div className="charts-grid">
              <div className="chart-card glass-panel main-chart">
                <h3>Sales Growth & Forecast</h3>
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={combinedChartData()} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="month" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
                      <Legend />
                      <Area type="monotone" dataKey="Actual" stroke="#3b82f6" fillOpacity={1} fill="url(#colorActual)" />
                      <Area type="monotone" dataKey="Predicted" stroke="#10b981" fillOpacity={1} fill="url(#colorPred)" strokeDasharray="5 5" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="chart-card glass-panel">
                <h3>Seasonal Trend Analysis</h3>
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={seasonalChartData()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="name" stroke="#94a3b8" tick={{fontSize: 12}} />
                      <YAxis stroke="#94a3b8" />
                      <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} cursor={{fill: '#334155'}} />
                      <Bar dataKey="Sales" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
            
          </div>
        )}
      </main>
    </div>
  )
}

export default App
