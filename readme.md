# RecentChanges Scanner CLI

This is a configurable scanner for Wikimedia's RecentChanges
EventStreams.

## Setup and configuration

`pip install -r requirements.txt`

Follow the instuctions in `config_example.py` to create your `config.py`
file.

## Running

Regex matches will be printed to the CLI and logged to a dated
subdirectory of the changes subdirectory. Include the `-v` / `--verbose`
flag when running the script to also print (but not log) non-matches.
