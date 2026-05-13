Here is the technical specification for implementing the `donazopy doctor` command.

This specification outlines the CLI interface, the heuristic rules engine (including your specific edge cases), the auto-remediation behaviors, and the internal Python API integration required to bring this feature to life.

---

## 1. Overview & Objectives

The `donazopy doctor` command will serve as an automated diagnostic and remediation utility for DNS zones. It will analyze a target zone (either a local BIND file or a live provider zone) against a suite of RFC compliance rules, security best practices, and common migration pitfalls.

When the `--fix` flag is supplied, the tool will leverage `donazopy`'s existing capabilities to automatically resolve safe-to-fix issues, or provide explicit manual instructions for complex structural violations.

---

## 2. CLI Interface & Target Notation

The command will integrate with the existing unified target notation (`[provider/][domain][:record_type][:host_name][:value]`).

### Command Syntax

```bash
donazopy doctor TARGET [--fix] [--rules=RULE_IDS] [--strict]

```

### Options

* `--fix`: Attempts to automatically remediate identified issues. If an issue cannot be auto-fixed, detailed manual instructions are printed.
* `--rules`: A comma-separated list of specific rule IDs to run (e.g., `NS_01,TXT_02`). Defaults to all.
* `--strict`: Enables pedantic warnings (e.g., missing `www` A record) that are not strictly RFC violations.

### Output Formatting

The output should be a scannable, color-coded report:

* 🔴 **Error**: Critical RFC violation or security risk.
* 🟡 **Warning**: Suboptimal configuration or missing best-practice record.
* 🟢 **Pass**: Check completed successfully.
* 🔧 **Fixed**: Successfully auto-remediated (only shown when `--fix` is active).
* 🛠️ **Manual Action Required**: Instructions for issues that cannot be auto-fixed.

---

## 3. Diagnostic Heuristics & Rules Engine

The core of `donazopy doctor` is the rules engine. Below are the specific tests to implement, heavily informed by common DNS misconfigurations and your specific migration use cases.

### Category 1: Delegation & Provider Mismatches

These issues often occur after using commands like `donazopy copy` to migrate zones between operational providers like IONOS and Cloudflare.

* **Rule `NS_01`: Stray / Orphaned NS Records (Your Case)**
* **Detection**: Queries the registrar for authoritative nameservers using `registrar.read_nameservers("domain.com")`. Compares these against the root `@` NS records in the zone file.
* **Logic**: If the zone contains NS records pointing to a known other provider (e.g., `ns-us.ionos.com` inside a Cloudflare zone), flag as an error. Root NS records in the zone *must* match the delegation.
* **Auto-Fix (`--fix`)**: Deletes the mismatched NS records from the zone using the provider API.



### Category 2: Syntax & Normalization

Differences in how providers export/import BIND text can cause syntax artifacts.

* **Rule `TXT_01`: Double-Quoted TXT Duplicates (Your Case)**
* **Detection**: Scans all TXT records for strings starting and ending with escaped quotes (e.g., `"\"v=spf1...\""`).
* **Logic**: Normalizes all TXT values by stripping outermost redundant quotes. Compares normalized values to detect duplicates.
* **Auto-Fix (`--fix`)**: Identifies the malformed duplicate, strips the redundant quotes, checks if the cleaned string perfectly matches an existing record, and if so, deletes the duplicate.



### Category 3: Email Security Best Practices

Missing or conflicting email records are the most common source of degraded domain reputation.

* **Rule `SEC_01`: Multiple SPF Records**
* **Detection**: Counts TXT records at the root (`@`) starting with `v=spf1`.
* **Logic**: RFC strictly forbids multiple SPF records. They must be merged.
* **Auto-Fix (`--fix`)**: Merges multiple records into one (e.g., combining `include:` mechanisms) if the character count remains under 255. If complex, flags for manual intervention.


* **Rule `SEC_02`: Missing SPF Record**
* **Detection**: Checks for the absence of `v=spf1` TXT records at the root.
* **Auto-Fix (`--fix`)**: Cannot auto-fix safely without knowing the email sender.
* **Manual Instruction**: Prints: *"Add a TXT record at '@' with your mail provider's SPF string (e.g., `v=spf1 include:_spf.google.com ~all`)."*


* **Rule `SEC_03`: Missing DMARC Record**
* **Detection**: Checks for a TXT record at `_dmarc` starting with `v=DMARC1`.
* **Auto-Fix (`--fix`)**: Safely creates a monitoring-only policy: `v=DMARC1; p=none;`.



### Category 4: Structural Integrity & RFC Compliance

* **Rule `RFC_01`: CNAME at Apex (Root)**
* **Detection**: Checks if a CNAME record exists at the root `@`.
* **Logic**: RFCs dictate the apex cannot be a CNAME because it conflicts with mandatory SOA and NS records.
* **Auto-Fix (`--fix`)**: Cannot auto-fix directly.
* **Manual Instruction**: Prints: *"Convert the CNAME at the root to an A/AAAA record, or use an ALIAS/ANAME record if your provider supports it."*


* **Rule `RFC_02`: MX Pointing to CNAME**
* **Detection**: Looks up the target of all MX records and checks if that target resolves to a CNAME in the zone.
* **Logic**: MX records must point directly to an A or AAAA record.
* **Auto-Fix (`--fix`)**: Resolves the CNAME chain internally and rewrites the MX record to point directly to the final A/AAAA hostname.


* **Rule `SEC_04`: Dangling CNAMEs**
* **Detection**: Identifies CNAMEs pointing to external domains and performs a lightweight DNS lookup.
* **Logic**: If the target returns `NXDOMAIN`, it is a dangling CNAME, posing a high risk for subdomain takeover.
* **Auto-Fix (`--fix`)**: Deletes the dangling CNAME record.



---

## 4. Implementation Architecture

The `doctor` command will be built utilizing the existing `donazopy` Python API structure.

### Step 1: Target Resolution & Data Ingestion

1. Parse the target using `parse_target(TARGET)` to determine if the user is scanning a local file (`.zone`) or a live provider (`cloudflare/example.com`).
2. Retrieve the records into a unified `records` list using `records_from_zone_file` (for local) or `provider.list_records(domain)` (for remote).

### Step 2: The Assessment Engine

Create a new module `donazopy.doctor` containing an abstract `DiagnosticRule` class.

```python
class DiagnosticRule:
    rule_id: str
    description: str
    
    def assess(self, records: list, provider=None, registrar=None) -> list[DoctorFinding]:
        pass
        
    def remediate(self, finding: DoctorFinding, provider=None) -> bool:
        pass

```

### Step 3: Execution and Remediation (`--fix` flow)

1. Run all active `DiagnosticRule.assess()` methods against the ingested records.
2. If `--fix` is passed, iterate through the generated `DoctorFinding` objects.
3. For remote targets, use the provider API to push changes. Since file writes refuse to overwrite without the `--overwrite` flag, apply the same safety model to the doctor command when dealing with local `.zone` files.
4. For live providers, use granular API calls (like updating specific records) to apply fixes. If a provider API lacks granular updates, utilize the existing diff logic via `diff_zone_records(before_records, after_records)` to calculate necessary changes, then sync.

### Step 4: Error Handling & Capabilities

Wrap the doctor execution in the existing safety net:

* Catch `ProviderCredentialError` if the doctor needs registrar access but lacks keys.
* Catch `ProviderAPIError` during auto-fix attempts and fallback to manual instructions.
* Ensure clear "not supported" errors if the doctor tries to check delegation on a provider that isn't mapped as a registrar.