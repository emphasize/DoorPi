"""Actions related to taking snapshots: snap_url, snap_picam"""
# pylint: disable=import-outside-toplevel

import datetime
import logging
import pathlib

import doorpi
from . import action

LOGGER = logging.getLogger(__name__)
DOORPI_SECTION = "DoorPi"


class SnapshotAction:
    """Base class for snapshotting actions."""

    @classmethod
    def cleanup(cls):
        """Cleans out the snapshot directory

        The oldest snapshots are deleted until the directory only
        contains as many snapshots as set in the configuration.
        """

        keep = doorpi.INSTANCE.config.get_int(DOORPI_SECTION, "snapshot_keep")
        if keep <= 0: return
        files = cls.list_all()
        for fi in files[0:-keep]:
            try:
                LOGGER.info("Deleting old snapshot %s", fi)
                fi.unlink()
            except OSError:
                LOGGER.exception("Could not clean up snapshot %s", fi.name)

    @staticmethod
    def get_base_path():
        """Fetches the snapshot directory path from the configuration."""

        path = doorpi.INSTANCE.config.get_string_parsed(DOORPI_SECTION, "snapshot_path")
        if not path: raise ValueError("snapshot_path must not be empty")
        path = pathlib.Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_next_path(cls):
        """Computes the next snapshot's path."""

        path = cls.get_base_path() / datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.jpg")
        doorpi.INSTANCE.config.set_value(DOORPI_SECTION, "last_snapshot", str(path))
        return path

    @classmethod
    def list_all(cls):
        """Lists all snapshot files in the snapshot directory."""
        return sorted(f for f in cls.get_base_path().iterdir() if f.is_file())


@action("snap_url")
class URLSnapshotAction(SnapshotAction):
    """Fetches a URL and saves it as snapshot."""

    def __init__(self, url):
        self.__url = url

    def __call__(self, event_id, extra):
        import requests

        response = requests.get(self.__url, stream=True)
        with self.get_next_path().open("wb") as output:
            for chunk in response.iter_content(1048576):  # 1 MiB chunks
                output.write(chunk)

        self.cleanup()

    def __str__(self):
        return f"Save the image from {self.__url} as snapshot"

    def __repr__(self):
        return f"snap_url:{self.__url}"


@action("snap_picam")
class PicamSnapshotAction(SnapshotAction):
    """Takes a snapshot from the Pi Camera."""

    def __init__(self):
        # Make sure picamera is importable
        import picamera  # pylint: disable=import-error, unused-import

    def __call__(self, event_id, extra):
        import picamera  # pylint: disable=import-error

        with picamera.PiCamera() as cam:
            cam.resolution = (1024, 768)
            cam.capture(self.get_next_path())

        self.cleanup()

    def __str__(self):
        return f"Take a snapshot from the Pi Camera"

    def __repr__(self):
        return f"snap_picam:"
