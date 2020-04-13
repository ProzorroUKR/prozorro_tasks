#!/bin/bash
set -e

python -c "from crawler.tasks import process_feed; process_feed.delay(mode='_all_')"

exec "$@"
