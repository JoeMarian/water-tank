# /Users/joemarian/water-tank/Dockerfile
# Use a Python 3.13 slim image based on Debian Bookworm
FROM python:3.13-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the ports that your applications will use
# FastAPI uses 8000 TCP
EXPOSE 8000
# CoAP server uses 5684 UDP
EXPOSE 5684/udp

# The command to run the services will be specified in docker-compose.yml