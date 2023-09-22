# running-with-prefect

This repo contains code for a [Prefect](https://www.prefect.io/) flow to sync activity data from my [Strava](https://www.strava.com/) account to [Bigquery](https://cloud.google.com/bigquery).

The data is visualized and available at [https://running-with-prefect.calmtech.link/](https://running-with-prefect.calmtech.link/).

## Running

Set up a pyenv:

```
pyenv install 3.10.11
pyenv virtualenv 3.10.11 rwp
pyenv activate rwp
pip install -r requirements.txt
```

Then run a sync like:
```
python flows/sync_activities.py
```

This will sync the past 3 days. Can sync specific date ranges like:
```
python flows/sync_activities.py --start_date=2023-01-01 --end_date=2023-05-01
```

## Deploy

Run:
```
prefect deployment apply sync_activities-deployment.yaml
```

### Docker

Build image:
```
docker buildx build --platform linux/amd64 -t running-with-prefect:v1 .
docker tag running-with-prefect:v1 us-west1-docker.pkg.dev/running-with-prefect/running-with-prefect/running-with-prefect:v1
docker push us-west1-docker.pkg.dev/running-with-prefect/running-with-prefect/running-with-prefect:v1
```

```
prefect deployment build flows/sync_activities.py:sync_activities -n sync_activities -sb github/github-running-with-prefect -ib cloud-run-job/gcp-cloud-run-running-with-prefect -o sync_activities-deployment.yaml --apply
```

## Streamlit

Run locally with:
```
streamlit run streamlit/app.py 
```
