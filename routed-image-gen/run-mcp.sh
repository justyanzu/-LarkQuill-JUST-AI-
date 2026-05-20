#!/bin/bash
# MCP wrapper for routed-image-gen
# Sets PYTHONPATH internally since Gateway blocks it in env
export PYTHONPATH="/root/.openclaw/routed-image-gen/src"
exec /root/.openclaw/routed-image-gen/.venv/bin/python -m routed_image_gen "$@"
