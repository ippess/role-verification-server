# Use the Alpine-based Python image
FROM python:3.9-alpine

# Install build dependencies and required packages
RUN apk --no-cache add build-base libffi-dev openssl-dev

# Set the working directory
WORKDIR /server

# Copy your application code and requirements file
COPY . /server

# Install Python packages
RUN pip install -r requirements.txt

# Set the command to run your application
CMD ["python", "app.py"]