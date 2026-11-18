-- @@ national
WITH pending AS (
    SELECT p.poll_id, p.api_time, p.states_total, p.states_kept
    FROM raw.opensky_poll p
    WHERE p.http_status = 200 AND p.api_time IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM analytics.live_national n WHERE n.poll_id = p.poll_id)
), classified AS (
    SELECT pe.poll_id, s.on_ground,
           (s.latitude IS NOT NULL AND s.time_position IS NOT NULL
            AND pe.api_time - s.time_position <= INTERVAL '60 seconds') AS fresh
    FROM pending pe
    JOIN raw.opensky_states s ON s.poll_id = pe.poll_id
)
INSERT INTO analytics.live_national
    (poll_id, api_time, states_total, states_kept, fresh_airborne, fresh_on_ground, fresh_share_pct)
SELECT pe.poll_id, pe.api_time, pe.states_total, pe.states_kept,
       COUNT(*) FILTER (WHERE c.fresh AND NOT COALESCE(c.on_ground, FALSE)),
       COUNT(*) FILTER (WHERE c.fresh AND COALESCE(c.on_ground, FALSE)),
       ROUND(100.0 * COUNT(*) FILTER (WHERE c.fresh) / NULLIF(COUNT(c.poll_id), 0), 2)
FROM pending pe
LEFT JOIN classified c ON c.poll_id = pe.poll_id
GROUP BY pe.poll_id, pe.api_time, pe.states_total, pe.states_kept;

-- @@ grid
WITH done AS (
    SELECT DISTINCT hour_utc FROM analytics.live_grid_hourly
), hours AS (
    SELECT date_trunc('hour', api_time) AS hour_utc, COUNT(*) AS polls_in_hour
    FROM raw.opensky_poll
    WHERE http_status = 200 AND api_time IS NOT NULL
      AND api_time < date_trunc('hour', now())
    GROUP BY 1
), todo AS (
    SELECT h.hour_utc, h.polls_in_hour
    FROM hours h LEFT JOIN done d ON d.hour_utc = h.hour_utc
    WHERE d.hour_utc IS NULL
), per_poll AS (
    SELECT t.hour_utc, p.poll_id,
           (floor(s.latitude  / 2) * 2)::smallint AS cell_lat,
           (floor(s.longitude / 2) * 2)::smallint AS cell_lon,
           COUNT(*) AS airborne
    FROM todo t
    JOIN raw.opensky_poll p   ON date_trunc('hour', p.api_time) = t.hour_utc AND p.http_status = 200
    JOIN raw.opensky_states s ON s.poll_id = p.poll_id
    WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
      AND NOT COALESCE(s.on_ground, FALSE)
      AND s.time_position IS NOT NULL
      AND p.api_time - s.time_position <= INTERVAL '60 seconds'
    GROUP BY t.hour_utc, p.poll_id, 3, 4
)
INSERT INTO analytics.live_grid_hourly
    (hour_utc, cell_lat, cell_lon, avg_airborne, max_airborne, polls_in_hour)
SELECT pp.hour_utc, pp.cell_lat, pp.cell_lon,
       ROUND(SUM(pp.airborne)::numeric / t.polls_in_hour, 2),
       MAX(pp.airborne),
       t.polls_in_hour
FROM per_poll pp
JOIN todo t ON t.hour_utc = pp.hour_utc
GROUP BY pp.hour_utc, pp.cell_lat, pp.cell_lon, t.polls_in_hour;

-- @@ retention
DELETE FROM raw.opensky_states s
USING raw.opensky_poll p
WHERE p.poll_id = s.poll_id
  AND p.api_time < now() - make_interval(days => %(keep_days)s)
  AND EXISTS (SELECT 1 FROM analytics.live_national n WHERE n.poll_id = p.poll_id)
  AND EXISTS (SELECT 1 FROM analytics.live_grid_hourly g
              WHERE g.hour_utc = date_trunc('hour', p.api_time));