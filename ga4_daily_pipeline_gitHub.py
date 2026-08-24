
import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    FilterExpression,
    Filter,
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# -----------------------------------
# SETTINGS
# -----------------------------------


PROPERTY_ID = os.getenv("GA4_PROPERTY_ID")

OAUTH_FILE = os.getenv("GOOGLE_OAUTH_FILE")

TOKEN_FILE = str(Path.home() / "ga4_token.json")

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv(
    "MYSQL_DATABASE",
    "marketing_analytics"
)

SCOPES = [ "https://www.googleapis.com/auth/analytics.readonly"]

# -----------------------------------
# VALIDATE ENVIRONMENT VARIABLES
# -----------------------------------
required_vars = {
    "GA4_PROPERTY_ID": PROPERTY_ID,
    "GOOGLE_OAUTH_FILE": OAUTH_FILE,
    "MYSQL_USER": MYSQL_USER,
    "MYSQL_PASSWORD": MYSQL_PASSWORD,
}

missing_vars = [
    name for name, value in required_vars.items()
    if not value
]

if missing_vars:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_vars)}"
    )



# -----------------------------------
# GOOGLE AUTHENTICATION
# -----------------------------------

credentials = None

if os.path.exists(TOKEN_FILE):
    credentials = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES
    )

if not credentials or not credentials.valid:

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            OAUTH_FILE,
            SCOPES
        )

        credentials = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as token:
        token.write(credentials.to_json())


# -----------------------------------
# CONNECT TO GA4
# -----------------------------------

client = BetaAnalyticsDataClient(
    credentials=credentials
)



# -----------------------------------
# EXTRACT ROLLING 3-DAY GA4 WINDOW
# -----------------------------------

request = RunReportRequest(
    property=f"properties/{PROPERTY_ID}",

    dimensions=[
        Dimension(name="date"),
        Dimension(name="sessionDefaultChannelGroup"),
        Dimension(name="sessionSourceMedium"),
        Dimension(name="deviceCategory"),
    ],

    metrics=[
        Metric(name="sessions"),
        Metric(name="activeUsers"),
        Metric(name="newUsers"),
        Metric(name="ecommercePurchases"),
        Metric(name="purchaseRevenue"),
        Metric(name="engagementRate"),
    ],

    date_ranges=[
        DateRange(
            start_date="3daysAgo",
            end_date="yesterday"
        )
    ]
)

response = client.run_report(request)


# -----------------------------------
# CONVERT GA4 RESPONSE TO DATAFRAME
# -----------------------------------

rows = []

for row in response.rows:

    rows.append({
        "date": row.dimension_values[0].value,
        "channel": row.dimension_values[1].value,
        "source_medium": row.dimension_values[2].value,
        "device": row.dimension_values[3].value,
        "sessions": row.metric_values[0].value,
        "active_users": row.metric_values[1].value,
        "new_users": row.metric_values[2].value,
        "purchases": row.metric_values[3].value,
        "purchase_revenue": row.metric_values[4].value,
        "engagement_rate": row.metric_values[5].value,
    })

df = pd.DataFrame(rows)


# -----------------------------------
# CLEAN DATA TYPES
# -----------------------------------

df["date"] = pd.to_datetime(
    df["date"],
    format="%Y%m%d"
)

for column in [
    "sessions",
    "active_users",
    "new_users",
    "purchases",
]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0).astype(int)

for column in [
    "purchase_revenue",
    "engagement_rate",
]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0)


# -----------------------------------
#  CLEAN AND CALCULATE METRICS
# -----------------------------------


df["purchase_revenue"] = df["purchase_revenue"].round(2)

df["engagement_rate"] = df["engagement_rate"].round(4)

df["purchase_conversion_rate"] = (
    df["purchases"] /
    df["sessions"].replace(0, pd.NA)
).fillna(0).round(4)

df["revenue_per_session"] = (
    df["purchase_revenue"] /
    df["sessions"].replace(0, pd.NA)
).fillna(0).round(2)

df["revenue_per_user"] = (
    df["purchase_revenue"] /
    df["active_users"].replace(0, pd.NA)
).fillna(0).round(2)


# -----------------------------------
# CONNECT TO MYSQL
# -----------------------------------

password_encoded = quote_plus(MYSQL_PASSWORD)

engine = create_engine(
    f"mysql+mysqlconnector://"
    f"{MYSQL_USER}:{password_encoded}"
    f"@localhost:3306/{MYSQL_DATABASE}"
)


# -----------------------------------
# REMOVE EXISTING RECORDS FOR REFRESH WINDOW
# -----------------------------------


start_date = df["date"].min()
end_date = df["date"].max()

with engine.begin() as connection:

    connection.execute(
        text("""
            DELETE FROM ga4_daily
            WHERE date BETWEEN :start_date AND :end_date
        """),
        {
            "start_date": start_date,
            "end_date": end_date
        }
    )


# -----------------------------------
#  INSERT FRESH GA4 DAILY DATA
# -----------------------------------

df.to_sql(
    name="ga4_daily",
    con=engine,
    if_exists="append",
    index=False
)

print(
    f"Pipeline completed successfully. "
    f"{len(df)} rows loaded."
)


# -----------------------------------
# EXTRACT ECOMMERCE FUNNEL EVENTS
# -----------------------------------

funnel_request = RunReportRequest(
    property=f"properties/{PROPERTY_ID}",

    dimensions=[
        Dimension(name="date"),
        Dimension(name="sessionDefaultChannelGroup"),
        Dimension(name="sessionSourceMedium"),
        Dimension(name="deviceCategory"),
        Dimension(name="eventName"),
    ],

    metrics=[
        Metric(name="eventCount"),
    ],

    dimension_filter=FilterExpression(
        filter=Filter(
            field_name="eventName",
            in_list_filter=Filter.InListFilter(
                values=[
                    "view_item",
                    "add_to_cart",
                    "begin_checkout",
                    "purchase",
                ]
            ),
        )
    ),

    date_ranges=[
        DateRange(
            start_date="3daysAgo",
            end_date="yesterday"
        )
    ]
)

funnel_response = client.run_report(funnel_request)


# -----------------------------------
# CONVERT FUNNEL DATA TO DATAFRAME
# -----------------------------------

funnel_rows = []

for row in funnel_response.rows:
    funnel_rows.append({
        "date": row.dimension_values[0].value,
        "channel": row.dimension_values[1].value,
        "source_medium": row.dimension_values[2].value,
        "device": row.dimension_values[3].value,
        "event_name": row.dimension_values[4].value,
        "event_count": row.metric_values[0].value,
    })

funnel_df = pd.DataFrame(funnel_rows)


# -----------------------------------
# PROCESS FUNNEL DATA
# -----------------------------------

if not funnel_df.empty:

    funnel_df["date"] = pd.to_datetime(
        funnel_df["date"],
        format="%Y%m%d"
    )

    funnel_df["event_count"] = pd.to_numeric(
        funnel_df["event_count"],
        errors="coerce"
    ).fillna(0).astype(int)

    funnel_daily = (
        funnel_df
        .pivot_table(
            index=[
                "date",
                "channel",
                "source_medium",
                "device",
            ],
            columns="event_name",
            values="event_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    funnel_daily.columns.name = None

    for column in [
        "view_item",
        "add_to_cart",
        "begin_checkout",
        "purchase",
    ]:
        if column not in funnel_daily.columns:
            funnel_daily[column] = 0


    # -----------------------------------
    # REFRESH FUNNEL RECORDS
    # -----------------------------------

    funnel_start_date = funnel_daily["date"].min()
    funnel_end_date = funnel_daily["date"].max()

    with engine.begin() as connection:
        connection.execute(
            text("""
                DELETE FROM ga4_funnel_daily
                WHERE date BETWEEN :start_date AND :end_date
            """),
            {
                "start_date": funnel_start_date,
                "end_date": funnel_end_date,
            }
        )


    # -----------------------------------
    # INSERT FRESH FUNNEL DATA
    # -----------------------------------

    funnel_daily.to_sql(
        name="ga4_funnel_daily",
        con=engine,
        if_exists="append",
        index=False,
    )

    print(
        f"Funnel pipeline completed successfully. "
        f"{len(funnel_daily)} rows loaded."
    )

else:
    print("No ecommerce funnel events found for the refresh window.")