#! /usr/bin/env bash
set -e

if [ -z "$(ls -A /gisi/data)" ]; then
   echo "Creating data folder"
   cp -r /gisi/_data/* /gisi/data
else
   echo "Data folder exists"
fi

exec /usr/bin/supervisord