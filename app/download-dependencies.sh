#!/bin/sh

set -e

echo "(Re)-creating directory"
rm -rf ./dependencies
mkdir ./dependencies
cd ./dependencies

echo "Downloading dependencies"
curl -sS https://d2eo22ngex1n9g.cloudfront.net/Documentation/SDK/bedrock-python-sdk.zip > sdk.zip

echo "Unpacking dependencies"
if command -v unzip &> /dev/null
then
    unzip sdk.zip && rm sdk.zip && echo "Done"
else
    echo "'unzip' command not found: Trying to unzip via Python"
    python3 -m zipfile -e sdk.zip . && rm sdk.zip && echo "Done"
fi

echo "Installing dependencies"
python3 -m pip install --no-build-isolation --force-reinstall \
    awscli-*-py3-none-any.whl \
    boto3-*-py3-none-any.whl \
    botocore-*-py3-none-any.whl

echo "Ok"
