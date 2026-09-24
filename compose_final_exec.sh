#!/bin/bash

COMMAND=$1
shift

# `./manage_dev.sh django <cmd>` is shorthand for running manage.py in the
# web container.
if [ "$1" = "django" ]; then
	shift
	COMMAND="$COMMAND exec web python ./manage.py"
fi

echo "Doing $COMMAND $@";

$COMMAND "$@"
