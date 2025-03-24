# We use the official Python 3.13 image as our base image and will add our code to it. For more details, see https://hub.docker.com/_/python
FROM python:3.13-slim

# We set the working directory to be the /home/speckle directory; all of our files will be copied here.
WORKDIR /home/speckle

# Copy all of our code and assets from the local directory into the /home/speckle directory of the container.
# We also ensure that the user 'speckle' owns these files, so it can access them
# This assumes that the Dockerfile is in the same directory as the rest of the code
COPY . /home/speckle

# Install the required packages directly using pip
RUN pip install --no-cache-dir -r requirements.txt