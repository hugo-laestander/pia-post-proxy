# pia-post-proxy
Simple post proxy using pia vpn.

Run the the docker container with the docker-compose.yml.

Make a request to http://127.0.0.1:5000/forward with the additional header "Target-Domain" and optionally "Filename".

The request is then returned like a normal post request. Whitelist websites and specify which headers to forward in the .env