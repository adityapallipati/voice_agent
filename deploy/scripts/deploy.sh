#!/bin/bash
set -e

# Colors
COLOR_RESET="\033[0m"
COLOR_INFO="\033[32m"
COLOR_WARN="\033[33m"
COLOR_ERROR="\033[31m"

# Configuration
APP_NAME="voice-agent"
REPO_URL=$(git config --get remote.origin.url)
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DEPLOY_DIR="deploy"
ENV="${1:-production}"  # Default to production if not specified

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
    local missing=0
    
    if [ -z "$VAPI_API_KEY" ]; then
        error "VAPI_API_KEY environment variable is not set."
        missing=1
    fi
    
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        error "ANTHROPIC_API_KEY environment variable is not set."
        missing=1
    fi
    
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        error "AWS credentials are not set."
        missing=1
    fi
    
    if [ -z "$DB_PASSWORD" ]; then
        error "DB_PASSWORD environment variable is not set."
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
}

# Validate the deployment environment
check_deploy_env() {
    case $ENV in
        production|staging|development)
            info "Deploying to $ENV environment"
            ;;
        *)
            error "Invalid environment: $ENV. Must be one of: production, staging, development"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."
    
    # Check required commands
    check_command "docker"
    check_command "terraform"
    check_command "aws"
    check_command "jq"
    
    # Check environment variables
    check_env_vars
    
    # Check deployment environment
    check_deploy_env
    
    info "Prerequisites check completed."
}

# Build Docker image
build_image() {
    info "Building Docker image..."
    
    local image_tag="${APP_NAME}:${TIMESTAMP}"
    docker build -t $image_tag .
    
    # Tag with environment
    docker tag $image_tag "${APP_NAME}:${ENV}"
    
    info "Docker image built successfully: $image_tag"
    echo $image_tag
}

# Push image to ECR
push_to_ecr() {
    info "Pushing image to ECR..."
    
    local image_tag=$1
    local aws_region=${AWS_REGION:-us-west-2}
    local aws_account_id=$(aws sts get-caller-identity --query "Account" --output text)
    local ecr_repo="${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com/${APP_NAME}"
    
    # Create repository if it doesn't exist
    aws ecr describe-repositories --repository-names ${APP_NAME} || \
        aws ecr create-repository --repository-name ${APP_NAME}
    
    # Login to ECR
    aws ecr get-login-password --region ${aws_region} | \
        docker login --username AWS --password-stdin ${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com
    
    # Tag and push image
    docker tag ${image_tag} ${ecr_repo}:${TIMESTAMP}
    docker tag ${image_tag} ${ecr_repo}:${ENV}
    docker tag ${image_tag} ${ecr_repo}:latest
    
    docker push ${ecr_repo}:${TIMESTAMP}
    docker push ${ecr_repo}:${ENV}
    docker push ${ecr_repo}:latest
    
    info "Image pushed to ECR: ${ecr_repo}:${TIMESTAMP}"
    echo ${ecr_repo}:${TIMESTAMP}
}

# Deploy with Terraform
deploy_terraform() {
    info "Deploying with Terraform..."
    
    local image_url=$1
    cd ${DEPLOY_DIR}/terraform
    
    # Initialize Terraform
    terraform init
    
    # Create tfvars file if it doesn't exist
    if [ ! -f "${ENV}.tfvars" ]; then
        warn "${ENV}.tfvars file not found. Creating from example..."
        cp terraform.tfvars.example ${ENV}.tfvars
        
        # Update values in tfvars file
        sed -i "s|your-ecr-repo-url|${image_url%:*}|g" ${ENV}.tfvars
        sed -i "s|latest|${TIMESTAMP}|g" ${ENV}.tfvars
        sed -i "s|development|${ENV}|g" ${ENV}.tfvars
    else
        # Update only the image tag
        sed -i "s|image_tag = \".*\"|image_tag = \"${TIMESTAMP}\"|g" ${ENV}.tfvars
    fi
    
    # Apply Terraform
    terraform plan -var-file="${ENV}.tfvars" -out=tfplan
    terraform apply -auto-approve tfplan
    
    info "Terraform deployment completed successfully."
}

# Set up database
setup_database() {
    info "Setting up database..."
    
    # Get database endpoint from Terraform output
    cd ${DEPLOY_DIR}/terraform
    local db_endpoint=$(terraform output -json db_endpoint | jq -r .)
    
    # Run migrations
    info "Running database migrations..."
    export DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@${db_endpoint}/voice_agent"
    alembic upgrade head
    
    info "Database setup completed."
}

# Import prompt templates
import_prompts() {
    info "Importing prompt templates..."
    
    # Get API URL from Terraform output
    cd ${DEPLOY_DIR}/terraform
    local api_url=$(terraform output -json api_url | jq -r .)
    
    # Import each template from prompts directory
    for template_file in ../../prompts/*.txt; do
        template_name=$(basename $template_file .txt)
        template_content=$(cat $template_file)
        
        info "Importing template: $template_name"
        curl -X POST "${api_url}/api/v1/prompts" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"${template_name}\", \"content\": $(echo $template_content | jq -Rs .), \"description\": \"Imported template\"}"
    done
    
    info "Prompt templates imported successfully."
}

# Main deployment function
main() {
    info "Starting deployment of $APP_NAME to $ENV environment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Build and push image
    local image_tag=$(build_image)
    local image_url=$(push_to_ecr $image_tag)
    
    # Deploy infrastructure
    deploy_terraform $image_url
    
    # Setup database and import prompts
    setup_database
    import_prompts
    
    info "Deployment completed successfully!"
    
    # Get API URL
    cd ${DEPLOY_DIR}/terraform
    local api_url=$(terraform output -json api_url | jq -r .)
    info "API is now available at: $api_url"
}

# Execute main function
main