FROM python:3.9-slim

# Install necessary tools and libraries
RUN apt update && \
    apt install -y wireguard-tools curl iptables python3-pip git jq iproute2 procps && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file into the container and install Python packages
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone the PIA manual-connections repo
RUN git clone https://github.com/pia-foss/manual-connections.git /pia-manual

# Copy the Flask app into the container
COPY app.py .

# Create json_files dir
RUN mkdir -p /app/json_files


# Run the Flask app
CMD ["python", "app.py"]
