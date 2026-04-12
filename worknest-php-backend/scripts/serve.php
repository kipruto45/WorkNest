<?php

echo "=== WorkNest PHP Backend Server ===\n\n";
echo "Starting local development server...\n\n";
echo "To start the server, run:\n";
echo "  php -S localhost:8000 -t public\n\n";
echo "Then visit: http://localhost:8000/api/health\n\n";
echo "To stop the server, press Ctrl+C\n";

if (php_sapi_name() !== 'cli') {
    echo "\nThis script should be run from command line.\n";
}