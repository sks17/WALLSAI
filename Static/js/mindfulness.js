/**
 * WALLS Mindfulness Resources Module
 * 
 * Handles breathing exercises, resource display, and therapist search.
 */

(function() {
    'use strict';
    
    // ---------------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------------
    
    const state = {
        resources: {},
        exercises: [],
        tips: [],
        learnTopics: [],
        currentExercise: null,
        breathingActive: false,
        breathingCycle: 0
    };
    
    // ---------------------------------------------------------------------------
    // DOM Elements
    // ---------------------------------------------------------------------------
    
    const elements = {
        exercisesGrid: document.getElementById('breathing-exercises'),
        breathingModal: document.getElementById('breathing-modal'),
        breathingBackdrop: document.getElementById('breathing-backdrop'),
        breathingTitle: document.getElementById('breathing-title'),
        breathingDesc: document.getElementById('breathing-desc'),
        breathingCircle: document.getElementById('breathing-circle'),
        breathingInstruction: document.getElementById('breathing-instruction'),
        breathingCycle: document.getElementById('breathing-cycle'),
        breathingTotal: document.getElementById('breathing-total'),
        breathingStart: document.getElementById('breathing-start'),
        breathingStop: document.getElementById('breathing-stop'),
        breathingClose: document.getElementById('breathing-close'),
        tipsGrid: document.getElementById('tips-grid'),
        resourcesGrid: document.getElementById('resources-grid'),
        learnGrid: document.getElementById('learn-grid'),
        directoryGrid: document.getElementById('directory-grid'),
        therapistLocation: document.getElementById('therapist-location'),
        therapistSpecialty: document.getElementById('therapist-specialty'),
        therapistSearchBtn: document.getElementById('therapist-search-btn')
    };
    
    // ---------------------------------------------------------------------------
    // API Functions
    // ---------------------------------------------------------------------------
    
    async function fetchBreathingExercises() {
        try {
            const response = await fetch('/api/resources/breathing');
            const data = await response.json();
            return data.exercises || [];
        } catch (error) {
            console.error('Failed to fetch exercises:', error);
            return [];
        }
    }
    
    async function fetchTips(category = null) {
        try {
            let url = '/api/resources/tips';
            if (category) url += `?category=${category}`;
            const response = await fetch(url);
            const data = await response.json();
            return data.tips || [];
        } catch (error) {
            console.error('Failed to fetch tips:', error);
            return [];
        }
    }
    
    async function fetchResources(category = null) {
        try {
            let url = '/api/resources/mindfulness';
            if (category) url += `?category=${category}`;
            const response = await fetch(url);
            const data = await response.json();
            return data.resources || {};
        } catch (error) {
            console.error('Failed to fetch resources:', error);
            return {};
        }
    }
    
    async function fetchLearnTopics() {
        try {
            const response = await fetch('/api/resources/learn');
            const data = await response.json();
            return data.topics || [];
        } catch (error) {
            console.error('Failed to fetch topics:', error);
            return [];
        }
    }
    
    async function searchTherapist(location, specialty) {
        try {
            let url = `/api/resources/search/therapist?location=${encodeURIComponent(location)}`;
            if (specialty) url += `&specialty=${encodeURIComponent(specialty)}`;
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Failed to search:', error);
            return null;
        }
    }
    
    // ---------------------------------------------------------------------------
    // Render Functions
    // ---------------------------------------------------------------------------
    
    function renderBreathingExercises(exercises) {
        if (!elements.exercisesGrid) return;
        
        elements.exercisesGrid.innerHTML = exercises.map(ex => `
            <div class="breathing-card" data-exercise-id="${ex.id}">
                <h3 class="breathing-card-title">${ex.name}</h3>
                <p class="breathing-card-desc">${ex.description}</p>
                <div class="breathing-card-benefits">
                    ${ex.benefits.map(b => `<span class="benefit-tag">${b}</span>`).join('')}
                </div>
            </div>
        `).join('');
        
        // Add click handlers
        elements.exercisesGrid.querySelectorAll('.breathing-card').forEach(card => {
            card.addEventListener('click', () => {
                const exerciseId = card.dataset.exerciseId;
                const exercise = state.exercises.find(e => e.id === exerciseId);
                if (exercise) openBreathingModal(exercise);
            });
        });
    }
    
    function renderTips(tips) {
        if (!elements.tipsGrid) return;
        
        elements.tipsGrid.innerHTML = tips.map(tip => `
            <div class="tip-card">
                <h3 class="tip-card-title">${tip.title}</h3>
                <p class="tip-card-content">${tip.content}</p>
            </div>
        `).join('');
    }
    
    function renderResources(resources, category) {
        if (!elements.resourcesGrid) return;
        
        const items = resources[category] || [];
        
        elements.resourcesGrid.innerHTML = items.map(item => `
            <div class="resource-card">
                <div class="resource-card-header">
                    <span class="resource-icon">${item.icon || '📎'}</span>
                    <span class="resource-card-title">${item.name}</span>
                </div>
                <p class="resource-card-desc">${item.description}</p>
                <div class="resource-tags">
                    ${item.tags.map(t => `<span class="benefit-tag">${t}</span>`).join('')}
                </div>
                <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="resource-link">
                    Visit Site →
                </a>
            </div>
        `).join('');
    }
    
    function renderLearnTopics(topics) {
        if (!elements.learnGrid) return;
        
        elements.learnGrid.innerHTML = topics.map(topic => `
            <div class="learn-card" data-topic-id="${topic.id}">
                <div class="learn-icon">${topic.icon}</div>
                <h3 class="learn-title">${topic.title}</h3>
                <p class="learn-summary">${topic.summary}</p>
            </div>
        `).join('');
        
        // Add click handlers
        elements.learnGrid.querySelectorAll('.learn-card').forEach(card => {
            card.addEventListener('click', () => {
                const topicId = card.dataset.topicId;
                window.location.href = `/learn/${topicId}`;
            });
        });
    }
    
    function renderDirectories(directories) {
        if (!elements.directoryGrid) return;
        
        elements.directoryGrid.innerHTML = directories.map(dir => `
            <div class="directory-card">
                <a href="${dir.url}" target="_blank" rel="noopener noreferrer">${dir.name}</a>
                <p>${dir.description}</p>
            </div>
        `).join('');
    }
    
    // ---------------------------------------------------------------------------
    // Breathing Exercise Logic
    // ---------------------------------------------------------------------------
    
    function openBreathingModal(exercise) {
        state.currentExercise = exercise;
        state.breathingCycle = 0;
        
        if (elements.breathingTitle) elements.breathingTitle.textContent = exercise.name;
        if (elements.breathingDesc) elements.breathingDesc.textContent = exercise.description;
        if (elements.breathingTotal) elements.breathingTotal.textContent = exercise.cycles;
        if (elements.breathingCycle) elements.breathingCycle.textContent = '0';
        if (elements.breathingInstruction) elements.breathingInstruction.textContent = 'Ready';
        if (elements.breathingCircle) elements.breathingCircle.className = 'breathing-circle';
        
        if (elements.breathingStart) elements.breathingStart.hidden = false;
        if (elements.breathingStop) elements.breathingStop.hidden = true;
        
        if (elements.breathingModal) {
            elements.breathingModal.removeAttribute('hidden');
            document.body.style.overflow = 'hidden';
        }
    }
    
    function closeBreathingModal() {
        stopBreathing();
        if (elements.breathingModal) {
            elements.breathingModal.setAttribute('hidden', '');
            document.body.style.overflow = '';
        }
        state.currentExercise = null;
    }
    
    function startBreathing() {
        if (!state.currentExercise) return;
        
        state.breathingActive = true;
        state.breathingCycle = 0;
        
        if (elements.breathingStart) elements.breathingStart.hidden = true;
        if (elements.breathingStop) elements.breathingStop.hidden = false;
        
        runBreathingCycle();
    }
    
    function stopBreathing() {
        state.breathingActive = false;
        if (elements.breathingCircle) elements.breathingCircle.className = 'breathing-circle';
        if (elements.breathingInstruction) elements.breathingInstruction.textContent = 'Stopped';
        if (elements.breathingStart) {
            elements.breathingStart.hidden = false;
            elements.breathingStart.textContent = 'Begin';
        }
        if (elements.breathingStop) elements.breathingStop.hidden = true;
    }
    
    async function runBreathingCycle() {
        const exercise = state.currentExercise;
        if (!exercise || !state.breathingActive) return;
        
        const steps = exercise.steps;
        
        for (let step of steps) {
            if (!state.breathingActive) return;
            
            if (elements.breathingInstruction) elements.breathingInstruction.textContent = step.instruction;
            if (elements.breathingCircle) elements.breathingCircle.className = `breathing-circle ${step.phase}`;
            
            // Wait for the duration
            await sleep(step.duration * 1000);
        }
        
        state.breathingCycle++;
        if (elements.breathingCycle) elements.breathingCycle.textContent = state.breathingCycle;
        
        // Check if we've completed all cycles
        if (state.breathingCycle >= exercise.cycles) {
            completeBreathing();
        } else if (state.breathingActive) {
            runBreathingCycle();
        }
    }
    
    function completeBreathing() {
        state.breathingActive = false;
        if (elements.breathingCircle) elements.breathingCircle.className = 'breathing-circle';
        if (elements.breathingInstruction) elements.breathingInstruction.textContent = 'Complete! 🎉';
        if (elements.breathingStart) {
            elements.breathingStart.textContent = 'Again';
            elements.breathingStart.hidden = false;
        }
        if (elements.breathingStop) elements.breathingStop.hidden = true;
    }
    
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // ---------------------------------------------------------------------------
    // Event Handlers
    // ---------------------------------------------------------------------------
    
    function handleTherapistSearch() {
        const location = elements.therapistLocation ? elements.therapistLocation.value.trim() : 'near me';
        const specialty = elements.therapistSpecialty ? elements.therapistSpecialty.value : '';
        
        searchTherapist(location || 'near me', specialty).then(data => {
            if (data && data.directories) {
                renderDirectories(data.directories);
            }
            
            // Also open DuckDuckGo in new tab
            if (data && data.search_urls && data.search_urls.duckduckgo) {
                window.open(data.search_urls.duckduckgo, '_blank');
            }
        });
    }
    
    // ---------------------------------------------------------------------------
    // Initialization
    // ---------------------------------------------------------------------------
    
    async function init() {
        console.log('[Mindfulness] Initializing...');
        
        // Load breathing exercises
        state.exercises = await fetchBreathingExercises();
        renderBreathingExercises(state.exercises);
        
        // Load tips (default: anxiety)
        state.tips = await fetchTips('anxiety');
        renderTips(state.tips);
        
        // Load resources (default: meditation_apps)
        state.resources = await fetchResources();
        renderResources(state.resources, 'meditation_apps');
        
        // Load learn topics
        state.learnTopics = await fetchLearnTopics();
        renderLearnTopics(state.learnTopics);
        
        // Load initial directories
        const searchData = await searchTherapist('', '');
        if (searchData && searchData.directories) {
            renderDirectories(searchData.directories);
        }
        
        // Tip tabs
        document.querySelectorAll('.tip-tab').forEach(tab => {
            tab.addEventListener('click', async () => {
                document.querySelectorAll('.tip-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const category = tab.dataset.category;
                state.tips = await fetchTips(category);
                renderTips(state.tips);
            });
        });
        
        // Resource tabs
        document.querySelectorAll('.resource-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.resource-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const category = tab.dataset.category;
                renderResources(state.resources, category);
            });
        });
        
        // Breathing modal controls
        if (elements.breathingStart) {
            elements.breathingStart.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                startBreathing();
            });
        }
        
        if (elements.breathingStop) {
            elements.breathingStop.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                stopBreathing();
            });
        }
        
        if (elements.breathingClose) {
            elements.breathingClose.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeBreathingModal();
            });
        }
        
        // Breathing modal backdrop click
        if (elements.breathingBackdrop) {
            elements.breathingBackdrop.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeBreathingModal();
            });
        }
        
        // Therapist search
        if (elements.therapistSearchBtn) {
            elements.therapistSearchBtn.addEventListener('click', handleTherapistSearch);
        }
        
        // Keyboard shortcut: Escape to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && elements.breathingModal && !elements.breathingModal.hasAttribute('hidden')) {
                closeBreathingModal();
            }
        });
        
        console.log('[Mindfulness] Initialized successfully');
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

