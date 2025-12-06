/**
 * WALLS Notes & Reflections Module
 * 
 * Handles note creation, listing, searching, and export.
 */

(function() {
    'use strict';
    
    // ---------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------
    
    const state = {
        notes: [],
        availableTags: [],
        selectedTags: [],
        selectedMood: null,
        currentFilter: 'all',
        currentNote: null
    };
    
    // ---------------------------------------------------------------------------
    // DOM Elements
    // ---------------------------------------------------------------------------
    
    const elements = {
        noteTitle: document.getElementById('note-title'),
        noteContent: document.getElementById('note-content'),
        charCount: document.getElementById('char-count'),
        saveBtn: document.getElementById('save-note-btn'),
        notesList: document.getElementById('notes-list'),
        notesEmpty: document.getElementById('notes-empty'),
        searchInput: document.getElementById('search-notes'),
        tagOptions: document.getElementById('tag-options'),
        exportBtn: document.getElementById('export-btn'),
        exportMenu: document.getElementById('export-menu'),
        moodSelector: document.getElementById('mood-selector'),
        modal: document.getElementById('note-modal'),
        modalTitle: document.getElementById('modal-title'),
        modalDate: document.getElementById('modal-date'),
        modalMood: document.getElementById('modal-mood'),
        modalTags: document.getElementById('modal-tags'),
        modalContent: document.getElementById('modal-content'),
        modalClose: document.getElementById('modal-close'),
        modalPinBtn: document.getElementById('modal-pin-btn'),
        modalDeleteBtn: document.getElementById('modal-delete-btn'),
        modalEditBtn: document.getElementById('modal-edit-btn')
    };
    
    // ---------------------------------------------------------------------------
    // API Functions
    // ---------------------------------------------------------------------------
    
    async function fetchNotes(filter = null) {
        let url = '/api/notes/list';
        if (filter && filter !== 'all' && filter !== 'pinned') {
            url += `?tags=${filter}`;
        }
        
        try {
            const response = await fetch(url, {
                headers: { 'X-User-ID': getUserId() }
            });
            const data = await response.json();
            
            let notes = data.notes || [];
            
            // Apply pinned filter client-side
            if (filter === 'pinned') {
                notes = notes.filter(n => n.is_pinned);
            }
            
            return notes;
        } catch (error) {
            console.error('Failed to fetch notes:', error);
            return [];
        }
    }
    
    async function createNote(noteData) {
        try {
            const response = await fetch('/api/notes/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': getUserId()
                },
                body: JSON.stringify(noteData)
            });
            
            if (!response.ok) {
                throw new Error('Failed to create note');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to create note:', error);
            throw error;
        }
    }
    
    async function updateNote(noteId, updates) {
        try {
            const response = await fetch(`/api/notes/${noteId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': getUserId()
                },
                body: JSON.stringify(updates)
            });
            
            if (!response.ok) {
                throw new Error('Failed to update note');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to update note:', error);
            throw error;
        }
    }
    
    async function deleteNote(noteId) {
        try {
            const response = await fetch(`/api/notes/${noteId}`, {
                method: 'DELETE',
                headers: { 'X-User-ID': getUserId() }
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete note');
            }
            
            return true;
        } catch (error) {
            console.error('Failed to delete note:', error);
            throw error;
        }
    }
    
    async function searchNotes(query) {
        try {
            const response = await fetch(`/api/notes/search?q=${encodeURIComponent(query)}`, {
                headers: { 'X-User-ID': getUserId() }
            });
            return (await response.json()).results || [];
        } catch (error) {
            console.error('Search failed:', error);
            return [];
        }
    }
    
    async function fetchTags() {
        try {
            const response = await fetch('/api/notes/tags');
            const data = await response.json();
            return data.tags || [];
        } catch (error) {
            console.error('Failed to fetch tags:', error);
            return [];
        }
    }
    
    async function exportNotes(format) {
        const url = `/api/notes/export?format=${format}`;
        window.location.href = url + `&user_id=${getUserId()}`;
    }
    
    // ---------------------------------------------------------------------------
    // Utility Functions
    // ---------------------------------------------------------------------------
    
    function getUserId() {
        let userId = localStorage.getItem('walls_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('walls_user_id', userId);
        }
        return userId;
    }
    
    function formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }
    
    function getMoodEmoji(score) {
        if (!score) return '';
        if (score <= 2) return '😢';
        if (score <= 4) return '😔';
        if (score <= 6) return '😐';
        if (score <= 8) return '🙂';
        if (score <= 9) return '😊';
        return '🌟';
    }
    
    // ---------------------------------------------------------------------------
    // Render Functions
    // ---------------------------------------------------------------------------
    
    function renderTags() {
        const container = elements.tagOptions;
        if (!container) return;
        
        container.innerHTML = state.availableTags.map(tag => `
            <button class="tag-btn ${state.selectedTags.includes(tag.id) ? 'selected' : ''}" 
                    data-tag="${tag.id}"
                    style="--tag-color: ${tag.color}">
                ${tag.label}
            </button>
        `).join('');
        
        // Add click handlers
        container.querySelectorAll('.tag-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tagId = btn.dataset.tag;
                if (state.selectedTags.includes(tagId)) {
                    state.selectedTags = state.selectedTags.filter(t => t !== tagId);
                    btn.classList.remove('selected');
                } else {
                    state.selectedTags.push(tagId);
                    btn.classList.add('selected');
                }
            });
        });
    }
    
    function renderFilterButtons() {
        const container = document.querySelector('.notes-filter');
        if (!container) return;
        
        const tagFilters = state.availableTags.map(tag => `
            <button class="filter-btn" data-filter="${tag.id}">${tag.label}</button>
        `).join('');
        
        container.innerHTML = `
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="pinned">📌 Pinned</button>
            ${tagFilters}
        `;
        
        // Add click handlers
        container.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentFilter = btn.dataset.filter;
                await loadNotes();
            });
        });
    }
    
    function renderNotes(notes) {
        const container = elements.notesList;
        const emptyState = elements.notesEmpty;
        
        if (!notes.length) {
            container.style.display = 'none';
            emptyState.hidden = false;
            return;
        }
        
        container.style.display = 'flex';
        emptyState.hidden = true;
        
        container.innerHTML = notes.map(note => {
            const tagHtml = note.tags.map(tagId => {
                const tag = state.availableTags.find(t => t.id === tagId);
                if (!tag) return '';
                return `<span class="note-tag" style="background: ${tag.color}20; color: ${tag.color}">${tag.label}</span>`;
            }).join('');
            
            return `
                <div class="note-card ${note.is_pinned ? 'pinned' : ''}" data-note-id="${note.id}">
                    <div class="note-card-header">
                        <h3 class="note-card-title">${note.is_pinned ? '📌 ' : ''}${escapeHtml(note.title)}</h3>
                        <span class="note-card-date">${formatDate(note.created_at)}</span>
                    </div>
                    <p class="note-card-preview">${escapeHtml(note.content)}</p>
                    <div class="note-card-footer">
                        <div class="note-card-tags">${tagHtml}</div>
                        <span class="note-card-mood">${getMoodEmoji(note.mood_score)}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click handlers
        container.querySelectorAll('.note-card').forEach(card => {
            card.addEventListener('click', () => {
                const noteId = card.dataset.noteId;
                const note = state.notes.find(n => n.id === noteId);
                if (note) showNoteModal(note);
            });
        });
    }
    
    function showNoteModal(note) {
        state.currentNote = note;
        
        if (elements.modalTitle) elements.modalTitle.textContent = note.title;
        if (elements.modalDate) elements.modalDate.textContent = formatDate(note.created_at);
        if (elements.modalMood) {
            elements.modalMood.textContent = note.mood_score ? 
                `Mood: ${getMoodEmoji(note.mood_score)} (${note.mood_score}/10)` : '';
        }
        
        if (elements.modalTags) {
            elements.modalTags.innerHTML = note.tags.map(tagId => {
                const tag = state.availableTags.find(t => t.id === tagId);
                if (!tag) return '';
                return `<span class="note-tag" style="background: ${tag.color}20; color: ${tag.color}">${tag.label}</span>`;
            }).join('');
        }
        
        if (elements.modalContent) elements.modalContent.textContent = note.content;
        if (elements.modalPinBtn) elements.modalPinBtn.textContent = note.is_pinned ? '📌 Unpin' : '📌 Pin';
        
        if (elements.modal) {
            elements.modal.removeAttribute('hidden');
            document.body.style.overflow = 'hidden';
        }
    }
    
    function hideModal() {
        if (elements.modal) {
            elements.modal.setAttribute('hidden', '');
            document.body.style.overflow = '';
        }
        state.currentNote = null;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ---------------------------------------------------------------------------
    // Event Handlers
    // ---------------------------------------------------------------------------
    
    async function handleSaveNote() {
        if (!elements.noteContent) return;
        
        const content = elements.noteContent.value.trim();
        if (!content) {
            elements.noteContent.focus();
            return;
        }
        
        const noteData = {
            content,
            title: elements.noteTitle ? elements.noteTitle.value.trim() : null,
            tags: state.selectedTags,
            mood_score: state.selectedMood
        };
        
        try {
            if (elements.saveBtn) {
                elements.saveBtn.disabled = true;
                elements.saveBtn.textContent = 'Saving...';
            }
            
            await createNote(noteData);
            
            // Reset form
            if (elements.noteTitle) elements.noteTitle.value = '';
            if (elements.noteContent) elements.noteContent.value = '';
            if (elements.charCount) elements.charCount.textContent = '0';
            state.selectedTags = [];
            state.selectedMood = null;
            
            // Deselect all tags
            document.querySelectorAll('.tag-btn.selected').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Deselect mood
            document.querySelectorAll('.mood-btn.selected').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Reload notes
            await loadNotes();
            
            // Show success feedback
            if (elements.saveBtn) {
                elements.saveBtn.textContent = '✓ Saved!';
                setTimeout(() => {
                    elements.saveBtn.innerHTML = '<span class="btn-icon">✓</span> Save Entry';
                }, 1500);
            }
            
        } catch (error) {
            if (elements.saveBtn) {
                elements.saveBtn.textContent = 'Error - Try Again';
                setTimeout(() => {
                    elements.saveBtn.innerHTML = '<span class="btn-icon">✓</span> Save Entry';
                }, 2000);
            }
        } finally {
            if (elements.saveBtn) elements.saveBtn.disabled = false;
        }
    }
    
    async function handleSearch() {
        if (!elements.searchInput) return;
        
        const query = elements.searchInput.value.trim();
        
        if (!query) {
            await loadNotes();
            return;
        }
        
        const results = await searchNotes(query);
        state.notes = results;
        renderNotes(results);
    }
    
    async function handlePinNote() {
        if (!state.currentNote) return;
        
        const newPinState = !state.currentNote.is_pinned;
        
        try {
            await updateNote(state.currentNote.id, { is_pinned: newPinState });
            hideModal();
            await loadNotes();
        } catch (error) {
            console.error('Failed to pin note:', error);
        }
    }
    
    async function handleDeleteNote() {
        if (!state.currentNote) return;
        
        if (!confirm('Are you sure you want to delete this note?')) {
            return;
        }
        
        try {
            await deleteNote(state.currentNote.id);
            hideModal();
            await loadNotes();
        } catch (error) {
            console.error('Failed to delete note:', error);
        }
    }
    
    // ---------------------------------------------------------------------------
    // Initialization
    // ---------------------------------------------------------------------------
    
    async function loadNotes() {
        state.notes = await fetchNotes(state.currentFilter);
        renderNotes(state.notes);
    }
    
    async function init() {
        console.log('[Notes] Initializing...');
        
        // Load available tags
        state.availableTags = await fetchTags();
        renderTags();
        renderFilterButtons();
        
        // Load notes
        await loadNotes();
        
        // Character counter
        if (elements.noteContent) {
            elements.noteContent.addEventListener('input', () => {
                const count = elements.noteContent.value.length;
                elements.charCount.textContent = count;
            });
        }
        
        // Save button
        if (elements.saveBtn) {
            elements.saveBtn.addEventListener('click', handleSaveNote);
        }
        
        // Search (debounced)
        let searchTimeout;
        if (elements.searchInput) {
            elements.searchInput.addEventListener('input', () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(handleSearch, 300);
            });
        }
        
        // Mood selector
        if (elements.moodSelector) {
            elements.moodSelector.querySelectorAll('.mood-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    elements.moodSelector.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    state.selectedMood = parseInt(btn.dataset.mood);
                });
            });
        }
        
        // Export dropdown
        if (elements.exportBtn && elements.exportMenu) {
            elements.exportBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                elements.exportMenu.classList.toggle('show');
            });
            
            document.addEventListener('click', () => {
                elements.exportMenu.classList.remove('show');
            });
            
            elements.exportMenu.querySelectorAll('.dropdown-item').forEach(item => {
                item.addEventListener('click', () => {
                    const format = item.dataset.format;
                    exportNotes(format);
                    elements.exportMenu.classList.remove('show');
                });
            });
        }
        
        // Modal handlers
        if (elements.modalClose) {
            elements.modalClose.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                hideModal();
            });
        }
        
        if (elements.modal) {
            const backdrop = elements.modal.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    hideModal();
                });
            }
        }
        
        if (elements.modalPinBtn) {
            elements.modalPinBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                handlePinNote();
            });
        }
        
        if (elements.modalDeleteBtn) {
            elements.modalDeleteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                handleDeleteNote();
            });
        }
        
        // Keyboard shortcut: Escape to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && elements.modal && !elements.modal.hasAttribute('hidden')) {
                hideModal();
            }
        });
        
        console.log('[Notes] Initialized successfully');
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

