from google.oauth2 import service_account
from google.cloud import bigquery
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt
from decimal import Decimal

st.title('Running with Prefect')
st.markdown("""
This is the visualization of the data from an activate pipeline to stream Strava activitiy data to Bigquery using Prefect.
Code for the pipeline can be found at https://github.com/kyledemeule/running-with-prefect.

One goal of this runner is to run a distance of 2,000KM in a single year (aka two mega-meters). So far they've never done it, but hopefully the pace and projections below can help them achieve that.
""")

# auth
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = bigquery.Client(credentials=credentials)

@st.cache_data(ttl=600)
def bq_run_query(query):
    query_job = client.query(query)
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows

# Weekly counts
st.subheader("Weekly Distance")
weekly_counts_query = """
select
  date(date_trunc(start_date, week)) as week,
  sum(distance) / 1000 as weekly_distance
from strava.activities
where activity_type = 'Run'
and date(start_date) >= date_trunc(current_date(), year)
group by 1
order by 1 asc
"""
weekly_count_data = bq_run_query(weekly_counts_query)
weekly_count_df = pd.DataFrame(weekly_count_data)
weekly_count_df["weekly_distance"] = pd.to_numeric(weekly_count_df["weekly_distance"])
c = alt.Chart(weekly_count_df).mark_bar().encode(
  x="week",
  y="weekly_distance"
)
st.altair_chart(c, use_container_width=True)

# Cumulative Distance
st.subheader("Annual Cumulative Distance Comparison")
cumulative_distance_query = """
with
day_counts as (
  select
    extract(year from start_date) as year,
    date_diff(start_date, date_trunc(start_date, year), day) + 1 as day_of_year,
    sum(distance) / 1000 as total_distance,
  from strava.activities
  where activity_type = 'Run'
  and start_date >= '2020-01-01'
  group by 1, 2
)
select
  year,
  day_of_year,
  sum(total_distance) over (partition by year order by day_of_year asc rows between unbounded preceding and current row) as cumulative_distance
from day_counts
"""

cd_data = bq_run_query(cumulative_distance_query)
cd_df = pd.DataFrame(cd_data)
cd_df["cumulative_distance"] = pd.to_numeric(cd_df["cumulative_distance"])
cd_df["year"] = cd_df["year"].astype("string")
c = alt.Chart(cd_df).mark_line().encode(
  x="day_of_year",
  y="cumulative_distance",
  color="year"
)
st.altair_chart(c, use_container_width=True)

current_year_distance_query = """
select
  sum(distance) / 1000 as current_year_distance
from strava.activities
where activity_type = 'Run'
and date(start_date) >= date_trunc(current_date(), year)
"""

# Stats
st.subheader("Pace and Projections")
current_year_data = bq_run_query(current_year_distance_query)
current_year_kms = current_year_data[0]["current_year_distance"]
day_of_year = datetime.now().timetuple().tm_yday
eoy_pace_km = (current_year_kms * 365) / day_of_year
days_remaining = 365 - day_of_year
daily_needed_kms = (2000 - current_year_kms) / days_remaining

st.write("Current pace and projections for reaching two mega-meters (2,000 KM).")
lines = [
  "Current year KMs: {:.2f} KM".format(round(current_year_kms, 2)),
  "Current end of year KM pace: {:.2f} KM\n".format(round(eoy_pace_km, 2)),
  "",
  "Daily needed KMs for twΩm: {:.2f} KM ({} days left)".format(round(daily_needed_kms, 2), days_remaining),
  "Weekly needed KMs for twΩm: {:.2f} KM ({} weeks left)".format(round(daily_needed_kms * 7, 2), round(days_remaining / 7, 2)),
  "Monthly needed KMs for twΩm: {:.2f} KM ({} months left)".format(round(daily_needed_kms * Decimal(30.5), 2), round(days_remaining / Decimal(30.5), 2))
]
st.code("\n".join(lines))
