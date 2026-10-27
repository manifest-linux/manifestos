#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

docker run --rm --privileged --platform linux/amd64 \
	-v "$PWD:/src" \
	-e MANIFESTOS_VERSION \
	-e MANIFESTOS_HOME_URL \
	-e MANIFESTOS_MIRROR \
	debian:trixie bash /src/mkiso.sh
