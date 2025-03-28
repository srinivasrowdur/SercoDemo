# Deploying to Google Cloud

This guide explains how to deploy the Medical Transcription Streamlit app to Google Cloud using Docker.

## Prerequisites

1. [Docker](https://docs.docker.com/get-docker/) installed locally
2. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured
3. Google Cloud account with billing enabled
4. A project created in Google Cloud

## Local Testing with Docker

1. Make sure you have a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

2. Build and run the Docker container locally:
   ```bash
   docker-compose up --build
   ```

3. Open your browser and navigate to http://localhost:8501 to test the application.

## Deploying to Google Cloud Run

Google Cloud Run is a fully managed platform that automatically scales stateless containers. It's perfect for Streamlit applications.

### Step 1: Configure Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable necessary APIs
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
```

### Step 2: Build and Push the Docker Image

```bash
# Create an Artifact Registry repository
gcloud artifacts repositories create medical-transcription --repository-format=docker --location=us-central1 --description="Medical Transcription App"

# Configure Docker to use Google Cloud authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and tag the Docker image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-transcription/streamlit-app:latest .

# Push the image to Artifact Registry
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-transcription/streamlit-app:latest
```

### Step 3: Deploy to Cloud Run

```bash
# Deploy the container to Cloud Run
gcloud run deploy medical-transcription-app \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-transcription/streamlit-app:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=your_openai_api_key_here"
```

For secure handling of the API key, consider using Secret Manager:

```bash
# Create a secret
gcloud secrets create openai-api-key --replication-policy="automatic"
echo -n "your_openai_api_key_here" | gcloud secrets versions add openai-api-key --data-file=-

# Grant access to the secret
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with the secret
gcloud run deploy medical-transcription-app \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medical-transcription/streamlit-app:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest"
```

### Step 4: Verify Deployment

Once deployed, Google Cloud Run will provide a URL for your application. Open this URL in your browser to verify the deployment.

## Setting up Continuous Deployment

For continuous deployment, consider setting up Cloud Build triggers:

1. Connect your GitHub repository to Google Cloud Build
2. Create a trigger that builds and deploys the image when changes are pushed to your main branch

## Managing Costs

To manage costs, you can:
- Set concurrency and maximum instance limits on your Cloud Run service
- Monitor usage with Google Cloud Monitoring
- Set up budget alerts in Google Cloud Console 