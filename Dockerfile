# We use the official Python 3.13 image as our base image and will add our code to it. For more details, see https://hub.docker.com/_/python
FROM python:3.12.4-slim

# We set the working directory to be the /home/speckle directory; all of our files will be copied here.
WORKDIR /home/speckle

# Copy all of our code and assets from the local directory into the /home/speckle directory of the container.
# We also ensure that the user 'speckle' owns these files, so it can access them
# This assumes that the Dockerfile is in the same directory as the rest of the code
COPY . /home/speckle

# uv will manage dependency installation
RUN pip install uv

# Install your package and dependencies
RUN uv pip install -e .

CMD ["python", "main.py", "run"]