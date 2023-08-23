FROM python:3.9
WORKDIR /usr/app/src

# requirements
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# bedrock python sdk
RUN wget https://d2eo22ngex1n9g.cloudfront.net/Documentation/SDK/bedrock-python-sdk.zip
RUN unzip bedrock-python-sdk.zip -d bedrock-python-sdk
RUN pip install "bedrock-python-sdk/$(ls -la bedrock-python-sdk | grep -o 'boto3.*.whl' --color=never)"
RUN pip install "bedrock-python-sdk/$(ls -la bedrock-python-sdk | grep -o 'botocore.*.whl' --color=never)"

# code
COPY ./ .

# run
EXPOSE 80
CMD ["streamlit", "run",\
    "--browser.serverAddress", "0.0.0.0",\
    "--server.enableCORS", "False",\
    "--server.port", "80",\
    "/usr/app/src/app.py"]
