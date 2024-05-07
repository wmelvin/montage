@default:
  @just --list

@build: lint check testm
  hatch build

# Check formatting
@check:
  hatch fmt --formatter --check

# Remove dist and hatch environments (prune)
@clean:
  rm dist/*
  rmdir dist
  hatch env prune

# Apply formatting
@format:
  hatch fmt --formatter

# Linter check
@lint:
  hatch fmt --linter --check

@test:
  hatch run test

# Test matrix
@testm:
  hatch run test:test
