#!/usr/bin/env bash
set -euo pipefail
PROJECT=actas_tests
ENV_FILE=.env.test
COMPOSE=(-p "$PROJECT" --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.test.yml)
[ -f "$ENV_FILE" ] || cp .env.test.example "$ENV_FILE"
mkdir -p test-artifacts
cleanup() {
  docker compose "${COMPOSE[@]}" ps -a > test-artifacts/compose-ps.txt || true
  docker compose "${COMPOSE[@]}" logs --no-color > test-artifacts/docker.log || true
  docker compose "${COMPOSE[@]}" down -v --remove-orphans || true
}
trap cleanup EXIT
docker compose "${COMPOSE[@]}" down -v --remove-orphans || true
docker compose "${COMPOSE[@]}" up -d --build
docker compose "${COMPOSE[@]}" --profile tests build test-runner
docker compose "${COMPOSE[@]}" --profile tests run --rm test-runner
