
# donazopy 

## Idea 

Python CLI tool for managing DNS stuff.

- Use Fire CLI
- Add ./build.sh that does `uvx hatch clean` then `uvx hatch build`
- Add ./publish.sh that does `uvx hatch clean`, `uvx gitnextver`, `uvx hatch build` and then `uv publish`
- Add __version__.py and _version.py and .DS_Store and other relevant stuff to .gitignore
- Must use hatch-vcs for git-tag-based semver 

## Prep

- Analyze ./private/research/ 
- Into ./private/ gather (download, clone etc.) materials, Python repos, documentation, API docs etc. from all the relevant parties. I’m interested in Cloudflare, Vercel, AWS, Azure, Google Cloud, Ionos, Joker, GoDaddy, Namecheap, Hosting.com, Hostinger, Bluehost, and some 5-10 most relevant providers. 
- Into ./spec/00-toc.md write a ToC of a 12-chapter spec of the project. Write a TLDR of each chapter there as well. 
- Into ./spec/01.md .. 12.md write the entire spec. 
- Into ./TODO.md write an actionable tasklist for the implementation based on the spec. 
- Remember: each provider needs to be in a separate module 

## Planned functionality

- parse and edit DNS zone files
- interact with domain registry services & APIS
- interact with DNS services & APIs of the providers 
- assign/reassign the nameservers for a given domain
- dump DNS configs for a domain to a zone file
- update DNS configs from a zone file
- perform other DNS-related editing

