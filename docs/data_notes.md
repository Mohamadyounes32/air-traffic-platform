# BTS Data Notes

### 1. What does one row represent?
One row represents a single domestic flight leg. It is one scheduled flight from an origin airport to a destination airport on a given date.

### 2. Why can't we calculate delay-cause percentages over all flights?
Because the delay cause columns (CarrierDelay, WeatherDelay, NASDelay, SecurityDelay, LateAircraftDelay) are only filled for flights that arrived 15 or more minutes late. They are also empty for cancelled and diverted flights. The cause breakdown describes late flights only, so the share of each cause must be computed against delayed flights, not all flights.

### 3. Which column lets us follow one aircraft through its day?
The `Tail_Number` column. It represents the aircraft's unique registration, which links flights flown by the same plane and is used for calculating delay propagation. To track a plane's day, we combine Tail_Number with FlightDate and sort by scheduled departure time. Note: rows with missing Tail_Number must be excluded from this analysis.


## Decision Rules (Agreed with Mentor)
1. `cancelled` is authoritative: for cancelled flights, ignore times and delays in all delay metrics.
2. Report medians and percentiles alongside averages.
3. Always state the denominator.
4. **Rule 4 (revised):** tail numbers are normalized by restoring a missing leading "N". Any tail that still doesn't match the US registration pattern maps to the `UNKNOWN` aircraft and is excluded from propagation analysis.
5. **Rule 5 (new):** a small number of delayed flights have no recorded cause (cause minutes are all empty). They remain in delayed-flight counts, and cause shares are computed over attributed minutes.

