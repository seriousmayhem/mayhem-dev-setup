#!/bin/bash
set -euo pipefail

# Switches the runners behind every workflow by setting two repo variables;
# the workflow files never change. Same script as mayhem-engine and moronmayhem.
#
# Workflows read runs-on from CI_RUNNER_SMALL (gitleaks, release, and the
# ubuntu-24.04 converge leg; 26.04 and Windows legs stay GitHub-hosted, since
# no provider here has those images), falling
# back to ubuntu-26.04 when unset. Use it when one provider's free minutes
# run out or GitHub stops scheduling hosted jobs (a billing hold).
#
# github: hosted runners. LARGE is the same 2 vCPU box, since larger hosted
#   runners are a paid add-on.
# blacksmith: 3000 free min/month, org repos only; the blacksmith-sh app
#   must have access to this repo.
# ubicloud: a small monthly free credit; the ubicloud app must have access.
#
# Usage: scripts/ci/set-runner-provider.sh {github|blacksmith|ubicloud} [--dry-run]

usage() {
  echo "Usage: $0 {github|blacksmith|ubicloud} [--dry-run]" >&2
  exit 1
}

provider="${1:-}"
case "$provider" in
  github)     small=ubuntu-26.04;                large=ubuntu-26.04 ;;
  blacksmith) small=blacksmith-2vcpu-ubuntu-2404; large=blacksmith-4vcpu-ubuntu-2404 ;;
  ubicloud)   small=ubicloud-standard-2;          large=ubicloud-standard-4 ;;
  *) usage ;;
esac

echo "provider $provider: CI_RUNNER_SMALL=$small CI_RUNNER_LARGE=$large"
if [ "${2:-}" = "--dry-run" ]; then
  echo "dry run: no variables changed"
  exit 0
fi
gh variable set CI_RUNNER_SMALL --body "$small"
gh variable set CI_RUNNER_LARGE --body "$large"
echo "set; runs already started keep their runner"
