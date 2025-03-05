# N8N Setup Guide for Voice Agent System

This guide covers how to set up and configure N8N for use with the Voice Agent system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Importing Workflows](#importing-workflows)
- [Setting Up Credentials](#setting-up-credentials)
- [Webhook Setup](#webhook-setup)
- [Workflow Execution](#workflow-execution)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- N8N installed (version 0.214.0 or higher recommended)
- Voice Agent API running and accessible
- VAPI API key
- Access to the Voice Agent system database and Redis

## Installation

### Using Docker (Recommended)

N8N is already included in the main docker-compose.yml file. You can start it with:

```bash
docker-compose up -d n8n
```

### Using NPM

If you prefer to run N8N separately:

```bash
npm install -g n8n
n8n start
```

## Configuration

1. Access the N8N web interface at http://localhost:5678 (default) or your configured URL
2. Log in with the credentials from your .env file:
   - Username: admin (default)
   - Password: your configured password

### Environment Variables

Set the following environment variables for N8N:

```
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your-password
WEBHOOK_URL=http://n8n:5678/
```

In production, set the proper hostname and use HTTPS:

```
N8N_HOST=n8n.your-domain.com
N8N_PROTOCOL=https
WEBHOOK_URL=https://n8n.your-domain.com/
```

## Importing Workflows

### Automatic Import

The easiest way to import the workflows is to use the provided script:

```bash
bash deploy/scripts/import_n8n_workflows.sh
```

This script will:
1. Import all workflow files from the `n8n/workflows/` directory
2. Update existing workflows if they already exist
3. Activate workflows that should be active

### Manual Import

To manually import workflows:

1. Go to the Workflows tab in N8N
2. Click "Import from File"
3. Select a workflow JSON file from the `n8n/workflows/` directory
4. Confirm the import

## Setting Up Credentials

The workflows require the following credentials:

### HTTP Request Authentication

1. Go to Settings > Credentials
2. Click "Create New"
3. Select "HTTP Request Authentication"
4. Choose "Header Auth" as the authentication type
5. Set the name to "Voice Agent API Auth"
6. Set the "Name" parameter to "Authorization"
7. Set the "Value" parameter to "Bearer your-secret-key" (from your .env file)
8. Save the credential

### VAPI Authentication

1. Go to Settings > Credentials
2. Click "Create New"
3. Select "HTTP Request Authentication"
4. Choose "Header Auth" as the authentication type
5. Set the name to "VAPI Auth"
6. Set the "Name" parameter to "Authorization"
7. Set the "Value" parameter to "Bearer your-vapi-api-key"
8. Save the credential

## Webhook Setup

### Inbound Call Webhook

The inbound call workflow is triggered by a webhook from VAPI. Configure VAPI to call your N8N webhook URL:

1. In VAPI dashboard, set up a virtual phone number
2. Configure the webhook URL to: `https://your-n8n-url/webhook/inbound-call`
3. Make sure this URL is publicly accessible

### Testing Webhooks

To test the webhook:

1. In the N8N editor, select the "VAPI Webhook" node
2. Click on "Test" tab
3. Click "Test Webhook" button
4. You can use the provided test payload to simulate a call

## Workflow Execution

### Inbound Call Processing

The `inbound_call.json` workflow handles:

1. Receiving call data from VAPI
2. Processing the transcript using the Voice Agent API
3. Determining the customer's intent
4. Directing the call to appropriate endpoints based on intent
5. Generating responses back to VAPI

### Outbound Call Processing

The `outbound_call.json` workflow handles:

1. Scheduling regular checks for pending callbacks
2. Fetching callback details
3. Generating appropriate call scripts
4. Making outbound calls via VAPI
5. Updating callback status

## Customizing Workflows

### Modifying Environment-Specific Settings

Each workflow contains a "Prepare API Request" node that sets the API URL based on the environment. To customize:

1. Edit the workflow
2. Find the "Prepare API Request" node
3. Modify the `environments` object to include your environments and URLs

Example:
```javascript
const environments = {
  production: "https://api.voice-agent.your-domain.com",
  staging: "https://api-staging.voice-agent.your-domain.com",
  development: "http://localhost:8000"
};
```

### Setting Default Phone Numbers

You can set default phone numbers in the workflow data:

1. Go to workflow settings (gear icon)
2. Under "Workflow Data" tab, add:
```json
{
  "company_phone_number": "+15551234567",
  "customer_service_number": "+15557654321"
}
```

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Data**
   - Check if your N8N instance is publicly accessible
   - Verify VAPI webhook configuration
   - Check N8N logs for any errors

2. **API Connection Failures**
   - Verify the API URL in the "Prepare API Request" node
   - Check if the API is running and accessible
   - Validate the authentication credentials

3. **Workflow Execution Errors**
   - Check the execution logs in N8N
   - Enable debug mode in the workflow settings
   - Verify all required parameters are being passed

### Logging

To enable more detailed logging:

1. Set the `N8N_LOG_LEVEL` environment variable to `debug`
2. Restart N8N
3. Check the logs for more information

```bash
export N8N_LOG_LEVEL=debug
docker-compose restart n8n
```

### Getting Support

If you encounter issues not covered in this guide:

1. Check the N8N documentation: https://docs.n8n.io/
2. Review the Voice Agent system documentation
3. Contact support or create an issue in the project repository