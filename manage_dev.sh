#!/bin/bash

source $(pwd)/.env

if [ "x$MY_ENV" != "xdev" ]; then
    echo "Error: MY_ENV for dev environment MUST be set to 'dev'";
    exit 100;
fi

COMMAND="docker compose -p $MY_PROJECT -f compose.yml"
if [ -e "compose.dev.yml" ]; then
    COMMAND="$COMMAND -f compose.dev.yml"
fi

echo "Doing $COMMAND $@";

$COMMAND "$@"
