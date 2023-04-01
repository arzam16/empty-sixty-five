#!/bin/sh
# SPDX-License-Identifier: Unlicense

dir="$(dirname "$0")"
cd "$(realpath "$dir")"

for target in $(make print-targets); do
	make TARGET="$target"
done
