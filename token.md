# Strava Token

Generating the token is a few steps, first go to:

```
https://www.strava.com/oauth/authorize?client_id=<client_id>&redirect_uri=http://localhost&response_type=code&approval_prompt=auto&scope=activity:read_all
```

Save the code and get a refresh token:

```
curl -X POST https://www.strava.com/api/v3/oauth/token -d client_id=<client_id> -d client_secret=<client_secret> -d code=<code> -d grant_type=authorization_code
```

Save the refresh token (and others) in Prefect as blocks.
