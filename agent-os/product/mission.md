# Product Mission

## Problem

Current coding agents don't leverage IDE capabilities. They reinvent the wheel — implementing file operations,
refactoring, linting, and other tasks that IDEs like PyCharm already do well. This wastes model compute on solved
problems and produces worse results than mature IDE tooling.

## Target Users

Python developers on modest hardware who want useful AI coding assistance without requiring high-end machines or
expensive cloud API costs.

## Solution

Punie shifts tool execution to the IDE via the Agent Client Protocol (ACP). Instead of the agent doing all the work,
PyCharm's existing machinery — refactoring, linting, type checking, code navigation — becomes the agent's tool runtime.
Punie also provides a parallel web interface for interacting with the agent outside the IDE.
