"""
Curated Mindfulness Resources Data

Contains categorized links to mental health resources.
All resources are free, public, and non-commercial references.

DISCLAIMER: These resources are provided for informational purposes only.
WALLS does not endorse any specific service or treatment approach.
Always consult a qualified healthcare professional for medical advice.
"""

# ---------------------------------------------------------------------------
# Mindfulness & Meditation Resources
# ---------------------------------------------------------------------------

MINDFULNESS_RESOURCES = {
    "meditation_apps": [
        {
            "name": "Insight Timer",
            "url": "https://insighttimer.com/",
            "description": "Free meditation app with thousands of guided meditations from teachers worldwide. No subscription required for most content.",
            "tags": ["free", "meditation", "sleep"],
            "icon": "🧘"
        },
        {
            "name": "UCLA Mindful Awareness",
            "url": "https://www.uclahealth.org/marc/mindful-meditations",
            "description": "Free guided meditations from UCLA's Mindful Awareness Research Center. Evidence-based and professionally recorded.",
            "tags": ["free", "research-backed", "meditation"],
            "icon": "🎓"
        },
        {
            "name": "Smiling Mind",
            "url": "https://www.smilingmind.com.au/",
            "description": "Free Australian non-profit meditation app with programs for all ages. Developed by psychologists and educators.",
            "tags": ["free", "all-ages", "meditation"],
            "icon": "😊"
        }
    ],
    
    "youtube_channels": [
        {
            "name": "The Honest Guys",
            "url": "https://www.youtube.com/user/TheHonestGuys",
            "description": "Popular YouTube channel with hundreds of free guided meditations, sleep stories, and relaxation videos.",
            "tags": ["free", "youtube", "sleep"],
            "icon": "▶️"
        },
        {
            "name": "Michael Sealey",
            "url": "https://www.youtube.com/user/MichaelSealey",
            "description": "Hypnotherapy and meditation videos for sleep, anxiety, and confidence. Over 2 million subscribers.",
            "tags": ["free", "youtube", "hypnotherapy"],
            "icon": "▶️"
        },
        {
            "name": "Great Meditation",
            "url": "https://www.youtube.com/c/GreatMeditation",
            "description": "Guided meditations focusing on anxiety relief, self-love, and healing. Gentle and accessible.",
            "tags": ["free", "youtube", "anxiety"],
            "icon": "▶️"
        },
        {
            "name": "Yoga With Adriene",
            "url": "https://www.youtube.com/user/yogawithadriene",
            "description": "Free yoga videos for all levels. Great for combining physical movement with mindfulness.",
            "tags": ["free", "youtube", "yoga", "exercise"],
            "icon": "🧘‍♀️"
        }
    ],
    
    "breathing_resources": [
        {
            "name": "Box Breathing Guide",
            "url": "https://www.healthline.com/health/box-breathing",
            "description": "Simple 4-4-4-4 breathing technique used by Navy SEALs for stress management. Easy to learn.",
            "tags": ["free", "breathing", "stress"],
            "icon": "🫁"
        },
        {
            "name": "4-7-8 Breathing Technique",
            "url": "https://www.medicalnewstoday.com/articles/324417",
            "description": "Dr. Andrew Weil's relaxation breathing method. Helps with anxiety and sleep.",
            "tags": ["free", "breathing", "sleep"],
            "icon": "🫁"
        }
    ],
    
    "crisis_resources": [
        {
            "name": "988 Suicide & Crisis Lifeline",
            "url": "https://988lifeline.org/",
            "description": "24/7 free and confidential support for people in distress. Call or text 988 (US).",
            "tags": ["crisis", "24/7", "free"],
            "icon": "🆘",
            "is_crisis": True
        },
        {
            "name": "Crisis Text Line",
            "url": "https://www.crisistextline.org/",
            "description": "Text HOME to 741741 to connect with a trained crisis counselor. Free and confidential.",
            "tags": ["crisis", "text", "free"],
            "icon": "💬",
            "is_crisis": True
        },
        {
            "name": "International Crisis Lines",
            "url": "https://www.iasp.info/resources/Crisis_Centres/",
            "description": "Directory of crisis centers worldwide from the International Association for Suicide Prevention.",
            "tags": ["crisis", "international"],
            "icon": "🌍",
            "is_crisis": True
        }
    ],
    
    "educational": [
        {
            "name": "NIMH - Mental Health Information",
            "url": "https://www.nimh.nih.gov/health/topics",
            "description": "Authoritative information on mental health conditions from the National Institute of Mental Health.",
            "tags": ["education", "research", "official"],
            "icon": "📚"
        },
        {
            "name": "Mind (UK)",
            "url": "https://www.mind.org.uk/information-support/",
            "description": "Comprehensive mental health information and support guides from UK's leading mental health charity.",
            "tags": ["education", "uk", "guides"],
            "icon": "📚"
        },
        {
            "name": "Anxiety and Depression Association",
            "url": "https://adaa.org/understanding-anxiety",
            "description": "Evidence-based resources about anxiety disorders, depression, and related conditions.",
            "tags": ["education", "anxiety", "depression"],
            "icon": "📚"
        }
    ]
}


# ---------------------------------------------------------------------------
# Breathing Exercises
# ---------------------------------------------------------------------------

BREATHING_EXERCISES = [
    {
        "id": "box_breathing",
        "name": "Box Breathing",
        "description": "Also known as square breathing. A simple technique to calm the nervous system.",
        "steps": [
            {"phase": "inhale", "duration": 4, "instruction": "Breathe in slowly"},
            {"phase": "hold", "duration": 4, "instruction": "Hold your breath"},
            {"phase": "exhale", "duration": 4, "instruction": "Breathe out slowly"},
            {"phase": "hold", "duration": 4, "instruction": "Hold empty"}
        ],
        "cycles": 4,
        "benefits": ["Reduces stress", "Improves focus", "Lowers blood pressure"]
    },
    {
        "id": "478_breathing",
        "name": "4-7-8 Breathing",
        "description": "Dr. Andrew Weil's relaxation technique. Great for anxiety and sleep.",
        "steps": [
            {"phase": "inhale", "duration": 4, "instruction": "Breathe in through nose"},
            {"phase": "hold", "duration": 7, "instruction": "Hold your breath"},
            {"phase": "exhale", "duration": 8, "instruction": "Exhale through mouth"}
        ],
        "cycles": 4,
        "benefits": ["Promotes sleep", "Reduces anxiety", "Calms mind"]
    },
    {
        "id": "physiological_sigh",
        "name": "Physiological Sigh",
        "description": "Stanford-researched technique for quick stress relief.",
        "steps": [
            {"phase": "inhale", "duration": 2, "instruction": "Deep breath in"},
            {"phase": "inhale", "duration": 1, "instruction": "Second short inhale"},
            {"phase": "exhale", "duration": 6, "instruction": "Long slow exhale"}
        ],
        "cycles": 3,
        "benefits": ["Rapid calm", "Reduces cortisol", "Evidence-based"]
    },
    {
        "id": "coherent_breathing",
        "name": "Coherent Breathing",
        "description": "5-5 breathing rhythm to activate the parasympathetic nervous system.",
        "steps": [
            {"phase": "inhale", "duration": 5, "instruction": "Slow inhale"},
            {"phase": "exhale", "duration": 5, "instruction": "Slow exhale"}
        ],
        "cycles": 6,
        "benefits": ["Heart rate variability", "Emotional balance", "Deep relaxation"]
    }
]


# ---------------------------------------------------------------------------
# Learn Topics (Science of Mental Health)
# ---------------------------------------------------------------------------

LEARN_TOPICS = [
    {
        "id": "stress_science",
        "title": "Understanding Stress",
        "summary": "Learn how stress affects your body and mind, and evidence-based ways to manage it.",
        "content": """
## What is Stress?

Stress is your body's response to demands or threats. When you feel threatened, your nervous system releases hormones including adrenaline and cortisol, preparing your body for emergency action.

### The Stress Response

1. **Fight or Flight**: Your heart pounds faster, muscles tighten, blood pressure rises
2. **Cortisol Release**: Increases blood sugar, enhances brain's use of glucose
3. **Non-Essential Functions Slow**: Digestion, immune response, growth processes

### Chronic vs. Acute Stress

**Acute stress** is short-term and can actually be helpful (meeting deadlines, avoiding danger).

**Chronic stress** occurs when stress persists over time, leading to:
- Sleep problems
- Weakened immune system
- Digestive issues
- Memory and concentration problems
- Heart disease risk

### Evidence-Based Stress Management

1. **Exercise**: 30 minutes of moderate activity reduces cortisol
2. **Sleep hygiene**: 7-9 hours consistently
3. **Social connection**: Releases oxytocin, counters stress hormones
4. **Mindfulness meditation**: Reduces amygdala reactivity
5. **Deep breathing**: Activates parasympathetic nervous system
        """,
        "icon": "🧠"
    },
    {
        "id": "anxiety_science",
        "title": "Understanding Anxiety",
        "summary": "The science behind anxiety disorders and proven treatment approaches.",
        "content": """
## What is Anxiety?

Anxiety is a normal emotion characterized by feelings of tension, worried thoughts, and physical changes. Anxiety disorders occur when these feelings are excessive, persistent, and interfere with daily life.

### Types of Anxiety Disorders

- **Generalized Anxiety Disorder (GAD)**: Persistent, excessive worry about various aspects of life
- **Panic Disorder**: Recurring panic attacks with physical symptoms
- **Social Anxiety**: Intense fear of social situations
- **Specific Phobias**: Intense fear of specific objects or situations

### What Happens in the Brain

The **amygdala** (threat detection center) becomes overactive, triggering false alarms. The **prefrontal cortex** (rational thinking) has reduced ability to calm the amygdala.

### Evidence-Based Treatments

1. **Cognitive Behavioral Therapy (CBT)**: Most researched and effective therapy
2. **Exposure therapy**: Gradually facing feared situations
3. **Mindfulness-Based Stress Reduction (MBSR)**
4. **Medication**: SSRIs, SNRIs when appropriate
5. **Lifestyle**: Exercise, sleep, caffeine reduction
        """,
        "icon": "💭"
    },
    {
        "id": "sleep_science",
        "title": "The Science of Sleep",
        "summary": "Why sleep matters for mental health and how to improve sleep quality.",
        "content": """
## Why Sleep Matters

Sleep is essential for:
- **Memory consolidation**: Brain processes and stores information
- **Emotional regulation**: REM sleep helps process emotions
- **Physical restoration**: Body repairs tissues, immune function
- **Toxin clearance**: Glymphatic system cleans brain waste

### Sleep Stages

1. **Stage 1 (Light)**: Transition from waking
2. **Stage 2 (Light)**: Body temperature drops, heart rate slows
3. **Stage 3 (Deep)**: Physical restoration, hardest to wake from
4. **REM**: Dreaming, emotional processing, memory

### Sleep and Mental Health

Poor sleep is both a **symptom** and a **cause** of mental health issues:
- Depression: Linked to REM sleep abnormalities
- Anxiety: Reduced with adequate sleep
- Stress: Cortisol regulation depends on sleep

### Sleep Hygiene Tips

1. **Consistent schedule**: Same bedtime/wake time daily
2. **Dark, cool room**: 65-68°F (18-20°C)
3. **No screens 1 hour before bed**: Blue light suppresses melatonin
4. **Limit caffeine after 2pm**
5. **Exercise early**: Not within 3 hours of bedtime
6. **Wind-down routine**: Reading, gentle stretching, warm bath
        """,
        "icon": "😴"
    },
    {
        "id": "depression_science",
        "title": "Understanding Depression",
        "summary": "The neuroscience of depression and paths to recovery.",
        "content": """
## What is Depression?

Clinical depression (Major Depressive Disorder) is more than feeling sad. It's a persistent condition affecting mood, thinking, and physical health.

### Symptoms (DSM-5 Criteria)

For at least 2 weeks, experiencing 5+ of:
- Depressed mood most of the day
- Loss of interest or pleasure
- Significant weight/appetite changes
- Sleep disturbance
- Fatigue
- Feelings of worthlessness or guilt
- Difficulty concentrating
- Thoughts of death or suicide

### The Brain in Depression

- **Serotonin, norepinephrine, dopamine**: Neurotransmitter imbalances
- **Hippocampus**: May shrink (reversible with treatment)
- **Prefrontal cortex**: Reduced activity
- **Amygdala**: Increased reactivity

### Treatment Approaches

1. **Psychotherapy**: CBT, interpersonal therapy, behavioral activation
2. **Medication**: Antidepressants work for many people
3. **Exercise**: As effective as medication for mild-moderate depression
4. **Social support**: Connection reduces isolation
5. **Sleep**: Critical for recovery

### Recovery is Possible

Depression is highly treatable. 80-90% of people respond to treatment. Recovery often means learning skills that prevent future episodes.
        """,
        "icon": "🌱"
    }
]


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

DISCLAIMER = """
**Important Notice**: The resources and information provided by WALLS are for educational and informational purposes only. They are not intended to be a substitute for professional medical advice, diagnosis, or treatment.

If you are experiencing a mental health crisis, please contact emergency services (911 in the US) or a crisis helpline immediately.

Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.
"""

