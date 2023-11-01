import os
import subprocess
import re
import requests
from flask import Flask, jsonify, request
from flask import abort

app = Flask(__name__)

# Constants
PIA_LOCATION_API = "https://www.privateinternetaccess.com/site-api/get-location-info"
PIA_EXPOSED_CHECK_API = "https://www.privateinternetaccess.com/site-api/exposed-check"
PIA_ENV_VARS = [
    'VPN_PROTOCOL', 'DISABLE_IPV6', 'MAX_LATENCY', 'DIP_TOKEN', 'AUTOCONNECT',
    'PIA_PF', 'PIA_DNS', 'PIA_USER', 'PIA_PASS'
]
WHITELISTED_DOMAINS = os.environ.get('WHITELISTED_DOMAINS', '') 
ENSURE_VPN = os.environ.get('ENSURE_VPN', 'false').lower() == 'true'

def get_pia_env_vars():
    """Get the environment variables for PIA commands."""
    return {key: os.environ.get(key) for key in PIA_ENV_VARS if os.environ.get(key)}

def establish_vpn_connection():
    """Switch to a different VPN server using PIA's scripts."""
    complete_env = {**os.environ, **get_pia_env_vars()}
    subprocess.run(["bash", "run_setup.sh"], cwd="/pia-manual", capture_output=True, text=True, env=complete_env)

def is_vpn_connected():
    """Check if we are using a VPN connection by getting the public IP and validating against PIA."""
    location_info_json = requests.get(PIA_LOCATION_API).json()
    ip_address = location_info_json.get('ip')

    exposed_check_response = requests.post(
        PIA_EXPOSED_CHECK_API,
        json={"ipAddress": ip_address},
        headers={"Content-Type": "application/json"}
    )
    return not exposed_check_response.json().get('status')  # True if not exposed (i.e., protected by PIA)

def save_response_to_file(response):
    """Save the response to a file and make sure filename is safe."""
    filename = request.headers.get('Filename')
    if filename:
        main, ext = os.path.splitext(filename)
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '', main) + ext
        filepath = os.path.join("/app/json_files", safe_filename)
        if response.content and 'application/json' in response.headers.get('Content-Type', ''):
            with open(filepath, 'w') as f:
                f.write(jsonify(response.json()).data.decode())


@app.route('/connect_vpn', methods=['GET'])
def connect_vpn():
    establish_vpn_connection()
    return check_vpn_connection()

@app.route('/check_vpn', methods=['GET'])
def check_vpn_connection():
    if is_vpn_connected():
        return jsonify(status="success", message="You are protected by PIA.")
    else:
        return jsonify(status="error", message="Your IP is exposed and not protected by PIA."), 400

@app.route('/forward', methods=['POST'])
def forward_request():
    if ENSURE_VPN and not is_vpn_connected():
        connect_vpn()
        if not is_vpn_connected():
            return jsonify(status="error", message="Failed to establish VPN connection."), 503

    target_domain = request.headers.get('Target-Domain')
    if not target_domain or target_domain not in WHITELISTED_DOMAINS:
        return jsonify(status="error", message="Invalid or missing Target-Domain."), 403

    forward_headers = os.environ.get('FORWARD_HEADERS', "").split(',')
    filtered_headers = {header: value for header, value in request.headers.items() if header in forward_headers}
    response = requests.post(target_domain, json=request.json, headers=filtered_headers)

    # Save response to file if filename is specified in headers
    save_response_to_file(response)
                
    # Check if response has content and if the content type is JSON
    if response.content and 'application/json' in response.headers.get('Content-Type', ''):
        return jsonify(response.json()), response.status_code
    else:
        return response.text, response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
