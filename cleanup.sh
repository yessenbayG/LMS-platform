#!/bin/bash

# ANSI color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== LMS Application Cache Cleanup Script ===${NC}"

# Clear Python cache files
echo -e "${BLUE}Cleaning Python cache files...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete

# Clear session files
echo -e "${BLUE}Cleaning session files...${NC}"
find . -type f -name "flask_session" -exec rm -rf {} \;

# Clear log files
echo -e "${BLUE}Cleaning log files...${NC}"
find . -type f -name "*.log" -delete

echo -e "${GREEN}Cleanup completed successfully!${NC}"
echo -e "${YELLOW}Note: Database has not been affected. Use reset_db.sh to reset the database.${NC}"