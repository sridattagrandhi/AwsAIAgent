# AI Sales Outreach Agent - AWS Hackathon 2025

## Project Overview
An autonomous AI agent that automates B2B sales outreach using Amazon Bedrock AgentCore, targeting Shopify retailers with personalized cold emails and intelligent follow-up management.

## Architecture
- **Brain**: Amazon Bedrock (nova-pro-v1:0) + AgentCore
- **Tools**: Lambda functions via API Gateway
- **Database**: DynamoDB for lead management
- **Email**: Amazon SES for outreach
- **UI**: Streamlit for demo interface

## Development Timeline (20 Days)

### Week 1: Foundations (Days 1-7)
- [x] Project setup
- [ ] AWS environment configuration
- [ ] Lambda functions (search + email)
- [ ] API Gateway setup
- [ ] DynamoDB table creation

### Week 2: Full Loop (Days 8-14)
- [ ] Bedrock agent configuration
- [ ] Multi-step workflow orchestration
- [ ] Email response monitoring
- [ ] Lead status updates

### Week 3: Polish (Days 15-20)
- [ ] Prompt optimization
- [ ] UI development
- [ ] Performance testing
- [ ] Final presentation prep

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure

# Deploy infrastructure
python deploy.py
```