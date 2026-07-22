# Repair incomplete mock ADT tyre surveys

This repair only targets draft Tyre Surveys created by `Mock Survey Generator`
between 1 January and 30 June 2026. It does not modify real/manual surveys.

It completes every targeted survey to six positions. Standard ADTs use
`LF, RF, LM, RM, LR, RR`. B60/B60E ADTs use
`LF, RF, LRO, LRI, RRI, RRO`.

Run the dry-run first, then apply only after reviewing the returned counts.
