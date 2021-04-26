# Project configuration
PROJECT_NAME = parallel-gateway

# Makefile parameters.
TAG ?= $(shell git describe --always)

# General.
SHELL = /bin/bash
TOPDIR = $(shell git rev-parse --show-toplevel)

# Docker.
DOCKER_ORG = rex
ECS_REGISTRY = 355508092300.dkr.ecr.us-west-2.amazonaws.com
DOCKER_REPO = $(DOCKER_ORG)/$(PROJECT_NAME)
DOCKER_IMG = $(DOCKER_REPO):$(TAG)

default: help

help: # Display help
	@awk -F ':|##' \
		'/^[^\t].+?:.*?##/ {\
			printf "\033[36m%-30s\033[0m %s\n", $$1, $$NF \
		}' $(MAKEFILE_LIST) | sort

build: ## Build the docker image
	docker build -t parallel-gateway .

conda: ## Setup the conda environment
	conda env update -f environment.yml
	@echo "****************************************"
	@echo "*remember to activate your environment!*"
	@echo "****************************************"

default: build
