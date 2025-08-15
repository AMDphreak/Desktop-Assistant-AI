#!/bin/bash
# Download dependencies from requirements.txt

pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu