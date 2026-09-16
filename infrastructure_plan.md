# Infrastructure Plan

> Planning only. This document describes future infrastructure work. No installations, configuration changes, containers, workflows, deployments, or other implementation files were created by the infrastructure-planning process.

## 1. Project and User Experience

- **Application:** Public-facing Django web application.
- **Primary users:** Public users with individual accounts.
- **Primary user task:** Not yet specified; users will sign in and manage their own saved data.
- **Selected platform:** Responsive browser-based web application.
- **User-experience rationale:** A single responsive interface provides immediate access on phone and desktop browsers without installation.
- **Required operating systems, browsers, or devices:** Current desktop and mobile browsers; no native-device integration is planned.
- **Offline or native-device requirements:** None confirmed.

## 2. Connectivity and Application Shape

- **Connectivity model:** Single-user web-enabled.
- **Accounts and authentication:** Django authentication; each account accesses only its own data.
- **Backend required:** Yes; Django serves pages, account features, and application logic.
- **Cross-device persistence:** Hosted PostgreSQL keeps a user's data available after sign-in on another device.
- **Interaction between accounts:** None planned.
- **Primary application components:** Django application, Django templates, HTMX interactions, and PostgreSQL.

## 3. Selected Technology Stack

| Area | Selected technology | Purpose | Version policy |
|---|---|---|---|
| Primary language | Python | Server-side application and tests | Supported stable Python release compatible with the selected Django release |
| Application framework | Django with templates and HTMX | Responsive server-rendered web UI and account features | Supported stable Django release |
| Runtime or SDK | CPython | Runs Django and tooling | Supported stable release |
| Package manager | uv | Dependency and virtual-environment management | Current supported stable release |
| Build or packaging tool | Django static-files collection | Prepares static assets for a future deployment | Match selected Django release |
| Backend framework | Django | Data models, authentication, pages, and business logic | Same as application framework |
| API or synchronization layer | None initially | HTMX requests update server-rendered page fragments | Add an API only if future clients require one |

## 4. Storage and Persistence

- **Storage model:** Hosted relational storage.
- **Primary data store:** PostgreSQL for accounts and saved application records.
- **User files or object storage:** Not planned.
- **Local-development storage:** PostgreSQL in the planned Docker Compose environment.
- **Production hosting model:** A managed PostgreSQL service chosen with the eventual hosting provider.
- **Schema and migration approach:** Django models and version-controlled Django migrations, applied during future deployment.
- **Backup, export, or recovery approach:** Select a managed provider with automated backups and point-in-time recovery before production; a user-data export is not currently planned.
- **Secrets and connection-string approach:** Supply the database URL and Django secret key through local environment variables and protected deployment secrets; never commit values.
- **Reason this storage fits the access pattern:** PostgreSQL supports reliable account-owned relational data shared across a user's devices.

## 5. Testing Tools

| Test layer | Tool or library | Planned scope | Planned execution point |
|---|---|---|---|
| Unit | pytest and pytest-django | Models, forms, utilities, and business rules | Local and pull requests |
| Integration | pytest-django with Django test client | Views, authentication, permissions, and database behavior | Local and pull requests |

## 6. Test Analysis

| Capability | Tool | Planned policy |
|---|---|---|
| Coverage | coverage.py with pytest-cov | Collect and publish a report for test runs |
| Coverage threshold or regression rule | None initially | Coverage informs review but does not block merging |
| Mutation testing | Not planned | Reconsider only for proven critical logic |
| Reporting | Coverage XML and HTML | Upload XML as a CI artifact; HTML is useful locally |

## 7. Static Analysis and Security

| Check | Tool | Planned enforcement |
|---|---|---|
| Formatting | Ruff format | Verify on pull requests; format locally before commits |
| Linting | Ruff check | Block merging on pull requests |
| Type checking or compiler warnings | Django system checks and Python warnings | Run Django checks in pull requests; add a type checker only when needed |
| Dependency vulnerability scanning | Dependabot | Open update pull requests and review them promptly |
| Secret scanning | Gitleaks | Block merging on pull requests |
| Static security analysis | GitHub CodeQL for Python | Run on pull requests and scheduled scans; investigate alerts before release |
| Container scanning | Not planned initially | Reassess if a production container image is released |

## 8. Development Technologies Requiring Manual Installation

These are developer-workstation prerequisites that will not be supplied by the planned Docker environment.

| Technology | Why it is needed | Required on which machines | Version policy | Planned installation or verification method | Why Docker does not provide it |
|---|---|---|---|---|---|
| Git | Clone the repository and manage source history | Every developer workstation | Supported stable release | Future onboarding verification: `git --version` | Source control operates on the host checkout |
| Docker Desktop or Docker Engine with Compose | Run the planned development containers | Every developer workstation | Current supported release | Future onboarding verification: `docker compose version` | It is the host container runtime |

### Host tools intentionally not required

- **Not required because Docker supplies them:** Python, uv, Django, PostgreSQL, and project dependencies.
- **Not required for this platform:** Xcode, Android Studio, native mobile SDKs, desktop packaging SDKs, and code-signing tools.

## 9. Docker Plan

- **Planned Docker role:** Reproducible development environment.
- **Future files that would be created during implementation:** `Dockerfile`, `compose.yml`, `.dockerignore`, and an example environment-variable file.
- **Planned images and services:** A Django development image and a PostgreSQL service.
- **Development container behavior:** Bind-mount source code, run the Django development server, and retain PostgreSQL data in a named volume.
- **Ports:** Expose the Django development port and PostgreSQL only to the developer machine when needed.
- **Bind mounts and named volumes:** Source bind mount for rapid edits; named PostgreSQL data volume.
- **Environment-variable and secret handling:** Use uncommitted local environment variables; Docker configuration must not embed credentials.
- **Local database or service containers:** PostgreSQL only.
- **Production image or non-container release path:** No production image is planned until a deployment destination is chosen; deploy manually at first.
- **Build stages and hardening:** If production containers are later adopted, use multi-stage builds, a non-root user, a minimal runtime image, `.dockerignore`, health checks, and no embedded secrets.
- **Planned future development command:** `docker compose up --build` (do not run during planning).
- **Planned future production or packaging command:** Deferred until a hosting destination is selected.

## 10. GitHub Actions Plan

### A. Automated pull-request checks

- **Future workflow file:** `.github/workflows/pr-checks.yml`
- **Trigger:** `pull_request`.
- **Runner or matrix:** `ubuntu-latest`; test the supported Python version selected at implementation time.
- **Permissions:** Read-only `contents`; grant only the specific permissions required by CodeQL uploads.
- **Planned jobs in order:**
  1. Check out code, set up Python and uv, restore cached uv downloads, and install locked dependencies.
  2. Verify Ruff formatting; run Ruff linting and Django system checks.
  3. Run pytest with coverage collection and upload coverage XML plus useful test logs on failure.
  4. Run Gitleaks and CodeQL; Dependabot supplies separate dependency-update pull requests.
  5. Validate the Django static-file collection or equivalent production-readiness build step.
- **Service containers:** PostgreSQL service container for integration tests when Django's test database configuration requires PostgreSQL behavior.
- **Caching:** Cache uv's download/cache directories using the lockfile hash.
- **Coverage and analysis reporting:** Retain coverage XML as an artifact; no coverage threshold initially.
- **Failure artifacts:** Coverage XML, pytest output, and CodeQL/Gitleaks results where supported.
- **Checks that should block merging:** Dependency installation, formatting, linting, Django checks, tests, static-file validation, Gitleaks, and CodeQL findings requiring remediation.
- **Proposed branch-protection settings:** Require the listed checks, require pull-request review, and require the branch to be current before merge.

### B. New-release deployment

- **Future workflow file:** `.github/workflows/release.yml`
- **Release trigger:** A manually initiated `workflow_dispatch` or a published GitHub Release after a hosting destination is selected.
- **Release destination:** Manual deployment initially; no hosting provider has been chosen.
- **Runner or matrix:** `ubuntu-latest` for validation and GitHub Release metadata.
- **Planned jobs in order:**
  1. Check out the tagged release source and repeat dependency, formatting, lint, Django-check, test, coverage, Gitleaks, and CodeQL validation.
  2. Collect the application release metadata and publish or update the GitHub Release record.
  3. Leave application deployment as an explicit manual, provider-specific operation until the destination is selected.
- **Build artifacts:** Source revision and release notes; deployment bundles are deferred.
- **Signing, notarization, or store requirements:** None for a browser-based application.
- **Database migration step:** Future deployment instructions must run reviewed Django migrations before or alongside the application release.
- **Environment approval:** Use a protected `production` environment once automated deployment is introduced.
- **Post-deployment verification:** After a provider is selected, perform a manual smoke test of the public page and sign-in flow.
- **Failed-release or rollback approach:** Stop deployment, revert to the last known-good application version at the host, and restore or roll forward migrations according to a pre-reviewed migration plan.

### GitHub configuration required later

| Name | Type | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret | Cryptographic signing key for the deployed Django application |
| `DATABASE_URL` | Secret | Production PostgreSQL connection string |
| `production` | GitHub environment | Protected future deployment approvals and environment-scoped secrets |
| Hosting-provider account and deployment credential | Account and token | Deferred; required only after a deployment provider is chosen |

## 11. Planned Repository Artifacts - Not Created by This Skill

- [ ] Application manifest or project file: `pyproject.toml`
- [ ] Lockfile: `uv.lock`
- [ ] Test configuration: pytest and coverage configuration in `pyproject.toml`
- [ ] Static-analysis configuration: Ruff, Gitleaks, and CodeQL configuration as applicable
- [ ] Docker or Compose files: `Dockerfile`, `compose.yml`, `.dockerignore`
- [ ] `.github/workflows/pr-checks.yml`: pull-request checks
- [ ] `.github/workflows/release.yml`: release validation and future deployment
- [ ] Deployment or store configuration: provider-specific configuration after host selection

## 12. Assumptions and Open Items

- **Assumptions:** No user file uploads, account-to-account collaboration, offline mode, native-app capability, or production container release is required initially.
- **Decisions still requiring an external account, credential, certificate, or organizational approval:** Select a hosting provider and managed PostgreSQL provider; create production credentials and approve GitHub environment protections.
- **Items to confirm before implementation begins:** The application's primary user task, supported browser policy, authentication method, data retention needs, the production host, backup/recovery requirements, and whether browser end-to-end tests should be added for critical journeys.
