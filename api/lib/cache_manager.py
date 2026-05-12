"""
Cache Manager - Centralized cache invalidation
===============================================
Helper class để quản lý cache invalidation across the application
"""

from typing import List
from api.lib.supabase import _profile_cache, _allowed_sources_cache


class CacheManager:
    """Centralized cache invalidation manager"""
    
    @staticmethod
    def invalidate_user_profile(user_id: str) -> bool:
        """
        Invalidate user profile cache
        
        Args:
            user_id: User ID to invalidate
            
        Returns:
            True if cache was invalidated
        """
        key = f"profile:{user_id}"
        return _profile_cache.invalidate(key)
    
    @staticmethod
    def invalidate_allowed_sources(user_id: str) -> bool:
        """
        Invalidate allowed sources cache for a user
        
        Args:
            user_id: User ID to invalidate
            
        Returns:
            True if cache was invalidated
        """
        key = f"allowed:{user_id}"
        return _allowed_sources_cache.invalidate(key)
    
    @staticmethod
    def invalidate_class_members(class_id: str, member_ids: List[str]) -> int:
        """
        Invalidate cache for all class members
        
        Args:
            class_id: Class ID
            member_ids: List of member user IDs
            
        Returns:
            Number of caches invalidated
        """
        count = 0
        for member_id in member_ids:
            if CacheManager.invalidate_allowed_sources(member_id):
                count += 1
        return count
    
    @staticmethod
    def invalidate_all_user_caches(user_id: str) -> dict:
        """
        Invalidate all caches related to a user
        
        Args:
            user_id: User ID to invalidate
            
        Returns:
            Dict with invalidation results
        """
        return {
            "profile": CacheManager.invalidate_user_profile(user_id),
            "allowed_sources": CacheManager.invalidate_allowed_sources(user_id)
        }
    
    @staticmethod
    def get_cache_stats() -> dict:
        """
        Get statistics for all caches
        
        Returns:
            Dict with cache statistics
        """
        return {
            "profile_cache": _profile_cache.stats(),
            "allowed_sources_cache": _allowed_sources_cache.stats()
        }
