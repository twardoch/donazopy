# Donazopy Specification Table of Contents

## 01. Vision and Scope

TLDR: Donazopy is a Python CLI for safe DNS zone-file workflows, provider DNS management, registrar delegation, and migration automation.

## 02. Domain Model

TLDR: The core model separates zones, records, provider accounts, hosted DNS services, registrar services, capabilities, and sync plans.

## 03. Zone File Engine

TLDR: Local zone files are the portable source of truth, parsed and serialized with dnspython and validated before any provider write.

## 04. Provider Architecture

TLDR: Each provider lives in a separate module and declares explicit DNS, registrar, import/export, and delegation capabilities.

## 05. Credential and Configuration Model

TLDR: Credentials come from environment variables or ignored local config, are never logged, and are validated per provider before writes.

## 06. CLI Experience

TLDR: Fire exposes simple commands for provider discovery, zone validation, export, diff, apply, migration, and delegation verification.

## 07. Read, Export, and Dump Workflows

TLDR: Donazopy can read provider DNS state and dump it to stable BIND zone files for audit, backup, and migration.

## 08. Write, Import, and Sync Workflows

TLDR: Writes are plan-first, dry-run by default for destructive changes, and provider adapters translate normalized records into API calls.

## 09. Nameserver and Registrar Workflows

TLDR: Parent-zone delegation is a registrar concern and must be implemented through domain APIs, not child-zone NS record edits.

## 10. Safety, Validation, and Observability

TLDR: The tool blocks unsafe changes, validates before and after writes, redacts secrets, and gives users clear plans and outcomes.

## 11. Testing Strategy

TLDR: Unit tests cover parsing and planning, mocked provider tests cover APIs, and gated live tests verify real provider behavior.

## 12. Implementation Roadmap

TLDR: Build the zone engine and provider protocol first, then add providers in capability-ranked slices with safety gates.
