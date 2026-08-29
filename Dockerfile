# The arena, containerised. One always-on worker: mint, resolve, publish.
#
# Cron is the wrong shape for this — a tick is a ~40s burst of parallel
# inference followed by a wait, and the pacing has to be a floor rather than
# a schedule, so the loop owns its own clock. One small container is cheaper
# than a scheduler and never skews.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates zsh \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /arena
# README.md rides along because pyproject's `readme` field points at it, and
# uv builds the local package during sync — without it the dependency layer
# fails on a file that is right there in the next COPY.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev || uv sync --no-dev
COPY . .

ENV TEETH_MARITIME=1 \
    TEETH_MARITIME_LANE_PREFIX=soul- \
    TEETH_TICK_SECONDS=900 \
    GIT_AUTHOR_NAME=teeth-arena \
    GIT_AUTHOR_EMAIL=arena@users.noreply.github.com \
    GIT_COMMITTER_NAME=teeth-arena \
    GIT_COMMITTER_EMAIL=arena@users.noreply.github.com

ENTRYPOINT ["/arena/scripts/worker.sh"]
