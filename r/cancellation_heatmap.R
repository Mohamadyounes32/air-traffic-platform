library(DBI)
library(RPostgres)
library(dplyr)
library(ggplot2)
library(lubridate)

readRenviron(".env")   # reuses the same DB settings as the Python code

con <- dbConnect(
  RPostgres::Postgres(),
  host = Sys.getenv("DB_HOST"), port = as.integer(Sys.getenv("DB_PORT")),
  dbname = Sys.getenv("DB_NAME"), user = Sys.getenv("DB_USER"),
  password = Sys.getenv("DB_PASSWORD"),
  bigint = "numeric"        # counts arrive as plain numbers, not integer64
)

daily <- dbGetQuery(con, "
  SELECT full_date, day_of_week,
         COUNT(*) AS scheduled,
         COUNT(*) FILTER (WHERE is_cancelled) AS cancelled
  FROM analytics.v_flights
  GROUP BY 1, 2
")
dbDisconnect(con)

daily <- daily |>
  mutate(
    full_date   = as.Date(full_date),
    cancel_rate = 100 * cancelled / scheduled,
    week_start  = floor_date(full_date, "week", week_start = 1),
    weekday     = factor(day_of_week, levels = 7:1,
                         labels = rev(c("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")))
  )

p <- ggplot(daily, aes(x = week_start, y = weekday, fill = pmin(cancel_rate, 15))) +
  geom_tile(color = "white", linewidth = 0.2) +
  scale_fill_viridis_c(option = "magma", direction = -1,
                       name = "Cancelled %\n(capped at 15)") +
  labs(title = "Daily cancellation rate, US domestic flights, 2024-2025",
       x = NULL, y = NULL,
       caption = "Source: BTS On-Time Performance (reporting carriers). Share of scheduled flights cancelled.") +
  theme_minimal(base_size = 12) +
  theme(panel.grid = element_blank())

ggsave("docs/cancellation_heatmap_r.png", p, width = 12, height = 3.2, dpi = 150)