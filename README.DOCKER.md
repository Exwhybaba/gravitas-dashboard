# Docker & CI/CD Setup

This directory contains Docker and GitHub Actions configs for building, publishing, and deploying the Gravitas dashboard.

## Quick Start

### Build and run locally with Docker:

```bash
# From src/ directory
docker build -t gravitas:local .
docker run -p 8050:8050 gravitas:local
```

### Using docker-compose:

```bash
# From src/ directory
docker compose up --build
```

The app will be available at `http://localhost:8050`

## GitHub Actions CI/CD

The workflow (`.github/workflows/ci-cd.yml`) automatically:

1. **Build**: Creates a Docker image from the Dockerfile
2. **Publish**: Pushes the image to GitHub Container Registry (GHCR)
3. **Deploy** (optional): Deploys to your remote server via SSH

### Setup for Deployment

Add these secrets in your GitHub repo (Settings > Secrets and variables > Actions):

- `DEPLOY_HOST` - Your server IP or hostname
- `DEPLOY_USER` - SSH username
- `DEPLOY_SSH_KEY` - SSH private key (PEM format)
- `DEPLOY_SSH_PORT` - SSH port (default: 22)
- `GHCR_PAT` - (optional) GitHub PAT for pulling images

### Example SSH key generation:

```bash
ssh-keygen -t rsa -b 4096 -f deploy_key -N ""
# Copy contents of deploy_key (private key) to DEPLOY_SSH_KEY secret
# Add deploy_key.pub (public key) to ~/.ssh/authorized_keys on your server
```

## File Structure

- `Dockerfile` - Multi-layer build for the Dash app
- `.dockerignore` - Excludes unnecessary files from build
- `docker-compose.yml` - Single-service compose file for local dev
- `.github/workflows/ci-cd.yml` - GitHub Actions workflow for CI/CD

## Troubleshooting

- **Build fails**: Ensure `requirements.txt`, `app.py`, and `assets/` are in `src/`
- **Deploy fails**: Verify SSH access and Docker installation on remote host
- **Image not pushed**: Check that GITHUB_TOKEN secret is available (auto-provided by GitHub)
