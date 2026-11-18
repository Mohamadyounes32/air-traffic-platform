import pandas as pd

DENOMINATOR = {"cancel_rate": "scheduled", "delay_rate": "operated"}


def fetch_daily(q, start: str, end: str, group_sql: str) -> pd.DataFrame:
    """Daily flight counts per group. group_sql is a SQL expression you write yourself
    (fine in your own notebook; never build SQL like this from user input in an app)."""
    return q(f"""
        SELECT full_date, day_of_week, is_federal_holiday,
               {group_sql} AS grp,
               COUNT(*)                                               AS scheduled,
               COUNT(*) FILTER (WHERE is_cancelled)                   AS cancelled,
               COUNT(*) FILTER (WHERE NOT is_cancelled)               AS operated,
               COUNT(*) FILTER (WHERE NOT is_cancelled AND dep_del15) AS delayed
        FROM analytics.v_flights
        WHERE full_date BETWEEN DATE '{start}' AND DATE '{end}'
        GROUP BY 1, 2, 3, 4
        ORDER BY 1, 4
    """)


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["full_date"] = pd.to_datetime(out["full_date"])
    out["is_federal_holiday"] = out["is_federal_holiday"].astype(bool)
    out["cancel_rate"] = 100.0 * out["cancelled"] / out["scheduled"]
    out["delay_rate"] = 100.0 * out["delayed"] / out["operated"]
    return out


def _recovery_date(g: pd.DataFrame, tolerance_pts: float, consecutive: int):
    ok = (g["deviation_pts"] <= tolerance_pts).tolist()
    dates = g["full_date"].tolist()
    for i in range(len(ok) - consecutive + 1):
        if all(ok[i:i + consecutive]):
            return dates[i]
    return None


def event_study(daily, event_start, window_end, baseline_weeks=4,
                tolerance_pts=1.0, metric="cancel_rate", consecutive=2):
    """Compare an event window with a same-weekday baseline. Returns (daily detail, summary)."""
    df = add_rates(daily)
    start, end = pd.Timestamp(event_start), pd.Timestamp(window_end)

    baseline = df[(df["full_date"] >= start - pd.Timedelta(weeks=baseline_weeks))
                  & (df["full_date"] < start)
                  & (~df["is_federal_holiday"])]
    expected = (baseline.groupby(["grp", "day_of_week"])[metric]
                .median().rename("expected_rate").reset_index())

    ev = (df[(df["full_date"] >= start) & (df["full_date"] <= end)]
          .merge(expected, on=["grp", "day_of_week"], how="left")
          .sort_values(["grp", "full_date"]))
    ev["deviation_pts"] = ev[metric] - ev["expected_rate"]
    ev["excess_flights"] = ev["deviation_pts"] / 100 * ev[DENOMINATOR[metric]]

    rows = []
    for grp, g in ev.groupby("grp"):
        recovery = _recovery_date(g, tolerance_pts, consecutive)
        until = g if recovery is None else g[g["full_date"] < recovery]
        peak = g.loc[g["deviation_pts"].idxmax()]
        rows.append({
            "group": grp,
            "baseline_rate": round(g["expected_rate"].median(), 2),
            "peak_rate": round(peak[metric], 1),
            "peak_date": peak["full_date"].date(),
            "recovery_date": recovery.date() if recovery is not None else None,
            "days_to_recover": (recovery - start).days if recovery is not None else None,
            "excess_flights": int(round(until["excess_flights"].sum())),
        })
    return ev, pd.DataFrame(rows)