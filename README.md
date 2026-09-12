# Cleanroom control ledger

This Python service coordinates operating-room pressure boundaries, environmental evidence and safety workflows. Rooms and pressure edges form a directed cleanliness graph. Evidence, commands, incidents and workflow revisions are stored in SQLite so a process can be reconciled after restart without replaying a device command.

Run `python -m unittest discover -s tests -v` for the integration suite or `python -m cleanroom --demo` for a pressure-commissioning example.
