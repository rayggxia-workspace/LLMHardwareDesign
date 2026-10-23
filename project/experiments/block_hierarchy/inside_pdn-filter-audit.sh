#!/usr/bin/env bash
# Same isolated read-only source audit, with in-memory parent via-site selection.
export LLHD_PG_FILTER_AUDIT=1
source "$LLHD_ATTEMPT/inside_pdn-audit.sh"
