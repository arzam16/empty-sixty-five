#!/bin/sh
# SPDX-License-Identifier: Unlicense

for target in $(make print-targets); do
	make TARGET="$target"
done
