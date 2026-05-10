#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat >&2 <<'EOF'
Refusing to loop uninstall/install.

That would inflate install_count with non-user installs and make the skill look
less trustworthy once people inspect the activity. Use the real growth helper
instead.
EOF

exec "$SCRIPT_DIR/grow_metric_brand_auditor.sh" "${@:-run}"
