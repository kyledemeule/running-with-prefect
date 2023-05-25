# running-with-prefect

This repo contains code for a [Prefect](https://www.prefect.io/) flow to sync activity data from my [Strava](https://www.strava.com/) account to [Bigquery](https://cloud.google.com/bigquery).

The data is visualized and available at [https://running-with-prefect.streamlit.app/](https://running-with-prefect.streamlit.app/).

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
