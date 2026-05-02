
        # Generate private key
        openssl genrsa -out certs/localhost-key.pem 2048
        
        # Generate certificate
        openssl req -new -x509 -key certs/localhost-key.pem -out certs/localhost.pem -days 365 -subj "/C=US/ST=Local/L=Local/O=Alice/CN=localhost"
        