# RecentChanges Scanner CLI & Logger

This is a configurable scanner for Wikimedia's RecentChanges
EventStreams.

## Setup and configuration

`pip install -r requirements.txt`

Copy `examples/config.py` and `examples/filterlist.py` to the main
directory and modify them as needed.

## Running

`scanner.py <filtername> [-v / --verbose]`

The filter name should be one listed in `filterlist.filterlist`.  `-v` /
`--verbose` instructs the program to print (but not log) non-matches.
All matches will be printed to the command line, and will be logged in
accordance with your `config.LOG_LEVEL`.
