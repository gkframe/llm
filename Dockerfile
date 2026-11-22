# The pinned llama.cpp image with the presets copied in. Built by `docker compose up --build`
# (which `deploy llm` runs), so a change to models.ini changes the image and Compose recreates
# the container; with no change the build cache gives the same image and nothing restarts.
# A bind mount wouldn't do that: the router reads the presets only when it starts.
# Pinned to a llama.cpp build; bump the tag on purpose and test with bin/dev first.
FROM ghcr.io/ggml-org/llama.cpp:server-vulkan-b12602
ARG PRESET=models.ini
COPY ${PRESET} /models.ini
