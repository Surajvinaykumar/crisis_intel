# Crisis Response Intelligence

A lightweight real-time crisis monitoring application that aggregates crisis signals from NASA EONET, UN ReliefWeb, and Twitter, applies machine learning risk prediction, and visualizes events on an interactive map.

![Screenshot 2025-11-18 000951.png]

## Features

- **Multi-Source Data Fetching**: Pulls crisis events from:
  - NASA Natural Events (satellite data)
  - UN Humanitarian Reports (ReliefWeb)
  - Twitter (live reports)

- **SQLite Storage**: Normalized event storage with deduplication

- **ML Risk Prediction**: Lightweight Logistic Regression model predicts major crisis risk

- **Interactive Filtering**: Filter by date range, time window, location (bounding box), and data source

- **Map Visualization**: Folium-based interactive map with color-coded risk levels

- **Lightweight Design**: Optimized for MacBook Air (8 GB RAM)

## Project Structure

```
crisis-response-intel/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .env.example                    # Environment variables template
├── crisis.db                       # SQLite database (created on first run)
├── artifacts/                      # Trained ML models
└── src/
    ├── db.py                       # Database operations
    ├── risk.py                     # Risk scoring
    ├── features.py                 # Feature engineering
    ├── fetchers/
    │   ├── eonet.py               # NASA EONET fetcher
    │   ├── reliefweb.py           # UN ReliefWeb fetcher
    │   └── twitter.py             # Twitter API fetcher
    └── models/
        ├── baseline_classifier.py  # ML model definition
        └── train_baseline.py       # Training script
```

## Setup

### Prerequisites

- Python 3.11 or newer
- Virtual environment support

### Installation

1. **Create and activate virtual environment:**

```bash
python3 -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` and add your Twitter API credentials:

```
TWITTER_API_KEY=JXqnxkcb1O2081nM2Odbx468s
TWITTER_API_SECRET=BBWUSiPVoSs0IrBQxL2mVjLMpGoJ7lIhywQDfQ8TeoXL5ye4rD
```

**Note**: The Twitter fetcher uses OAuth 2.0 client credentials flow (no user consent required).

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

### Workflow

1. **Select Data Sources**: Use the sidebar to select which sources to fetch from (NASA, UN, Twitter)

2. **Fetch Data**: Click "Fetch data" to pull recent crisis events from selected sources

3. **Train ML Model**: Click "Train ML model (tiny)" to train the risk prediction model
   - Requires at least 10 events in the database
   - Model is saved to `artifacts/baseline_crisis_lr.joblib`

4. **Score Events**: Click "Score events (ML)" to predict risk levels for all events
   - Adds `ml_risk` (0 or 1) and `priority_score` (0.0-1.0) to events

5. **Apply Filters**: Use sidebar controls to filter events:
   - **Date Range**: Start and end dates
   - **Time Window**: Last N hours (0 = disabled)
   - **Bounding Box**: Geographic filter (format: `minLon,minLat,maxLon,maxLat`)
   - **Data Sources**: Show/hide specific sources

6. **View Results**:
   - **Table**: Detailed event information with ML risk scores
   - **Map**: Interactive Folium map with color-coded markers:
     - Red: High risk (ml_risk = 1)
     - Green: Low risk (ml_risk = 0)
     - Blue: Not yet scored

## Data Sources

### NASA EONET
- **Endpoint**: https://eonet.gsfc.nasa.gov/api/v3/events
- **Data**: Natural events (wildfires, storms, earthquakes, etc.)
- **Severity Heuristic**: 7.0 for Wildfires/Storms, 5.0 default

### UN ReliefWeb
- **Endpoint**: https://api.reliefweb.int/v1/reports
- **Data**: Humanitarian situation reports
- **Features**: Retry logic with exponential backoff for HTTP 202 responses

### Twitter
- **Endpoint**: https://api.twitter.com/2/tweets/search/recent
- **Authentication**: Bearer token via client credentials (API key + secret)
- **Query**: Crisis-related keywords (earthquake, flood, wildfire, etc.)
- **Geo Extraction**: Uses place bounding box center when available

## Machine Learning

### Model
- **Algorithm**: Logistic Regression (scikit-learn)
- **Features**:
  - `sev`: Event severity
  - `has_coords`: Has geographic coordinates
  - `is_high_type`: High-risk event type
  - `src_eonet`: From NASA EONET
  - `src_relief`: From ReliefWeb

### Label Heuristic
An event is labeled as major crisis risk (1) if:
- Severity >= 6.5, OR
- High-risk type AND has coordinates

Otherwise labeled as low risk (0).

### Training
- Requires at least 10 events in database
- Saves model to `artifacts/baseline_crisis_lr.joblib`
- Displays class distribution after training

## Troubleshooting

### No events fetched
- Check internet connection
- Verify Twitter API credentials in `.env`
- Check console for error messages

### Training fails
- Ensure at least 10 events are in database
- Click "Fetch data" first to populate database

### Map not displaying
- Ensure events have latitude/longitude coordinates
- NASA EONET events always have coordinates
- Twitter events require geo-tagged tweets

### Twitter authentication fails
- Verify API key and secret are correct in `.env`
- Ensure no extra whitespace in credentials
- Check Twitter API rate limits

## Security

- Never commit `.env` file to source control
- API keys are loaded from environment variables only
- Bearer token is stored in memory only (not persisted)

## Performance

- Optimized for 8 GB RAM MacBook Air
- Lightweight Logistic Regression model
- SQLite for minimal memory footprint
- Efficient pandas operations with lazy loading

## License

This is a demonstration project for educational purposes.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
