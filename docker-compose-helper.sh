#!/bin/bash

# LoRA Pilot Docker Compose Helper Script
# Makes it easy to manage different configurations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to check if workspace exists
check_workspace() {
    if [ ! -d "workspace" ]; then
        print_warning "Workspace directory not found. Creating it..."
        mkdir -p workspace/{models,datasets,outputs,logs,config,cache}
        print_status "Workspace directory created."
    fi
}

# Function to show available services
show_services() {
    print_header "Available Services"
    echo "ControlPilot (Main UI): http://localhost:7878"
    echo "JupyterLab:          http://localhost:8888"
    echo "VS Code Server:      http://localhost:8443"
    echo "ComfyUI:             http://localhost:5555"
    echo "Kohya SS:            http://localhost:6666"
    echo "InvokeAI:            http://localhost:9090"
    echo "Diffusion Pipe:       http://localhost:4444"
    echo ""
}

# Function to get container status
get_status() {
    print_header "Container Status"
    if [ -f ".env" ]; then
        source .env
    fi
    
    COMPOSE_FILE="docker-compose.yml"
    if [ "$1" = "dev" ]; then
        COMPOSE_FILE="docker-compose.dev.yml"
    elif [ "$1" = "cpu" ]; then
        COMPOSE_FILE="docker-compose.cpu.yml"
    fi
    
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"
    else
        docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"
    fi
        print_status "LoRA Pilot is running"
        show_services
    else
        print_warning "LoRA Pilot is not running"
    fi
    
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" ps
    else
        docker-compose -f "$COMPOSE_FILE" ps
    fi
}

# Function to start services
start_services() {
    local mode=${1:-"standard"}
    
    print_header "Starting LoRA Pilot ($mode mode)"
    check_docker
    check_workspace
    
    case $mode in
        "dev"|"development")
            COMPOSE_FILE="docker-compose.dev.yml"
            ;;
        "cpu"|"minimal")
            COMPOSE_FILE="docker-compose.cpu.yml"
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            ;;
    esac
    
    print_status "Using compose file: $COMPOSE_FILE"
    
    # Load environment variables if .env exists
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
        print_status "Environment variables loaded from .env"
    fi
    
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" up -d
    else
        docker-compose -f "$COMPOSE_FILE" up -d
    fi
    
    if [ $? -eq 0 ]; then
        print_status "LoRA Pilot started successfully!"
        show_services
        print_status "Use './docker-compose-helper.sh logs' to view logs"
    else
        print_error "Failed to start LoRA Pilot"
        exit 1
    fi
}

# Function to stop services
stop_services() {
    local mode=${1:-"standard"}
    
    print_header "Stopping LoRA Pilot"
    
    case $mode in
        "dev"|"development")
            COMPOSE_FILE="docker-compose.dev.yml"
            ;;
        "cpu"|"minimal")
            COMPOSE_FILE="docker-compose.cpu.yml"
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            ;;
    esac
    
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" down
    else
        docker-compose -f "$COMPOSE_FILE" down
    fi
    
    if [ $? -eq 0 ]; then
        print_status "LoRA Pilot stopped successfully!"
    else
        print_error "Failed to stop LoRA Pilot"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    local mode=${1:-"standard"}
    
    case $mode in
        "dev"|"development")
            COMPOSE_FILE="docker-compose.dev.yml"
            ;;
        "cpu"|"minimal")
            COMPOSE_FILE="docker-compose.cpu.yml"
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            ;;
    esac
    
    print_header "Showing LoRA Pilot Logs"
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" logs -f
    else
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Function to access container shell
access_shell() {
    local mode=${1:-"standard"}
    
    case $mode in
        "dev"|"development")
            COMPOSE_FILE="docker-compose.dev.yml"
            SERVICE_NAME="lora-pilot"  # Use service name, not container name
            ;;
        "cpu"|"minimal")
            COMPOSE_FILE="docker-compose.cpu.yml"
            SERVICE_NAME="lora-pilot"  # Use service name, not container name
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            SERVICE_NAME="lora-pilot"  # Use service name, not container name
            ;;
    esac
    
    print_header "Accessing Container Shell"
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" bash
    else
        docker-compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" bash
    fi
}

# Function to update image
update_image() {
    print_header "Updating LoRA Pilot Image"
    # Use docker compose (space) instead of docker-compose (dash) for modern Docker
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose pull lora-pilot
    else
        docker-compose pull lora-pilot
    fi
    print_status "Image updated. Restart with './docker-compose-helper.sh start'"
}

# Function to setup workspace
setup_workspace() {
    print_header "Setting up Workspace"
    
    # Create workspace directory structure
    mkdir -p workspace/{models,datasets,outputs,logs,config,cache}
    mkdir -p workspace/outputs/{comfy,invoke}
    mkdir -p workspace/datasets/{images,ZIPs}
    
    # Copy .env.example if .env doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_status "Created .env file from template"
        print_warning "Please edit .env file with your settings"
    fi
    
    print_status "Workspace setup complete!"
}

# Function to show help
show_help() {
    print_header "LoRA Pilot Docker Compose Helper"
    echo ""
    echo "Usage: $0 [COMMAND] [MODE]"
    echo ""
    echo "Commands:"
    echo "  start [mode]     Start LoRA Pilot (modes: standard, dev, cpu)"
    echo "  stop [mode]      Stop LoRA Pilot (modes: standard, dev, cpu)"
    echo "  restart [mode]   Restart LoRA Pilot (modes: standard, dev, cpu)"
    echo "  status [mode]    Show container status (modes: standard, dev, cpu)"
    echo "  logs [mode]      Show container logs (modes: standard, dev, cpu)"
    echo "  shell [mode]     Access container shell (modes: standard, dev, cpu)"
    echo "  update           Update LoRA Pilot image"
    echo "  setup            Setup workspace directory"
    echo "  help             Show this help message"
    echo ""
    echo "Modes:"
    echo "  standard         Full GPU setup with all services (default)"
    echo "  dev, development Development setup with source code mounting"
    echo "  cpu, minimal    CPU-only setup with resource limits"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start standard GPU setup"
    echo "  $0 start dev               # Start development setup"
    echo "  $0 start cpu               # Start CPU-only setup"
    echo "  $0 logs                    # Show logs for standard setup"
    echo "  $0 shell dev               # Access development container shell"
    echo ""
}

# Main script logic
case "${1:-}" in
    "start")
        start_services "${2:-standard}"
        ;;
    "stop")
        stop_services "${2:-standard}"
        ;;
    "restart")
        stop_services "${2:-standard}"
        sleep 2
        start_services "${2:-standard}"
        ;;
    "status")
        get_status "${2:-standard}"
        ;;
    "logs")
        show_logs "${2:-standard}"
        ;;
    "shell")
        access_shell "${2:-standard}"
        ;;
    "update")
        update_image
        ;;
    "setup")
        setup_workspace
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
