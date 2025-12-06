/**
 * KERNEL Survey Module
 * 
 * Enhanced survey system supporting:
 * - Likert scales (PHQ-9, GAD-7 validated instruments)
 * - Continuous sliders
 * - Dropdowns
 * - Free-text with real-time sentiment preview
 * 
 * Outputs are formatted for the KERNEL API which provides
 * distributional predictions with uncertainty.
 */

const KernelSurvey = (function() {
    'use strict';

    // ========================================================================
    // Configuration
    // ========================================================================
    
    const API_ENDPOINT = '/api/kernel/predict';
    const SCHEMA_ENDPOINT = '/api/kernel/schema';
    
    // ========================================================================
    // State
    // ========================================================================
    
    let schema = null;
    let responses = {};
    let currentSection = 0;
    let containerEl = null;
    let onCompleteCallback = null;
    let isSubmitting = false;

    // ========================================================================
    // Initialization
    // ========================================================================

    /**
     * Initialize the survey
     */
    async function init(containerId, options = {}) {
        containerEl = document.getElementById(containerId);
        if (!containerEl) {
            console.error('[KernelSurvey] Container not found:', containerId);
            return false;
        }

        onCompleteCallback = options.onComplete || null;
        
        // Show loading state
        containerEl.innerHTML = `
            <div class="survey-loading">
                <div class="loading-spinner"></div>
                <p>Loading assessment...</p>
            </div>
        `;

        // Load schema
        try {
            const response = await fetch(SCHEMA_ENDPOINT);
            if (!response.ok) throw new Error('Failed to load schema');
            schema = await response.json();
            console.log('[KernelSurvey] Schema loaded:', schema.sections?.length, 'sections');
        } catch (e) {
            console.error('[KernelSurvey] Failed to load schema:', e);
            containerEl.innerHTML = `
                <div class="survey-error">
                    <p>Failed to load assessment. Please refresh the page.</p>
                </div>
            `;
            return false;
        }

        // Initialize state
        responses = {};
        currentSection = 0;

        // Render
        render();
        bindEvents();
        
        return true;
    }

    // ========================================================================
    // Rendering
    // ========================================================================

    function render() {
        if (!containerEl || !schema) return;

        const sections = schema.sections || [];
        
        containerEl.innerHTML = `
            <div class="kernel-survey">
                <div class="survey-header">
                    <h1 class="survey-title" data-animate="chars">Mental Health Assessment</h1>
                    <p class="survey-subtitle">Take your time. Your responses help us understand how you're feeling.</p>
                </div>

                <div class="survey-progress">
                    ${renderProgressBar()}
                </div>

                <div class="survey-sections">
                    ${sections.map((section, idx) => renderSection(section, idx)).join('')}
                </div>

                <div class="survey-navigation">
                    <button type="button" class="btn btn-ghost survey-prev" ${currentSection === 0 ? 'disabled' : ''}>
                        ← Previous
                    </button>
                    <span class="survey-indicator">
                        ${currentSection + 1} of ${sections.length}
                    </span>
                    ${currentSection === sections.length - 1 
                        ? `<button type="button" class="btn btn-primary survey-submit">
                             Analyze My Responses
                           </button>`
                        : `<button type="button" class="btn btn-primary survey-next">
                             Continue →
                           </button>`
                    }
                </div>
            </div>
        `;

        showSection(currentSection);
    }

    function renderProgressBar() {
        const sections = schema.sections || [];
        const progress = ((currentSection + 1) / sections.length) * 100;
        
        return `
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="progress-steps">
                ${sections.map((section, idx) => `
                    <div class="progress-step ${idx <= currentSection ? 'active' : ''} ${idx < currentSection ? 'completed' : ''}"
                         data-section="${idx}">
                        <span class="step-dot"></span>
                        <span class="step-label">${section.title}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    function renderSection(section, idx) {
        const isActive = idx === currentSection;
        
        return `
            <section class="survey-section ${isActive ? 'active' : ''}" 
                     data-section="${idx}" 
                     ${!isActive ? 'hidden' : ''}>
                <div class="section-header">
                    <h2 class="section-title">${section.title}</h2>
                    <p class="section-description">${section.description}</p>
                    ${section.instrument ? `
                        <span class="section-badge">${schema.instruments?.[section.instrument]?.name || section.instrument}</span>
                    ` : ''}
                </div>
                <div class="section-questions">
                    ${section.questions.map(q => renderQuestion(q, section)).join('')}
                </div>
            </section>
        `;
    }

    function renderQuestion(q, section) {
        let input = '';
        const value = responses[q.id];

        switch (q.type) {
            case 'likert':
                input = renderLikert(q, value, section);
                break;
            case 'slider':
                input = renderSlider(q, value);
                break;
            case 'dropdown':
                input = renderDropdown(q, value);
                break;
            case 'textarea':
                input = renderTextarea(q, value);
                break;
            default:
                input = `<input type="text" name="${q.id}" value="${value || ''}" class="survey-input">`;
        }

        return `
            <div class="question ${q.flag === 'critical' ? 'question--critical' : ''}" 
                 data-question="${q.id}">
                <label class="question-label">
                    ${q.text}
                    ${q.required ? '<span class="required">*</span>' : ''}
                </label>
                <div class="question-input">
                    ${input}
                </div>
            </div>
        `;
    }

    function renderLikert(q, value, section) {
        const options = q.options || [];
        
        return `
            <div class="likert-scale" data-id="${q.id}">
                ${options.map((opt, idx) => `
                    <label class="likert-option ${value === opt.value ? 'selected' : ''}">
                        <input type="radio" 
                               name="${q.id}" 
                               value="${opt.value}"
                               ${value === opt.value ? 'checked' : ''}>
                        <span class="likert-indicator"></span>
                        <span class="likert-label">${opt.label}</span>
                    </label>
                `).join('')}
            </div>
        `;
    }

    function renderSlider(q, value) {
        const currentValue = value !== undefined ? value : q.default;
        const min = q.min || 0;
        const max = q.max || 100;
        const step = q.step || 1;
        const labels = q.labels || {};
        const unit = q.unit || '';
        
        return `
            <div class="slider-container" data-id="${q.id}">
                <div class="slider-labels">
                    ${Object.entries(labels).map(([pos, label]) => `
                        <span class="slider-label" style="left: ${(pos / max) * 100}%">${label}</span>
                    `).join('')}
                </div>
                <input type="range" 
                       name="${q.id}"
                       min="${min}" 
                       max="${max}" 
                       step="${step}"
                       value="${currentValue}"
                       class="slider-input">
                <div class="slider-value">
                    <span class="value-display">${currentValue}</span>
                    ${unit ? `<span class="value-unit">${unit}</span>` : ''}
                </div>
                <div class="slider-track">
                    <div class="slider-fill" style="width: ${((currentValue - min) / (max - min)) * 100}%"></div>
                </div>
            </div>
        `;
    }

    function renderDropdown(q, value) {
        const options = q.options || [];
        
        return `
            <select name="${q.id}" class="dropdown-select" ${q.required ? 'required' : ''}>
                <option value="" ${!value ? 'selected' : ''}>Select an option...</option>
                ${options.map(opt => `
                    <option value="${opt.value}" ${value === opt.value ? 'selected' : ''}>${opt.label}</option>
                `).join('')}
            </select>
        `;
    }

    function renderTextarea(q, value) {
        const maxLength = q.maxLength || 2000;
        
        return `
            <div class="textarea-container" data-id="${q.id}">
                <textarea name="${q.id}" 
                          class="textarea-input"
                          placeholder="${q.placeholder || ''}"
                          maxlength="${maxLength}"
                          rows="5">${value || ''}</textarea>
                <div class="textarea-footer">
                    <div class="textarea-counter">
                        <span class="char-count">${(value || '').length}</span> / ${maxLength}
                    </div>
                    <div class="textarea-sentiment" id="sentiment-${q.id}">
                        <!-- Real-time sentiment preview will appear here -->
                    </div>
                </div>
            </div>
        `;
    }

    // ========================================================================
    // Navigation
    // ========================================================================

    function showSection(idx) {
        const sections = schema.sections || [];
        if (idx < 0 || idx >= sections.length) return;

        currentSection = idx;
        
        // Hide all sections
        containerEl.querySelectorAll('.survey-section').forEach(el => {
            el.hidden = true;
            el.classList.remove('active');
        });

        // Show current section
        const currentEl = containerEl.querySelector(`.survey-section[data-section="${idx}"]`);
        if (currentEl) {
            currentEl.hidden = false;
            currentEl.classList.add('active');
            
            // Trigger animations
            setTimeout(() => {
                currentEl.querySelectorAll('.question').forEach((q, i) => {
                    q.style.animationDelay = `${i * 0.05}s`;
                    q.classList.add('fade-in');
                });
            }, 50);
        }

        // Update progress
        updateProgress();
        
        // Update navigation
        updateNavigation();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function updateProgress() {
        const sections = schema.sections || [];
        const progress = ((currentSection + 1) / sections.length) * 100;
        
        const fill = containerEl.querySelector('.progress-fill');
        if (fill) fill.style.width = `${progress}%`;
        
        containerEl.querySelectorAll('.progress-step').forEach((step, i) => {
            step.classList.toggle('active', i <= currentSection);
            step.classList.toggle('completed', i < currentSection);
        });
    }

    function updateNavigation() {
        const sections = schema.sections || [];
        
        const prevBtn = containerEl.querySelector('.survey-prev');
        const nextBtn = containerEl.querySelector('.survey-next');
        const submitBtn = containerEl.querySelector('.survey-submit');
        const indicator = containerEl.querySelector('.survey-indicator');
        
        if (prevBtn) prevBtn.disabled = currentSection === 0;
        if (indicator) indicator.textContent = `${currentSection + 1} of ${sections.length}`;
        
        // Swap next/submit
        const isLastSection = currentSection === sections.length - 1;
        if (nextBtn) nextBtn.style.display = isLastSection ? 'none' : 'inline-flex';
        if (submitBtn) submitBtn.style.display = isLastSection ? 'inline-flex' : 'none';
    }

    function nextSection() {
        if (validateCurrentSection()) {
            showSection(currentSection + 1);
        }
    }

    function prevSection() {
        showSection(currentSection - 1);
    }

    // ========================================================================
    // Event Binding
    // ========================================================================

    function bindEvents() {
        if (!containerEl) return;

        // Navigation
        containerEl.addEventListener('click', (e) => {
            if (e.target.closest('.survey-next')) {
                nextSection();
            } else if (e.target.closest('.survey-prev')) {
                prevSection();
            } else if (e.target.closest('.survey-submit')) {
                handleSubmit();
            } else if (e.target.closest('.progress-step')) {
                const stepIdx = parseInt(e.target.closest('.progress-step').dataset.section);
                if (stepIdx < currentSection) {
                    showSection(stepIdx);
                }
            }
        });

        // Likert options
        containerEl.addEventListener('change', (e) => {
            if (e.target.closest('.likert-scale input')) {
                const scale = e.target.closest('.likert-scale');
                const qid = scale.dataset.id;
                const value = parseInt(e.target.value);
                
                responses[qid] = value;
                
                // Update visual selection
                scale.querySelectorAll('.likert-option').forEach(opt => {
                    const optValue = parseInt(opt.querySelector('input').value);
                    opt.classList.toggle('selected', optValue === value);
                });
            }
        });

        // Sliders
        containerEl.addEventListener('input', (e) => {
            if (e.target.classList.contains('slider-input')) {
                const container = e.target.closest('.slider-container');
                const qid = container.dataset.id;
                const value = parseFloat(e.target.value);
                const min = parseFloat(e.target.min);
                const max = parseFloat(e.target.max);
                
                responses[qid] = value;
                
                // Update visual
                container.querySelector('.value-display').textContent = value;
                container.querySelector('.slider-fill').style.width = 
                    `${((value - min) / (max - min)) * 100}%`;
            }
        });

        // Dropdowns
        containerEl.addEventListener('change', (e) => {
            if (e.target.classList.contains('dropdown-select')) {
                responses[e.target.name] = e.target.value ? parseInt(e.target.value) : null;
            }
        });

        // Textareas
        containerEl.addEventListener('input', (e) => {
            if (e.target.classList.contains('textarea-input')) {
                const name = e.target.name;
                const value = e.target.value;
                
                responses[name] = value;
                
                // Update character count
                const counter = e.target.closest('.textarea-container').querySelector('.char-count');
                if (counter) counter.textContent = value.length;
                
                // Debounced sentiment preview (would need API call)
                // For now, show basic feedback
                updateSentimentPreview(name, value);
            }
        });
    }

    function updateSentimentPreview(qid, text) {
        const sentimentEl = document.getElementById(`sentiment-${qid}`);
        if (!sentimentEl || !text.trim()) {
            if (sentimentEl) sentimentEl.innerHTML = '';
            return;
        }
        
        // Simple client-side sentiment indicators
        const negativeWords = ['sad', 'anxious', 'depressed', 'hopeless', 'worried', 'tired', 'stressed'];
        const positiveWords = ['good', 'happy', 'hopeful', 'better', 'improving', 'grateful'];
        
        const textLower = text.toLowerCase();
        const hasNegative = negativeWords.some(w => textLower.includes(w));
        const hasPositive = positiveWords.some(w => textLower.includes(w));
        
        let indicator = '';
        if (hasNegative && !hasPositive) {
            indicator = '<span class="sentiment-negative">We hear you ❤️</span>';
        } else if (hasPositive && !hasNegative) {
            indicator = '<span class="sentiment-positive">That\'s great to hear! ✨</span>';
        } else if (text.length > 50) {
            indicator = '<span class="sentiment-neutral">Thank you for sharing</span>';
        }
        
        sentimentEl.innerHTML = indicator;
    }

    // ========================================================================
    // Validation
    // ========================================================================

    function validateCurrentSection() {
        const sections = schema.sections || [];
        const section = sections[currentSection];
        if (!section) return true;

        let isValid = true;
        const errors = [];

        section.questions.forEach(q => {
            if (q.required) {
                const value = responses[q.id];
                if (value === undefined || value === null || value === '') {
                    isValid = false;
                    errors.push(q.text);
                    
                    // Highlight the question
                    const questionEl = containerEl.querySelector(`.question[data-question="${q.id}"]`);
                    if (questionEl) {
                        questionEl.classList.add('error');
                        setTimeout(() => questionEl.classList.remove('error'), 3000);
                    }
                }
            }
        });

        if (!isValid) {
            showError(`Please answer: ${errors.slice(0, 2).join(', ')}${errors.length > 2 ? '...' : ''}`);
        }

        return isValid;
    }

    function showError(message) {
        const existing = containerEl.querySelector('.survey-error-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'survey-error-toast';
        toast.innerHTML = `
            <span class="error-icon">⚠</span>
            <span class="error-text">${message}</span>
        `;
        
        containerEl.querySelector('.survey-navigation').before(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    // ========================================================================
    // Submission
    // ========================================================================

    async function handleSubmit() {
        if (isSubmitting) return;
        if (!validateCurrentSection()) return;

        isSubmitting = true;
        
        const submitBtn = containerEl.querySelector('.survey-submit');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Analyzing...';
        }

        // Collect all responses
        collectAllResponses();

        // Separate free text from structured responses
        const freeTextFields = ['free_text_main', 'free_text_coping'];
        const freeText = freeTextFields
            .map(f => responses[f] || '')
            .filter(t => t.trim())
            .join('\n\n');
        
        const structuredResponses = {};
        for (const [key, value] of Object.entries(responses)) {
            if (!freeTextFields.includes(key)) {
                structuredResponses[key] = value;
            }
        }

        try {
            // Call KERNEL API
            const result = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    responses: structuredResponses,
                    free_text: freeText,
                    user_id: WallsAPI?.getUserId() || 'anonymous',
                    save: true,
                    mc_samples: 15  // More samples for better uncertainty
                })
            });

            if (!result.ok) {
                throw new Error(`API error: ${result.status}`);
            }

            const data = await result.json();
            console.log('[KernelSurvey] Result:', data);

            // Dispatch event for visualizations
            window.dispatchEvent(new CustomEvent('kernel:prediction', { detail: data }));

            // Save locally
            if (window.WallsAPI) {
                WallsAPI.saveLocalEntry({
                    timestamp: new Date().toISOString(),
                    responses: structuredResponses,
                    free_text: freeText,
                    result: data
                });
            }

            // Show success and redirect
            showSuccess(data);

            // Call callback
            if (onCompleteCallback) {
                onCompleteCallback(data, structuredResponses, freeText);
            }

        } catch (error) {
            console.error('[KernelSurvey] Submit error:', error);
            showError('Failed to analyze responses. Please try again.');
            
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Analyze My Responses';
            }
        } finally {
            isSubmitting = false;
        }
    }

    function collectAllResponses() {
        containerEl.querySelectorAll('input, select, textarea').forEach(el => {
            if (!el.name) return;
            
            if (el.type === 'radio') {
                if (el.checked) {
                    responses[el.name] = parseInt(el.value);
                }
            } else if (el.type === 'range') {
                responses[el.name] = parseFloat(el.value);
            } else if (el.tagName === 'SELECT') {
                responses[el.name] = el.value ? parseInt(el.value) : null;
            } else {
                responses[el.name] = el.value;
            }
        });
    }

    function showSuccess(data) {
        const scores = data.scores || {};
        
        containerEl.innerHTML = `
            <div class="survey-success">
                <div class="success-header">
                    <div class="success-icon">✓</div>
                    <h2>Assessment Complete</h2>
                    <p>Here's a summary of your results</p>
                </div>

                <div class="success-scores">
                    ${renderScoreCard('Stress', scores.stress, '#ff6b6b', '0-100')}
                    ${renderScoreCard('Depression', scores.depression, '#8b5cf6', 'PHQ-9')}
                    ${renderScoreCard('Anxiety', scores.anxiety, '#00d4aa', 'GAD-7')}
                    ${renderScoreCard('Sleep', scores.sleep_quality, '#3b82f6', '0-10')}
                    ${renderScoreCard('Wellbeing', scores.wellbeing, '#fbbf24', '0-100')}
                </div>

                ${data.flags?.length ? `
                    <div class="success-flags">
                        ${data.flags.map(f => `<span class="flag">${f}</span>`).join('')}
                    </div>
                ` : ''}

                ${data.text_analysis ? `
                    <div class="success-text-analysis">
                        <h3>Text Analysis</h3>
                        <div class="sentiment-bar">
                            <span class="positive" style="width: ${data.text_analysis.sentiment.positive * 100}%"></span>
                            <span class="neutral" style="width: ${data.text_analysis.sentiment.neutral * 100}%"></span>
                            <span class="negative" style="width: ${data.text_analysis.sentiment.negative * 100}%"></span>
                        </div>
                    </div>
                ` : ''}

                <div class="success-redirect">
                    <p>Redirecting to your dashboard in <span id="countdown">3</span> seconds...</p>
                    <div class="redirect-progress">
                        <div class="redirect-bar"></div>
                    </div>
                </div>

                <div class="success-actions">
                    <a href="/dashboard" class="btn btn-primary">View Full Analysis →</a>
                    <button type="button" class="btn btn-ghost" onclick="KernelSurvey.reset()">Take Another Assessment</button>
                </div>
            </div>
        `;

        // Auto-redirect
        let countdown = 3;
        const countdownEl = document.getElementById('countdown');
        const redirectBar = containerEl.querySelector('.redirect-bar');
        
        if (redirectBar) {
            redirectBar.style.transition = 'width 3s linear';
            redirectBar.style.width = '100%';
        }
        
        const timer = setInterval(() => {
            countdown--;
            if (countdownEl) countdownEl.textContent = countdown;
            
            if (countdown <= 0) {
                clearInterval(timer);
                window.location.href = '/dashboard';
            }
        }, 1000);
    }

    function renderScoreCard(label, score, color, scale) {
        if (!score) return '';
        
        return `
            <div class="score-card" style="--accent: ${color}">
                <div class="score-header">
                    <span class="score-label">${label}</span>
                    <span class="score-scale">${scale}</span>
                </div>
                <div class="score-value">
                    ${score.mean.toFixed(1)}
                    <span class="score-uncertainty">± ${score.std.toFixed(1)}</span>
                </div>
                <div class="score-ci">
                    95% CI: [${score.ci_lower.toFixed(1)}, ${score.ci_upper.toFixed(1)}]
                </div>
            </div>
        `;
    }

    // ========================================================================
    // Public API
    // ========================================================================

    function reset() {
        responses = {};
        currentSection = 0;
        if (schema) {
            render();
            bindEvents();
        }
    }

    function getResponses() {
        collectAllResponses();
        return { ...responses };
    }

    return {
        init,
        reset,
        getResponses
    };
})();

// Export globally
window.KernelSurvey = KernelSurvey;

