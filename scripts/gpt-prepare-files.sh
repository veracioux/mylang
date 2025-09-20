#!/usr/bin/env bash

shopt -s globstar

cd "$(git root)/scripts"
mkdir -p ../gpt

write_and_log_if_changed() {
    local filepath="$1"
    local temp_file=$(mktemp)

    # Output to temp file
    cat - > "$temp_file"

    # Check if the temp file differs from the target file
    if ! diff -q "$temp_file" "$filepath" > /dev/null; then
        # If different, update the target file and log the change
        mv "$temp_file" "$filepath"
        echo "Updated: $filepath"
    else
        # If no change, remove temp file
        rm "$temp_file"
    fi
}

# Dump code samples
cat ../tests/flows/*.my | write_and_log_if_changed ../gpt/code-dump.txt

# Dump brainstorms
{
    for f in ../brainstorm/**.org; do
        echo "#+TITLE: $f"
        cat "$f"
    done

    echo "#+TITLE: Dump of other brainstormed code"
    echo "#+begin_src"
    cat ../brainstorm/**.my
    echo "#+end_src"
} | write_and_log_if_changed ../gpt/brainstorm.md
