FROM python:3.12-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y gcc libpq-dev

# install dependencies first
COPY pyproject.toml ./

RUN pip install --upgrade pip

# if using uv
# RUN pip install uv && uv pip install --system .

# normal pip install
RUN pip install -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]