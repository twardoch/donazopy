I want to add `donazopy doctor` that takes a domain spec and identifies problems, and if `--fix` is given, fixes them.  

I already have two problems: 

1. Because I copied the DNS zone from Ionos to Cloudflare, in the Cloudflare zone I had "NS" records pointing to the Ionos nameservers, which was very odd. I don’t think we ever want that? 

2. Because of different quotation methods, I have duplicate entries such as one `TXT` with content `"v=spf1 include:_spf-us.ionos.com ~all"` and another for the same server with content `"\"v=spf1 include:_spf-us.ionos.com ~all\""`. 

I want these types of tests, especially some that don’t require validation. Also commonly needed but missing records (e.g. for email security) should be reported. If --fix is given, the tool should attempt to fix it using its own capabilities, but if not possible, should print detailed instructions what the user may need to do. 

Read the following reports and suggestions: 

- [ ] issues/doctor/01-grok.md
- [ ] issues/doctor/02-gemi.md
- [ ] issues/doctor/03-qwen.md
- [ ] issues/doctor/04-cla.md
- [ ] issues/doctor/05-ds.md
- [ ] issues/doctor/06-gpt.md

Then organize the plan into a `- [ ]`-prefixed tasklist into @TODO.md (at its start). Adjust the other tasks accordingly. 

Then start implementing all tasks. 

