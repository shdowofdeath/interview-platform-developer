FROM python:latest

ARG UV_INDEX_URL
ARG REPUTATION_API_KEY

ENV UV_INDEX_URL=${UV_INDEX_URL}
ENV REPUTATION_API_KEY=${REPUTATION_API_KEY}
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install uv

COPY . .

RUN uv sync --group dev

EXPOSE 9400

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9400", "--reload"]
