#!/bin/sh
BUCKET=$1
ENV=$2
DB=$3
HOST="localhost"
if [ $# -lt 3 ]; then
  echo 1>&2 "$0: not enough arguments"
  echo 1>&2 "usage: $0 BUCKET ENV DB [HOST]"
  exit 2
elif [ $# -eq 4 ]; then
    HOST=$4
elif [ $# -gt 4 ]; then
  echo 1>&2 "$0: too many arguments"
  echo 1>&2 "usage: $0 BUCKET ENV DB [HOST]"
  exit 2
fi

S3PATH="s3://$BUCKET/$ENV/$DB"
S3BACKUP="$S3PATH-`date +"%Y%m%d-%H%M%S"`.dump.gz"
S3LATEST="$S3PATH-latest.dump.gz"
/usr/bin/aws s3 mb $S3PATH
/usr/bin/mongodump -h $HOST -d $DB --gzip --archive | aws s3 cp - $S3BACKUP
aws s3 cp $S3BACKUP $S3LATEST
