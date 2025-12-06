"""
Notes Storage Module

Provides an abstract storage interface and implementations:
- JSONStorage: File-based storage (default)
- Future: FirestoreStorage, SupabaseStorage

Usage:
    from src.notes.storage import get_storage
    
    storage = get_storage()
    note_id = storage.create(user_id, content, tags)
    notes = storage.list(user_id)
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("walls.notes.storage")

# Project root
ROOT = Path(__file__).resolve().parent.parent.parent
NOTES_DIR = ROOT / "user_data" / "notes"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class Note:
    """Note data model."""
    
    def __init__(
        self,
        id: str,
        user_id: str,
        content: str,
        tags: List[str],
        created_at: str,
        updated_at: str,
        title: Optional[str] = None,
        mood_score: Optional[int] = None,
        is_pinned: bool = False
    ):
        self.id = id
        self.user_id = user_id
        self.content = content
        self.tags = tags
        self.created_at = created_at
        self.updated_at = updated_at
        self.title = title or self._generate_title(content)
        self.mood_score = mood_score
        self.is_pinned = is_pinned
    
    def _generate_title(self, content: str) -> str:
        """Generate title from first line of content."""
        first_line = content.split('\n')[0][:50]
        return first_line.strip() or "Untitled Note"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "mood_score": self.mood_score,
            "is_pinned": self.is_pinned
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            content=data["content"],
            tags=data.get("tags", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            title=data.get("title"),
            mood_score=data.get("mood_score"),
            is_pinned=data.get("is_pinned", False)
        )


# ---------------------------------------------------------------------------
# Abstract Storage Interface
# ---------------------------------------------------------------------------

class NoteStorage(ABC):
    """
    Abstract interface for note storage.
    
    Implement this to add new storage backends (Firestore, Supabase, etc.)
    """
    
    @abstractmethod
    def create(
        self,
        user_id: str,
        content: str,
        tags: List[str] = None,
        title: Optional[str] = None,
        mood_score: Optional[int] = None
    ) -> Note:
        """Create a new note."""
        pass
    
    @abstractmethod
    def get(self, user_id: str, note_id: str) -> Optional[Note]:
        """Get a single note."""
        pass
    
    @abstractmethod
    def list(
        self,
        user_id: str,
        tags: List[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Note]:
        """List notes for a user."""
        pass
    
    @abstractmethod
    def update(
        self,
        user_id: str,
        note_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        mood_score: Optional[int] = None,
        is_pinned: Optional[bool] = None
    ) -> Optional[Note]:
        """Update an existing note."""
        pass
    
    @abstractmethod
    def delete(self, user_id: str, note_id: str) -> bool:
        """Delete a note."""
        pass
    
    @abstractmethod
    def search(self, user_id: str, query: str) -> List[Note]:
        """Search notes by content."""
        pass
    
    @abstractmethod
    def export(self, user_id: str, format: str = "json") -> str:
        """Export all notes."""
        pass


# ---------------------------------------------------------------------------
# JSON File Storage Implementation
# ---------------------------------------------------------------------------

class JSONStorage(NoteStorage):
    """
    JSON file-based note storage.
    
    Stores notes in: user_data/notes/{user_id}.json
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or NOTES_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get the file path for a user's notes."""
        safe_id = "".join(c if c.isalnum() or c in "._-@" else "_" for c in user_id)
        return self.storage_dir / f"{safe_id}.json"
    
    def _load_notes(self, user_id: str) -> List[Note]:
        """Load all notes for a user."""
        file_path = self._get_user_file(user_id)
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Note.from_dict(n) for n in data.get("notes", [])]
        except Exception as e:
            logger.error(f"Failed to load notes for {user_id}: {e}")
            return []
    
    def _save_notes(self, user_id: str, notes: List[Note]) -> None:
        """Save all notes for a user."""
        file_path = self._get_user_file(user_id)
        
        data = {
            "user_id": user_id,
            "updated_at": datetime.now().isoformat(),
            "notes": [n.to_dict() for n in notes]
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create(
        self,
        user_id: str,
        content: str,
        tags: List[str] = None,
        title: Optional[str] = None,
        mood_score: Optional[int] = None
    ) -> Note:
        """Create a new note."""
        now = datetime.now().isoformat()
        
        note = Note(
            id=str(uuid.uuid4())[:8],
            user_id=user_id,
            content=content,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            title=title,
            mood_score=mood_score
        )
        
        notes = self._load_notes(user_id)
        notes.insert(0, note)  # Add to beginning
        self._save_notes(user_id, notes)
        
        logger.info(f"Created note {note.id} for user {user_id}")
        return note
    
    def get(self, user_id: str, note_id: str) -> Optional[Note]:
        """Get a single note."""
        notes = self._load_notes(user_id)
        for note in notes:
            if note.id == note_id:
                return note
        return None
    
    def list(
        self,
        user_id: str,
        tags: List[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Note]:
        """List notes for a user."""
        notes = self._load_notes(user_id)
        
        # Filter by tags if specified
        if tags:
            notes = [n for n in notes if any(t in n.tags for t in tags)]
        
        # Sort: pinned first, then by date
        notes.sort(key=lambda n: (not n.is_pinned, n.created_at), reverse=True)
        
        # Apply pagination
        return notes[offset:offset + limit]
    
    def update(
        self,
        user_id: str,
        note_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        mood_score: Optional[int] = None,
        is_pinned: Optional[bool] = None
    ) -> Optional[Note]:
        """Update an existing note."""
        notes = self._load_notes(user_id)
        
        for i, note in enumerate(notes):
            if note.id == note_id:
                if content is not None:
                    note.content = content
                if tags is not None:
                    note.tags = tags
                if title is not None:
                    note.title = title
                if mood_score is not None:
                    note.mood_score = mood_score
                if is_pinned is not None:
                    note.is_pinned = is_pinned
                
                note.updated_at = datetime.now().isoformat()
                notes[i] = note
                self._save_notes(user_id, notes)
                
                logger.info(f"Updated note {note_id} for user {user_id}")
                return note
        
        return None
    
    def delete(self, user_id: str, note_id: str) -> bool:
        """Delete a note."""
        notes = self._load_notes(user_id)
        original_count = len(notes)
        
        notes = [n for n in notes if n.id != note_id]
        
        if len(notes) < original_count:
            self._save_notes(user_id, notes)
            logger.info(f"Deleted note {note_id} for user {user_id}")
            return True
        
        return False
    
    def search(self, user_id: str, query: str) -> List[Note]:
        """Search notes by content."""
        notes = self._load_notes(user_id)
        query_lower = query.lower()
        
        results = []
        for note in notes:
            if (query_lower in note.content.lower() or 
                query_lower in note.title.lower() or
                any(query_lower in tag.lower() for tag in note.tags)):
                results.append(note)
        
        return results
    
    def export(self, user_id: str, format: str = "json") -> str:
        """Export all notes."""
        notes = self._load_notes(user_id)
        
        if format == "json":
            return json.dumps([n.to_dict() for n in notes], indent=2)
        
        elif format == "markdown":
            lines = ["# My Notes & Reflections\n"]
            for note in notes:
                lines.append(f"## {note.title}")
                lines.append(f"*{note.created_at}*")
                if note.tags:
                    lines.append(f"Tags: {', '.join(note.tags)}")
                lines.append("")
                lines.append(note.content)
                lines.append("\n---\n")
            return "\n".join(lines)
        
        elif format == "text":
            lines = []
            for note in notes:
                lines.append(f"=== {note.title} ===")
                lines.append(f"Date: {note.created_at}")
                if note.tags:
                    lines.append(f"Tags: {', '.join(note.tags)}")
                lines.append("")
                lines.append(note.content)
                lines.append("\n" + "=" * 40 + "\n")
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's notes."""
        notes = self._load_notes(user_id)
        
        tag_counts = {}
        mood_scores = []
        
        for note in notes:
            for tag in note.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            if note.mood_score is not None:
                mood_scores.append(note.mood_score)
        
        return {
            "total_notes": len(notes),
            "tag_counts": tag_counts,
            "avg_mood": sum(mood_scores) / len(mood_scores) if mood_scores else None,
            "pinned_count": sum(1 for n in notes if n.is_pinned)
        }


# ---------------------------------------------------------------------------
# Storage Factory
# ---------------------------------------------------------------------------

_storage: Optional[NoteStorage] = None


def get_storage(backend: str = "json") -> NoteStorage:
    """
    Get the storage backend.
    
    Args:
        backend: "json" (default), "firestore" (future), "supabase" (future)
    
    Returns:
        NoteStorage implementation
    """
    global _storage
    
    if _storage is None:
        if backend == "json":
            _storage = JSONStorage()
        # Future implementations:
        # elif backend == "firestore":
        #     _storage = FirestoreStorage()
        # elif backend == "supabase":
        #     _storage = SupabaseStorage()
        else:
            raise ValueError(f"Unknown storage backend: {backend}")
    
    return _storage


# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Notes Storage Self-Test")
    print("=" * 60)
    
    storage = JSONStorage()
    test_user = "test_notes_user"
    
    # Create
    print("\n1. Creating note...")
    note = storage.create(
        user_id=test_user,
        content="Today I felt much better after my morning walk. The fresh air really helped clear my mind.",
        tags=["stress", "exercise", "positive"],
        mood_score=7
    )
    print(f"   Created: {note.id} - {note.title}")
    
    # List
    print("\n2. Listing notes...")
    notes = storage.list(test_user)
    print(f"   Found {len(notes)} note(s)")
    
    # Update
    print("\n3. Updating note...")
    updated = storage.update(
        user_id=test_user,
        note_id=note.id,
        content=note.content + "\n\nUpdate: Still feeling good this evening!",
        is_pinned=True
    )
    print(f"   Updated: {updated.id}, pinned: {updated.is_pinned}")
    
    # Search
    print("\n4. Searching notes...")
    results = storage.search(test_user, "morning walk")
    print(f"   Found {len(results)} result(s)")
    
    # Export
    print("\n5. Exporting notes...")
    export = storage.export(test_user, "markdown")
    print(f"   Export length: {len(export)} chars")
    
    # Stats
    print("\n6. Getting stats...")
    stats = storage.get_stats(test_user)
    print(f"   Stats: {stats}")
    
    # Cleanup
    print("\n7. Deleting test note...")
    deleted = storage.delete(test_user, note.id)
    print(f"   Deleted: {deleted}")
    
    print("\n" + "=" * 60)
    print("Self-test complete!")
    print("=" * 60)

