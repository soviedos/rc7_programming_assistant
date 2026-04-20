from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import MinioException

from src.core.config import settings


class ManualStorageError(RuntimeError):
    pass


class ManualStorageService:
    def __init__(self, client: Minio | None = None, bucket_name: str | None = None):
        self.bucket_name = bucket_name or settings.minio_bucket_manuals
        self.client = client or self._build_client()

    def _build_client(self) -> Minio:
        parsed_endpoint = urlparse(settings.minio_endpoint)
        endpoint = parsed_endpoint.netloc or parsed_endpoint.path
        secure = parsed_endpoint.scheme == "https"

        return Minio(
            endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=secure,
        )

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except MinioException as exc:
            raise ManualStorageError(
                "No fue posible validar el bucket de manuales en MinIO."
            ) from exc

    def upload_manual(
        self, content: bytes, storage_key: str, content_type: str
    ) -> None:
        self.ensure_bucket()

        try:
            self.client.put_object(
                self.bucket_name,
                storage_key,
                BytesIO(content),
                length=len(content),
                content_type=content_type,
            )
        except MinioException as exc:
            raise ManualStorageError(
                "No fue posible almacenar el manual en MinIO."
            ) from exc

    def download_manual(self, storage_key: str) -> bytes:
        self.ensure_bucket()

        try:
            response = self.client.get_object(self.bucket_name, storage_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except MinioException as exc:
            raise ManualStorageError(
                "No fue posible descargar el manual desde MinIO."
            ) from exc

    def delete_manual(self, storage_key: str) -> None:
        self.ensure_bucket()

        try:
            self.client.remove_object(self.bucket_name, storage_key)
        except MinioException as exc:
            raise ManualStorageError(
                "No fue posible eliminar el manual en MinIO."
            ) from exc


def get_manual_storage_service() -> ManualStorageService:
    return ManualStorageService()
