### Finding: Delays increase significantly by evening.
- Number: XX% delay rate at 6 PM vs YY% at 6 AM, over millions of flights.
- Caveat: This is correlation, not causation; propagation is likely.
- Query: Step 8.4 (By scheduled departure hour)

### Finding: Delays compound significantly throughout the day due to propagation.
- Number: Delay rate jumps from 7.7% at 6 AM to 30.7% at 6 PM, peaking at 32.8% at 8 PM.
- Caveat: Correlation, but points directly to late-arriving aircraft as the root mechanism.
- Query: Step 8.4 (By scheduled departure hour)

### Finding: Late-arriving aircraft is the #1 cause of all delay minutes.
- Number: 39.8% of all attributed delay minutes, followed by Carrier (33.4%) and NAS (20.4%).
- Caveat: This is a chain effect; the root cause is upstream, which is why propagation matters.
- Query: Step 8.5 (Overall cause breakdown)

### Finding: July 2024 had higher cancellations than July 2025.
- Number: 2.89% cancelled in July 2024 vs. 2.45% in July 2025. (Likely due to the CrowdStrike outage).
- Caveat: We need specific day-level analysis to isolate the CrowdStrike event.
- Query: Step 8.4 (By month)

### Finding: DFW is the most delayed major airport.
- Number: 28.0% delay rate over 629,436 departures.
- Caveat: DFW is a massive hub; hub-and-spoke networks concentrate delays.
- Query: Step 8.3 (Top Airports)