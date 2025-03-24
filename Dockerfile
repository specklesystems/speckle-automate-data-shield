# We use the official Python 3.13 image as our base image and will add our code to it. For more details, see https://hub.docker.com/_/python
FROM python:3.13-slim

# We set the working directory to be the /home/speckle directory; all of our files will be copied here.
WORKDIR /home/speckle

# Copy all of our code and assets from the local directory into the /home/speckle directory of the container.
# We also ensure that the user 'speckle' owns these files, so it can access them
# This assumes that the Dockerfile is in the same directory as the rest of the code
COPY . /home/speckle

# Install tooling needed for legacy builds and wheel installs
RUN pip install --no-cache-dir wheel setuptools==77.0.3

# Preinstall stringcase using legacy build workaround
RUN pip install --no-use-pep517 'stringcase==1.2.0'

# Install all dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set the PYTHONPATH to find modules in src/
ENV PYTHONPATH="/home/speckle/src"

# Set the default command
CMD ["python", "main.py", "run"]
