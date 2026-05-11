# ADR-003: Stability vs exploratory experiment classification

## Status
Accepted

## Context
Some pipeline features are stable and should not change between builds. Others (ML classifier, non-uniformity metrics, linkage analysis) are under active development and may intentionally produce different results across builds.

## Decision
Experiments are classified as either `stability` or `exploratory`. Only stability experiments contribute to the build verdict. Exploratory experiments are tracked longitudinally and generate warnings on deviation, but never fail a build.

## Reasoning
- Prevents false failures when actively developed features intentionally change behaviour
- Allows the regression suite to grow to include in-development features without noise
- Exploratory experiments still generate longitudinal data, preserving the ability to detect unintended regressions even in development features
- Classification is a single field in the manifest — graduating an experiment from exploratory to stability requires only a one-field change

## Consequences
- Someone must make a conscious decision to classify each experiment at registration time
- The build verdict is only meaningful for the stability suite — exploratory results require separate human review
- Risk that an experiment stays classified as exploratory longer than necessary — periodic review of classifications is advisable

## Alternatives considered
- All experiments contribute to the build verdict — rejected because it would cause constant false failures during active development
- Separate regression suites for stable and exploratory — rejected as unnecessary complexity for the MVP
