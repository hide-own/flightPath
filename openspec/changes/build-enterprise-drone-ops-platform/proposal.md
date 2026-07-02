## Why

The current product is a local single-user flight-log trajectory and video tool, but the target product is now a performance-first enterprise operations platform for teams that manage logs, videos, aircraft, batteries, parts, maintenance, pilots, compliance, analytics, and long-running processing workflows in one place.

This change turns the proven Python log/video engine into a scalable worker behind a Java SaaS-style control plane while keeping all required development/runtime data on the D drive because the C drive is capacity constrained.

## What Changes

- Add a Java Spring Boot main service for enterprise identity, organization isolation, projects, assets, metadata, tasks, analytics, administration, audit, and API orchestration.
- Keep Python as the compute worker for `.bin` parsing, trajectory extraction, log analysis, and video/render/report generation because the existing implementation already relies on `pymavlink`, image processing, and ffmpeg tooling.
- Add RabbitMQ-based asynchronous communication between Java and Python workers with separate queues for parsing, analysis, rendering, report generation, retries, cancellation, and dead-letter handling.
- Add PostgreSQL as the authoritative relational store for users, organizations, projects, assets, tasks, analysis summaries, fleet inventory, maintenance, parts, compliance, and audit records.
- Add Redis or Valkey for session acceleration, hot caches, task progress, worker heartbeats, dashboard cache, idempotency keys, and short-lived coordination data.
- Add MinIO/S3-compatible object storage for raw logs, uploaded videos, generated videos, thumbnails, reports, and worker artifacts.
- Require all installable development/runtime environments, tools, data directories, storage buckets, queue data, database data, and generated artifacts to live under D-drive paths.
- Add a modern professional admin/user backend UI with light, dark, and system theme modes, token-based color/style rules, high-density operational tables, WebGL map/video analysis workspaces, and performance-aware loading states.
- Add user modules for project workspaces, log upload management, video upload management, log analysis, trajectory replay, data analytics, reports, compliance checklists, fleet inventory, battery management, parts management, maintenance records, pilot/personnel records, and generated media review.
- Add administrator modules for user management, organization/member management, role permission management, global asset governance, queue/job monitoring, worker observability, failure recovery, system logs, operation audit, dictionaries/tags, theme policy, and global analytics.
- Add competitive-product-inspired capabilities from AirData, DroneLogbook, DJI FlightHub 2, DroneDeploy, and Aloft, focusing on flight data intelligence, fleet health, maintenance, compliance, project operations, reporting, and enterprise governance while excluding commercial pricing, subscription packages, and quota monetization.
- Add a standalone HTML prototype that demonstrates the modern backend information architecture, light/dark/system theme controls, dashboard, upload/jobs, analysis workspace, fleet/parts/maintenance, compliance, admin governance, and performance status surfaces.

## Capabilities

### New Capabilities

- `enterprise-platform-architecture`: Java control plane, Python worker compute plane, messaging, storage, deployment topology, D-drive environment layout, and service boundaries.
- `tenant-identity-access`: Login, organization/team space, members, roles, permissions, project-scoped authorization, and tenant isolation.
- `project-operations-workspace`: Project and mission-oriented workspaces for logs, videos, analyses, reports, checklists, aircraft, personnel, and operational timelines.
- `asset-upload-storage`: High-performance log/video upload management, object storage integration, metadata extraction, virus/file validation hooks, deduplication, retention, and download rules.
- `async-processing-performance`: RabbitMQ queue contracts, worker lifecycle, task scheduling, progress, cancellation, retries, dead letters, idempotency, backpressure, and performance targets.
- `flight-log-analysis`: `.bin` parsing, trajectory extraction, time-series telemetry, 2D/3D replay data, anomaly summaries, battery/aircraft hints, and analysis result contracts.
- `media-rendering-review`: Uploaded video management, generated video rendering, thumbnails, previews, downloads, render profiles, and media-task isolation.
- `fleet-inventory-maintenance`: Aircraft/device inventory, battery inventory, zero/parts management, component lifecycle, maintenance scheduling, inspections, replacement history, and service records.
- `personnel-compliance-reporting`: Pilot/personnel qualifications, document tracking, compliance checklists, custom reports, exportable evidence packs, and audit-ready operational records.
- `analytics-dashboards`: User and administrator dashboards for flight activity, upload trends, task performance, anomalies, asset health, maintenance load, personnel readiness, and platform health.
- `modern-admin-ui-prototype`: Professional backend UI behavior, navigation, theme modes, design tokens, responsive density, map/video workspace ergonomics, and HTML prototype requirements.
- `admin-observability-governance`: Administrator user/organization controls, global asset oversight, task/worker monitoring, system logs, audit logs, dictionaries, settings, and governance workflows.

### Modified Capabilities

- None. The accepted baseline `openspec/specs/` directory has no active capability specs. Existing changes under `openspec/changes/` are historical context for the current local Web tool and are superseded by this enterprise platform proposal.

## Impact

- Adds a new Java backend codebase and build/runtime toolchain, preferably under a D-drive-managed development environment such as `D:\devtools\jdk-21`, `D:\devtools\maven`, and project-local wrapper scripts.
- Adds PostgreSQL, RabbitMQ, Redis/Valkey, and MinIO runtime dependencies with data directories under `D:\flightpath-data\...`.
- Refactors the Python backend from a localhost user-facing FastAPI service into one or more internal worker entry points while preserving parser, model, map, and renderer logic where appropriate.
- Keeps the Vue frontend but expands it from a local single-screen tool into a multi-module enterprise backend with route-level code splitting, theme tokens, dashboard/workspace layouts, and operational tables.
- Introduces new API contracts for identity, organizations, projects, assets, uploads, jobs, worker callbacks, analysis results, dashboards, fleet inventory, maintenance, parts, compliance, reports, audit, and admin governance.
- Introduces security and isolation requirements across every API and database query through organization/project scoping.
- Introduces performance requirements around API latency, upload flow, queue throughput, worker concurrency, task progress freshness, large trajectory data loading, dashboard caching, and render isolation.
- Introduces an HTML prototype artifact under the change directory for review before implementation.
