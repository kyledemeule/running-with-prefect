with
this_year as (
  select
    sum(distance) / 1000 as total_distance,
    date_diff(current_date(), date_trunc(current_date(), year), day) as day_of_year,
    date_diff(last_day(current_date(), year), current_date(), day) + 1 as days_remaining
  from strava.activities
  where activity_type = 'Run'
  and date(start_date) >= date_trunc(current_date(), year)
),
this_year_t1 as (
  select
    *,
    total_distance / day_of_year as daily_average,
    (total_distance / day_of_year) * days_remaining + total_distance as end_of_year_pace,
    (2000 - this_year.total_distance) / days_remaining as daily_needed_km
  from this_year
),
this_year_t2 as (
  select
    *,
    daily_needed_km * 7 as weekly_needed_km,
    days_remaining / 7 as weeks_remaining,
    daily_needed_km * 30.5 as monthly_needed_km,
    days_remaining / 30.5 as months_remaining
  from this_year_t1
)
select
  'Current KMs: ' || round(total_distance, 2) || 'KM' || '\n' ||
  'Current end of year KM pace: ' || round(end_of_year_pace, 2) || 'KM' || '\n\n' ||
  'Daily needed KMs for twΩm: ' || round(daily_needed_km, 2) || 'KM (' || round(days_remaining, 2) || ' days left)' || '\n' ||
  'Weekly needed KMs for twΩm: ' || round(weekly_needed_km, 2) || 'KM (' || round(weeks_remaining, 2) || ' weeks left)' || '\n' ||
  'Monthly needed KMs for twΩm: ' || round(monthly_needed_km, 2) || 'KM (' || round(months_remaining, 2) || ' months left)' as status
from this_year_t2


select
  date(date_trunc(start_date, week)) as week,
  sum(distance) / 1000 as total_distance
from strava.activities
where activity_type = 'Run'
and date(start_date) >= date_trunc(current_date(), year)
group by 1
order by 1 asc

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
  *,
  sum(total_distance) over (partition by year order by day_of_year asc rows between unbounded preceding and current row) as cumulative_distance
from day_counts