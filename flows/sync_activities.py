import argparse
import datetime
from google.cloud import bigquery
import json
import requests

from prefect import flow, task, get_run_logger
from prefect.blocks.system import Secret

STRAVA_MAX_PAGES=100
STRAVA_PAGE_SIZE=100

GBQ_STRAVA_ACTIVITIES_SCHEMA = [
  bigquery.SchemaField("id", "int"),
  bigquery.SchemaField("start_date", "timestamp"),
  bigquery.SchemaField("distance", "numeric"),
  bigquery.SchemaField("elapsed_time", "numeric"),
  bigquery.SchemaField("moving_time", "numeric"),
  bigquery.SchemaField("total_elevation_gain", "numeric")
]

@task
def parse_dates(start_date, end_date):
  if start_date:
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
  else:
    # default to 3 days
    start_date = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.min.time())

  if end_date:
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
  else:
    # default to tomorrow
    end_date = datetime.datetime.combine(datetime.datetime.now() + datetime.timedelta(days=1), datetime.datetime.min.time())

  return start_date, end_date

@task
def get_strava_token():
  strava_client_id = Secret.load("strava-client-id").get()
  strava_secret = Secret.load("strava-secret").get()
  strava_refresh_token = Secret.load("strava-refresh-token").get()

  r = requests.post(
    "https://www.strava.com/oauth/token",
    data={
      "client_id": strava_client_id,
      "client_secret": strava_secret,
      "refresh_token": strava_refresh_token,
      "grant_type": "refresh_token",
    }
  )
  r.raise_for_status()
  tokens = json.loads(r.text)
  return tokens["access_token"]

@task
def fetch_activities_from_strava(strava_token, start_date, end_date):
  logger = get_run_logger()
  logger.info("Starting with params {}, {}".format(start_date, end_date))

  activities = []
  for page_i in range(1, STRAVA_MAX_PAGES + 1):
    r = requests.get(
      "https://www.strava.com/api/v3/athlete/activities",
      headers={"Authorization": "Bearer {}".format(strava_token)},
      params={
        "after": int(start_date.timestamp()),
        "before": int(end_date.timestamp()),
        "page": page_i,
        "per_page": STRAVA_PAGE_SIZE
      }
    )
    r.raise_for_status()
    page_activities = json.loads(r.text)
    for a in page_activities:
      if a.get("type") == "Run":
        activities.append(
          {
            "distance": a.get("distance"),
            "elapsed_time": a.get("elapsed_time"),
            "id": a.get("id"),
            "moving_time": a.get("moving_time"),
            "start_date": a.get("start_date"),
            "total_elevation_gain": a.get("total_elevation_gain"),
          }
        )
      else:
        pass
    if len(page_activities) == 0:
      break
  else:
    raise RuntimeError("Reached max page {} but still not finished.".format(STRAVA_MAX_PAGES))

  return activities

@task
def upsert_activities_to_bigquery(activities):
  logger = get_run_logger()
  logger.info("Started with {} activities to upsert.".format(len(activities)))

  tmp_table_ref = insert_activities_into_temp_table(activities)
  result = apply_merge_query_bigquery(tmp_table_ref)
  logger.info("Bigquery mergre query result: {}".format(result))

def insert_activities_into_temp_table(activities):
  logger = get_run_logger()
  client = bigquery.Client()

  tmp_table_id = "strava_activities_tmp_{}".format(datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f"))
  tmp_table_ref = client.dataset("strava_tmp").table(tmp_table_id)
  tmp_table = bigquery.Table(tmp_table_ref, schema=GBQ_STRAVA_ACTIVITIES_SCHEMA)
  tmp_table.expires=datetime.datetime.utcnow() + datetime.timedelta(days=3)
  client.create_table(tmp_table)

  errors = client.insert_rows_json(tmp_table_ref, activities)
  if errors == []:
    logger.info("Uploaded {} records to bigquery table tmp table {}".format(len(activities), tmp_table_ref))
  else:
    raise RuntimeError("Error(s) writing to Big Query table {}:\n{}".format(tmp_table_ref, errors))
  return tmp_table_ref

def get_merge_query(tmp_tample_id):
  update_set_statement = ", ".join(["activities.{field} = tmp_table.{field}".format(field=f.name) for f in GBQ_STRAVA_ACTIVITIES_SCHEMA])
  insert_fields = ", ".join([f.name for f in GBQ_STRAVA_ACTIVITIES_SCHEMA])
  insert_values = ", ".join(["tmp_table.{}".format(f.name) for f in GBQ_STRAVA_ACTIVITIES_SCHEMA])
  return """
    merge strava.activities
    using (
      select
        *
      from strava_tmp.{tmp_table_id}
    ) as tmp_table
    on activities.id = tmp_table.id
    when matched then
      update set {update_set_statement}
    when not matched then
      insert ({insert_fields}) values({insert_values})
  """.format(
    tmp_tample_id=tmp_tample_id,
    update_set_statement=update_set_statement,
    insert_fields=insert_fields,
    insert_values=insert_values
  )

def apply_merge_query_bigquery(tmp_table_ref):
  merge_query = get_merge_query(tmp_table_ref.table_id)
  client = bigquery.Client()
  query_job = client.query(merge_query)
  return query_job.result()

@flow
def sync_activities(start_date=None, end_date=None):
  start_date, end_date = parse_dates(start_date, end_date)
  strava_token = get_strava_token()
  activities = fetch_activities_from_strava(strava_token, start_date, end_date)
  upsert_activities_to_bigquery(activities)

parser = argparse.ArgumentParser()
parser.add_argument("--start_date", help="", action="store", required=False)
parser.add_argument("--end_date", help="", action="store", required=False)
if __name__=="__main__":
  args = parser.parse_args()
  sync_activities(
    start_date=args.start_date,
    end_date=args.end_date
  )