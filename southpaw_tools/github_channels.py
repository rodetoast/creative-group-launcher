"""Fixed distribution repository identities; owner migration grants no new trust keys."""

# IDs were recorded from the authenticated pre-transfer inventory. Do not discover
# replacements from redirects or configuration: a recreated old name is not this repo.
_CHANNEL_IDS = {
    "creative-group-releases": 1447701732,
    "creative-group-trial-releases": 1452413703,
}
CANONICAL_REPOSITORY = "rodetoast/creative-group-releases"
CANONICAL_REPOSITORY_ID = 1462539740
CANONICAL_CATALOG_ID = "creative-group-launcher-rodetoast-1462539740"


def canonical_channel(channel):
    return (channel.get("repository") == CANONICAL_REPOSITORY
            and type(channel.get("repository_id")) is int
            and channel["repository_id"] == CANONICAL_REPOSITORY_ID)


_OWNERS = ("toast-source", "rodetoast")


def repository_aliases(repository: str, repository_id=None) -> tuple[str, ...]:
    if repository_id is not None:
        if not canonical_channel({"repository": repository, "repository_id": repository_id}):
            from .common import LauncherError
            raise LauncherError("신규 채널의 정확한 저장소 ID가 필요합니다.")
        return (repository,)
    owner, _, name = repository.partition("/")
    if owner in _OWNERS and name in _CHANNEL_IDS:
        return tuple(f"{owner}/{name}" for owner in _OWNERS)
    return (repository,)


def managed_repository(repository: str, repository_id=None) -> bool:
    if repository_id is not None:
        return canonical_channel({"repository": repository, "repository_id": repository_id})
    return len(repository_aliases(repository)) == 2


def latest_api_url(repository: str, repository_id=None) -> str:
    if repository_id is not None:
        repository_aliases(repository, repository_id)
        return f"https://api.github.com/repositories/{repository_id}/releases/latest"
    if managed_repository(repository):
        identity = _CHANNEL_IDS[repository.split("/")[1]]
        return f"https://api.github.com/repositories/{identity}/releases/latest"
    return f"https://api.github.com/repos/{repository}/releases/latest"
