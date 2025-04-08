# Use an official Python runtime as a parent image
FROM python:3.13

# Set the working directory
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Run the command on container startup
CMD ["/usr/local/bin/python", "/app/main.py"]
# CMD ["tail", "-f", "/dev/null"]
