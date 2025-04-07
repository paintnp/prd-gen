# PowerShell Installation Script for PRD Generator
# This script sets up the required dependencies and environment for Windows users

Write-Host "PRD Generator - Installation Script" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

# Create and activate a virtual environment if it doesn't exist
if (-not (Test-Path -Path "prd-gen-env")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv prd-gen-env
    $venvCreated = $true
} else {
    Write-Host "Virtual environment already exists" -ForegroundColor Yellow
    $venvCreated = $false
}

# Activate the virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\prd-gen-env\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
pip install --upgrade pip

# Install dependencies with the --upgrade flag
Write-Host "Installing latest dependencies..." -ForegroundColor Cyan
pip install --upgrade -r requirements.txt

# Set up environment file if it doesn't exist
if (-not (Test-Path -Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Cyan
    @"
# PRD Generator Environment Configuration

# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# LLM Configuration
MODEL=gpt-4o
TEMPERATURE=0.7
MAX_TOKENS=4000
"@ | Out-File -FilePath ".env" -Encoding utf8
    
    Write-Host ".env file created. Please edit it to add your OpenAI API key." -ForegroundColor Yellow
}

# Create output directory if it doesn't exist
if (-not (Test-Path -Path "output")) {
    New-Item -Path "output" -ItemType Directory | Out-Null
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""

if ($venvCreated) {
    Write-Host "To get started:" -ForegroundColor Cyan
    Write-Host "1. Edit the .env file and add your OpenAI API key" -ForegroundColor White
    Write-Host "2. Activate the virtual environment with: .\prd-gen-env\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "3. Run the generator: python -m prd_gen.main --idea `"Your product idea`"" -ForegroundColor White
} else {
    Write-Host "To get started:" -ForegroundColor Cyan
    Write-Host "1. Make sure your OpenAI API key is set in the .env file" -ForegroundColor White
    Write-Host "2. Run the generator: python -m prd_gen.main --idea `"Your product idea`"" -ForegroundColor White
}
Write-Host ""
Write-Host "For more options, run: python -m prd_gen.main --help" -ForegroundColor White 