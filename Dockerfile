FROM python:3.7-slim as base

LABEL com.jrr.image.vendor="Jose Gabriel Rivera"
LABEL com.jrr.image.url="https://www.linkedin.com/in/jose-gabriel-rivera-rodriguez-967a3154/"
LABEL com.jrr.image.title="Test Aplazame"
LABEL com.jrr.image.source="https://github.com/projectname"

WORKDIR /usr/local/src

#
# Backend build stage
#
FROM base as backend-build-stage

# Install dev/build dependencies
# Man pages folder needed to avoid postgresql-client install fail on slim image
RUN mkdir -p /usr/share/man/man1 && \
    mkdir -p /usr/share/man/man7 && \
    apt-get update && apt-get install -qq -y \
    postgresql-client \
    --no-install-recommends

# Install wheel support
RUN pip install wheel --upgrade

# Pip environment variables (Build)
ENV WHEELHOUSE=/wheelhouse \
    PIP_WHEEL_DIR=/wheelhouse \
    PIP_FIND_LINKS=/wheelhouse \
    XDG_CACHE_HOME=/cache

# Create wheelhouse and cache folders
RUN mkdir /wheelhouse && \
    mkdir /cache && \
    mkdir /build

COPY . /usr/local/src

# Download requirements to build cache (Useful if /build and /cache are volumes)
# Install application test requirements
# Add app to python path
# Build applicaiton wheels
RUN pip download -d /build -r aplazame/requirements/common.txt --no-input && \
    pip install --no-index -f /build -r aplazame/requirements/common.txt && \
    pip install -e . && \
    pip wheel --no-index -f /build .


#
# Backend Test Stage
#
FROM backend-build-stage as backend-test-stage

RUN pip install -r aplazame/requirements/test.txt --no-input

# Add test entrypoint script
COPY test_entrypoint.sh /usr/local/bin/test_entrypoint.sh
RUN chmod +x /usr/local/bin/test_entrypoint.sh

# Set defaults for entrypoint and command string
ENTRYPOINT ["/usr/local/bin/test_entrypoint.sh"]
CMD ["python", "manage.py", "test"]


#
# Production Image Stage
#
FROM base as backend-production-stage

# Copy and install application wheels
COPY --from=backend-build-stage /wheelhouse /wheelhouse
RUN pip install --no-index -f /wheelhouse aplazame && \
    pip install gunicorn && \
    rm -rf /wheelhouse

# Configure default run values
EXPOSE 5000
CMD ["gunicorn", "aplazame.wsgi:application", "-b", "0.0.0.0:5000", "--workers=2"]
