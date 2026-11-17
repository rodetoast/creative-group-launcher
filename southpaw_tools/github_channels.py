"""Fixed distribution repository identities; owner migration grants no new trust keys."""

# IDs were recorded from the authenticated pre-transfer inventory. Do not discover
# replacements from redirects or configuration: a recreated old name is not this repo.
_CHANNEL_IDS = {
    "creative-group-releases": 1447701732,
    "creative-group-trial-releases": 1452413703,
}
_OWNERS = ("toast-source", "rodetoast")


def repository_aliases(repository: str) -> tuple[str, ...]:
    owner, _, name = repository.partition("/")
    if owner in _OWNERS and name in _CHANNEL_IDS:
        return tuple(f"{owner}/{name}" for owner in _OWNERS)
    return (repository,)


def managed_repository(repository: str) -> bool:
    return len(repository_aliases(repository)) == 2


def latest_api_url(repository: str) -> str:
    if managed_repository(repository):
        identity = _CHANNEL_IDS[repository.split("/")[1]]
        return f"https://api.github.com/repositories/{identity}/releases/latest"
    return f"https://api.github.com/repos/{repository}/releases/latest"
