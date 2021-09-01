"""Configuration data for `scanner`."""
# COPY THIS TO THE MAIN DIRECTORY AND MODIFY AS NEEDED.

# 0:  Log nothing.
# 1:  Log revids to `REVID_LOG`.
# 2:  Also log flagged changes to `FLAGGED_CHANGES`.
# 3:  Also log content of flagged changes to dated subfolder
#     of `LOG_DIR`.
LOG_LEVEL = 3
# Main log directory.
LOG_DIR = 'logs'
# Subdirectory of `LOG_DIR` for copies of changes.
CHANGES_SUBDIR = 'changes'
# File in `LOG_DIR` to list metadata about flagged changes in.
FLAGGED_CHANGES_LOG = 'flagged_changes.json'
# File in `REVID_LOG` to list flagged revids in.
REVID_LOG = 'revids.txt'
