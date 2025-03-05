# Voice Agent System

A production-ready voice agent system that handles both inbound and outbound calls using VAPI, N8N, and Python. This system provides a complete solution for businesses to automate customer interactions through voice.

## Features

- Inbound call handling for:
  - Answering general questions
  - Booking appointments
  - Rescheduling appointments
  - Cancelling appointments
  - Human handoff when needed
- Outbound call capabilities for:
  - Follow-up calls
  - Appointment reminders
  - Sales and marketing campaigns
- Integration with:
  - VAPI for voice processing
  - N8N for workflow automation
  - LLMs (Claude/GPT) for intelligence
  - CRM systems and calendars
  - Knowledge bases

## System Architecture

The system consists of the following components:

- **FastAPI Backend**: Core API service
- **PostgreSQL Database**: Data storage
- **Redis**: Caching and queue management
- **N8N**: Workflow automation
- **VAPI Integration**: Voice call handling
- **Claude/GPT Integration**: Natural language processing

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- N8N instance
- VAPI account with API key
- Anthropic API key (or other LLM provider)
- PostgreSQL 15+
- Redis 7+

## Local Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/voice-agent.git
cd voice-agent
```

### 2. Create environment file

```bash
cp .env.example .env
```

Update the `.env` file with your API keys and configuration.

### 3. Set up development environment

```bash
# Using the Makefile
make setup
make install-deps

# OR manually
pip install -r requirements.txt
```

### 4. Start the local development environment

```bash
# Using Docker (recommended)
make dev-docker

# OR using local Python
make dev
```

### 5. Run database migrations

```bash
make migrate
```

### 6. Import example prompt templates

```bash
cp -r prompts/* app/templates/
```

## Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make test-cov
```

## Project Structure

```
voice_agent/
├── app/                      # Application source code
│   ├── api/                  # API endpoints
│   ├── core/                 # Core functionality
│   ├── db/                   # Database models and config
│   ├── models/               # Pydantic models
│   └── services/             # Business logic services
├── deploy/                   # Deployment configurations
│   ├── kubernetes/           # Kubernetes manifests
│   ├── terraform/            # Terraform IaC files
│   └── scripts/              # Deployment scripts
├── n8n/                      # N8N workflow definitions
├── prompts/                  # Prompt templates
└── tests/                    # Test suite
```

## API Documentation

When running the development server, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment

### AWS Deployment using Terraform

1. Set up AWS credentials

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-west-2
```

2. Update Terraform variables

```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration.

3. Initialize and apply Terraform

```bash
terraform init
terraform plan
terraform apply
```

### Kubernetes Deployment

1. Update Kubernetes manifests in `deploy/kubernetes/`
2. Apply the manifests:

```bash
kubectl apply -f deploy/kubernetes/
```

## N8N Workflow Setup

1. Import the workflow files from `n8n/workflows/` into your N8N instance
2. Configure the webhook URLs to point to your deployed API
3. Set the API key in N8N credentials

## Environment Variables

Key environment variables that need to be configured:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development, production) | development |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://postgres:postgres@db:5432/voice_agent |
| `REDIS_URL` | Redis connection string | redis://redis:6379/0 |
| `VAPI_API_KEY` | VAPI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `N8N_URL` | N8N instance URL | http://n8n:5678 |
| `SECRET_KEY` | App secret key | - |

## Customization Guide

### Adding New Prompt Templates

1. Create a new text file in the `prompts/` directory
2. Use the API to upload it to the database:

```bash
curl -X POST http://localhost:8000/api/v1/prompts \
  -H "Content-Type: application/json" \
  -d '{"name": "your_template_name", "content": "Your prompt template content", "description": "Description"}'
```

### Adding Knowledge Base Items

```bash
curl -X POST http://localhost:8000/api/v1/knowledge \
  -H "Content-Type: application/json" \
  -d '{"title": "Item Title", "content": "Item content", "category": "general", "tags": ["faq", "hours"]}'
```

### Configuring CRM Integration

Update the `app/core/crm.py` file with your CRM provider's API endpoints and authentication methods.

## Monitoring and Logging

- Application logs are sent to stdout/stderr and can be collected by container orchestration systems
- Health check endpoint is available at `/health`
- Metrics can be collected via Prometheus integration (if enabled)

## Security Considerations

- All API keys are stored as environment variables, not in code
- Database passwords are securely managed via environment variables
- HTTPS is enforced in production
- Rate limiting is applied to API endpoints
- Authentication is required for admin operations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.