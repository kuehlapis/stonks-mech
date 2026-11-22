# Submission image built from the repo root (the track builds the top-level Dockerfile).
# The bot lives in python/; this is the same image as python/Dockerfile.
FROM python:3.13.18-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
WORKDIR /bot
COPY python/ .
ENTRYPOINT ["python3", "-u", "/bot/bot.py"]
