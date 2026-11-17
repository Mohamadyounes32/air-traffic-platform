UPDATE analytics.dim_airport AS d
SET airport_name = m.name,
    latitude     = m.lat,
    longitude    = m.lon
FROM (
    SELECT DISTINCT ON (da.airport_key)
           da.airport_key,
           o.name,
           o.latitude_deg::double precision  AS lat,
           o.longitude_deg::double precision AS lon
    FROM analytics.dim_airport da
    JOIN raw.ourairports_airports o
      ON o.iata_code = da.airport_code
      OR o.ident     = 'K' || da.airport_code
    WHERE o.type IN ('large_airport', 'medium_airport', 'small_airport', 'seaplane_base')
      AND o.iso_country IN ('US', 'PR', 'VI', 'GU', 'MP', 'AS', 'UM')
      AND o.latitude_deg  IS NOT NULL
      AND o.longitude_deg IS NOT NULL
    ORDER BY da.airport_key,
             (o.iata_code = da.airport_code) DESC,
             COALESCE(o.scheduled_service = 'yes', FALSE) DESC,
             CASE o.type WHEN 'large_airport'  THEN 1
                         WHEN 'medium_airport' THEN 2
                         WHEN 'small_airport'  THEN 3
                         ELSE 4 END,
             o.id::int
) AS m
WHERE d.airport_key = m.airport_key;