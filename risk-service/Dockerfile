# Risk service for feature 001. Standard library only: no pip install (constitution III).
FROM python:3.10-slim@sha256:2ee0fb8794bf82af1b2db168ada5869b4c27d17720dd3b155b56c111fb4a38ae
WORKDIR /app
COPY risk_service /app/risk_service
EXPOSE 18110
CMD ["python", "-m", "risk_service.server"]
