# Use an official Python runtime as a parent image
FROM python:3.13

# Install cron
RUN apt-get update && apt-get install -y cron


# Set the working directory
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Copy the cron job file into the cron.d directory
COPY cronjob /etc/cron.d/cronjob

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/cronjob

# Apply the cron job
RUN crontab /etc/cron.d/cronjob

# # Run the command on container startup
CMD cron && tail -f /app_log/cron.log

# Run the command on container startup
# CMD ["/usr/local/bin/python", "/app/main.py"]
# CMD ["tail", "-f", "/dev/null"]
