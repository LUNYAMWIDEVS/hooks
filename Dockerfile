# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Set the environment variable for ImageMagick
ENV IMAGEMAGICK_BINARY=/usr/bin/convert

# Copy the custom policy.xml into the container
COPY policy.xml /etc/ImageMagick-6/policy.xml

# Copy the requirements file into the container
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Ensure the shell script has execution permissions
RUN chmod +x ./set-env.sh

# Run the set-env.sh script on container start and then run the application
CMD ["bash", "-c", "./set-env.sh && python maange.py runserver"]