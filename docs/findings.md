### Finding: Delays increase significantly by evening.
- Number: XX% delay rate at 6 PM vs YY% at 6 AM, over millions of flights.
- Caveat: This is correlation, not causation; propagation is likely.
- Query: Step 8.4 (By scheduled departure hour)

### Finding: Delays compound significantly throughout the day due to propagation.
- Number: Delay rate jumps from 7.7% at 6 AM to 30.7% at 6 PM, peaking at 32.8% at 8 PM.
- Caveat: Correlation, but points directly to late-arriving aircraft as the root mechanism.
- Query: Step 8.4 (By scheduled departure hour)

### Finding: Most flights leave on time or early, but a substantial minority leave very late.
- Number: At DFW (the worst major hub), 28% leave 15+ min late, and 1 in 10 leaves > 60 min late.
- Caveat: Top 5 airports are within 2% of each other, so ranking is weak. We need the system-wide baseline.
- Query: Step 8.3 (Top Airports)

### Finding: Late-arriving aircraft is the #1 cause of all delay minutes.
- Number: 39.8% of all attributed delay minutes, followed by Carrier (33.4%) and NAS (20.4%).
- Caveat: Weather is recorded as the direct cause of only 6.2%, but the true weather share is higher and hidden across NAS and late-arriving categories.
- Query: Step 8.5 (Overall cause breakdown)

### Finding: July cancellations are seasonally high in both years.
- Number: 2.89% in July 2024 vs. 2.45% in July 2025.
- Caveat: Monthly view cannot isolate specific events like the CrowdStrike outage; we need a daily view.
- Query: Step 8.4 (By month)

### Finding: The system-wide delay rate is 21.2%, with a median of -2 minutes and a p90 of 45 minutes.
- Number: 13.88M operated flights; 21.2% delayed 15+ mins. DFW's 28% is worse than average but not an outlier.
- Caveat: Averages mislead because most flights are on time, while a large minority leave very late.
- Query: Step 8b (System-wide baseline)

### Finding: January 2024 cancellations were overwhelmingly weather-driven.
- Number: 3.73% total cancellation rate; 2.21% due to weather (code B), 1.41% due to carrier (code A).
- Caveat: Monthly view cannot isolate specific winter storms, but the seasonal weather signal is undeniable.
- Query: Step 8b (Cancellation causes by month)

### Finding: The CrowdStrike outage caused a massive, prolonged impact for Delta specifically.
- Number: Delta's cancellation rate spiked to 47.4% on July 21, 2024, while all other airlines were at 3.6%. Delta's recovery took over a week.
- Caveat: The outage was a specific event, but the data clearly isolates Delta's vulnerability.
- Query: Step 8b (Delta vs others)

### Finding: Scheduled ground time acts as a buffer to absorb inbound delays.
- Number: When an aircraft arrives 90+ min late, the next departure is delayed 99.5% of the time if ground time is <45 min, but drops to 65.0% if ground time is 90+ min.
- Caveat: Association, not causation. But the buffer effect is strongly supported by the data.
- Query: Step 8b (Propagation table)

### Finding: Taxi-out time increases with airport load, but the effect varies by hub.
- Number: At ORD, median taxi-out goes from 15.5 min at <25% load to 24.75 min at >100% load. At ATL, it only goes from 14.0 to 16.0 min.
- Caveat: Time of day is tangled with load, so we can't fully isolate congestion from daily propagation patterns.
- Query: Step 8b (Congestion chart)### Finding: The system-wide delay rate is 21.2%, with a median of -2 minutes and a p90 of 45 minutes.
- Number: 13.88M operated flights; 21.2% delayed 15+ mins. DFW's 28% is worse than average but not an outlier.
- Caveat: Averages mislead because most flights are on time, while a large minority leave very late.
- Query: Step 8b (System-wide baseline)

### Finding: January 2024 cancellations were overwhelmingly weather-driven.
- Number: 3.73% total cancellation rate; 2.21% due to weather (code B), 1.41% due to carrier (code A).
- Caveat: Monthly view cannot isolate specific winter storms, but the seasonal weather signal is undeniable.
- Query: Step 8b (Cancellation causes by month)

### Finding: The CrowdStrike outage caused a massive, prolonged impact for Delta specifically.
- Number: Delta's cancellation rate spiked to 47.4% on July 21, 2024, while all other airlines were at 3.6%. Delta's recovery took over a week.
- Caveat: The outage was a specific event, but the data clearly isolates Delta's vulnerability.
- Query: Step 8b (Delta vs others)

### Finding: Scheduled ground time acts as a buffer to absorb inbound delays.
- Number: When an aircraft arrives 90+ min late, the next departure is delayed 99.5% of the time if ground time is <45 min, but drops to 65.0% if ground time is 90+ min.
- Caveat: Association, not causation. But the buffer effect is strongly supported by the data.
- Query: Step 8b (Propagation table)

### Finding: Taxi-out time increases with airport load, but the effect varies by hub.
- Number: At ORD, median taxi-out goes from 15.5 min at <25% load to 24.75 min at >100% load. At ATL, it only goes from 14.0 to 16.0 min.
- Caveat: Time of day is tangled with load, so we can't fully isolate congestion from daily propagation patterns.
- Query: Step 8b (Congestion chart)

### Finding: System-wide delay rate is 21.2% (median -2 mins, p90 45 mins).
- Number: 13.88M operated flights. DFW is 6.8 points above average (28%), but the top 5 airports are within 2 points of each other, so ranking is weak.
- Query: Step 8b (System-wide baseline)

### Finding: Delta and Endeavor suffered disproportionately during CrowdStrike.
- Number: Delta peaked at 47.4% cancellation, Endeavor at 49.0%. Others peaked at 10.9% and recovered in 2 days. Delta and Endeavor took 5-6 days to recover.
- Caveat: This shows magnitude and duration, not cause. Endeavor operates as Delta Connection.
- Query: Step 8c (Event study)

### Finding: Scheduled ground time acts as a buffer, but the 13.9% vs 10.3% gap persists across all times of day.
- Number: For 90+ min late inbound flights, next departure delay is 99.5% (<45m ground), 75.6% (120-179m ground), and 46.6% (180+m ground).
- Caveat: The time-of-day check showed the gap is not a Simpson's paradox. Long ground times might simply be scheduled for inherently delayed routes/hubs.
- Query: Step 8c (Propagation checks)

### Finding: Anomaly detection found a massive event in November 2025 (z=61.8).
- Number: 2025-11-08 to 2025-11-13 had a 12.1% cancellation rate. Other explained events: CrowdStrike (July 2024), Hurricane Milton (Oct 2024), Hurricane Debby (Aug 2024).
- Query: Step 8c (Anomaly detection)

### Finding: November 2025 cancellations strongly align with the FAA flight-reduction order.
- Number: The gap between affected airports (40 major hubs) and other flights widened from ~0 pts before Nov 7 to 9.9 pts on Nov 9. The cancellation cause was overwhelmingly `NAS` (National Air System), peaking at 7.61% on Nov 9.
- Caveat: The gap narrowed after Nov 11, but airlines didn't exactly hit the mandated percentages (4%-10%), likely due to practical constraints. The "other flights" group also saw a slight bump, likely due to network effects.