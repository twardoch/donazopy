# Technical specification for donazopy doctor

## Purpose and design principles

`donazopy doctor` should be a first-class diagnostic and remediation command that accepts the same target notation already used by the project for local zone files and provider-backed zones, then produces a structured health report, an optional fix plan, and—when `--fix` is present—applies only high-confidence changes that are safe within the tool’s actual provider capabilities. That fits the current shape of `donazopy`, which already supports local BIND-style validation and normalization, provider record export/import/copy, and nameserver operations. fileciteturn0file0

The design should be **static-first**, **provider-aware**, and **safe-by-default**. Static-first matters because many of the most valuable checks do not require live DNS validation at all: malformed RRsets, duplicate-equivalent TXT content, singleton-record conflicts, and migration artifacts can all be caught from a zone file or provider record inventory alone. Provider-aware matters because some findings are only “wrong” in a specific setup—for example, apex `NS` records inside a provider-controlled zone can be a harmless import artifact in one mode and an intentional multi-provider configuration in another. Safe-by-default matters because DNS mistakes can be immediately user-visible, and some changes require knowledge that the zone alone cannot provide, such as the intended mail provider, report mailbox, or certificate authority policy. citeturn22view7turn11view24turn11view25turn11view12turn11view26

A key nuance for your first example is that **zone-apex NS records are mandatory in a real DNS zone**, but **provider-managed DNS products often synthesize or control them themselves**. RFC 2181 says every zone must have an SOA and origin NS RRset, while Cloudflare’s documentation says that in normal full setup it ignores apex `NS` records unless multi-provider DNS is enabled. So `doctor` should not implement the simplistic rule “apex NS is always bad.” Instead, it should implement the more precise rule: “apex NS that points to a previous provider is suspicious in a provider-managed destination zone unless multi-provider or secondary DNS is intentionally enabled.” citeturn15view2turn22view7turn11view14

## Data model and execution modes

The command should operate on three progressively richer data sources. First is the **declared zone state**: a local zone file or provider record inventory. Second is the **provider-control state**: hosted-zone metadata, editable record identifiers, and registrar nameserver assignment when available. Third is the **observed live DNS state**: parent delegation, authoritative answers, DNSSEC chain-of-trust behavior, and optional AXFR tests. Keeping these layers separate is important because users explicitly want checks “especially some that don’t require validation,” and because fixability depends on whether the tool is holding a file, a hosted zone, or a registrar-backed domain. The current project already has the right primitives for this split: local zone operations, provider record operations, zone export/import/copy, and registrar nameserver operations. fileciteturn0file0

I would define three execution modes:

- `--mode=static`: parse the zone or provider inventory only; no live DNS lookups.
- `--mode=standard` (default): include provider metadata and registrar nameserver state when available, but avoid expensive authoritative probing.
- `--mode=full`: add live DNS queries against parent and authoritative servers, DNSSEC checks, delegation consistency checks, and optional AXFR exposure checks. fileciteturn0file0

Internally, `doctor` should normalize everything into a canonical RRset model with: fully-qualified owner name, RR class, type, TTL, provider record id if any, source provenance, raw text form, canonical wire digest, and semantic variants used by specific protocols. The right implementation base is urldnspython docsturn23search1: `dns.zone.from_text()` / `from_file()` can parse zone text, and `dns.rdata` supports text and wire transformations including canonical digestable form. That gives you both stable comparison and precise round-tripping. citeturn23search1turn23search6turn23search9

TXT records need an additional semantic layer. RFC 1035 defines TXT RDATA as one or more `<character-string>` values; SPF explicitly says multiple strings in a single TXT RR must be concatenated without adding spaces; TLS-RPT says the same for its TXT record. That means `doctor` should not compare TXT strings by raw quoted presentation. It should compare at least three forms: raw provider value, parsed RR wire form, and concatenated semantic payload. Your quoted/unquoted duplicate example is exactly why this layer matters. citeturn22view2turn22view3turn22view5

## Rule catalog

### Static structural rules

The first rule family should be hard structural errors. For local BIND-style zones, this includes parse failure, missing SOA, and missing apex NS. RFC 2181 is explicit that SOA and origin NS are the mandatory records in every zone. These are immediate `error` findings and are fixable for local files, but in provider-hosted zones they may be informational if the provider manages those records implicitly. citeturn15view2

The next family is incompatible co-existence at the same owner name. At minimum, `doctor` should enforce provider-side constraints that are well documented and operationally important: on Cloudflare, `A`/`AAAA` cannot exist on the same name as `CNAME`, and `NS` cannot exist on the same name as any other record type. For hosted-zone fixes, this ordering matters because destructive blockers must be removed before replacements are created. citeturn11view12turn18search21

Then add alias-target rules. RFC 2181 says the domain name used as the value of an `NS` record, or part of the value of an `MX` record, must not be an alias, and RFC 1912 reiterates that MX records shall not point to a CNAME. SMTP also requires the domain name returned from MX processing to yield at least one address record. These checks are valuable even in static mode, because when the target is in-zone you can verify it without any network lookup; when it is external, you can downgrade to “needs validation.” citeturn15view0turn11view1turn21view3turn22view0

### Duplicate and normalization rules

A large portion of `doctor`’s value should come from equivalence detection rather than RFC-invalidity. Implement four duplicate classes:

- **Exact duplicates**: same owner, type, class, TTL, and canonical wire RDATA.
- **Provider-presentation duplicates**: same RRset semantics, different textual forms due to case, trailing dots, Punycode presentation, or IP text normalization.
- **TXT semantic duplicates**: same TXT payload after protocol-appropriate concatenation of multi-string TXT records.
- **Escaped-wrapper duplicates**: a structured TXT record whose payload is one layer of quotes deeper than its sibling, such as `v=spf1 ...` versus `"v=spf1 ..."` represented as a literal quoted string. citeturn22view2turn22view3turn22view5turn23search6

The fix policy for duplicates should be conservative. Exact duplicates can be auto-removed. Provider-presentation duplicates can be auto-collapsed to a canonical presentation. TXT semantic duplicates can be auto-collapsed **only when the semantic payloads are provably equivalent**. Escaped-wrapper duplicates should only be auto-fixed when two records become identical after a single safe dequote/unescape pass and at least one of them matches a known structured TXT protocol such as SPF, DMARC, MTA-STS, TLS-RPT, or DKIM key material. Literal quotes are legal TXT content, so the tool must avoid globally stripping quotes from arbitrary TXT records. citeturn22view2turn22view3turn15view7turn22view4turn22view5

### Protocol-specific singleton rules

Some DNS-published protocols effectively require exactly one applicable record. These should be implemented as high-signal checks:

- **SPF**: RFC 7208 says an SPF record is a single TXT RR at the owner name, multiple SPF records are not permitted, and if SPF selection finds more than one record the result is `permerror`. It also sets a hard overall limit of 10 DNS-lookup-causing mechanisms/modifiers and says the `ptr` mechanism should not be published. These should be `error` or `warning` findings with no network requirement for basic detection. citeturn16view0turn16view3turn15view5turn15view6

- **DMARC**: RFC 7489 says that if DMARC policy discovery leaves multiple records or no records, DMARC processing is not applied. That makes duplicate DMARC records a high-priority issue. A syntactically valid single DMARC record at `_dmarc` is therefore a singleton requirement. citeturn22view6turn15view7

- **MTA-STS**: RFC 8461 says that after filtering for records that start with `v=STSv1;`, if the resulting count is not exactly one, senders must assume no available MTA-STS policy. citeturn22view4

- **TLS-RPT**: RFC 8460 says that after filtering for `v=TLSRPTv1;`, if the resulting count is not exactly one, senders must assume the domain does not implement TLSRPT. It also explicitly inherits TXT multi-string concatenation behavior. citeturn22view5

These four singleton checks should be treated as core doctor rules, because they are easy to implement, do not need live validation, and produce findings that are both actionable and operationally important. citeturn16view0turn22view6turn22view4turn22view5

### Email-security presence rules

`doctor` should report missing but commonly-needed email records whenever the zone appears mail-capable. The trigger should be any of: MX records, SPF record, DKIM selector records, `_dmarc`, `_mta-sts`, `_smtp._tls`, common mail hostnames, or provider fingerprints indicating email use. Once triggered, report these presence checks:

- **Missing DMARC** if mail is in use and no DMARC record exists. DMARC is now a practical baseline, not a niche enhancement: RFC 7489 defines it as the domain-level policy layer over SPF/DKIM, Google’s sender guidance says bulk senders are required to set up SPF, DKIM, and DMARC, and Microsoft’s high-volume sender guidance requires SPF, DKIM, and DMARC as well. citeturn11view5turn11view16turn8search7turn9search0

- **Missing DKIM** if mail is in use and there is no in-zone evidence of DKIM selectors. DKIM is one of the two alignment sources DMARC depends on, and provider docs such as IONOS explicitly position it as a standard email-authentication control. citeturn2search1turn22view12turn11view16

- **Missing SPF** if mail is in use and no SPF TXT is present. RFC 7208 makes SPF a TXT-published authorization mechanism, and mailbox-provider guidance now treats it as baseline hygiene. citeturn11view4turn8search7turn9search0

- **Missing MTA-STS / TLS-RPT** as advisory, not error, when the domain receives mail. RFC 8461 and RFC 8460 define them as mechanisms to prevent downgrade or diagnose SMTP TLS failures. These are valuable hardening checks, but not every domain needs them on day one. citeturn11view6turn11view7

A useful extra rule is **“probably no inbound mail, but no Null MX”**. RFC 5321 says that when no MX exists, SMTP falls back to an implicit MX pointing to the host itself, and RFC 7505 defines Null MX precisely so domains can declare that they do not accept mail. If the zone looks purely web-facing and has no mail configuration, `doctor` should recommend a Null MX as an advisory. It should not auto-add one unless the user explicitly opts into a “no mail” profile, because adding Null MX changes semantics. citeturn21view3turn19search0turn19search6

### Web and PKI hardening rules

`doctor` should include **CAA advisory checks** for zones that appear publicly web-facing. RFC 8659 defines CAA as the DNS control that limits which certificate authorities may issue for the domain, and both Let’s Encrypt and Cloudflare document it as a meaningful certificate-governance control. This should be reported as **advisory hardening**, not an automatic fix, because the wrong CAA policy can break certificate issuance. citeturn11view8turn18search0turn18search1turn18search4

`doctor` should also include a **DNSSEC presence and posture** advisory. RFC 4033 defines DNSSEC as adding origin authentication and integrity, but also states that it does not provide confidentiality. So the right doctor behavior is: report absence as an advisory opportunity, but treat broken DNSSEC—especially stale DS after nameserver changes—as a critical live finding. citeturn11view9turn15view11turn22view8

### Provider-aware migration heuristics

This is the family of rules most directly responsive to your two examples.

The first is **old-provider authoritative residue**. In a provider-managed destination zone, apex `NS` records that point at the previous DNS host should be flagged when the current mode is plainly full-managed single-provider DNS. On Cloudflare, that is usually an import artifact because Cloudflare ignores apex `NS` unless multi-provider DNS is enabled; but the same records become meaningful and potentially correct in multi-provider or secondary-DNS setups. Severity should therefore be computed like this:

- `warning` if provider is Cloudflare full setup and apex NS points at non-Cloudflare nameservers while multi-provider is not enabled.
- `info` or suppressed if zone is known multi-provider/secondary.
- `error` only if live validation shows registrar delegation and served apex NS materially disagree in a way that breaks intended authority. citeturn22view7turn11view14turn6search6

The second is **quoted/escaped TXT import residue**. Zone import/export tools and provider APIs expose TXT values differently, while RFCs reason about parsed character strings rather than UI quotation. `doctor` should therefore intentionally detect semantically identical TXT RDATA expressed through different quoting conventions and collapse them to a canonical representation. This is one of the highest-value no-validation checks in the whole tool. citeturn22view2turn22view3turn22view5

## Live validation and authoritative-state checks

The default experience should still be valuable without the network, but the full mode should add a second tier of checks that catch problems static analysis cannot see.

The most important live check is **delegation consistency**: compare the parent-side NS/DS view with the child-zone authoritative view and the provider/registrar control-plane state. Cloudflare’s DNSSEC troubleshooting docs explicitly describe the classic failure where authoritative nameservers are changed but DS records are not updated, producing DNSSEC `SERVFAIL`. This should be a critical rule, usually manual-fix unless the registrar API exposes DS management. citeturn22view8

The second live check is **authoritative convergence**. Query each authoritative server directly for SOA and a representative sample of RRsets, then report inconsistent SOA serials or materially divergent answers. This is especially useful for multi-provider, hidden-primary, or partially migrated zones. Cloudflare’s multi-provider documentation and DNS transfer documentation make clear that multi-provider is real and supported, so divergence detection should be part of any serious “doctor.” citeturn22view7turn11view14turn6search16

The third live check is **glue and delegation-host consistency**. IANA’s nameserver requirements say that when glue IPs are listed for name servers, those IPs must match the authoritative `A`/`AAAA` for that host. RFC 9471 further clarifies expectations around referral glue. This is useful for diagnosing broken or stale in-bailiwick nameserver host records. citeturn14search15turn14search3turn14search6

The fourth live check is **lame delegation**. RFC 1912 describes the operational problem where a server is listed in delegation but is not actually authoritative or properly configured for the child zone. This should be a `warning` or `error` depending on whether at least one healthy nameserver remains. citeturn14search8

An optional fifth live check is **AXFR exposure posture**. RFC 5936 defines AXFR, and RFC 9103 explains that zone transfers are otherwise cleartext and that TSIG is used to restrict direct transfers while XoT adds confidentiality. `doctor` should therefore treat successful unauthenticated AXFR from public servers as a configurable security advisory. Some operators allow it intentionally; many do not. citeturn14search1turn14search9

## Fix engine and safety model

`--fix` should not mean “blindly mutate DNS until the report is green.” It should mean “apply only deterministic, reversible, capability-supported repairs.” The correct execution model is:

1. Resolve the target and take a pre-fix snapshot.
2. Run doctor and compute a fix plan.
3. Print the plan unless `--yes` is present.
4. Apply mutations in dependency order.
5. Re-read the final state and rerun static checks.
6. Emit a post-fix report plus any remaining manual steps. fileciteturn0file0

For local zone files, the snapshot is simply the original file. For provider-backed zones, the snapshot should be an exported BIND zone or provider-native record dump. That is a natural fit with the project’s existing export/import/copy functionality and with Cloudflare’s documented import/export endpoints. fileciteturn0file0 citeturn22view9turn11view26

Fixes should be divided into three classes.

**Safe automatic fixes**:
- delete exact duplicate records;
- collapse semantically identical duplicates to one canonical record;
- remove a proven extra-quote-wrapper TXT duplicate when the surviving record is structurally valid and equivalent;
- normalize case, trailing dots, and IDNA presentation in local files;
- remove stale apex `NS` residue on Cloudflare only when all of the following are true: the zone is in normal full setup, multi-provider DNS is not enabled, registrar nameservers are Cloudflare-only, and the suspect apex `NS` set points to a different provider. citeturn22view7turn11view14

**Plan-only fixes with human review by default**:
- replacing conflicting `CNAME` / `A` / `AAAA` / `NS` combinations;
- consolidating or rewriting SPF;
- adding DMARC, MTA-STS, TLS-RPT, Null MX, or CAA;
- enabling or disabling DNSSEC;
- changing registrar nameservers. citeturn11view12turn16view0turn22view6turn22view4turn22view5turn19search0turn11view8

**Manual-only instructions**:
- creating DKIM selectors when the mail platform must generate keys;
- setting reverse DNS / PTR for outbound mail IPs;
- updating DS records when the registrar API is unavailable;
- deciding the correct reporting mailbox for DMARC/TLS-RPT;
- choosing the proper CAA issuers for a multi-CA environment. citeturn22view12turn22view8turn18search0turn15view9

On Cloudflare-backed hosted zones, use batched record commits when possible. Cloudflare documents both the ordering semantics for batch operations—deletes, then patches, then puts, then posts—and specific same-name restrictions. That is a strong reason for `doctor` to build an explicit action graph instead of emitting unordered record mutations. citeturn5search4turn11view12turn22view10

## Provider integration and command contract

Within the current project shape, `doctor` should reuse donazopy’s existing target parsing and provider abstractions, while layering on top of urlCloudflare DNS docsturn6search17, urlIONOS Developer APIturn13search2, urlJoker.com DMAPI docsturn5search3, and urldnspython docsturn23search1. The present codebase already has the right conceptual split between DNS-hosting providers and registrar providers, which is exactly what `doctor` needs for hosted-zone fixes versus delegation fixes. fileciteturn0file0 citeturn12search0turn12search1turn22view14turn7search1

I would add a small provider capability interface used only by `doctor`:

- `list_zone_records()`
- `export_zone_snapshot()`
- `create_records()` / `update_records()` / `delete_records()`
- `batch_apply()` if supported
- `get_zone_mode()` for features like Cloudflare full/multi-provider/secondary
- `read_nameservers()` / `assign_nameservers()`
- `read_dnssec_state()` if exposed
- `supports_manual_instructions(record_type, rule_id)` for provider-specific remediation text

The command-line contract should look like this:

```bash
donazopy doctor TARGET
donazopy doctor TARGET --fix
donazopy doctor TARGET --mode static|standard|full
donazopy doctor TARGET --format text|json|sarif
donazopy doctor TARGET --severity info|warning|error
donazopy doctor TARGET --profile web|mail|no-mail|strict
donazopy doctor TARGET --yes
donazopy doctor TARGET --output report.json
```

The output model should be stable and machine-readable. Every finding should include:

```json
{
  "rule_id": "TXT_EXTRA_QUOTE_WRAPPER",
  "severity": "warning",
  "confidence": "high",
  "source": "static",
  "owner": "example.com.",
  "rrtype": "TXT",
  "record_ids": ["provider:123", "provider:456"],
  "summary": "Semantically duplicate SPF records differ only by an extra literal quote layer.",
  "evidence": {
    "raw_values": [
      "v=spf1 include:_spf-us.ionos.com ~all",
      "\"v=spf1 include:_spf-us.ionos.com ~all\""
    ],
    "normalized_payload": "v=spf1 include:_spf-us.ionos.com ~all"
  },
  "fixable": true,
  "applied": false,
  "manual_steps": []
}
```

That JSON schema matters because `doctor` should be usable interactively, in CI, and in higher-level automation. It should exit nonzero for `error` findings unless `--allow-errors` is set, and it should separately indicate whether remaining findings are due to lack of capability rather than lack of a possible remediation. The report should also print exact manual next steps when it cannot fix something itself—for example, “update DS at registrar,” “enable DKIM in mail platform and publish these selectors,” or “set multi-provider DNS before keeping apex NS records.” citeturn22view7turn22view8turn22view12

## Recommended initial rule set

For a first implementation, I would ship the following rule set immediately.

**Core static rules that require no validation**:
`ZONE_PARSE_ERROR`, `ZONE_MISSING_SOA`, `ZONE_MISSING_APEX_NS` (file mode only), `DUPLICATE_EXACT`, `DUPLICATE_SEMANTIC_TXT`, `TXT_EXTRA_QUOTE_WRAPPER`, `SPF_MULTIPLE`, `SPF_TOO_MANY_LOOKUPS_ESTIMATE`, `SPF_PTR_USED`, `DMARC_MULTIPLE`, `MTA_STS_MULTIPLE_OR_INVALID`, `TLS_RPT_MULTIPLE_OR_INVALID`, `MX_TARGET_ALIAS`, `NS_TARGET_ALIAS`, `MX_TARGET_NO_INZONE_ADDRESS`, `CLOUDFLARE_APEX_NS_PREVIOUS_PROVIDER`, `NULL_MX_RECOMMENDED`, `DMARC_MISSING_FOR_MAIL`, `DKIM_MISSING_FOR_MAIL`, `SPF_MISSING_FOR_MAIL`, `CAA_MISSING_ADVISORY`. These cover the largest slice of common, automatable mistakes with the lowest risk. citeturn15view2turn16view0turn16view3turn15view5turn15view6turn22view6turn22view4turn22view5turn15view0turn21view3turn11view8turn22view7

**Full-mode validation rules**:
`DELEGATION_NS_MISMATCH`, `DNSSEC_DS_STALE_OR_BROKEN`, `AUTHORITATIVE_DIVERGENCE`, `GLUE_MISMATCH`, `LAME_DELEGATION`, `AXFR_EXPOSED`. These should come next because they are extremely useful operationally, but they involve timeouts, partial failures, and ambiguity that make them less suitable as the first release’s default UX. citeturn22view8turn14search15turn14search8turn14search1turn14search9

**Automatic fixes to enable on day one**:
`DUPLICATE_EXACT`, `DUPLICATE_SEMANTIC_TXT`, `TXT_EXTRA_QUOTE_WRAPPER`, and the Cloudflare migration-specific stale-apex-NS cleanup when the decision criteria are unambiguous. Everything else should initially remain plan-only. That gives users immediate value while avoiding dangerous false certainty. citeturn22view7turn11view14

## Open questions and limitations

The biggest open design question is **intent inference**. A domain can have no MX because it truly has no mail, because mail is not yet configured, or because the operator relies on implicit MX behavior. Likewise, missing DMARC might be a mistake, or the domain might only receive mail and never send it. The right answer is to add `--profile` and `--assume-*` switches so the user can tell `doctor` whether the domain is web-only, mail-sending, mail-receiving, or strict-hardening. Without that, some “missing record” checks must stay advisory. citeturn21view3turn19search0turn11view16

The next limitation is **provider feature asymmetry**. The current project clearly supports record operations and nameserver operations, but not every provider exposes every setting through the same API surface, and some critical remediations—especially DS/registrar actions and DKIM generation—may remain outside `doctor`’s direct control. The command should therefore distinguish “not fixable by DNS semantics” from “fixable in theory but not by this provider adapter.” fileciteturn0file0 citeturn12search0turn12search1turn22view14

The last important limitation is **advanced multi-provider and DNSSEC topologies**. Cloudflare explicitly supports multi-provider DNS and points to multi-signer DNSSEC concerns, which means some states that look odd in a simple migration are actually correct in a high-availability design. `doctor` therefore needs a suppression/escalation model, not just pass/fail logic. In practice, every finding should carry `severity`, `confidence`, and a `requires_intent_confirmation` flag. citeturn22view7turn6search8turn22view8