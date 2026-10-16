
# Red-help Enterprise System Project
### Enterprise RAG AI Operations Platform (ERAOP)

An AI-powered infrastructure monitoring and operations platform designed to help administrators monitor databases, servers, and security events through a modern web interface, Retrieval-Augmented Generation (RAG), and Telegram notifications.

## Overview

The Red-help Enterprise System Project aims to simplify infrastructure monitoring by bringing operational information into a centralized platform. It combines monitoring data, AI-assisted analysis, and alert notifications to help administrators understand system conditions, investigate incidents, and identify possible solutions.

## Key Features

- **Database Monitoring:** Connect to a configured database, inspect supported schemas and metadata, and retrieve monitoring information using read-only database access.
- **Server Monitoring:** Integrate with server monitoring tools such as Zabbix to collect infrastructure metrics and health information.
- **Security Monitoring:** Analyze available security logs and events to help identify suspicious activity and potential risks.
- **AI Assistant:** Use Retrieval-Augmented Generation (RAG) to answer infrastructure questions using relevant retrieved context.
- **Intelligent Incident Analysis:** Summarize detected issues, explain possible root causes, and provide recommended troubleshooting steps.
- **Alert Management:** Present monitoring alerts, severity, timestamps, and relevant incident details.
- **Telegram Notifications:** Deliver configured alerts and operational updates to authorized administrators through a Telegram bot.
- **Modern Dashboard:** Provide a centralized interface for viewing monitoring information and interacting with the AI assistant.
- **Secure Access:** Support authentication, role-based permissions, and controlled access to system features.

## System Modules

### 1. Database Monitoring
- Database connectivity and health checks.
- Schema and metadata discovery.
- Read-only data access for monitoring and analysis.
- AI-assisted investigation of database issues.

### 2. Server Monitoring
- Integration with Zabbix or a compatible monitoring source.
- Collection of server health and performance metrics.
- Identification of availability and resource-utilization issues.
- AI-assisted troubleshooting recommendations.

### 3. Security Monitoring
- Analysis of available application, server, and security logs.
- Identification of potentially suspicious events.
- Alert classification and incident summaries.
- Recommendations for investigation and remediation.

### 4. AI and RAG
- Retrieval of relevant operational context.
- Context-aware responses to infrastructure questions.
- Natural-language explanations of monitoring findings.
- Suggested troubleshooting steps based on available evidence.

### 5. Notifications
- Dashboard alerts.
- Telegram notifications for configured events.
- Incident severity and supporting information.
- Administrator-focused operational updates.

## Architecture

The platform follows a modular architecture:

1. User interface
2. API and authentication layer
3. AI orchestration and intent classification
4. Database, server, and security monitoring agents
5. Monitoring data collection
6. Document processing and embedding generation
7. Vector storage and retrieval
8. Context construction and language-model response generation
9. Response validation and alert delivery

The actual components and integrations depend on the configured environment.

## Technology Stack

The intended technology stack includes:

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database | PostgreSQL / Supabase |
| AI architecture | Retrieval-Augmented Generation (RAG) |
| Language model | Configurable provider, such as Groq or Ollama |
| Embeddings | Configurable embedding model |
| Server monitoring | Zabbix |
| Notifications | Telegram Bot API |
| Frontend | Project-configured web technologies |
| Version control | Git and GitHub |

Some integrations may require additional configuration before they are operational.

## Getting Started

### Prerequisites

Install the tools required by your project:

- Python 3.11 or the version supported by your dependencies.
- Git.
- Access to the configured PostgreSQL or Supabase database.
- API credentials for any enabled AI provider.
- Zabbix access if server monitoring is enabled.
- A Telegram bot token if Telegram notifications are enabled.

### 1. Clone the repository

```bash
git clone https://github.com/Ermi21/Red-help-interpise-system-project.git
cd Red-help-interpise-system-project
```

### 2. Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Check the repository for its dependency file. If it contains `requirements.txt`, run:

```powershell
pip install -r requirements.txt
```

If the backend is inside a subfolder, navigate to that folder first and use its dependency file.

### 4. Configure environment variables

Create a local `.env` file using the project's `.env.example` as a template, if provided.

Configure the variables required by your actual application, such as:

- Database connection settings.
- Application database credentials.
- Authentication and JWT secrets.
- AI provider API keys and model configuration.
- Embedding model configuration.
- Zabbix API connection settings.
- Telegram bot token and administrator chat configuration.

Use the variable names expected by the application code. Never commit `.env` files, passwords, API keys, or other secrets to GitHub.

### 5. Start the backend

From the backend directory, activate the virtual environment, install dependencies, and run:

```powershell
uvicorn app.main:app --reload
```

This command assumes the backend package contains `app/main.py` and that the project's configuration supports this entry point.

The API will typically be available at:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs

These URLs are local development addresses, not public deployment links.

## Security

- Use a dedicated, read-only database account for monitoring queries.
- Keep database credentials and API tokens in environment variables.
- Never expose privileged database credentials to the frontend.
- Restrict access to monitoring endpoints and administrative functions.
- Validate AI-generated recommendations before taking operational action.
- Do not allow AI-generated SQL to modify or delete production data.
- Protect security logs and notification destinations.
- Configure production HTTPS, access controls, and secret management before deployment.

## Development Status

This repository is under active development. Features, integrations, and setup instructions may change as implementation progresses.

A successful GitHub push does not by itself confirm that every integration is configured or operational. Refer to the source code and project configuration for the currently implemented functionality.

## Contributing

1. Fork or clone the repository.
2. Create a feature branch.
3. Make and test your changes.
4. Commit your work with a descriptive message.
5. Submit a pull request for review.

## Repository

GitHub: https://github.com/Ermi21/Red-help-interpise-system-project

## License

No license has been specified yet. Add an appropriate `LICENSE` file before distributing the project under an open-source license.

---

**Red-help Enterprise System Project — AI-assisted infrastructure monitoring and operations.**
