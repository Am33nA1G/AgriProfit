Write-Host "Running all tests..."
pytest tests/ -v

Write-Host "Running only unit tests..."
pytest tests/ -v -m unit

Write-Host "Running only integration tests..."
pytest tests/ -v -m integration

Write-Host "Running with coverage report..."
pytest tests/ -v --cov=app --cov-report=html --cov-report=term
