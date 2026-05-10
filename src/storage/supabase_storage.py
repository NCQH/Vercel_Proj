"""Supabase Storage client for file upload/download operations."""

import os
import logging
from typing import BinaryIO
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)


class SupabaseStorageClient:
    """Client for interacting with Supabase Storage API."""
    
    def __init__(self, supabase_url: str, service_role_key: str):
        """
        Initialize Supabase Storage client.
        
        Args:
            supabase_url: Base URL of Supabase project
            service_role_key: Service role key for authentication
        """
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.storage_url = f"{self.supabase_url}/storage/v1"
        
    def _get_headers(self, content_type: str = "application/octet-stream") -> dict:
        """Get headers for Supabase Storage API requests."""
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": content_type,
        }
    
    def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> dict:
        """
        Upload a file to Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket (e.g., "user_123/file.pdf")
            file_data: Binary file content
            content_type: MIME type of the file
            upsert: If True, overwrite existing file
            
        Returns:
            dict: Response from Supabase Storage API
            
        Raises:
            Exception: If upload fails
        """
        url = f"{self.storage_url}/object/{bucket}/{path}"
        headers = self._get_headers(content_type)
        
        # Remove Content-Type from headers, let httpx handle it
        headers.pop("Content-Type", None)
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                headers=headers,
                content=file_data,
                params={"upsert": "true" if upsert else "false"},
            )
        
        if response.status_code >= 300:
            logger.error(f"Upload failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to upload file: {response.text}")
        
        return response.json()
    
    def download_file(self, bucket: str, path: str) -> bytes:
        """
        Download a file from Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            
        Returns:
            bytes: File content
            
        Raises:
            Exception: If download fails
        """
        url = f"{self.storage_url}/object/{bucket}/{path}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url, headers=headers)
        
        if response.status_code >= 300:
            logger.error(f"Download failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to download file: {response.text}")
        
        return response.content
    
    def delete_file(self, bucket: str, path: str) -> dict:
        """
        Delete a file from Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            
        Returns:
            dict: Response from Supabase Storage API
            
        Raises:
            Exception: If deletion fails
        """
        url = f"{self.storage_url}/object/{bucket}/{path}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.delete(url, headers=headers)
        
        if response.status_code >= 300:
            logger.error(f"Delete failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to delete file: {response.text}")
        
        return response.json() if response.text else {}
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """
        Get public URL for a file (if bucket is public).
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            
        Returns:
            str: Public URL
        """
        return f"{self.storage_url}/object/public/{bucket}/{path}"
    
    def create_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> dict:
        """
        Create a signed URL for temporary access to a private file.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            dict: Response containing signed URL
            
        Raises:
            Exception: If creation fails
        """
        url = f"{self.storage_url}/object/sign/{bucket}/{path}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        payload = {"expiresIn": expires_in}
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
        
        if response.status_code >= 300:
            logger.error(f"Signed URL creation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create signed URL: {response.text}")
        
        return response.json()
    
    def list_files(self, bucket: str, path: str = "", limit: int = 100) -> list:
        """
        List files in a bucket path.
        
        Args:
            bucket: Storage bucket name
            path: Directory path within bucket (optional)
            limit: Maximum number of files to return
            
        Returns:
            list: List of file objects
            
        Raises:
            Exception: If listing fails
        """
        url = f"{self.storage_url}/object/list/{bucket}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prefix": path,
            "limit": limit,
            "offset": 0,
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
        
        if response.status_code >= 300:
            logger.error(f"List files failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to list files: {response.text}")
        
        return response.json()
