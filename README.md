# Automated-GA4-Marketing-Analytics-Pipeline
Automated GA4 data pipeline using Python, MySql and Tableau for marketing analysts, ecommerce tracking and daily reporting 


Automated GA4 Marketing Analytics Pipeline
 Project Overview
Built an automated marketing analytics pipeline that extracts website and ecommerce data from Google Analytics 4 (GA4) through the Google Analytics Data API, transforms and cleans the data with Python/Pandas, and loads analysis-ready datasets into MySQL.

The pipeline runs daily and creates a centralized marketing dataset for SQL analysis and future Tableau reporting, reducing the need for repetitive manual GA4 exports.

 Pipeline
GA4 → Google Analytics Data API → Python/Pandas → MySQL → Tableau

Business Problem
Marketing teams need consistent data to understand traffic acquisition, ecommerce behavior, conversions, revenue, and campaign performance. Manually exporting GA4 reports makes recurring analysis inefficient and harder to maintain.

This project automates that workflow and creates a reusable analytics foundation for questions such as:

The current pipeline supports analysis of questions such as:
- Which channels, sources, and devices drive valuable traffic and conversions?
- Where are customers dropping off in the ecommerce journey?
- How much revenue does each session or user generate?



As the pipeline expands to include paid media and cost data, it will support questions such as:
- How do paid campaigns perform based on ROAS, CPA, and CAC?
- Are campaigns profitable after accounting for COGS and other variable costs?
- What is the business's break-even ROAS?


 Pipeline Architecture

              Google Analytics 4
                       │
                       ▼
          Google Analytics Data API
                       │
                 OAuth 2.0
                       │
                       ▼
               Python / Pandas
          Extract • Clean • Transform
                       │
                       ▼
                     MySQL
              ┌────────┴────────┐
              │                 │
          ga4_daily      ga4_funnel_daily
              │                 │
              └────────┬────────┘
                       │
                       ▼
                    Tableau

MySQL serves as the centralized analytics database where cleaned GA4 data can be stored, queried, aggregated, and analyzed using SQL before being used for visualization and reporting.

Technologies Used

| Technology | Purpose |
|---|---|
| Google Analytics 4 | Website and ecommerce analytics |
| Google Analytics Data API | Programmatic GA4 data extraction |
| Google Cloud / OAuth 2.0 | API configuration and authentication |
| Python | ETL pipeline development |
| Pandas | Data cleaning and transformation |
| SQLAlchemy | Python-to-MySQL integration |
| MySQL | Analytics data storage, querying, and analysis |
| launchd | Daily pipeline scheduling on macOS |
| Tableau | Planned Visualization and reporting layer |


Data Pipeline
 1. GA4 Data Extraction

Python connects to GA4 through the *Google Analytics Data API* and retrieves daily acquisition, engagement, ecommerce, and revenue data.

Key dimensions include:
- Date
- Session channel group
- Session source / medium
- Device category

Key metrics include:
- Sessions
- Active users
- New users
- Purchases
- Purchase revenue
- Engagement rate

 2. Data Cleaning & Transformation

The GA4 API response is converted into a Pandas Data Frame and transformed into analysis-ready data.

The pipeline handles:

- Date and numeric type conversion
- Missing values
- Zero-denominator handling
- Consistent column naming
- Monetary and rate formatting

Additional marketing metrics are calculated in Python:
Purchase Conversion Rate = Purchases / Sessions
Revenue per Session = Purchase Revenue / Sessions
Revenue per User = Purchase Revenue / Active Users

 3. MySQL Data Loading

Cleaned data is loaded into the `marketing_analytics` MySQL database.

The pipeline currently maintains two analytics tables:

 ga4_daily

Daily acquisition and performance data containing:

date
channel
source_medium
device
sessions
active_users
new_users
purchases
purchase_revenue
engagement_rate
purchase_conversion_rate
revenue_per_session
revenue_per_user



ga4_funnel_daily

Daily ecommerce event data containing:

date
channel
source_medium
device
view_item
add_to_cart
begin_checkout
purchase

Separating acquisition/performance data from funnel-event data keeps the database easier to query and maintain.

4. Ecommerce Funnel Tracking



A second GA4 API request extracts key ecommerce events:

view_item
    ↓
add_to_cart
    ↓
begin_checkout
    ↓
purchase

Python transforms the event-level API response into a structured daily dataset that can be analyzed by *channel, source/medium, device, and date*.

This provides the foundation for identifying ecommerce drop-off points as more customer data becomes available.


 5. Daily Automation

The pipeline is scheduled using **macOS launchd** and automatically:

Connect to GA4
      ↓
Extract Recent Data
      ↓
Clean & Transform
      ↓
Refresh Recent Records
      ↓
Load into MySQL



A rolling recent-date window is refreshed instead of simply appending new records.

This helps accommodate updated GA4 data while preventing duplicate records in MySQL.


 Data Quality & Validation

API results were compared against GA4 reports to validate ecommerce events and confirm that the pipeline was retrieving the expected data.

During validation, unusually high `add_to_cart` activity relative to product views was identified. Because the website's ecommerce implementation is still being developed, raw event counts are retained while tracking quality continues to be evaluated.

This prevents potentially unreliable tracking behavior from being interpreted as a definitive marketing-performance finding.


Project Status
 Completed

- GA4 Data API integration
- OAuth authentication
- Automated Python extraction pipeline
- Pandas cleaning and transformation
- MySQL database integration
- Acquisition/performance dataset
- Ecommerce funnel dataset
- Calculated revenue and conversion metrics
- Ecommerce event validation
- Rolling recent-data refresh
- Daily local automation

 Next Phase

The core data pipeline is operational. Additional campaign data will be collected before building the final performance dashboard and making stronger marketing recommendations.


 Future Development

- **Meta Ads API** — integrate campaign, spend, impressions, clicks, CTR, and CPC
- **Paid Media Analytics** — calculate ROAS, CPA, CAC, and campaign-level revenue
- **Tableau Dashboard** — visualize acquisition, device performance, revenue, and ecommerce funnel behavior
- **Profitability Layer** — incorporate COGS and variable costs to calculate contribution profit, profit margin, and break-even ROAS
- **Cloud Deployment** — move scheduled execution from a local machine to cloud infrastructure






