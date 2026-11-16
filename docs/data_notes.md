# BTS Data Notes

### 1. What does one row represent?
One row represents a single domestic flight leg. It is one scheduled flight from an origin airport to a destination airport on a given date.

### 2. Why can't we calculate delay-cause percentages over all flights?
Because the delay cause columns (CarrierDelay, WeatherDelay, NASDelay, SecurityDelay, LateAircraftDelay) are only filled for flights that arrived 15 or more minutes late. They are also empty for cancelled and diverted flights. The cause breakdown describes late flights only, so the share of each cause must be computed against delayed flights, not all flights.

### 3. Which column lets us follow one aircraft through its day?
The `Tail_Number` column. It represents the aircraft's unique registration, which links flights flown by the same plane and is used for calculating delay propagation. To track a plane's day, we combine Tail_Number with FlightDate and sort by scheduled departure time. Note: rows with missing Tail_Number must be excluded from this analysis. 