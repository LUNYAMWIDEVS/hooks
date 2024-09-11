#!/bin/bash

# Replace placeholders in index.html with actual environment variables
sed -i "s|%%REACT_APP_SERVER_URL%%|${REACT_APP_SERVER_URL}|g" build/index.html
sed -i "s|%%REACT_APP_MERGER_URL%%|${REACT_APP_MERGER_URL}|g" build/index.html
