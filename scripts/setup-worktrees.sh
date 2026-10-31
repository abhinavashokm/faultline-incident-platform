#!/bin/bash

SOURCE="$(pwd)"

WORKTREES=(
    "../faultline-backend"
    "../faultline-frontend"
)

SHARED_ITEMS=(
    ".local"
    ".env"
)

for WORKTREE in "${WORKTREES[@]}"; do
    for ITEM in "${SHARED_ITEMS[@]}"; do
        ln -sfn "$SOURCE/$ITEM" "$WORKTREE/$ITEM"
    done
done

echo "Worktree shared files linked successfully!"
