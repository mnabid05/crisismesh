FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --system --uid 10001 crisismesh
COPY services/intelligence/app ./app
COPY services/intelligence/models ./models
USER crisismesh
EXPOSE 8090
CMD ["python", "-m", "app.server"]
