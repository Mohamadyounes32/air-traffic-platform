UPDATE analytics.dim_airport AS d
SET airport_name = m.name,
    latitude     = m.lat,
    longitude    = m.lon
FROM (
    SELECT DISTINCT ON (iata_code)
           iata_code,
           name,
           latitude_deg::double precision  AS lat,
           longitude_deg::double precision AS lon
    FROM raw.ourairports_airports
    WHERE iata_code IS NOT NULL
      AND type IN ('large_airport', 'medium_airport', 'small_airport', 'seaplane_base')
      AND iso_country IN ('US', 'PR', 'VI', 'GU', 'MP', 'AS', 'UM')
      AND latitude_deg IS NOT NULL
      AND longitude_deg IS NOT NULL
    ORDER BY iata_code,
             COALESCE(scheduled_service = 'yes', FALSE) DESC,
             CASE type WHEN 'large_airport'  THEN 1
                       WHEN 'medium_airport' THEN 2
                       WHEN 'small_airport'  THEN 3
                       ELSE 4 END,
             id::int
) AS m
WHERE d.airport_code = m.iata_code;