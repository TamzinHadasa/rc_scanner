# RecentChanges Scanner CLI

This is a configurable scanner for Wikimedia's RecentChanges
EventStreams.

## Setup and configuration

`pip install -r requirements.txt`

Follow the instuctions in `config_example.py` to create your `config.py`
file.

## Running

`scanner.py <filtername> [-v / --verbose]`

The filter name should be one listed in `config.filters`.  `-v` /
`--verbose` instructs the program to print (but not log) non-matches.
All matches will be printed to the command line, and will be logged in
accordance with your `config.LOG_LEVEL`.
