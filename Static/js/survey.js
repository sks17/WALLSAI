/**
 * WALLS Dynamic Survey Module
 * 
 * Handles dynamic survey rendering with multiple input types:
 * - Sliders (0-4 scale)
 * - Dropdowns
 * - Yes/No toggles
 * - Free-form text
 * 
 * Serializes responses and submits to ML inference API.
 */

const WallsSurvey = (function() {
    'use strict';

    // ========================================================================
    // Survey Question Definitions
    // ========================================================================

    // Survey questions mapped to CORRECT schema.json features
    // These match the PyTorch model trained on Static/Data/dataset.csv
    // Features: feeling.nervous, panic, breathing.rapidly, sweating, trouble.in.concentration,
    // having.trouble.in.sleeping, having.trouble.with.work, hopelessness, anger, over.react,
    // change.in.eating, suicidal.thought, feeling.tired, close.friend, social.media.addiction,
    // weight.gain, material.possessions, introvert, popping.up.stressful.memory, having.nightmares,
    // avoids.people.or.activities, feeling.negative, trouble.concentrating, blamming.yourself
    
    // IMPORTANT: Questions use non-clinical, liability-safe phrasing
    // WALLS provides reflective insights, not medical guidance
    
    const DEFAULT_TOOLTIP = "Your answers help WALLS reflect patterns, not evaluate medical conditions.";
    const SLIDER_TOOLTIP = "This slider helps WALLS understand intensity rather than simple yes/no responses.";
    
    // Slider labels for 0-100 scale
    const INTENSITY_LABELS = {
        0: "Not at all",
        25: "Slightly",
        50: "Moderately", 
        75: "Very",
        100: "Extremely"
    };
    
    const SURVEY_SECTIONS = [
        {
            id: 'physical_responses',
            title: 'Physical Responses',
            description: 'Reflect on any physical sensations you\'ve noticed recently.',
            questions: [
                {
                    id: 'feeling.nervous',
                    label: 'Recently, have you noticed yourself leaning toward feelings of unease or nervousness?',
                    type: 'yesno',
                    required: true,
                    tooltip: DEFAULT_TOOLTIP
                },
                {
                    id: 'panic',
                    label: 'Recently, have you experienced moments of sudden, intense discomfort or overwhelm?',
                    type: 'yesno',
                    required: true,
                    tooltip: "This reflects personal experience, not a clinical evaluation."
                },
                {
                    id: 'breathing.rapidly',
                    label: 'Recently, have you found your breathing becoming quicker or shallower during certain moments?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Breathing patterns vary naturally and are not diagnostic."
                },
                {
                    id: 'sweating',
                    label: 'Recently, have you noticed increased perspiration during times of stress or discomfort?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Physical responses are personal and vary widely."
                }
            ]
        },
        {
            id: 'emotional_patterns',
            title: 'Emotional Patterns',
            description: 'Reflect on your recent emotional experiences.',
            questions: [
                {
                    // SLIDER QUESTION 1: Hopelessness/Motivation (intensity matters)
                    id: 'hopelessness',
                    label: 'How much have you been experiencing feelings of reduced optimism or motivation recently?',
                    type: 'intensity_slider',
                    min: 0,
                    max: 100,
                    defaultValue: 25,
                    required: true,
                    tooltip: SLIDER_TOOLTIP,
                    sliderHelp: "Drag the slider to indicate intensity. 0 = Not at all, 100 = Extremely."
                },
                {
                    id: 'feeling.negative',
                    label: 'Recently, have you noticed a tendency toward less positive thoughts?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Thought patterns shift based on circumstances."
                },
                {
                    id: 'blamming.yourself',
                    label: 'Recently, have you been inclined to be harder on yourself than usual?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Self-perception fluctuates and is influenced by many factors."
                },
                {
                    id: 'suicidal.thought',
                    label: 'Recently, have you had thoughts about not wanting to continue or feeling like a burden?',
                    type: 'yesno',
                    required: true,
                    tooltip: "If you're struggling, please reach out to a crisis helpline: 988",
                    isSensitive: true
                },
                {
                    // SLIDER QUESTION 2: Anger/Irritability (intensity matters)
                    id: 'anger',
                    label: 'How much frustration or irritability have you been experiencing recently?',
                    type: 'intensity_slider',
                    min: 0,
                    max: 100,
                    defaultValue: 25,
                    required: true,
                    tooltip: SLIDER_TOOLTIP,
                    sliderHelp: "Drag the slider to indicate intensity. 0 = Not at all, 100 = Extremely."
                },
                {
                    id: 'over.react',
                    label: 'Recently, have you felt your emotional responses may be stronger than usual?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Reaction intensity varies based on circumstances."
                }
            ]
        },
        {
            id: 'daily_experience',
            title: 'Daily Experience',
            description: 'Reflect on how your typical day has felt recently.',
            questions: [
                {
                    id: 'trouble.in.concentration',
                    label: 'Recently, have you found it more challenging to maintain focus on tasks?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Concentration varies due to many factors."
                },
                {
                    id: 'trouble.concentrating',
                    label: 'Recently, have you found your mind wandering more than usual?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Focus varies based on many life factors."
                },
                {
                    id: 'having.trouble.with.work',
                    label: 'Recently, have you found daily tasks or responsibilities feeling more demanding?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Work-related feelings reflect personal circumstances."
                },
                {
                    // SLIDER QUESTION 3: Energy/Fatigue (intensity matters)
                    id: 'feeling.tired',
                    label: 'How much fatigue or low energy have you been experiencing recently?',
                    type: 'intensity_slider',
                    min: 0,
                    max: 100,
                    defaultValue: 25,
                    required: true,
                    tooltip: SLIDER_TOOLTIP,
                    sliderHelp: "Drag the slider to indicate intensity. 0 = Not at all, 100 = Extremely."
                }
            ]
        },
        {
            id: 'rest_patterns',
            title: 'Rest & Relaxation',
            description: 'Reflect on your sleep and stress patterns.',
            questions: [
                {
                    id: 'having.trouble.in.sleeping',
                    label: 'Recently, have you experienced changes in your sleep patterns or difficulty resting?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Sleep quality is influenced by many lifestyle factors."
                },
                {
                    id: 'having.nightmares',
                    label: 'Recently, have you experienced disturbing dreams or disrupted sleep?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Dream content varies and has many influences."
                },
                {
                    id: 'popping.up.stressful.memory',
                    label: 'Recently, have unwanted memories or thoughts surfaced unexpectedly?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Memory patterns are personal experiences."
                }
            ]
        },
        {
            id: 'social_connection',
            title: 'Social Connection',
            description: 'Reflect on your social interactions and preferences.',
            questions: [
                {
                    id: 'avoids.people.or.activities',
                    label: 'Recently, have you felt inclined to withdraw from social situations or activities?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Social needs vary from person to person."
                },
                {
                    id: 'introvert',
                    label: 'Do you generally prefer quieter environments or smaller social settings?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Social preferences are personal traits, not problems."
                },
                {
                    id: 'close.friend',
                    label: 'Do you currently have someone you feel comfortable confiding in?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Social connection is an important aspect of wellbeing."
                },
                {
                    id: 'social.media.addiction',
                    label: 'Recently, have you found yourself spending more time on social media than intended?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Digital habits vary and evolve over time."
                }
            ]
        },
        {
            id: 'lifestyle_patterns',
            title: 'Lifestyle Patterns',
            description: 'Reflect on changes in your daily habits.',
            questions: [
                {
                    id: 'change.in.eating',
                    label: 'Recently, have you noticed shifts in your appetite or eating patterns?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Eating patterns change due to many factors."
                },
                {
                    id: 'weight.gain',
                    label: 'Recently, have you noticed unintended changes in your weight?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Weight fluctuations are influenced by many factors."
                },
                {
                    id: 'material.possessions',
                    label: 'Do you find comfort or identity closely tied to material belongings?',
                    type: 'yesno',
                    required: true,
                    tooltip: "Values and priorities are personal and valid."
                }
            ]
        },
        {
            id: 'free_response',
            title: 'Additional Reflections',
            description: 'Share anything else you\'d like WALLS to consider.',
            questions: [
                {
                    id: 'free_text',
                    label: 'Is there anything else on your mind? (Optional)',
                    type: 'textarea',
                    placeholder: 'Share your thoughts or feelings. Remember: WALLS provides reflections, not diagnosis or treatment advice.',
                    maxLength: 1000,
                    required: false,
                    securityNote: true
                },
                {
                    id: 'wellbeing_influences',
                    label: 'In your own words, describe anything that has been influencing your wellbeing recently.',
                    type: 'textarea',
                    placeholder: 'Examples: work stress, relationships, health concerns, positive changes, goals achieved... Share what feels relevant.',
                    maxLength: 1500,
                    required: false,
                    securityNote: true,
                    processWithKernel: true,
                    tooltip: "This open reflection helps WALLS understand context beyond structured questions."
                }
            ]
        }
    ];

    // ========================================================================
    // State
    // ========================================================================

    let responses = {};
    let currentSection = 0;
    let containerEl = null;
    let onSubmitCallback = null;
    let isSubmitting = false;

    // ========================================================================
    // Rendering Functions
    // ========================================================================

    /**
     * Initialize the survey in a container element
     */
    function init(containerId, options = {}) {
        containerEl = document.getElementById(containerId);
        if (!containerEl) {
            console.error('[Survey] Container not found:', containerId);
            return;
        }

        onSubmitCallback = options.onSubmit || null;
        responses = {};
        currentSection = 0;

        render();
        bindEvents();
    }

    /**
     * Render the entire survey
     */
    function render() {
        if (!containerEl) return;

        containerEl.innerHTML = `
            <div class="survey-container">
                <div class="survey-progress">
                    ${renderProgressBar()}
                </div>
                <div class="survey-sections">
                    ${SURVEY_SECTIONS.map((section, idx) => renderSection(section, idx)).join('')}
                </div>
                <div class="survey-navigation">
                    <button type="button" class="btn btn-ghost survey-nav-prev" ${currentSection === 0 ? 'disabled' : ''}>
                        ← Previous
                    </button>
                    <span class="survey-nav-indicator">
                        ${currentSection + 1} of ${SURVEY_SECTIONS.length}
                    </span>
                    ${currentSection === SURVEY_SECTIONS.length - 1 
                        ? `<button type="button" class="btn btn-primary survey-submit">
                             Analyze My Responses →
                           </button>`
                        : `<button type="button" class="btn btn-primary survey-nav-next">
                             Next →
                           </button>`
                    }
                </div>
            </div>
        `;

        // Show current section
        showSection(currentSection);
    }

    /**
     * Render progress bar
     */
    function renderProgressBar() {
        const progress = ((currentSection + 1) / SURVEY_SECTIONS.length) * 100;
        return `
            <div class="survey-progress-bar">
                <div class="survey-progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="survey-progress-steps">
                ${SURVEY_SECTIONS.map((section, idx) => `
                    <div class="survey-progress-step ${idx <= currentSection ? 'active' : ''} ${idx < currentSection ? 'completed' : ''}"
                         data-section="${idx}">
                        <span class="step-number">${idx + 1}</span>
                        <span class="step-label">${section.title}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Render a survey section
     */
    function renderSection(section, idx) {
        const isLastSection = idx === SURVEY_SECTIONS.length - 1;
        
        return `
            <div class="survey-section" data-section="${idx}" ${idx !== currentSection ? 'hidden' : ''}>
                <div class="survey-section-header">
                    <h2 class="survey-section-title">${section.title}</h2>
                    <p class="survey-section-desc">${section.description}</p>
                </div>
                <div class="survey-questions">
                    ${section.questions.map(q => renderQuestion(q)).join('')}
                </div>
                ${isLastSection ? `
                    <div class="survey-section-submit">
                        <button type="button" class="btn btn-primary btn-large survey-submit-inline">
                            <span class="btn-icon">✓</span>
                            Submit & Analyze My Responses
                        </button>
                        <p class="survey-submit-hint">Your responses will be analyzed by our AI to provide personalized insights.</p>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render a single question based on type
     */
    function renderQuestion(q) {
        let input = '';
        const value = responses[q.id];

        switch (q.type) {
            case 'slider':
                input = renderSlider(q, value);
                break;
            case 'intensity_slider':
                input = renderIntensitySlider(q, value);
                break;
            case 'dropdown':
                input = renderDropdown(q, value);
                break;
            case 'yesno':
                input = renderYesNo(q, value);
                break;
            case 'textarea':
                input = renderTextarea(q, value);
                break;
            default:
                input = `<input type="text" name="${q.id}" value="${value || ''}">`;
        }

        // Build tooltip HTML
        const tooltipHtml = q.tooltip ? `
            <span class="question-tooltip" tabindex="0" aria-label="${q.tooltip}">
                <span class="question-tooltip-icon">?</span>
                <span class="question-tooltip-text">${q.tooltip}</span>
            </span>
        ` : '';

        // Sensitive question warning
        const sensitiveHtml = q.isSensitive ? `
            <div class="sensitive-warning">
                <span class="warning-icon">💙</span>
                <span>If you're struggling, help is available: 
                    <a href="tel:988" class="crisis-inline">Call 988</a> or 
                    <a href="sms:741741?body=HELLO" class="crisis-inline">Text HOME to 741741</a>
                </span>
            </div>
        ` : '';

        // Security note for free text
        const securityNoteHtml = q.securityNote ? `
            <div class="security-note">
                <strong>🔒 Privacy note:</strong> Free-text inputs are analyzed to detect patterns, 
                but WALLS does not store or infer identifiable personal information. 
                Avoid including personal names, addresses, or identifying details.
            </div>
        ` : '';

        // Slider type indicator
        const sliderTypeClass = q.type === 'intensity_slider' ? 'question-slider' : '';

        return `
            <div class="survey-question ${q.isSensitive ? 'question-sensitive' : ''} ${sliderTypeClass}" data-question="${q.id}">
                <label class="survey-question-label">
                    ${q.label}
                    ${q.required ? '<span class="required">*</span>' : ''}
                    ${tooltipHtml}
                </label>
                ${sensitiveHtml}
                <div class="survey-question-input">
                    ${input}
                </div>
                ${securityNoteHtml}
            </div>
        `;
    }

    /**
     * Render slider input (0-4 scale)
     */
    function renderSlider(q, value) {
        const currentValue = value !== undefined ? value : 2;
        return `
            <div class="survey-slider" data-id="${q.id}">
                <input type="range" 
                       name="${q.id}" 
                       min="${q.min}" 
                       max="${q.max}" 
                       value="${currentValue}"
                       class="survey-slider-input">
                <div class="survey-slider-labels">
                    ${q.labels.map((label, idx) => `
                        <span class="survey-slider-label ${idx === currentValue ? 'active' : ''}" 
                              data-value="${idx}">${label}</span>
                    `).join('')}
                </div>
                <div class="survey-slider-value">${q.labels[currentValue]}</div>
            </div>
        `;
    }

    /**
     * Render intensity slider (0-100 scale)
     * Used for emotional intensity questions
     */
    function renderIntensitySlider(q, value) {
        const currentValue = value !== undefined ? value : (q.defaultValue || 25);
        const intensityLabel = getIntensityLabel(currentValue);
        
        return `
            <div class="survey-intensity-slider" data-id="${q.id}">
                <div class="intensity-slider-container">
                    <input type="range" 
                           name="${q.id}" 
                           min="${q.min || 0}" 
                           max="${q.max || 100}" 
                           value="${currentValue}"
                           step="1"
                           class="intensity-slider-input"
                           aria-label="${q.label}"
                           aria-valuemin="${q.min || 0}"
                           aria-valuemax="${q.max || 100}"
                           aria-valuenow="${currentValue}"
                           aria-valuetext="${intensityLabel}">
                    <div class="intensity-track">
                        <div class="intensity-fill" style="width: ${currentValue}%"></div>
                    </div>
                </div>
                <div class="intensity-labels">
                    <span class="intensity-label-min">Not at all</span>
                    <span class="intensity-label-max">Extremely</span>
                </div>
                <div class="intensity-value-display">
                    <span class="intensity-number">${currentValue}</span>
                    <span class="intensity-label">${intensityLabel}</span>
                </div>
                ${q.sliderHelp ? `<p class="slider-help-text">${q.sliderHelp}</p>` : ''}
            </div>
        `;
    }

    /**
     * Get intensity label from value (0-100)
     */
    function getIntensityLabel(value) {
        if (value === 0) return "Not at all";
        if (value <= 20) return "Slightly";
        if (value <= 40) return "Somewhat";
        if (value <= 60) return "Moderately";
        if (value <= 80) return "Very";
        return "Extremely";
    }

    /**
     * Render dropdown input
     */
    function renderDropdown(q, value) {
        return `
            <select name="${q.id}" class="survey-select" ${q.required ? 'required' : ''}>
                <option value="" ${!value ? 'selected' : ''}>Select an option...</option>
                ${q.options.map(opt => `
                    <option value="${opt}" ${value === opt ? 'selected' : ''}>${opt}</option>
                `).join('')}
            </select>
        `;
    }

    /**
     * Render yes/no toggle
     */
    function renderYesNo(q, value) {
        return `
            <div class="survey-yesno" data-id="${q.id}">
                <button type="button" 
                        class="survey-yesno-btn ${value === 'Yes' ? 'active' : ''}" 
                        data-value="Yes">
                    Yes
                </button>
                <button type="button" 
                        class="survey-yesno-btn ${value === 'No' ? 'active' : ''}" 
                        data-value="No">
                    No
                </button>
                <input type="hidden" name="${q.id}" value="${value || ''}">
            </div>
        `;
    }

    /**
     * Render textarea
     */
    function renderTextarea(q, value) {
        return `
            <textarea name="${q.id}" 
                      class="survey-textarea" 
                      placeholder="${q.placeholder || ''}"
                      maxlength="${q.maxLength || 1000}"
                      rows="4">${value || ''}</textarea>
            <div class="survey-textarea-counter">
                <span class="char-count">${(value || '').length}</span> / ${q.maxLength || 1000}
            </div>
        `;
    }

    // ========================================================================
    // Navigation
    // ========================================================================

    function showSection(idx) {
        if (idx < 0 || idx >= SURVEY_SECTIONS.length) return;

        currentSection = idx;
        
        // Hide all sections
        containerEl.querySelectorAll('.survey-section').forEach(el => {
            el.hidden = true;
        });

        // Show current section
        const currentEl = containerEl.querySelector(`.survey-section[data-section="${idx}"]`);
        if (currentEl) {
            currentEl.hidden = false;
            currentEl.classList.add('fade-in');
        }

        // Update progress
        const progressFill = containerEl.querySelector('.survey-progress-fill');
        if (progressFill) {
            progressFill.style.width = `${((idx + 1) / SURVEY_SECTIONS.length) * 100}%`;
        }

        // Update step indicators
        containerEl.querySelectorAll('.survey-progress-step').forEach((step, i) => {
            step.classList.toggle('active', i <= idx);
            step.classList.toggle('completed', i < idx);
        });

        // Update navigation buttons
        const prevBtn = containerEl.querySelector('.survey-nav-prev');
        const nextBtn = containerEl.querySelector('.survey-nav-next');
        const submitBtn = containerEl.querySelector('.survey-submit');
        const indicator = containerEl.querySelector('.survey-nav-indicator');

        if (prevBtn) prevBtn.disabled = idx === 0;
        if (indicator) indicator.textContent = `${idx + 1} of ${SURVEY_SECTIONS.length}`;

        // Swap next/submit buttons
        if (idx === SURVEY_SECTIONS.length - 1) {
            if (nextBtn) nextBtn.style.display = 'none';
            if (submitBtn) submitBtn.style.display = 'inline-flex';
        } else {
            if (nextBtn) nextBtn.style.display = 'inline-flex';
            if (submitBtn) submitBtn.style.display = 'none';
        }
    }

    function nextSection() {
        if (validateCurrentSection()) {
            showSection(currentSection + 1);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    function prevSection() {
        showSection(currentSection - 1);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ========================================================================
    // Event Binding
    // ========================================================================

    function bindEvents() {
        if (!containerEl) return;

        // Navigation
        containerEl.addEventListener('click', (e) => {
            if (e.target.closest('.survey-nav-next')) {
                nextSection();
            } else if (e.target.closest('.survey-nav-prev')) {
                prevSection();
            } else if (e.target.closest('.survey-submit') || e.target.closest('.survey-submit-inline')) {
                handleSubmit();
            } else if (e.target.closest('.survey-progress-step')) {
                const stepIdx = parseInt(e.target.closest('.survey-progress-step').dataset.section);
                if (stepIdx < currentSection) {
                    showSection(stepIdx);
                }
            }
        });

        // Yes/No buttons
        containerEl.addEventListener('click', (e) => {
            const btn = e.target.closest('.survey-yesno-btn');
            if (btn) {
                const container = btn.closest('.survey-yesno');
                const id = container.dataset.id;
                const value = btn.dataset.value;
                
                container.querySelectorAll('.survey-yesno-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                container.querySelector('input[type="hidden"]').value = value;
                responses[id] = value;
            }
        });

        // Sliders (original 0-4 scale)
        containerEl.addEventListener('input', (e) => {
            if (e.target.classList.contains('survey-slider-input')) {
                const slider = e.target.closest('.survey-slider');
                const id = slider.dataset.id;
                const value = parseInt(e.target.value);
                const question = SURVEY_SECTIONS.flatMap(s => s.questions).find(q => q.id === id);
                
                if (question && question.labels) {
                    slider.querySelector('.survey-slider-value').textContent = question.labels[value];
                    slider.querySelectorAll('.survey-slider-label').forEach((label, idx) => {
                        label.classList.toggle('active', idx === value);
                    });
                }
                
                responses[id] = value;
            }
        });

        // Intensity Sliders (0-100 scale)
        containerEl.addEventListener('input', (e) => {
            if (e.target.classList.contains('intensity-slider-input')) {
                const container = e.target.closest('.survey-intensity-slider');
                const id = container.dataset.id;
                const value = parseInt(e.target.value);
                
                // Update visual elements
                const fill = container.querySelector('.intensity-fill');
                const numberEl = container.querySelector('.intensity-number');
                const labelEl = container.querySelector('.intensity-label');
                
                if (fill) fill.style.width = `${value}%`;
                if (numberEl) numberEl.textContent = value;
                if (labelEl) labelEl.textContent = getIntensityLabel(value);
                
                // Update ARIA
                e.target.setAttribute('aria-valuenow', value);
                e.target.setAttribute('aria-valuetext', getIntensityLabel(value));
                
                responses[id] = value;
            }
        });

        // Dropdowns and other inputs
        containerEl.addEventListener('change', (e) => {
            if (e.target.name) {
                responses[e.target.name] = e.target.value;
            }
        });

        // Textarea character counter
        containerEl.addEventListener('input', (e) => {
            if (e.target.classList.contains('survey-textarea')) {
                const counter = e.target.closest('.survey-question-input').querySelector('.char-count');
                if (counter) {
                    counter.textContent = e.target.value.length;
                }
                responses[e.target.name] = e.target.value;
            }
        });
    }

    // ========================================================================
    // Validation
    // ========================================================================

    function validateCurrentSection() {
        const section = SURVEY_SECTIONS[currentSection];
        let isValid = true;
        const errors = [];

        section.questions.forEach(q => {
            if (q.required) {
                const value = responses[q.id];
                if (value === undefined || value === '' || value === null) {
                    isValid = false;
                    errors.push(q.label);
                    
                    // Highlight the question
                    const questionEl = containerEl.querySelector(`.survey-question[data-question="${q.id}"]`);
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
        // Remove existing error
        const existing = containerEl.querySelector('.survey-error');
        if (existing) existing.remove();

        const errorEl = document.createElement('div');
        errorEl.className = 'survey-error';
        errorEl.innerHTML = `
            <span class="error-icon">⚠</span>
            <span class="error-text">${message}</span>
        `;
        
        const nav = containerEl.querySelector('.survey-navigation');
        nav.parentNode.insertBefore(errorEl, nav);

        setTimeout(() => errorEl.remove(), 5000);
    }

    // ========================================================================
    // Submission
    // ========================================================================

    async function handleSubmit() {
        if (isSubmitting) return;
        if (!validateCurrentSection()) return;

        isSubmitting = true;
        
        // Disable both submit buttons (nav and inline)
        const submitBtns = containerEl.querySelectorAll('.survey-submit, .survey-submit-inline');
        submitBtns.forEach(btn => {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Analyzing...';
        });

        // Collect all responses
        collectAllResponses();

        // Separate free text fields from features
        const freeText = responses.free_text || '';
        const wellbeingInfluences = responses.wellbeing_influences || '';
        
        // Combine both text fields for KERNEL processing
        const combinedFreeText = [freeText, wellbeingInfluences].filter(t => t.trim()).join('\n\n');
        
        const features = { ...responses };
        delete features.free_text;
        delete features.wellbeing_influences;

        // Map slider values to categorical where needed
        const mappedFeatures = mapFeaturesToMLFormat(features);

        try {
            // Call ML inference API with combined free text
            // Uses Firebase UID for account-based persistence
            const result = await WallsAPI.predict(mappedFeatures, combinedFreeText, WallsAPI.getUserId());

            // Note: Data is saved to Firestore automatically by WallsAPI.predict()
            // New users start with empty history

            // Call success callback
            if (onSubmitCallback) {
                onSubmitCallback(result, mappedFeatures, freeText);
            }

            // Show success state with auto-redirect
            showSuccess(result, true);

        } catch (error) {
            console.error('[Survey] Submission error:', error);
            showError('Failed to analyze responses. Please try again.');
            submitBtns.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = 'Submit & Analyze My Responses';
            });
        } finally {
            isSubmitting = false;
        }
    }

    function collectAllResponses() {
        // Collect any values not yet captured
        containerEl.querySelectorAll('input, select, textarea').forEach(el => {
            if (el.name && el.value !== undefined) {
                if (el.type === 'range') {
                    responses[el.name] = parseInt(el.value);
                } else {
                    responses[el.name] = el.value;
                }
            }
        });
    }

    function mapFeaturesToMLFormat(features) {
        const mapped = {};
        
        // Questions that use intensity sliders (0-100 scale)
        const sliderQuestions = ['hopelessness', 'anger', 'feeling.tired'];
        
        // The PyTorch model expects lowercase "yes"/"no" values
        // For slider questions, we convert intensity to yes/no for backwards compatibility
        // Threshold: >= 50 = "yes", < 50 = "no"
        for (const [key, value] of Object.entries(features)) {
            // Skip free_text fields, they're handled separately
            if (key === 'free_text' || key === 'wellbeing_influences') {
                continue;
            }
            
            // Handle intensity slider values (0-100) -> yes/no conversion
            if (sliderQuestions.includes(key) && typeof value === 'number') {
                // Store raw intensity for KERNEL processing
                mapped[`${key}_intensity`] = value;
                // Convert to yes/no for PyTorch model compatibility
                mapped[key] = value >= 50 ? 'yes' : 'no';
                continue;
            }
            
            // Convert Yes/No to lowercase for the model
            if (value === 'Yes' || value === 'yes' || value === true) {
                mapped[key] = 'yes';
            } else if (value === 'No' || value === 'no' || value === false) {
                mapped[key] = 'no';
            } else {
                // Keep other values as-is
                mapped[key] = value;
            }
        }

        return mapped;
    }

    function showSuccess(result, autoRedirect = false) {
        const scores = result.scores || {};
        const stress = scores.stress_score?.toFixed(1) || 'N/A';
        const depression = scores.depression_score?.toFixed(1) || 'N/A';
        const anxiety = scores.anxiety_score?.toFixed(1) || 'N/A';
        const sleep = scores.sleep_quality?.toFixed(1) || 'N/A';
        
        containerEl.innerHTML = `
            <div class="survey-success">
                <div class="success-icon">✓</div>
                <h2>Analysis Complete</h2>
                <p>Your responses have been analyzed by our AI.</p>
                
                <div class="success-scores">
                    <div class="score-item score-item--stress">
                        <span class="score-label">Stress</span>
                        <span class="score-value">${stress}</span>
                    </div>
                    <div class="score-item score-item--depression">
                        <span class="score-label">Depression</span>
                        <span class="score-value">${depression}</span>
                    </div>
                    <div class="score-item score-item--anxiety">
                        <span class="score-label">Anxiety</span>
                        <span class="score-value">${anxiety}</span>
                    </div>
                    <div class="score-item score-item--sleep">
                        <span class="score-label">Sleep</span>
                        <span class="score-value">${sleep}</span>
                    </div>
                </div>

                <div class="success-redirect" id="redirect-message">
                    <p class="redirect-text">Redirecting to your dashboard in <span id="countdown">3</span> seconds...</p>
                    <div class="redirect-progress">
                        <div class="redirect-progress-bar" id="redirect-bar"></div>
                    </div>
                </div>

                <div class="success-actions">
                    <a href="/dashboard" class="btn btn-primary" id="view-dashboard-btn">View Full Analysis Now →</a>
                    <button type="button" class="btn btn-ghost" onclick="WallsSurvey.reset()">Take Another Survey</button>
                </div>
            </div>
        `;

        // Auto-redirect countdown
        if (autoRedirect) {
            let countdown = 3;
            const countdownEl = document.getElementById('countdown');
            const progressBar = document.getElementById('redirect-bar');
            
            // Start progress bar animation
            if (progressBar) {
                progressBar.style.transition = 'width 3s linear';
                progressBar.style.width = '100%';
            }
            
            const timer = setInterval(() => {
                countdown--;
                if (countdownEl) {
                    countdownEl.textContent = countdown;
                }
                
                if (countdown <= 0) {
                    clearInterval(timer);
                    // Redirect to dashboard
                    window.location.href = '/dashboard';
                }
            }, 1000);

            // Allow clicking the button to go immediately
            const dashBtn = document.getElementById('view-dashboard-btn');
            if (dashBtn) {
                dashBtn.addEventListener('click', (e) => {
                    clearInterval(timer);
                });
            }
        }
    }

    // ========================================================================
    // Public API
    // ========================================================================

    function reset() {
        responses = {};
        currentSection = 0;
        render();
        bindEvents();
    }

    function getResponses() {
        collectAllResponses();
        return { ...responses };
    }

    return {
        init,
        reset,
        getResponses,
        SURVEY_SECTIONS
    };
})();

// Make available globally
window.WallsSurvey = WallsSurvey;

