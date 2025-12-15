#!/bin/bash

# Quick test script for Phases 1-8
# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

echo -e "\n${BLUE}================================================================================${NC}"
echo -e "${BLUE}                 QUICK TEST - Student Face Recognition SaaS${NC}"
echo -e "${BLUE}================================================================================${NC}\n"

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected="$4"
    local token="$5"
    
    if [ -z "$token" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint")
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint" -H "Authorization: Bearer $token")
    fi
    
    if [ "$response" -eq "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name (Status: $response)"
    else
        echo -e "${RED}✗${NC} $name (Expected: $expected, Got: $response)"
    fi
}

# Phase 0: Health Checks
echo -e "${BLUE}[Phase 0: Health Checks]${NC}"
test_endpoint "Health Check" "GET" "/health" 200
test_endpoint "Root Endpoint" "GET" "/" 200
test_endpoint "API Docs" "GET" "/docs" 200
echo ""

# Check if server is running
if [ $(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health") -ne 200 ]; then
    echo -e "${RED}✗ Server is not running!${NC}"
    echo -e "${YELLOW}Start server: uvicorn app.main:app --reload${NC}\n"
    exit 1
fi

# Get token from argument
TOKEN="$1"

if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}⚠️  No Auth0 token provided. Skipping protected endpoints.${NC}"
    echo -e "${YELLOW}Usage: ./test_quick.sh YOUR_AUTH0_TOKEN${NC}\n"
else
    echo -e "${BLUE}[Phase 2-8: Protected Endpoints]${NC}"
    test_endpoint "Token Info" "GET" "/api/v1/auth/token-info" 200 "$TOKEN"
    test_endpoint "List Organizations" "GET" "/api/v1/organizations/" 200 "$TOKEN"
    test_endpoint "List Departments" "GET" "/api/v1/academic/departments/" 200 "$TOKEN"
    test_endpoint "List Students" "GET" "/api/v1/students/" 200 "$TOKEN"
    test_endpoint "List Faculty" "GET" "/api/v1/faculty/" 200 "$TOKEN"
    test_endpoint "List Subjects" "GET" "/api/v1/subjects/" 200 "$TOKEN"
    test_endpoint "List Timetable" "GET" "/api/v1/timetable/" 200 "$TOKEN"
    echo ""
fi

echo -e "${BLUE}================================================================================${NC}"
echo -e "${GREEN}✓ Quick test complete!${NC}"
echo -e "${BLUE}================================================================================${NC}\n"
