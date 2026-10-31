FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Dry-run by default: resolves leader windows, checks clients, parses a block.
# Nothing is ever sent without the explicit `send --live` subcommand plus a
# keypair supplied via the PROBE_KEYPAIR_FILE environment variable.
ENTRYPOINT ["python", "-m", "probe.cli"]
CMD ["dry-run"]
