FROM amazonlinux:2
WORKDIR /usr/app/src

# update
RUN yum -y update
RUN yum -y install python3
RUN yum -y install python3-pip
# requirements
COPY requirements.txt requirements.txt
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# BedRock Python SDK
COPY ./download-dependencies.sh .
RUN ./download-dependencies.sh

# code
COPY ./ .

# run
EXPOSE 80
CMD ["streamlit", "run",\
    "--browser.serverAddress", "0.0.0.0",\
    "--server.enableCORS", "False",\
    "--server.port", "80",\
    "--theme.base", "light",\
    "--theme.primaryColor", "purple",\
    "/usr/app/src/app.py"]
