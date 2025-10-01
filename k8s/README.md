# ACM Agent OpenShift Deployment

This directory contains Kubernetes manifests to deploy the ACM Agent with OAuth authentication on OpenShift.

## Architecture

```
User → Route (HTTPS) → OAuth Proxy → Streamlit App
         ↓               ↓             ↓
    TLS Termination  OpenShift Auth  ACM Agent
```

## Prerequisites

1. **OpenShift cluster** with admin access
2. **Container registry** access (quay.io, Docker Hub, or internal registry)
3. **API keys** for OpenAI and MCP server
4. **Docker** or **Podman** for building images

## Quick Start

### 1. Copy Templates to Working Files

The `templates/` directory contains clean template files. Copy them to create your working configuration:

```bash
cd k8s/
cp templates/*.template .
# Remove .template extension
for file in *.template; do mv "$file" "${file%.template}"; done
```

### 2. Build Container Image

From the project root directory:

```bash
# Build with your registry
./build.sh latest your-registry/namespace --push

# Example:
./build.sh latest quay.io/youruser --push
```

### 3. Update Configuration

Edit the copied files with your values:

**k8s/secret.yaml:**
```yaml
stringData:
  openai-api-key: "sk-your-actual-openai-key"
  mcp-bearer-token: "your-actual-mcp-token"

  # For proxy-secret, generate a random secret:
  # python -c "import secrets; print(secrets.token_urlsafe(32))"
  session_secret: "your-generated-random-secret"
```

**k8s/configmap.yaml:**
```yaml
data:
  mcp-server-url: "https://your-mcp-server.example.com/sse"
```

**k8s/route.yaml:**
```yaml
spec:
  host: acm-agent.apps.your-cluster.example.com
```

**k8s/deployment.yaml:**
```yaml
- name: streamlit-app
  image: your-registry/acm-agent:latest
```

### 4. Deploy to OpenShift

```bash
# Create namespace and RBAC
oc apply -f k8s/namespace.yaml
oc apply -f k8s/serviceaccount.yaml

# Create configuration
oc apply -f k8s/configmap.yaml
oc apply -f k8s/secret.yaml

# Deploy application
oc apply -f k8s/service.yaml
oc apply -f k8s/deployment.yaml
oc apply -f k8s/route.yaml
```

### 5. Verify Deployment

```bash
# Check pods
oc get pods -n acm-agent

# Check route
oc get route -n acm-agent

# Check logs
oc logs -f deployment/acm-agent -c streamlit-app -n acm-agent
oc logs -f deployment/acm-agent -c oauth-proxy -n acm-agent
```

## Authentication Flow

1. User visits the route URL
2. OAuth proxy redirects to OpenShift login
3. After authentication, user is redirected back
4. OAuth proxy forwards requests to Streamlit app
5. Streamlit app receives user info in headers:
   - `X-Remote-User`: Username
   - `X-Remote-Group`: User groups

## Configuration

### Environment Variables

The app is configured via ConfigMap and Secret:

| Variable | Source | Description |
|----------|--------|-------------|
| `OPENAI_API_KEY` | Secret | OpenAI API key |
| `MCP_BEARER_TOKEN` | Secret | MCP server token |
| `MODEL_PROVIDER` | ConfigMap | LLM provider (openai) |
| `MODEL_NAME` | ConfigMap | Model name (gpt-4o) |
| `MODEL_TEMPERATURE` | ConfigMap | Temperature (0.01) |
| `MCP_SERVER_URL` | ConfigMap | MCP server URL |
| `MCP_TRANSPORT` | ConfigMap | Transport type (sse) |

### OAuth Proxy Configuration

The OAuth proxy is configured to:
- Require OpenShift authentication
- Delegate authorization to namespace access
- Use service CA for TLS
- Forward user headers to app

## Troubleshooting

### Common Issues

**1. OAuth Proxy failing to start:**
```bash
# Check service account permissions
oc describe sa acm-agent -n acm-agent

# Check TLS certificate
oc get secret acm-agent-tls -n acm-agent -o yaml
```

**2. Streamlit app not receiving headers:**
```bash
# Check logs for auth debugging
oc logs deployment/acm-agent -c streamlit-app -n acm-agent | grep AUTH
```

**3. Route not accessible:**
```bash
# Check route status
oc describe route acm-agent -n acm-agent

# Check if host is correct
oc get route acm-agent -n acm-agent -o jsonpath='{.spec.host}'
```

### Development Mode

For development without OAuth proxy, set environment variables:
```bash
export DEV_USER="your-username@example.com"
export DEV_GROUPS="system:authenticated,acm-users"
```

## Security Notes

- OAuth proxy provides authentication via OpenShift users
- TLS is handled by reencrypt termination
- Service CA automatically manages certificates
- No NetworkPolicy applied (kept simple)

## File Structure

```
k8s/
├── templates/              # Clean template files (version controlled)
│   ├── deployment.yaml.template
│   ├── secret.yaml.template
│   ├── configmap.yaml.template
│   ├── route.yaml.template
│   ├── namespace.yaml
│   ├── service.yaml
│   └── serviceaccount.yaml
├── README.md              # This documentation
├── *.yaml                 # Your working files (gitignored)
└── ...
```

**Template vs Working Files:**
- `templates/*.template` - Clean templates checked into version control
- `*.yaml` - Your customized working files (gitignored for security)
- Copy templates to working files and customize them
- Your credentials and settings stay private

## Next Steps

1. Set up monitoring and alerting
2. Configure backup for persistent data
3. Add NetworkPolicy for network security
4. Set up CI/CD pipeline for updates