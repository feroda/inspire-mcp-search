#!/bin/bash

source $(pwd)/.env

# keep files written into bind mounts owned by the developer
export DOCKER_UID=$(id -u)
export DOCKER_GID=$(id -g)

if [ "x$MY_ENV" != "xdev" ]; then
    echo "Error: MY_ENV for dev environment MUST be set to 'dev'";
    exit 100;
fi

COMMAND="docker compose -p $MY_PROJECT -f compose.yml"
if [ -e "compose.dev.yml" ]; then
    COMMAND="$COMMAND -f compose.dev.yml"
fi
if [ "x$USE_GPU" = "x1" ]; then
    COMMAND="$COMMAND -f compose.gpu.yml"
fi

./compose_final_exec.sh "$COMMAND" "$@"
