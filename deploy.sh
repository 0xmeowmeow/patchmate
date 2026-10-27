#!/usr/bin/env bash
# Deploy to patchmate.meow-meow.io (DreamHost, Passenger). ./deploy.sh -n for a dry run.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
DEST=patchmate.meow-meow.io
rsync -az --delete ${1:-} --exclude-from=- ./ "mm:$DEST/app/" <<'X'
.git/
.venv/
.env
data/
tests/
__pycache__/
.pytest_cache/
X
[ "${1:-}" = "-n" ] && exit 0
rsync -az deploy/passenger_wsgi.py "mm:$DEST/passenger_wsgi.py"
rsync -az --chmod=F755 deploy/app.cgi "mm:$DEST/app.cgi"
rsync -az --chmod=F644 deploy/htaccess "mm:$DEST/.htaccess"
ssh mm "cd $DEST && mkdir -p public tmp data \
  && { [ -x venv/bin/python3 ] || python3 -m venv venv; } \
  && venv/bin/pip install -q -r app/requirements.txt && touch tmp/restart.txt"
echo "deployed: https://$DEST/"
