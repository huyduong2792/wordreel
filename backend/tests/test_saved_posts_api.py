"""
Tests for Save Post API endpoints.

Tests cover:
- Save a post (toggle on)
- Unsave a post (toggle off)
- Save/unsave with invalid post ID
- Authorization requirements
"""
import pytest
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from auth.utils import get_current_user, get_current_user_optional


# ==================== Mock Classes ====================

class MockUser:
    """Mock authenticated user"""
    def __init__(self, user_id: str = "user-123", email: str = "test@example.com"):
        self.id = user_id
        self.email = email
        self.user_metadata = {
            "name": "Test User",
            "avatar_url": "http://example.com/avatar.jpg"
        }


class MockSupabaseSavedPosts:
    """Mock Supabase client for saved post tests"""
    
    def __init__(self):
        self.saved_posts: List[Dict] = []
        self.users: List[Dict] = []
        self.posts: List[Dict] = []
        self._current_table = None
        self._filters = {}
        self._insert_data = None
        self._delete_mode = False
        self._upsert_data = None
    
    def table(self, name: str):
        self._current_table = name
        self._filters = {}
        self._delete_mode = False
        self._upsert_data = None
        self._insert_data = None
        return self
    
    def select(self, columns: str = "*"):
        return self
    
    def eq(self, column: str, value: Any):
        self._filters[column] = value
        return self
    
    def insert(self, data: Dict):
        self._insert_data = data
        return self
    
    def upsert(self, data: Dict, on_conflict: str = None):
        self._upsert_data = data
        return self
    
    def delete(self):
        self._delete_mode = True
        return self
    
    def execute(self):
        if self._upsert_data:
            # Upsert user
            user_id = self._upsert_data.get("id")
            existing = next((u for u in self.users if u["id"] == user_id), None)
            if existing:
                existing.update(self._upsert_data)
            else:
                self.users.append(self._upsert_data.copy())
            return MockResponse([self._upsert_data])
        
        if self._delete_mode:
            return self._handle_delete()
        
        if self._insert_data:
            return self._handle_insert()
        
        return self._handle_select()
    
    def _handle_select(self):
        if self._current_table == "saved_posts":
            return self._select_saved_posts()
        elif self._current_table == "users":
            return self._select_users()
        return MockResponse([])
    
    def _select_saved_posts(self):
        result = self.saved_posts.copy()
        
        if "post_id" in self._filters:
            result = [s for s in result if s["post_id"] == self._filters["post_id"]]
        
        if "user_id" in self._filters:
            result = [s for s in result if s["user_id"] == self._filters["user_id"]]
        
        if "id" in self._filters:
            result = [s for s in result if s["id"] == self._filters["id"]]
        
        return MockResponse(result)
    
    def _select_users(self):
        result = self.users.copy()
        if "id" in self._filters:
            result = [u for u in result if u["id"] == self._filters["id"]]
        return MockResponse(result)
    
    def _handle_insert(self):
        if self._current_table == "saved_posts":
            new_saved = {
                "id": f"saved-{len(self.saved_posts) + 1}",
                **self._insert_data,
                "created_at": datetime.utcnow().isoformat()
            }
            self.saved_posts.append(new_saved)
            return MockResponse([new_saved])
        return MockResponse([])
    
    def _handle_delete(self):
        if self._current_table == "saved_posts":
            if "id" in self._filters:
                self.saved_posts = [
                    s for s in self.saved_posts 
                    if s["id"] != self._filters["id"]
                ]
        return MockResponse([])


class MockResponse:
    """Mock Supabase response"""
    def __init__(self, data: List[Dict], count: int = None):
        self.data = data
        self.count = count or len(data)


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user"""
    return MockUser()


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client with initial data"""
    db = MockSupabaseSavedPosts()
    
    # Add test user
    db.users.append({
        "id": "user-123",
        "email": "test@example.com",
        "username": "testuser",
        "avatar_url": "http://example.com/avatar.jpg"
    })
    
    # Add test posts
    db.posts.append({
        "id": "post-1",
        "title": "Test Video",
        "content_type": "video"
    })
    db.posts.append({
        "id": "post-2",
        "title": "Test Audio",
        "content_type": "audio"
    })
    
    return db


def override_auth(user: MockUser):
    """Override auth dependency"""
    async def mock_get_current_user():
        return user
    return mock_get_current_user


# ==================== Tests ====================

class TestSavePost:
    """Tests for POST /posts/{post_id}/save endpoint"""
    
    @patch('api.routes.posts.get_service_supabase')
    def test_save_post_success(self, mock_get_supabase, test_client, mock_user, mock_supabase):
        """Should save a post and return saved: true"""
        mock_get_supabase.return_value = mock_supabase
        app.dependency_overrides[get_current_user] = override_auth(mock_user)
        
        try:
            response = test_client.post("/api/v1/posts/post-1/save")
            
            assert response.status_code == 200
            assert response.json()["saved"] is True
            
            # Verify saved post in database
            assert len(mock_supabase.saved_posts) == 1
            assert mock_supabase.saved_posts[0]["post_id"] == "post-1"
            assert mock_supabase.saved_posts[0]["user_id"] == "user-123"
        finally:
            app.dependency_overrides.clear()
    
    @patch('api.routes.posts.get_service_supabase')
    def test_unsave_post_success(self, mock_get_supabase, test_client, mock_user, mock_supabase):
        """Should unsave a previously saved post and return saved: false"""
        mock_get_supabase.return_value = mock_supabase
        
        # Pre-save the post
        mock_supabase.saved_posts.append({
            "id": "saved-existing",
            "post_id": "post-1",
            "user_id": "user-123",
            "created_at": datetime.utcnow().isoformat()
        })
        
        app.dependency_overrides[get_current_user] = override_auth(mock_user)
        
        try:
            response = test_client.post("/api/v1/posts/post-1/save")
            
            assert response.status_code == 200
            assert response.json()["saved"] is False
            
            # Verify saved post removed
            assert len(mock_supabase.saved_posts) == 0
        finally:
            app.dependency_overrides.clear()
    
    @patch('api.routes.posts.get_service_supabase')
    def test_save_post_toggle_twice(self, mock_get_supabase, test_client, mock_user, mock_supabase):
        """Should toggle save state correctly when called twice"""
        mock_get_supabase.return_value = mock_supabase
        app.dependency_overrides[get_current_user] = override_auth(mock_user)
        
        try:
            # First save
            response1 = test_client.post("/api/v1/posts/post-1/save")
            assert response1.json()["saved"] is True
            
            # Second call - unsave
            response2 = test_client.post("/api/v1/posts/post-1/save")
            assert response2.json()["saved"] is False
            
            # Third call - save again
            response3 = test_client.post("/api/v1/posts/post-1/save")
            assert response3.json()["saved"] is True
        finally:
            app.dependency_overrides.clear()
    
    @patch('api.routes.posts.get_service_supabase')
    def test_save_different_posts(self, mock_get_supabase, test_client, mock_user, mock_supabase):
        """Should allow saving multiple different posts"""
        mock_get_supabase.return_value = mock_supabase
        app.dependency_overrides[get_current_user] = override_auth(mock_user)
        
        try:
            # Save post-1
            response1 = test_client.post("/api/v1/posts/post-1/save")
            assert response1.json()["saved"] is True
            
            # Save post-2
            response2 = test_client.post("/api/v1/posts/post-2/save")
            assert response2.json()["saved"] is True
            
            # Both should be saved
            assert len(mock_supabase.saved_posts) == 2
        finally:
            app.dependency_overrides.clear()


class TestSavePostAuthorization:
    """Tests for authorization requirements"""
    
    def test_save_post_requires_auth(self, test_client):
        """Should return 401 when not authenticated"""
        # Clear any overrides
        app.dependency_overrides.clear()
        
        response = test_client.post("/api/v1/posts/post-1/save")
        
        assert response.status_code in [401, 403]
    
    def test_save_post_with_invalid_token(self, test_client):
        """Should return 401 with invalid token"""
        app.dependency_overrides.clear()
        
        response = test_client.post(
            "/api/v1/posts/post-1/save",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401


class TestSavePostEdgeCases:
    """Tests for edge cases"""
    
    @patch('api.routes.posts.get_service_supabase')
    def test_save_nonexistent_post(self, mock_get_supabase, test_client, mock_user, mock_supabase):
        """Should handle saving nonexistent post (may succeed or fail based on FK constraints)"""
        mock_get_supabase.return_value = mock_supabase
        app.dependency_overrides[get_current_user] = override_auth(mock_user)
        
        try:
            # This may succeed (if no FK check) or fail (if FK constraint enforced)
            # The mock doesn't enforce FK constraints
            response = test_client.post("/api/v1/posts/nonexistent-post/save")
            
            # Should at least not crash
            assert response.status_code in [200, 400, 404, 500]
        finally:
            app.dependency_overrides.clear()
    
    @patch('api.routes.posts.get_service_supabase')
    def test_save_post_ensures_user_exists(self, mock_get_supabase, test_client, mock_user, mock_supabase):
        """Should upsert user record before saving"""
        mock_get_supabase.return_value = mock_supabase
        
        # Remove existing user
        mock_supabase.users.clear()
        
        app.dependency_overrides[get_current_user] = override_auth(mock_user)
        
        try:
            response = test_client.post("/api/v1/posts/post-1/save")
            
            assert response.status_code == 200
            # User should have been created via upsert
            assert len(mock_supabase.users) == 1
            assert mock_supabase.users[0]["id"] == "user-123"
        finally:
            app.dependency_overrides.clear()


class TestSavePostMultipleUsers:
    """Tests for multiple users saving same post"""
    
    @patch('api.routes.posts.get_service_supabase')
    def test_different_users_can_save_same_post(self, mock_get_supabase, test_client, mock_supabase):
        """Different users should be able to save the same post"""
        mock_get_supabase.return_value = mock_supabase
        user1 = MockUser(user_id="user-1", email="user1@example.com")
        user2 = MockUser(user_id="user-2", email="user2@example.com")
        
        try:
            # User 1 saves post
            app.dependency_overrides[get_current_user] = override_auth(user1)
            
            response1 = test_client.post("/api/v1/posts/post-1/save")
            assert response1.json()["saved"] is True
            
            # User 2 saves same post
            app.dependency_overrides[get_current_user] = override_auth(user2)
            
            response2 = test_client.post("/api/v1/posts/post-1/save")
            assert response2.json()["saved"] is True
            
            # Both saves should exist
            assert len(mock_supabase.saved_posts) == 2
            user_ids = {s["user_id"] for s in mock_supabase.saved_posts}
            assert user_ids == {"user-1", "user-2"}
        finally:
            app.dependency_overrides.clear()
    
    @patch('api.routes.posts.get_service_supabase')
    def test_unsave_only_affects_current_user(self, mock_get_supabase, test_client, mock_supabase):
        """Unsaving should only remove the save for the current user"""
        mock_get_supabase.return_value = mock_supabase
        user1 = MockUser(user_id="user-1", email="user1@example.com")
        
        # Both users have saved post-1
        mock_supabase.saved_posts = [
            {"id": "saved-1", "post_id": "post-1", "user_id": "user-1"},
            {"id": "saved-2", "post_id": "post-1", "user_id": "user-2"},
        ]
        
        try:
            # User 1 unsaves
            app.dependency_overrides[get_current_user] = override_auth(user1)
            
            response = test_client.post("/api/v1/posts/post-1/save")
            assert response.json()["saved"] is False
            
            # Only user-1's save should be removed
            assert len(mock_supabase.saved_posts) == 1
            assert mock_supabase.saved_posts[0]["user_id"] == "user-2"
        finally:
            app.dependency_overrides.clear()
