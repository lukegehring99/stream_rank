#!/bin/bash
# ===========================================
# wait-for-it.sh
# ===========================================
# Use this script to wait for a service to be available
# before starting dependent services
#
# Usage: ./wait-for-it.sh host:port [-t timeout] [-- command args]
#
# Examples:
#   ./wait-for-it.sh mysql:3306 -- echo "MySQL is up"
#   ./wait-for-it.sh mysql:3306 -t 60 -- python -m worker.main
# ===========================================

set -e

WAITFORIT_TIMEOUT=60
WAITFORIT_QUIET=0
WAITFORIT_STRICT=0
WAITFORIT_HOST=""
WAITFORIT_PORT=""
WAITFORIT_CHILD=0

echoerr() {
    if [ "$WAITFORIT_QUIET" -ne 1 ]; then
        echo "$@" 1>&2
    fi
}

usage() {
    cat << USAGE >&2
Usage:
    $0 host:port [-s] [-t timeout] [-- command args]
    
Options:
    host:port       Host and port to test
    -s | --strict   Only execute subcommand if the test succeeds
    -q | --quiet    Don't output any status messages
    -t TIMEOUT      Timeout in seconds, zero for no timeout (default: $WAITFORIT_TIMEOUT)
    -- COMMAND ARGS Execute command with args after the test finishes

Examples:
    $0 mysql:3306 -- echo "MySQL is up"
    $0 mysql:3306 -t 30 -s -- python app.py
    $0 api:8000 --quiet -- curl http://api:8000/health
USAGE
    exit 1
}

wait_for() {
    local wait_host="$1"
    local wait_port="$2"
    
    if [ "$WAITFORIT_TIMEOUT" -gt 0 ]; then
        echoerr "$0: Waiting $WAITFORIT_TIMEOUT seconds for $wait_host:$wait_port"
    else
        echoerr "$0: Waiting for $wait_host:$wait_port without a timeout"
    fi
    
    local start_ts=$(date +%s)
    
    while :; do
        # Try to connect using different methods
        if command -v nc > /dev/null 2>&1; then
            nc -z "$wait_host" "$wait_port" > /dev/null 2>&1
        elif command -v bash > /dev/null 2>&1; then
            (echo > /dev/tcp/"$wait_host"/"$wait_port") > /dev/null 2>&1
        else
            # Fallback: try with timeout command if available
            timeout 1 bash -c "cat < /dev/null > /dev/tcp/$wait_host/$wait_port" 2>/dev/null
        fi
        
        local result=$?
        
        if [ $result -eq 0 ]; then
            local end_ts=$(date +%s)
            echoerr "$0: $wait_host:$wait_port is available after $((end_ts - start_ts)) seconds"
            return 0
        fi
        
        # Check timeout
        local current_ts=$(date +%s)
        if [ "$WAITFORIT_TIMEOUT" -gt 0 ] && [ $((current_ts - start_ts)) -ge "$WAITFORIT_TIMEOUT" ]; then
            echoerr "$0: Timeout occurred after waiting $WAITFORIT_TIMEOUT seconds for $wait_host:$wait_port"
            return 1
        fi
        
        sleep 1
    done
}

wait_for_wrapper() {
    # In order to support SIGINT during timeout, we use the pattern
    # described at http://unix.stackexchange.com/a/57692
    if [ "$WAITFORIT_QUIET" -eq 1 ]; then
        timeout "$WAITFORIT_TIMEOUT" "$0" --quiet --child --host="$WAITFORIT_HOST" --port="$WAITFORIT_PORT" --timeout="$WAITFORIT_TIMEOUT" &
    else
        timeout "$WAITFORIT_TIMEOUT" "$0" --child --host="$WAITFORIT_HOST" --port="$WAITFORIT_PORT" --timeout="$WAITFORIT_TIMEOUT" &
    fi
    local pid=$!
    trap "kill -INT -$pid" INT
    wait $pid
    local result=$?
    if [ $result -ne 0 ]; then
        echoerr "$0: Timeout or error occurred"
    fi
    return $result
}

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        *:* )
            WAITFORIT_HOST=$(printf "%s\n" "$1" | cut -d : -f 1)
            WAITFORIT_PORT=$(printf "%s\n" "$1" | cut -d : -f 2)
            shift 1
            ;;
        --child)
            WAITFORIT_CHILD=1
            shift 1
            ;;
        -q | --quiet)
            WAITFORIT_QUIET=1
            shift 1
            ;;
        -s | --strict)
            WAITFORIT_STRICT=1
            shift 1
            ;;
        -t)
            WAITFORIT_TIMEOUT="$2"
            if [ -z "$WAITFORIT_TIMEOUT" ]; then usage; fi
            shift 2
            ;;
        --timeout=*)
            WAITFORIT_TIMEOUT="${1#*=}"
            shift 1
            ;;
        --host=*)
            WAITFORIT_HOST="${1#*=}"
            shift 1
            ;;
        --port=*)
            WAITFORIT_PORT="${1#*=}"
            shift 1
            ;;
        --)
            shift
            WAITFORIT_CLI=("$@")
            break
            ;;
        --help)
            usage
            ;;
        *)
            echoerr "Unknown argument: $1"
            usage
            ;;
    esac
done

if [ -z "$WAITFORIT_HOST" ] || [ -z "$WAITFORIT_PORT" ]; then
    echoerr "Error: You need to provide a host and port to test."
    usage
fi

# Run the wait
if [ "$WAITFORIT_CHILD" -gt 0 ]; then
    wait_for "$WAITFORIT_HOST" "$WAITFORIT_PORT"
    exit $?
else
    wait_for "$WAITFORIT_HOST" "$WAITFORIT_PORT"
    WAITFORIT_RESULT=$?
fi

# Execute the command if provided
if [ ${#WAITFORIT_CLI[@]} -gt 0 ]; then
    if [ "$WAITFORIT_RESULT" -ne 0 ] && [ "$WAITFORIT_STRICT" -eq 1 ]; then
        echoerr "$0: Strict mode, refusing to execute subprocess"
        exit $WAITFORIT_RESULT
    fi
    exec "${WAITFORIT_CLI[@]}"
else
    exit $WAITFORIT_RESULT
fi
