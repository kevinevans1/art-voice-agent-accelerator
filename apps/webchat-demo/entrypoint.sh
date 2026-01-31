#!/bin/sh
set -e

# Inject runtime configuration
# This allows setting BACKEND_URL at container runtime instead of build time

if [ -n "$BACKEND_URL" ]; then
    echo "Injecting runtime config: BACKEND_URL=$BACKEND_URL"
    
    # Create runtime config that will be loaded by the app
    cat > /app/dist/runtime-config.js << EOF
window.__RUNTIME_CONFIG__ = {
    BACKEND_URL: "${BACKEND_URL}"
};
EOF

    # Inject the script into index.html
    sed -i 's|</head>|<script src="/runtime-config.js"></script></head>|' /app/dist/index.html
fi

# Start the server
exec serve -s dist -l 3001
