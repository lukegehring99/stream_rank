#!/bin/bash
# ===========================================
# MySQL Initialization Script
# ===========================================
# This script runs when the MySQL container starts for the first time
# It sets up the database, user, and permissions
# ===========================================

set -e

echo "=========================================="
echo "Initializing StreamRank Database..."
echo "=========================================="

# Function to execute MySQL commands
mysql_exec() {
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "$@"
}

# Wait for MySQL to be ready
wait_for_mysql() {
    echo "Waiting for MySQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" --silent 2>/dev/null; then
            echo "MySQL is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: MySQL not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: MySQL did not become ready in time"
    return 1
}

# Create database if it doesn't exist
create_database() {
    echo "Creating database '${MYSQL_DATABASE}' if not exists..."
    mysql_exec -e "CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    echo "Database created successfully!"
}

# Create user and grant permissions
setup_user() {
    echo "Setting up user '${MYSQL_USER}'..."
    
    # Create user if not exists
    mysql_exec -e "CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';"
    
    # Grant all privileges on the database
    mysql_exec -e "GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';"
    
    # Flush privileges
    mysql_exec -e "FLUSH PRIVILEGES;"
    
    echo "User setup complete!"
}

# Set MySQL configuration for better performance
configure_mysql() {
    echo "Applying MySQL configurations..."
    
    mysql_exec -e "
        SET GLOBAL max_connections = 200;
        SET GLOBAL innodb_buffer_pool_size = 268435456;
        SET GLOBAL innodb_log_file_size = 67108864;
        SET GLOBAL slow_query_log = 1;
        SET GLOBAL long_query_time = 2;
    " 2>/dev/null || echo "Some MySQL configurations may require restart"
    
    echo "MySQL configurations applied!"
}

# Verify setup
verify_setup() {
    echo "Verifying database setup..."
    
    # Check database exists
    if mysql_exec -e "USE ${MYSQL_DATABASE};" 2>/dev/null; then
        echo "✓ Database '${MYSQL_DATABASE}' exists"
    else
        echo "✗ Database '${MYSQL_DATABASE}' not found!"
        return 1
    fi
    
    # Check user can connect
    if mysql -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" -h localhost -e "SELECT 1;" 2>/dev/null; then
        echo "✓ User '${MYSQL_USER}' can connect"
    else
        echo "✗ User '${MYSQL_USER}' cannot connect!"
        return 1
    fi
    
    echo "Verification complete!"
}

# Main execution
main() {
    echo ""
    echo "Environment variables:"
    echo "  MYSQL_DATABASE: ${MYSQL_DATABASE}"
    echo "  MYSQL_USER: ${MYSQL_USER}"
    echo ""
    
    # Note: When running as docker-entrypoint-initdb.d script,
    # MySQL is already initialized, so we skip waiting
    
    create_database
    setup_user
    # configure_mysql  # Uncomment if you want to apply custom configs
    verify_setup
    
    echo ""
    echo "=========================================="
    echo "StreamRank Database Initialization Complete!"
    echo "=========================================="
    echo ""
}

# Run main function
main
