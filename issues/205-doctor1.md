I ran: 

```
for p in $(cat private/domains.txt ); do donazopy doctor cloudflare/$p; done;
```

and I got the following report: 

<REPORT>
DNS Doctor Report: cloudflare/font.ac
========================================
errors=0 warnings=1 info=1 fixable=1 fixed=0

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.font.ac.
  Suggested: _dmarc.font.ac. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@font.ac"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - font.ac.
  Suggested: font.ac. 3600 IN CAA 0 issue "letsencrypt.org"

Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for font.bond.: rdataset type is not compatible with a CNAME node
DNS Doctor Report: cloudflare/fontbond.com
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '0b9186dfe55368f29ec27fbd66e29a6c4f5bf88e8dc7a9b592da63eefc2c38bf_1777931767486'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontbond.com. 3600 IN TXT "0b9186dfe55368f29ec27fbd66e29a6c4f5bf88e8dc7a9b592da63eefc2c38bf_1777931767486"
    - _dep_ws_mutex.fontbond.com. 3600 IN TXT "\"0b9186dfe55368f29ec27fbd66e29a6c4f5bf88e8dc7a9b592da63eefc2c38bf_1777931767486\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontbond.com. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontbond.com. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontbond.com.
  Suggested: _dmarc.fontbond.com. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontbond.com"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontbond.com.
  Suggested: fontbond.com. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.ai
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '7b50aaddac489c33b430b2c3eefe0cdda23f462ae8e117b414891fe09373a226_1777931693152'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.ai. 3600 IN TXT "7b50aaddac489c33b430b2c3eefe0cdda23f462ae8e117b414891fe09373a226_1777931693152"
    - _dep_ws_mutex.fontlab.ai. 3600 IN TXT "\"7b50aaddac489c33b430b2c3eefe0cdda23f462ae8e117b414891fe09373a226_1777931693152\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.ai. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.ai. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.ai. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.ai. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.ai.
  Suggested: _dmarc.fontlab.ai. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.ai"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.ai.
  Suggested: fontlab.ai. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.app
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '2d4ec89b1d76a51591d62fec0c6cbf6d67b4db41ce6c8e53e65489b375907631_1777992275802'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.app. 3600 IN TXT "2d4ec89b1d76a51591d62fec0c6cbf6d67b4db41ce6c8e53e65489b375907631_1777992275802"
    - _dep_ws_mutex.fontlab.app. 3600 IN TXT "\"2d4ec89b1d76a51591d62fec0c6cbf6d67b4db41ce6c8e53e65489b375907631_1777992275802\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.app. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.app. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.app. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.app. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.app.
  Suggested: _dmarc.fontlab.app. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.app"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.app.
  Suggested: fontlab.app. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.biz
========================================
errors=5 warnings=0 info=1 fixable=5 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '67ae2e1301d5df5a0799bdf779cb7f367964ae336cdee4ca0e836f789825f555_1777932527781'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.biz. 3600 IN TXT "67ae2e1301d5df5a0799bdf779cb7f367964ae336cdee4ca0e836f789825f555_1777932527781"
    - _dep_ws_mutex.fontlab.biz. 3600 IN TXT "\"67ae2e1301d5df5a0799bdf779cb7f367964ae336cdee4ca0e836f789825f555_1777932527781\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dmarc share the same payload after unquoting (fixable)
  Semantic payload: 'v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dmarc.fontlab.biz. 3600 IN TXT "\"v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com\""
    - _dmarc.fontlab.biz. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _github-pages-challenge-fontlab share the same payload after unquoting (fixable)
  Semantic payload: '14adc09d53dd05bb6ebc103703eb93'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _github-pages-challenge-fontlab.fontlab.biz. 3600 IN TXT "14adc09d53dd05bb6ebc103703eb93"
    - _github-pages-challenge-fontlab.fontlab.biz. 3600 IN TXT "\"14adc09d53dd05bb6ebc103703eb93\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.biz. 3600 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.biz. 3600 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.biz. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.biz. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.biz.
  Suggested: fontlab.biz. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.cc
========================================
errors=4 warnings=0 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'd1845deffe98b2ef52165c6124911e51b7f4df273b6174a9445a21468a5f64c6_1778017243876'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.cc. 3600 IN TXT "\"d1845deffe98b2ef52165c6124911e51b7f4df273b6174a9445a21468a5f64c6_1778017243876\""
    - _dep_ws_mutex.fontlab.cc. 3600 IN TXT "d1845deffe98b2ef52165c6124911e51b7f4df273b6174a9445a21468a5f64c6_1778017243876"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dmarc share the same payload after unquoting (fixable)
  Semantic payload: 'v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dmarc.fontlab.cc. 3600 IN TXT "\"v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com\""
    - _dmarc.fontlab.cc. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.cc. 3600 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.cc. 3600 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.cc. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.cc. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.cc.
  Suggested: fontlab.cc. 3600 IN CAA 0 issue "letsencrypt.org"

Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for fontlab.co.: rdataset type is not compatible with a CNAME node
DNS Doctor Report: cloudflare/fontlab.dev
========================================
errors=0 warnings=0 info=1 fixable=0 fixed=0

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.dev.
  Suggested: fontlab.dev. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.eu
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.eu. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.eu. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.eu. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.eu. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.eu.
  Suggested: _dmarc.fontlab.eu. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.eu"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.eu.
  Suggested: fontlab.eu. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.forum
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'd38acdcaaba3d0a523d63e9d732d24795010fb7c4869e530737f7b1a12235a41_1777994514061'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.forum. 3600 IN TXT "\"d38acdcaaba3d0a523d63e9d732d24795010fb7c4869e530737f7b1a12235a41_1777994514061\""
    - _dep_ws_mutex.fontlab.forum. 3600 IN TXT "d38acdcaaba3d0a523d63e9d732d24795010fb7c4869e530737f7b1a12235a41_1777994514061"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.forum. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.forum. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.forum.
  Suggested: _dmarc.fontlab.forum. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.forum"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.forum.
  Suggested: fontlab.forum. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.help
========================================
errors=4 warnings=1 info=1 fixable=5 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - fontlab.help. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - fontlab.help. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - fontlab.help. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - fontlab.help. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '147d086e9e5022a5fa55e14c308bb55a8818f94b66288e336af4a8a37d52f9ab_1777935372844'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.help. 3600 IN TXT "147d086e9e5022a5fa55e14c308bb55a8818f94b66288e336af4a8a37d52f9ab_1777935372844"
    - _dep_ws_mutex.fontlab.help. 3600 IN TXT "\"147d086e9e5022a5fa55e14c308bb55a8818f94b66288e336af4a8a37d52f9ab_1777935372844\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.help. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.help. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.help. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.help. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.help.
  Suggested: _dmarc.fontlab.help. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.help"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.help.
  Suggested: fontlab.help. 3600 IN CAA 0 issue "letsencrypt.org"

Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for fontlab.in.: rdataset type is not compatible with a CNAME node
Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for fontlab.info.: rdataset type is not compatible with a CNAME node
DNS Doctor Report: cloudflare/fontlab.ltd
========================================
errors=1 warnings=0 info=1 fixable=1 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'f4543827adf951ed689cfda9a19bb4e8022ad1a43b3553fc95bfa0dc0eb9a40d_1777935505483'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.ltd. 3600 IN TXT "\"f4543827adf951ed689cfda9a19bb4e8022ad1a43b3553fc95bfa0dc0eb9a40d_1777935505483\""
    - _dep_ws_mutex.fontlab.ltd. 3600 IN TXT "f4543827adf951ed689cfda9a19bb4e8022ad1a43b3553fc95bfa0dc0eb9a40d_1777935505483"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.ltd.
  Suggested: fontlab.ltd. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.me
========================================
errors=4 warnings=0 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '6537a82db8cab0fd35ff1c91f2d5efb013c97a37ee00cc80fd1ba785a214e7d0_1777935547456'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.me. 3600 IN TXT "6537a82db8cab0fd35ff1c91f2d5efb013c97a37ee00cc80fd1ba785a214e7d0_1777935547456"
    - _dep_ws_mutex.fontlab.me. 3600 IN TXT "\"6537a82db8cab0fd35ff1c91f2d5efb013c97a37ee00cc80fd1ba785a214e7d0_1777935547456\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dmarc share the same payload after unquoting (fixable)
  Semantic payload: 'v=DMARC1; p=none;'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dmarc.fontlab.me. 3600 IN TXT "\"v=DMARC1; p=none;\""
    - _dmarc.fontlab.me. 3600 IN TXT "v=DMARC1; p=none;"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'mailerlite-domain-verification=f94b3358266c85b1b1a4a91429141d7df6c3bda4'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.me. 3600 IN TXT "\"mailerlite-domain-verification=f94b3358266c85b1b1a4a91429141d7df6c3bda4\""
    - fontlab.me. 3600 IN TXT "mailerlite-domain-verification=f94b3358266c85b1b1a4a91429141d7df6c3bda4"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 a mx include:_spf.mlsend.com ?all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.me. 3600 IN TXT "\"v=spf1 a mx include:_spf.mlsend.com ?all\""
    - fontlab.me. 3600 IN TXT "v=spf1 a mx include:_spf.mlsend.com ?all"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.me.
  Suggested: fontlab.me. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.mobi
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '2cf7492e06421cc5f175539ccef9b38bd5c43db6f1a174b159f081aabce8cd86_1778020396852'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.mobi. 3600 IN TXT "2cf7492e06421cc5f175539ccef9b38bd5c43db6f1a174b159f081aabce8cd86_1778020396852"
    - _dep_ws_mutex.fontlab.mobi. 3600 IN TXT "\"2cf7492e06421cc5f175539ccef9b38bd5c43db6f1a174b159f081aabce8cd86_1778020396852\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.mobi. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.mobi. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.mobi. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.mobi. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.mobi.
  Suggested: _dmarc.fontlab.mobi. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.mobi"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.mobi.
  Suggested: fontlab.mobi. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.org
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _github-pages-challenge-fontlaborg share the same payload after unquoting (fixable)
  Semantic payload: '78321a6e61b535da4ebf8dae7490be'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _github-pages-challenge-fontlaborg.fontlab.org. 3600 IN TXT "78321a6e61b535da4ebf8dae7490be"
    - _github-pages-challenge-fontlaborg.fontlab.org. 3600 IN TXT "\"78321a6e61b535da4ebf8dae7490be\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.org. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.org. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.org.
  Suggested: _dmarc.fontlab.org. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.org"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.org.
  Suggested: fontlab.org. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.pro
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '84702c36ce4ac9ae8fbffbde472c70051387628e5c55a62363026bf88b0e55c6_1777995805827'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.pro. 3600 IN TXT "84702c36ce4ac9ae8fbffbde472c70051387628e5c55a62363026bf88b0e55c6_1777995805827"
    - _dep_ws_mutex.fontlab.pro. 3600 IN TXT "\"84702c36ce4ac9ae8fbffbde472c70051387628e5c55a62363026bf88b0e55c6_1777995805827\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.pro. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.pro. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.pro. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.pro. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.pro.
  Suggested: _dmarc.fontlab.pro. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.pro"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.pro.
  Suggested: fontlab.pro. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.ru
========================================
errors=1 warnings=2 info=1 fixable=2 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'fc6c934a10dc2658742a48bedc5c15b2eea1f8b859129c9ffcc5962f2d8752e4_1777935662314'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.ru. 3600 IN TXT "\"fc6c934a10dc2658742a48bedc5c15b2eea1f8b859129c9ffcc5962f2d8752e4_1777935662314\""
    - _dep_ws_mutex.fontlab.ru. 3600 IN TXT "fc6c934a10dc2658742a48bedc5c15b2eea1f8b859129c9ffcc5962f2d8752e4_1777935662314"

[WARNING] SPF_MISSING: No SPF record found despite MX records being present
  Without an SPF record, receivers cannot validate which servers may send email for this domain. Add a TXT record at the apex listing authorized senders.
    - fontlab.ru.
  Suggested: fontlab.ru. 3600 IN TXT "v=spf1 include:_spf.your-provider.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.ru.
  Suggested: _dmarc.fontlab.ru. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.ru"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.ru.
  Suggested: fontlab.ru. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.shop
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'cc82fba98087095781af5e9165a9194ae0fa91424d06304cc17c205d9adb2e43_1777935739420'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.shop. 3600 IN TXT "\"cc82fba98087095781af5e9165a9194ae0fa91424d06304cc17c205d9adb2e43_1777935739420\""
    - _dep_ws_mutex.fontlab.shop. 3600 IN TXT "cc82fba98087095781af5e9165a9194ae0fa91424d06304cc17c205d9adb2e43_1777935739420"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.shop. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.shop. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.shop.
  Suggested: _dmarc.fontlab.shop. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.shop"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.shop.
  Suggested: fontlab.shop. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.studio
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '2a7b510baee6ef225b9d18ea65edd7a416dd1080e474dcd73a3c0716cae8a6ae_1778002787298'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.studio. 3600 IN TXT "2a7b510baee6ef225b9d18ea65edd7a416dd1080e474dcd73a3c0716cae8a6ae_1778002787298"
    - _dep_ws_mutex.fontlab.studio. 3600 IN TXT "\"2a7b510baee6ef225b9d18ea65edd7a416dd1080e474dcd73a3c0716cae8a6ae_1778002787298\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.studio. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.studio. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.studio. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.studio. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.studio.
  Suggested: _dmarc.fontlab.studio. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.studio"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.studio.
  Suggested: fontlab.studio. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.tv
========================================
errors=4 warnings=1 info=1 fixable=5 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '2d6f8522407a2b7da19c97f07f8dce03e249eff47e078d717fe51c688bcda925_1777985367734'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.tv. 3600 IN TXT "2d6f8522407a2b7da19c97f07f8dce03e249eff47e078d717fe51c688bcda925_1777985367734"
    - _dep_ws_mutex.fontlab.tv. 3600 IN TXT "\"2d6f8522407a2b7da19c97f07f8dce03e249eff47e078d717fe51c688bcda925_1777985367734\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _github-pages-challenge-fontlab share the same payload after unquoting (fixable)
  Semantic payload: '1657c2a179bcf1097361b0a487b204'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _github-pages-challenge-fontlab.fontlab.tv. 3600 IN TXT "1657c2a179bcf1097361b0a487b204"
    - _github-pages-challenge-fontlab.fontlab.tv. 3600 IN TXT "\"1657c2a179bcf1097361b0a487b204\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.tv. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.tv. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.tv. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.tv. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.tv.
  Suggested: _dmarc.fontlab.tv. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.tv"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.tv.
  Suggested: fontlab.tv. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlab.us
========================================
errors=4 warnings=1 info=1 fixable=5 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '6bcea816d309ef1b43d57a1b2f715fe56f7895a72e52f24a57b03ed4bd110802_1777985136946'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlab.us. 3600 IN TXT "6bcea816d309ef1b43d57a1b2f715fe56f7895a72e52f24a57b03ed4bd110802_1777985136946"
    - _dep_ws_mutex.fontlab.us. 3600 IN TXT "\"6bcea816d309ef1b43d57a1b2f715fe56f7895a72e52f24a57b03ed4bd110802_1777985136946\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _github-pages-challenge-fontlab share the same payload after unquoting (fixable)
  Semantic payload: '8cc35e0f934aeb74ba6342afb2e6ff'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _github-pages-challenge-fontlab.fontlab.us. 3600 IN TXT "8cc35e0f934aeb74ba6342afb2e6ff"
    - _github-pages-challenge-fontlab.fontlab.us. 3600 IN TXT "\"8cc35e0f934aeb74ba6342afb2e6ff\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'brevo-code:c4e69544627569f82416065f2490c857'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.us. 300 IN TXT "\"brevo-code:c4e69544627569f82416065f2490c857\""
    - fontlab.us. 300 IN TXT "brevo-code:c4e69544627569f82416065f2490c857"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlab.us. 300 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlab.us. 300 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlab.us.
  Suggested: _dmarc.fontlab.us. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlab.us"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlab.us.
  Suggested: fontlab.us. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/fontlock.com
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '2e24b58bbb8f7b67971f3a91927fc17a6d1c41bb1403618f4d1b9009638e9c5e_1777996509161'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.fontlock.com. 3600 IN TXT "2e24b58bbb8f7b67971f3a91927fc17a6d1c41bb1403618f4d1b9009638e9c5e_1777996509161"
    - _dep_ws_mutex.fontlock.com. 3600 IN TXT "\"2e24b58bbb8f7b67971f3a91927fc17a6d1c41bb1403618f4d1b9009638e9c5e_1777996509161\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - fontlock.com. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - fontlock.com. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.fontlock.com.
  Suggested: _dmarc.fontlock.com. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@fontlock.com"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - fontlock.com.
  Suggested: fontlock.com. 3600 IN CAA 0 issue "letsencrypt.org"

Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for fontographer.info.: rdataset type is not compatible with a CNAME node
Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for fontographer.net.: rdataset type is not compatible with a CNAME node
Traceback (most recent call last):
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 104, in parse_zone_text
    zone = dns.zone.from_text(text, origin=origin, relativize=relativize, check_origin=True)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1312, in from_text
    return _from_text(
        text,
    ...<8 lines>...
        allow_directives,
    )
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zone.py", line 1242, in _from_text
    reader.read()
    ~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 551, in read
    self._rr_line()
    ~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 275, in _rr_line
    self.txn.add(name, ttl, rd)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 172, in add
    self._add(False, args)
    ~~~~~~~~~^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 460, in _add
    self._checked_put_rdataset(name, rdataset)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/transaction.py", line 541, in _checked_put_rdataset
    check(self, name, rdataset)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/dns/zonefile.py", line 57, in _check_cname_and_other_data
    raise CNAMEAndOtherData("rdataset type is not compatible with a CNAME node")
dns.zonefile.CNAMEAndOtherData: rdataset type is not compatible with a CNAME node

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.13/bin/donazopy", line 10, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/__main__.py", line 11, in main
    fire.Fire(Donazopy)
    ~~~~~~~~~^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 135, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 468, in _Fire
    component, remaining_args = _CallAndUpdateTrace(
                                ~~~~~~~~~~~~~~~~~~~^
        component,
        ^^^^^^^^^^
    ...<2 lines>...
        treatment='class' if is_class else 'routine',
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        target=component.__name__)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/fire/core.py", line 684, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/cli.py", line 342, in doctor
    report = analyze_provider_records(list(records), domain=domain, provider_key=key)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/doctor.py", line 606, in analyze_provider_records
    records = records_from_zone_text(zone_text, origin)
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 280, in records_from_zone_text
    return records_from_zone(parse_zone_text(text, origin))
                             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/Users/adam/Developer/vcs3/github.twardoch/pub/donazopy/src/donazopy/zonefile.py", line 107, in parse_zone_text
    raise ZoneFileError(msg) from exc
donazopy.zonefile.ZoneFileError: invalid zone for fontographer.org.: rdataset type is not compatible with a CNAME node
DNS Doctor Report: cloudflare/font.ski
========================================
errors=1 warnings=1 info=1 fixable=2 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '9231591f0ab970b135c562a852cb45e881bbf0b62e71c1b589c3f51224a6dcf7_1777930981082'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.font.ski. 3600 IN TXT "9231591f0ab970b135c562a852cb45e881bbf0b62e71c1b589c3f51224a6dcf7_1777930981082"
    - _dep_ws_mutex.font.ski. 3600 IN TXT "\"9231591f0ab970b135c562a852cb45e881bbf0b62e71c1b589c3f51224a6dcf7_1777930981082\""

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.font.ski.
  Suggested: _dmarc.font.ski. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@font.ski"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - font.ski.
  Suggested: font.ski. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/intellifont.com
========================================
errors=1 warnings=1 info=1 fixable=2 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '7e313f9b752612c506cb75edf6b5d843a5ca5ad89f428c6fd4996a000e52b0cb_1777984922488'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.intellifont.com. 3600 IN TXT "7e313f9b752612c506cb75edf6b5d843a5ca5ad89f428c6fd4996a000e52b0cb_1777984922488"
    - _dep_ws_mutex.intellifont.com. 3600 IN TXT "\"7e313f9b752612c506cb75edf6b5d843a5ca5ad89f428c6fd4996a000e52b0cb_1777984922488\""

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.intellifont.com.
  Suggested: _dmarc.intellifont.com. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@intellifont.com"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - intellifont.com.
  Suggested: intellifont.com. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/photofont.com
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '72b04439a1a2df49dade92e4a6f89841e1e2f3ce18b760ecef6984831670b54f_1777984859329'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.photofont.com. 3600 IN TXT "72b04439a1a2df49dade92e4a6f89841e1e2f3ce18b760ecef6984831670b54f_1777984859329"
    - _dep_ws_mutex.photofont.com. 3600 IN TXT "\"72b04439a1a2df49dade92e4a6f89841e1e2f3ce18b760ecef6984831670b54f_1777984859329\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - photofont.com. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - photofont.com. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.photofont.com.
  Suggested: _dmarc.photofont.com. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@photofont.com"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - photofont.com.
  Suggested: photofont.com. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/photofont.info
========================================
errors=1 warnings=1 info=1 fixable=2 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'd20b1d340e824cb5634eba89f75ca254185b399271f1e88cfba2762b336469e5_1777984816732'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.photofont.info. 3600 IN TXT "\"d20b1d340e824cb5634eba89f75ca254185b399271f1e88cfba2762b336469e5_1777984816732\""
    - _dep_ws_mutex.photofont.info. 3600 IN TXT "d20b1d340e824cb5634eba89f75ca254185b399271f1e88cfba2762b336469e5_1777984816732"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.photofont.info.
  Suggested: _dmarc.photofont.info. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@photofont.info"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - photofont.info.
  Suggested: photofont.info. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/transtype.info
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'cdb857ce961d0e5b08601d316ee72a9ca9e46d5dcc4f81c473a789a3089cb1b4_1777984744990'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.transtype.info. 3600 IN TXT "\"cdb857ce961d0e5b08601d316ee72a9ca9e46d5dcc4f81c473a789a3089cb1b4_1777984744990\""
    - _dep_ws_mutex.transtype.info. 3600 IN TXT "cdb857ce961d0e5b08601d316ee72a9ca9e46d5dcc4f81c473a789a3089cb1b4_1777984744990"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - transtype.info. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - transtype.info. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.transtype.info.
  Suggested: _dmarc.transtype.info. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@transtype.info"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - transtype.info.
  Suggested: transtype.info. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/typedub.com
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - typedub.com. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - typedub.com. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - typedub.com. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - typedub.com. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '905a8dd8f02e3a3eac6a22202dfd01c574ff785a6cad24c4776cdcaec5d24c5a_1777997946553'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.typedub.com. 3600 IN TXT "905a8dd8f02e3a3eac6a22202dfd01c574ff785a6cad24c4776cdcaec5d24c5a_1777997946553"
    - _dep_ws_mutex.typedub.com. 3600 IN TXT "\"905a8dd8f02e3a3eac6a22202dfd01c574ff785a6cad24c4776cdcaec5d24c5a_1777997946553\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - typedub.com. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - typedub.com. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.typedub.com.
  Suggested: _dmarc.typedub.com. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@typedub.com"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - typedub.com.
  Suggested: typedub.com. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/typetool.info
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - typetool.info. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - typetool.info. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - typetool.info. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - typetool.info. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '90759d48d04f77d1b4f42315330049f41ea2abf7b6e2f7521aea8a225ecf9b57_1777984691066'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.typetool.info. 3600 IN TXT "90759d48d04f77d1b4f42315330049f41ea2abf7b6e2f7521aea8a225ecf9b57_1777984691066"
    - _dep_ws_mutex.typetool.info. 3600 IN TXT "\"90759d48d04f77d1b4f42315330049f41ea2abf7b6e2f7521aea8a225ecf9b57_1777984691066\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - typetool.info. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - typetool.info. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.typetool.info.
  Suggested: _dmarc.typetool.info. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@typetool.info"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - typetool.info.
  Suggested: typetool.info. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.art
========================================
errors=12 warnings=1 info=1 fixable=13 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.art. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.art. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.art. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.art. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.api share the same payload after unquoting (fixable)
  Semantic payload: '3b488de5d9dce82459f0928d3fcc4c4e664597b2577aa971d92e5cad16daa9d8_1778004962163'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.api.vexy.art. 3600 IN TXT "3b488de5d9dce82459f0928d3fcc4c4e664597b2577aa971d92e5cad16daa9d8_1778004962163"
    - _dep_ws_mutex.api.vexy.art. 3600 IN TXT "\"3b488de5d9dce82459f0928d3fcc4c4e664597b2577aa971d92e5cad16daa9d8_1778004962163\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.bezz share the same payload after unquoting (fixable)
  Semantic payload: '6fd5dee4fd927ef645b53f48392f8ddfa83f5606ada7a52a982036faef5e14ad_1778005132139'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.bezz.vexy.art. 3600 IN TXT "6fd5dee4fd927ef645b53f48392f8ddfa83f5606ada7a52a982036faef5e14ad_1778005132139"
    - _dep_ws_mutex.bezz.vexy.art. 3600 IN TXT "\"6fd5dee4fd927ef645b53f48392f8ddfa83f5606ada7a52a982036faef5e14ad_1778005132139\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.download share the same payload after unquoting (fixable)
  Semantic payload: 'ee6dd11085cf289bb04e854cd73e945f29dc4727b65a6d49fdcf387dcb06d78c_1778005464179'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.download.vexy.art. 3600 IN TXT "\"ee6dd11085cf289bb04e854cd73e945f29dc4727b65a6d49fdcf387dcb06d78c_1778005464179\""
    - _dep_ws_mutex.download.vexy.art. 3600 IN TXT "ee6dd11085cf289bb04e854cd73e945f29dc4727b65a6d49fdcf387dcb06d78c_1778005464179"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.forum share the same payload after unquoting (fixable)
  Semantic payload: 'd2a33af9be02139ce4c679aab2ec49998f2ab80f30dca4ba06c37f98023ad9a3_1778005578469'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.forum.vexy.art. 3600 IN TXT "\"d2a33af9be02139ce4c679aab2ec49998f2ab80f30dca4ba06c37f98023ad9a3_1778005578469\""
    - _dep_ws_mutex.forum.vexy.art. 3600 IN TXT "d2a33af9be02139ce4c679aab2ec49998f2ab80f30dca4ba06c37f98023ad9a3_1778005578469"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.get share the same payload after unquoting (fixable)
  Semantic payload: '00aec83f5b7f539785ff6f193eaf4510e3a6f817162ccf415d4ac9dd58129459_1778005608622'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.get.vexy.art. 3600 IN TXT "00aec83f5b7f539785ff6f193eaf4510e3a6f817162ccf415d4ac9dd58129459_1778005608622"
    - _dep_ws_mutex.get.vexy.art. 3600 IN TXT "\"00aec83f5b7f539785ff6f193eaf4510e3a6f817162ccf415d4ac9dd58129459_1778005608622\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.go share the same payload after unquoting (fixable)
  Semantic payload: '00f149123c471495d7efcb130a9f142af12c658c77fb39e3aa283810971bbae1_1778005795812'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.go.vexy.art. 3600 IN TXT "00f149123c471495d7efcb130a9f142af12c658c77fb39e3aa283810971bbae1_1778005795812"
    - _dep_ws_mutex.go.vexy.art. 3600 IN TXT "\"00f149123c471495d7efcb130a9f142af12c658c77fb39e3aa283810971bbae1_1778005795812\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex.lines share the same payload after unquoting (fixable)
  Semantic payload: '609eeed9ea4c8bd2b2718726d56928bec8c3d15984bb2a2e06da6eee9f475c82_1778006404951'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.lines.vexy.art. 3600 IN TXT "609eeed9ea4c8bd2b2718726d56928bec8c3d15984bb2a2e06da6eee9f475c82_1778006404951"
    - _dep_ws_mutex.lines.vexy.art. 3600 IN TXT "\"609eeed9ea4c8bd2b2718726d56928bec8c3d15984bb2a2e06da6eee9f475c82_1778006404951\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'fb537e94934bbe071605cbe9df1bd5b5130fa682341fe718c1c9bc875129f1ed_1778024977764'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.art. 3600 IN TXT "\"fb537e94934bbe071605cbe9df1bd5b5130fa682341fe718c1c9bc875129f1ed_1778024977764\""
    - _dep_ws_mutex.vexy.art. 3600 IN TXT "fb537e94934bbe071605cbe9df1bd5b5130fa682341fe718c1c9bc875129f1ed_1778024977764"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _github-pages-challenge-fontlab share the same payload after unquoting (fixable)
  Semantic payload: 'e24cd03623a977eafca668f1b5f825'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _github-pages-challenge-fontlab.vexy.art. 3600 IN TXT "\"e24cd03623a977eafca668f1b5f825\""
    - _github-pages-challenge-fontlab.vexy.art. 3600 IN TXT "e24cd03623a977eafca668f1b5f825"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at api share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - api.vexy.art. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - api.vexy.art. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.art. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.art. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.art.
  Suggested: _dmarc.vexy.art. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.art"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.art.
  Suggested: vexy.art. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.cc
========================================
errors=2 warnings=1 info=1 fixable=3 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.cc. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.cc. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.cc. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.cc. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.cc. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.cc. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.cc.
  Suggested: _dmarc.vexy.cc. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.cc"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.cc.
  Suggested: vexy.cc. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.co
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.co. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.co. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.co. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.co. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '2f7c303313af42800372f42008a2968309ffa4ff26a675805982127cc408ec0e_1777984333610'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.co. 3600 IN TXT "2f7c303313af42800372f42008a2968309ffa4ff26a675805982127cc408ec0e_1777984333610"
    - _dep_ws_mutex.vexy.co. 3600 IN TXT "\"2f7c303313af42800372f42008a2968309ffa4ff26a675805982127cc408ec0e_1777984333610\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.co. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.co. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.co.
  Suggested: _dmarc.vexy.co. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.co"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.co.
  Suggested: vexy.co. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.design
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.design. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.design. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.design. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.design. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '89ec1107fa72c276f9ecd9cc83258bb51c0a2293b227d0a9aa5226d7b4b3498d_1777984233599'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.design. 3600 IN TXT "89ec1107fa72c276f9ecd9cc83258bb51c0a2293b227d0a9aa5226d7b4b3498d_1777984233599"
    - _dep_ws_mutex.vexy.design. 3600 IN TXT "\"89ec1107fa72c276f9ecd9cc83258bb51c0a2293b227d0a9aa5226d7b4b3498d_1777984233599\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.design. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.design. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.design.
  Suggested: _dmarc.vexy.design. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.design"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.design.
  Suggested: vexy.design. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.dev
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.dev. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.dev. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.dev. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.dev. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '526c70e837bec647476e8b0e3b82031cfec15cef18d6d9baa7a9b9892c8d927b_1777983948573'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.dev. 3600 IN TXT "526c70e837bec647476e8b0e3b82031cfec15cef18d6d9baa7a9b9892c8d927b_1777983948573"
    - _dep_ws_mutex.vexy.dev. 3600 IN TXT "\"526c70e837bec647476e8b0e3b82031cfec15cef18d6d9baa7a9b9892c8d927b_1777983948573\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.dev. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.dev. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.dev.
  Suggested: _dmarc.vexy.dev. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.dev"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.dev.
  Suggested: vexy.dev. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexygram.com
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexygram.com. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexygram.com. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexygram.com. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexygram.com. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '014c4edacd683282055a92b3edcfa42959dd433c559b3b2c9754671828b452ee_1777928968104'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexygram.com. 3600 IN TXT "014c4edacd683282055a92b3edcfa42959dd433c559b3b2c9754671828b452ee_1777928968104"
    - _dep_ws_mutex.vexygram.com. 3600 IN TXT "\"014c4edacd683282055a92b3edcfa42959dd433c559b3b2c9754671828b452ee_1777928968104\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexygram.com. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexygram.com. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexygram.com.
  Suggested: _dmarc.vexygram.com. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexygram.com"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexygram.com.
  Suggested: vexygram.com. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.ltd
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.ltd. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.ltd. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.ltd. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.ltd. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '9b26b7fe7adc0f8ee64fe0c3bcb4512138db19ab81a33f711b80c484dd8a41bc_1777983591247'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.ltd. 3600 IN TXT "9b26b7fe7adc0f8ee64fe0c3bcb4512138db19ab81a33f711b80c484dd8a41bc_1777983591247"
    - _dep_ws_mutex.vexy.ltd. 3600 IN TXT "\"9b26b7fe7adc0f8ee64fe0c3bcb4512138db19ab81a33f711b80c484dd8a41bc_1777983591247\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.ltd. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.ltd. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.ltd.
  Suggested: _dmarc.vexy.ltd. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.ltd"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.ltd.
  Suggested: vexy.ltd. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.me
========================================
errors=6 warnings=0 info=1 fixable=6 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.me. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.me. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.me. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.me. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: 'a92ffe8f311e2a75ed26c3a4df70214a5c3eae19f159146d5705f61979c2dffc_1777983561028'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.me. 3600 IN TXT "\"a92ffe8f311e2a75ed26c3a4df70214a5c3eae19f159146d5705f61979c2dffc_1777983561028\""
    - _dep_ws_mutex.vexy.me. 3600 IN TXT "a92ffe8f311e2a75ed26c3a4df70214a5c3eae19f159146d5705f61979c2dffc_1777983561028"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dmarc share the same payload after unquoting (fixable)
  Semantic payload: 'v=DMARC1; p=none;'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dmarc.vexy.me. 300 IN TXT "\"v=DMARC1; p=none;\""
    - _dmarc.vexy.me. 300 IN TXT "v=DMARC1; p=none;"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _github-pages-challenge-fontlab share the same payload after unquoting (fixable)
  Semantic payload: '3fa6f6016332df6cefc284ca8c4d50'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _github-pages-challenge-fontlab.vexy.me. 3600 IN TXT "3fa6f6016332df6cefc284ca8c4d50"
    - _github-pages-challenge-fontlab.vexy.me. 3600 IN TXT "\"3fa6f6016332df6cefc284ca8c4d50\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'mailerlite-domain-verification=253ba082283a562929002bdb8812bfc5577d3efb'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.me. 300 IN TXT "\"mailerlite-domain-verification=253ba082283a562929002bdb8812bfc5577d3efb\""
    - vexy.me. 300 IN TXT "mailerlite-domain-verification=253ba082283a562929002bdb8812bfc5577d3efb"

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 a mx include:_spf.mlsend.com include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.me. 300 IN TXT "\"v=spf1 a mx include:_spf.mlsend.com include:_spf-us.ionos.com ~all\""
    - vexy.me. 300 IN TXT "v=spf1 a mx include:_spf.mlsend.com include:_spf-us.ionos.com ~all"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.me.
  Suggested: vexy.me. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.studio
========================================
errors=3 warnings=1 info=1 fixable=4 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.studio. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.studio. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.studio. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.studio. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at _dep_ws_mutex share the same payload after unquoting (fixable)
  Semantic payload: '33888beff59730352e6f60a7af3029937438eb8a293637e5d315af971df6773f_1777983491680'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - _dep_ws_mutex.vexy.studio. 3600 IN TXT "33888beff59730352e6f60a7af3029937438eb8a293637e5d315af971df6773f_1777983491680"
    - _dep_ws_mutex.vexy.studio. 3600 IN TXT "\"33888beff59730352e6f60a7af3029937438eb8a293637e5d315af971df6773f_1777983491680\""

[ERROR] TXT_SEMANTIC_DUPLICATE: 2 TXT records at @ share the same payload after unquoting (fixable)
  Semantic payload: 'v=spf1 include:_spf-us.ionos.com ~all'. Duplicate TXT entries typically come from import/export quoting mismatches (literal escaped quotes vs. canonical form). Keeping only the canonical record removes ambiguity.
    - vexy.studio. 3600 IN TXT "\"v=spf1 include:_spf-us.ionos.com ~all\""
    - vexy.studio. 3600 IN TXT "v=spf1 include:_spf-us.ionos.com ~all"

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.studio.
  Suggested: _dmarc.vexy.studio. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.studio"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.studio.
  Suggested: vexy.studio. 3600 IN CAA 0 issue "letsencrypt.org"

DNS Doctor Report: cloudflare/vexy.tv
========================================
errors=1 warnings=1 info=1 fixable=2 fixed=0

[ERROR] NS_MIGRATION_ARTIFACT: 4 apex NS record(s) point to a different provider than 'cloudflare' (fixable)
  These NS records likely remain from a previous provider after a zone copy. Resolvers ignore apex NS in some providers but they can also confuse delegation checks and downstream tooling. Removing them is safe when the registrar's delegation already points at the current provider.
    - vexy.tv. 86400 IN NS ns1045.ui-dns.biz. (owned by ionos)
    - vexy.tv. 86400 IN NS ns1045.ui-dns.com. (owned by ionos)
    - vexy.tv. 86400 IN NS ns1045.ui-dns.de. (owned by ionos)
    - vexy.tv. 86400 IN NS ns1045.ui-dns.org. (owned by ionos)

[WARNING] DMARC_MISSING: No DMARC record at _dmarc despite MX records being present (fixable)
  DMARC tells receivers what to do with messages that fail SPF/DKIM. Starting with a monitoring-only policy (p=none) is safe and produces actionable reports.
    - _dmarc.vexy.tv.
  Suggested: _dmarc.vexy.tv. 3600 IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@vexy.tv"

[INFO] CAA_MISSING: No CAA records at the zone apex
  CAA records restrict which Certificate Authorities may issue certificates for the domain, mitigating mis-issuance attacks.
    - vexy.tv.
  Suggested: vexy.tv. 3600 IN CAA 0 issue "letsencrypt.org"
</REPORT>

# Fix 1

FIX: the failures shown above. 

# Fix 2 

FIX: The `doctor --fix` command should accept `--dmarc_email support@fontlab.com` or something like that, and then it should include that email address in `rua=mailto:`

Since we choose an email address outside of your domain, there is an extra step you must take.

By default, receiving mail servers will only send DMARC reports to an email address that matches the domain publishing the DMARC record. If you want to route those reports to an external domain (e.g., sending `yourdomain.com`'s reports to an IT service at `dmarc-service.com`), the receiving domain must explicitly grant permission.

This process is known as **External Domain Verification** (or External Destination Routing).

### Why is this permission required?

It is a security mechanism. Without it, a malicious actor could publish a DMARC record on a highly trafficked spam domain and set the `rua` address to an unsuspecting victim's email. The victim's inbox would instantly be bombarded (DDoS'd) with millions of XML reports from servers all over the world.

### How to authorize an external domain

If you want to send reports from `yourdomain.com` to `reports@dmarc-service.com`, the owner of `dmarc-service.com` must publish a specific TXT record in their DNS to prove they are willing to accept those reports.

**The DNS Record (published on the receiving domain):**

* **Host/Name:** `yourdomain.com._report._dmarc.dmarc-service.com`
* **Type:** `TXT`
* **Value:** `v=DMARC1;`

> **How to read this format:** `[SendingDomain]._report._dmarc.[ReceivingDomain]`

### What happens if you skip this step?

If you put an external email address in your `rua` tag and that receiving domain has not set up the required authorization record, mail servers like Gmail, Yahoo, and Outlook will simply **drop the reports**. You will not receive any data.

