import grp
import logging
import os
import pwd


logger = logging.getLogger(__name__)


def _resolve_uid(user):
    if user in (None, '', False):
        return -1
    if isinstance(user, int):
        return user
    return pwd.getpwnam(user).pw_uid


def _resolve_gid(group):
    if group in (None, '', False):
        return -1
    if isinstance(group, int):
        return group
    return grp.getgrnam(group).gr_gid


def safe_set_file_metadata(path, mode=None, user=None, group=None):
    if mode is not None:
        try:
            os.chmod(path, mode)
        except OSError as exc:
            logger.warning("Unable to chmod %s to %s: %s", path, oct(mode), exc)

    if user in (None, '', False) and group in (None, '', False):
        return

    try:
        uid = _resolve_uid(user)
        gid = _resolve_gid(group)
    except KeyError as exc:
        logger.warning("Skipping ownership update for %s: %s", path, exc)
        return

    try:
        os.chown(path, uid, gid)
    except PermissionError as exc:
        logger.warning("Unable to chown %s: %s", path, exc)
    except OSError as exc:
        logger.warning("Unable to update ownership for %s: %s", path, exc)


def resolve_runtime_artifact(path, base_dir):
    if not path:
        return path
    if os.path.exists(path):
        return path
    candidate = os.path.join(base_dir, os.path.basename(path))
    if os.path.exists(candidate):
        return candidate
    return path
