CURRENT_DIR=$(shell pwd)
VERSION=$(shell cat ${CURRENT_DIR}/VERSION)
TEMP_VERSION=$(shell date -u '+%Y%m%d%H%M%S')

# docker image publishing options
DOCKER_PUSH=false
SNAPSHOT=false
IMAGE_NAMESPACE=myelinio
IMAGE_NAME=myelin-drift-detection

ifdef IMAGE_NAMESPACE
IMAGE_PREFIX=${IMAGE_NAMESPACE}/
endif

ifeq ($(SNAPSHOT),true)
IMAGE_VERSION=${VERSION}-${TEMP_VERSION}
else
IMAGE_VERSION=${VERSION}
endif


.PHONY: all
all: build-docker

.PHONY: build-docker
build-docker:
	docker image build -t ${IMAGE_PREFIX}${IMAGE_NAME}:${IMAGE_VERSION} . -f Dockerfile.drift
	@if [ "$(DOCKER_PUSH)" = "true" ] ; then docker push ${IMAGE_PREFIX}${IMAGE_NAME}:${IMAGE_VERSION} ; fi
