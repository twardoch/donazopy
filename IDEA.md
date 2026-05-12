
# donazopy 

Python CLI tool for managing DNS stuff.

- Use Fire CLI
- Add ./build.sh that does `uvx hatch clean` then `uvx hatch build`
- Add ./publish.sh that does `uvx hatch clean`, `uvx gitnextver`, `uvx hatch build` and then `uv publish`
- Add __version__.py and _version.py and .DS_Store and other relevant stuff to .gitignore
- Must use hatch-vcs for git-tag-based semver 

- 