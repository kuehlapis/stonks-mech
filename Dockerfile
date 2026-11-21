# Submission image built from the repo root (the track builds the top-level Dockerfile).
# The bot lives in python/; this is the same image as python/Dockerfile.
FROM python:3.13-slim
WORKDIR /bot
COPY python/ .
ENTRYPOINT ["python3", "-u", "/bot/bot.py"]
