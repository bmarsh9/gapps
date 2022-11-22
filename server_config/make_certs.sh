openssl req -x509 -nodes -days 365 -subj "/C=GB/CN=foo" \
                  -addext "subjectAltName = DNS: 0.0.0.0" \
                  -addext "certificatePolicies = 1.2.3.4" \
                  -newkey rsa:2048 -keyout certs/server.key -out certs/server.crt
