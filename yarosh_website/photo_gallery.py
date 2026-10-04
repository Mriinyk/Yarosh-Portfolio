import logging
import re
from html.parser import HTMLParser

import requests
from django.core.cache import cache


logger = logging.getLogger(__name__)


class PhotoGalleryError(Exception):
    pass


class _DriveImageParser(HTMLParser):
    image_extension = re.compile(
        r"\.(?:jpe?g|png|webp|gif|bmp|avif|heic|heif|tiff?)(?=[\"'\s]|$)",
        flags=re.IGNORECASE,
    )

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.file_ids = []
        self._row = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag.lower() == "tr" and "data-selectable" in attributes:
            self._row = {"ids": [], "root_ids": [], "labels": []}

        image_id = attributes.get("data-id")
        labels = [
            attributes.get(name, "")
            for name in ("data-tooltip", "aria-label", "title")
        ]
        labels.extend(
            value
            for name, value in attrs
            if name in {"data-mime-type", "data-mime"}
        )

        if self._row is not None:
            if image_id:
                key = "root_ids" if tag.lower() == "tr" else "ids"
                self._row[key].append(image_id)
            self._row["labels"].extend(labels)
        elif image_id and self._is_image(labels):
            self.file_ids.append(image_id)

    def handle_endtag(self, tag):
        if tag.lower() != "tr" or self._row is None:
            return
        if self._is_image(self._row["labels"]):
            self.file_ids.extend(self._row["root_ids"] or self._row["ids"])
        self._row = None

    @classmethod
    def _is_image(cls, labels):
        return any(
            "image/" in label.lower() or cls.image_extension.search(label.strip())
            for label in labels
        )


def get_photo_session_images(photo_session):
    folder_id = photo_session.get_drive_folder_id()
    if not folder_id:
        raise PhotoGalleryError("Посилання на папку Google Drive некоректне.")

    cache_key = f"photo-session-gallery:{folder_id}"
    file_ids = cache.get(cache_key)
    if file_ids is None:
        try:
            response = requests.get(
                f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing",
                timeout=10,
                headers={
                    "Accept": "text/html",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
            )
            response.raise_for_status()
        except requests.RequestException as error:
            logger.exception(
                "Could not load Google Drive folder for photo session %s.",
                photo_session.pk,
            )
            raise PhotoGalleryError(
                "Не вдалося завантажити галерею. Перевірте доступ до папки."
            ) from error

        file_ids = _extract_image_file_ids(response.text)
        if file_ids:
            cache.set(cache_key, file_ids, 60 * 60)
        else:
            logger.warning(
                "No image files were found in Google Drive folder for photo session %s.",
                photo_session.pk,
            )

    if not file_ids:
        raise PhotoGalleryError(
            "У папці немає доступних фото або вона закрита для перегляду."
        )

    cover_url = photo_session.direct_cover_url
    cover_match = re.search(r"(?:/d/|[?&]id=)([A-Za-z0-9_-]+)", photo_session.cover_url)
    cover_id = cover_match.group(1) if cover_match else None
    images = [cover_url]
    images.extend(
        f"https://lh3.googleusercontent.com/d/{file_id}"
        for file_id in file_ids
        if file_id != cover_id
    )
    return images


def _extract_image_file_ids(folder_html):
    parser = _DriveImageParser()
    parser.feed(folder_html)
    return list(dict.fromkeys(
        file_id
        for file_id in parser.file_ids
        if re.fullmatch(r"[A-Za-z0-9_-]+", file_id)
    ))
