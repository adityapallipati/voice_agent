#!/bin/bash
set -e

# Colors
COLOR_RESET="\033[0m"
COLOR_INFO="\033[32m"
COLOR_WARN="\033[33m"
COLOR_ERROR="\033[31m"

# Configuration
N8N_URL="${N8N_URL:-http://localhost:5678}"
N8N_API_KEY="${N8N_API_KEY:-admin:password}"
WORKFLOWS_DIR="./n8n/workflows"

# Print info message
info() {
    echo -e "${COLOR_INFO}[INFO] $1${COLOR_RESET}"
}

# Print warning message
warn() {
    echo -e "${COLOR_WARN}[WARN] $1${COLOR_RESET}"
}

# Print error message
error() {
    echo -e "${COLOR_ERROR}[ERROR] $1${COLOR_RESET}" >&2
}

# Check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "$1 is required but not installed. Please install it first."
        exit 1
    fi
}

# Check required environment variables
check_env_vars() {
    if [ -z "$N8N_API_KEY" ]; then
        warn "N8N_API_KEY environment variable is not set. Using default credentials."
    fi
    
    if [ -z "$N8N_URL" ]; then
        warn "N8N_URL environment variable is not set. Using default URL: http://localhost:5678"
    fi
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."
    
    # Check required commands
    check_command "curl"
    check_command "jq"
    
    # Check environment variables
    check_env_vars
    
    # Check if workflows directory exists
    if [ ! -d "$WORKFLOWS_DIR" ]; then
        error "Workflows directory not found: $WORKFLOWS_DIR"
        exit 1
    fi
    
    info "Prerequisites check completed."
}

# Get authentication header
get_auth_header() {
    if [[ "$N8N_API_KEY" == *":"* ]]; then
        # Basic auth (username:password)
        echo "-u $N8N_API_KEY"
    else
        # API key auth
        echo "-H 'X-N8N-API-KEY: $N8N_API_KEY'"
    fi
}

# Import a workflow
import_workflow() {
    local workflow_file=$1
    local workflow_name=$(jq -r '.name' $workflow_file)
    local auth_header=$(get_auth_header)
    
    info "Importing workflow: $workflow_name"
    
    # Check if workflow already exists
    local existing_workflows=$(curl -s $auth_header "${N8N_URL}/api/v1/workflows")
    
    if echo $existing_workflows | jq -e ".data[] | select(.name == \"$workflow_name\")" > /dev/null; then
        local workflow_id=$(echo $existing_workflows | jq -r ".data[] | select(.name == \"$workflow_name\") | .id")
        info "Workflow '$workflow_name' already exists with ID: $workflow_id. Updating..."
        
        # Update existing workflow
        curl -s $auth_header \
             -X PUT \
             -H "Content-Type: application/json" \
             -d @$workflow_file \
             "${N8N_URL}/api/v1/workflows/$workflow_id" > /dev/null
        
        info "Workflow '$workflow_name' updated successfully."
    else
        # Create new workflow
        curl -s $auth_header \
             -X POST \
             -H "Content-Type: application/json" \
             -d @$workflow_file \
             "${N8N_URL}/api/v1/workflows" > /dev/null
        
        info "Workflow '$workflow_name' imported successfully."
    fi
}

# Activate a workflow
activate_workflow() {
    local workflow_file=$1
    local workflow_name=$(jq -r '.name' $workflow_file)
    local auth_header=$(get_auth_header)
    
    # Get workflow ID
    local workflows=$(curl -s $auth_header "${N8N_URL}/api/v1/workflows")
    local workflow_id=$(echo $workflows | jq -r ".data[] | select(.name == \"$workflow_name\") | .id")
    
    if [ -z "$workflow_id" ] || [ "$workflow_id" == "null" ]; then
        warn "Cannot activate workflow '$workflow_name': Workflow not found."
        return
    fi
    
    info "Activating workflow: $workflow_name (ID: $workflow_id)"
    
    # Activate workflow
    curl -s $auth_header \
         -X POST \
         -H "Content-Type: application/json" \
         -d '{"active": true}' \
         "${N8N_URL}/api/v1/workflows/$workflow_id/activate" > /dev/null
    
    info "Workflow '$workflow_name' activated successfully."
}

# Import all workflows
import_workflows() {
    info "Importing workflows from $WORKFLOWS_DIR..."
    
    # Find all JSON files in the workflows directory
    local workflow_files=$(find $WORKFLOWS_DIR -type f -name "*.json")
    
    if [ -z "$workflow_files" ]; then
        warn "No workflow files found in $WORKFLOWS_DIR"
        return
    fi
    
    # Import each workflow
    for workflow_file in $workflow_files; do
        import_workflow $workflow_file
    done
    
    info "All workflows imported successfully."
}

# Activate all workflows
activate_workflows() {
    info "Activating workflows..."
    
    # Find all JSON files in the workflows directory
    local workflow_files=$(find $WORKFLOWS_DIR -type f -name "*.json")
    
    # Activate each workflow
    for workflow_file in $workflow_files; do
        # Check if the workflow should be active
        local should_activate=$(jq -r '.active // false' $workflow_file)
        
        if [ "$should_activate" == "true" ]; then
            activate_workflow $workflow_file
        fi
    done
    
    info "All workflows activated successfully."
}

# Main function
main() {
    info "Starting N8N workflow import..."
    
    # Check prerequisites
    check_prerequisites
    
    # Import workflows
    import_workflows
    
    # Activate workflows
    activate_workflows
    
    info "N8N workflow import completed successfully!"
}

# Execute main function
main