# Hugging Face Spaces (Docker SDK) ke liye.
# Space ke Files me "Create a new file" -> naam: Dockerfile -> ye content paste karo.
FROM python:3.11-slim
RUN pip install --no-cache-dir flask gunicorn
WORKDIR /app
ADD https://raw.githubusercontent.com/pclwaqas786-ctrl/schoolweb/master/hf-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 7860
ENTRYPOINT ["/entrypoint.sh"]
