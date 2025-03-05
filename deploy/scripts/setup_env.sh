#!/bin/bash
set -e

# Colors
COLOR_RESET="\033[0m"
COLOR_INFO="\033[32m"
COLOR_WARN="\033[33m"
COLOR_ERROR="\033[31m"

# Configuration
PROJECT_NAME="voice-agent"
VAPI_SIGNUP_URL="https://vapi.ai/signup"
ANTHROPIC_SIGNUP_URL="https://console.anthropic.com/"

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

# Generate a random secure password
generate_password() {
    # Generate a 24-character secure password with letters, numbers, and symbols
    local password=$(tr -dc 'a-zA-Z0-9!@#$%^&*()_+?><~' < /dev/urandom | head -c 24)
    echo "$password"
}

# Generate a random secret key
generate_secret_key() {
    # Generate a 32-character secret key (alphanumeric)
    local secret=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 32)
    echo "$secret"
}

# Main setup function
setup_env() {
    info "Setting up environment for ${PROJECT_NAME}"
    
    # Check prerequisites
    info "Checking prerequisites..."
    check_command "docker"
    check_command "docker-compose"
    check_command "git"
    check_command "python3"
    check_command "pip3"
    
    # Create project directories
    info "Creating project directories..."
    mkdir -p prompts
    mkdir -p knowledge_base
    mkdir -p data/postgres
    mkdir -p data/redis
    mkdir -p data/n8n
    
    # Create .env file
    info "Creating .env file..."
    
    if [ -f .env ]; then
        warn ".env file already exists. Creating .env.new instead."
        ENV_FILE=".env.new"
    else
        ENV_FILE=".env"
    fi
    
    # Generate credentials
    DB_PASSWORD=$(generate_password)
    SECRET_KEY=$(generate_secret_key)
    N8N_PASSWORD=$(generate_password)
    
    # Create environment file
    cat > ${ENV_FILE} << EOF
# Application Settings
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
APP_WORKERS=1
LOG_LEVEL=debug

# Database Settings
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/voice_agent
DB_PASSWORD=${DB_PASSWORD}

# Security
SECRET_KEY=${SECRET_KEY}
TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# CORS
CORS_ORIGINS=*

# API Keys
VAPI_API_KEY=your-vapi-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# N8N Settings
N8N_URL=http://n8n:5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}

# CRM Integration
CRM_TYPE=none
CRM_API_URL=
CRM_API_KEY=

# Phone Settings
DEFAULT_PHONE_NUMBER=
CUSTOMER_SERVICE_NUMBER=

# Storage Settings
PROMPT_TEMPLATES_DIR=./prompts
KNOWLEDGE_BASE_DIR=./knowledge_base

# Redis
REDIS_URL=redis://redis:6379/0
EOF
    
    info "Environment file created at ${ENV_FILE}"
    
    # Copy prompt templates
    info "Copying prompt templates..."
    cp -r ./app/templates/* ./prompts/ || true
    
    # Create example knowledge base items
    info "Creating example knowledge base items..."
    mkdir -p knowledge_base/examples
    
    cat > knowledge_base/examples/business_hours.json << EOF
{
    "id": "business_hours",
    "title": "Business Hours",
    "content": "Our business hours are Monday to Friday from 9:00 AM to 6:00 PM, and Saturday from 10:00 AM to 4:00 PM. We are closed on Sundays and major holidays.",
    "category": "general",
    "tags": ["hours", "schedule"],
    "version": 1
}
EOF
    
    cat > knowledge_base/examples/services.json << EOF
{
    "id": "services",
    "title": "Available Services",
    "content": "We offer the following services: haircuts, color treatments, styling, perms, extensions, and beard trims. Please call us to book an appointment or book online.",
    "category": "services",
    "tags": ["services", "pricing"],
    "version": 1
}
EOF
    
    cat > knowledge_base/examples/location.json << EOF
{
    "id": "location",
    "title": "Location Information",
    "content": "We are located at 123 Main Street, Downtown, New York. We have ample parking available behind the building. The closest subway station is Central Station, just 2 blocks away.",
    "category": "general",
    "tags": ["location", "directions"],
    "version": 1
}
EOF
    
    info "Example knowledge base items created"
    
    # Create Docker Compose override file
    info "Creating docker-compose.override.yml..."
    cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - ./prompts:/app/prompts
      - ./knowledge_base:/app/knowledge_base
    environment:
      - PYTHONPATH=/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    volumes:
      - ./data/postgres:/var/lib/postgresql/data

  redis:
    volumes:
      - ./data/redis:/data

  n8n:
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
    volumes:
      - ./data/n8n:/home/node/.n8n
      - ./n8n/workflows:/tmp/workflows
EOF
    
    info "Docker Compose override file created"
    
    # Setup import script for N8N workflows
    info "Setting up N8N workflow import script..."
    mkdir -p n8n/workflows
    cp -r ./n8n/workflows/* ./n8n/workflows/ || true
    
    # Setup Python virtual environment
    info "Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    info "Environment setup complete!"
    info ""
    info "Next steps:"
    info "1. Update ${ENV_FILE} with your VAPI API key (signup at ${VAPI_SIGNUP_URL})"
    info "2. Update ${ENV_FILE} with your Anthropic API key (signup at ${ANTHROPIC_SIGNUP_URL})"
    info "3. Start the development environment with: make dev-docker"
    info "4. Access the API at: http://localhost:8000/docs"
    info "5. Access N8N at: http://localhost:5678 (admin / ${N8N_PASSWORD})"
    info ""
    info "For production deployment, see documentation in deploy/ directory"
}

# Execute the setup
setup_env