#!/bin/bash

# ACM Agent Container Build Script
#
# Usage: ./build.sh [TAG] [REGISTRY] [--push]
#
# Arguments:
#   TAG (optional): Image tag, defaults to 'latest'
#   REGISTRY (optional): Container registry, defaults to 'quay.io/bjoydeep'
#   --push (optional): Push image to registry after building
#
# Examples:
#   ./build.sh                                    # Build with latest tag, default registry
#   ./build.sh v1.0                              # Build with v1.0 tag, default registry
#   ./build.sh latest quay.io/myuser             # Build with custom registry
#   ./build.sh latest quay.io/myuser --push      # Build and push to custom registry
#   ./build.sh latest --push                     # Build and push to default registry

set -e

# Configuration
IMAGE_NAME="acm-agent"
IMAGE_TAG="${1:-latest}"
REGISTRY="${2:-quay.io/bjoydeep}"

# Full image names
LOCAL_IMAGE_NAME="$IMAGE_NAME:$IMAGE_TAG"
REGISTRY_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

echo "🐳 Building ACM Agent container image..."
echo "📦 Local image: $LOCAL_IMAGE_NAME"
echo "📦 Registry image: $REGISTRY_IMAGE_NAME"

# Build the image with platform specification for OpenShift compatibility
podman build --platform linux/amd64 -t "$LOCAL_IMAGE_NAME" .

echo "✅ Build completed successfully!"

# Tag for registry
podman tag "localhost/$LOCAL_IMAGE_NAME" "$REGISTRY_IMAGE_NAME"
echo "🏷️ Tagged as: $REGISTRY_IMAGE_NAME"

# Show image info
podman images | grep "$IMAGE_NAME" | head -1

echo ""
echo "🚀 Next steps:"
echo "1. Test locally: podman run -p 8501:8501 --env-file .env $LOCAL_IMAGE_NAME"
echo "2. Push to registry: podman push $REGISTRY_IMAGE_NAME"
echo "3. Update k8s/deployment.yaml with image name"
echo ""

# Push if --push flag is provided (can be 2nd or 3rd argument)
if [ "$2" = "--push" ] || [ "$3" = "--push" ]; then
    echo "📤 Pushing to registry..."
    podman push "$REGISTRY_IMAGE_NAME"
    echo "✅ Push completed!"
fi