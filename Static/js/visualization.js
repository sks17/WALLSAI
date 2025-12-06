/**
 * WALLS Visualization Module
 * 
 * Advanced 3D + 2D visualizations for mental health AI dashboard.
 * 
 * Features:
 * - Three.js 3D visualizations (point cloud, hyperplane, mental sphere)
 * - Chart.js 2D charts (radar, line, bar, heatmap)
 * - Real-time animation and updates
 * - Event-driven data synchronization
 * 
 * Dependencies:
 * - Three.js (loaded via CDN)
 * - Chart.js (loaded via CDN)
 */

const WallsVisualizations = (function() {
    'use strict';

    // ========================================================================
    // State
    // ========================================================================
    
    const state = {
        scores: { stress: 0, depression: 0, anxiety: 0, sleep: 0 },
        history: [],
        charts: {},
        threeScenes: {},
        animationFrameIds: {},
        initialized: false
    };

    // Color scheme
    const COLORS = {
        stress: { main: '#ff6b6b', glow: 'rgba(255, 107, 107, 0.5)' },
        depression: { main: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.5)' },
        anxiety: { main: '#00f5ff', glow: 'rgba(0, 245, 255, 0.5)' },
        sleep: { main: '#3b82f6', glow: 'rgba(59, 130, 246, 0.5)' },
        grid: '#1a1a2e',
        accent: '#00f5ff',
        text: '#e0e0e0'
    };

    // ========================================================================
    // Initialization
    // ========================================================================

    /**
     * Initialize all visualizations
     */
    async function init(options = {}) {
        if (state.initialized) return;

        console.log('[Viz] Initializing visualization system...');

        // Load history data
        try {
            const historyData = await WallsAPI.getHistory(WallsAPI.getUserId(), 50);
            state.history = historyData.evaluations || [];
            
            const metricsData = await WallsAPI.getMetrics(WallsAPI.getUserId());
            if (metricsData.latest_scores) {
                updateScores(metricsData.latest_scores);
            }
        } catch (e) {
            console.warn('[Viz] Could not load initial data:', e);
        }

        // Subscribe to prediction events
        WallsAPI.onPrediction((result) => {
            console.log('[Viz] New prediction received:', result);
            if (result.scores) {
                updateScores(result.scores);
            }
        });

        state.initialized = true;
        console.log('[Viz] Initialization complete');
    }

    /**
     * Update scores and refresh visualizations
     */
    function updateScores(scores) {
        state.scores = {
            stress: scores.stress_score || 0,
            depression: scores.depression_score || 0,
            anxiety: scores.anxiety_score || 0,
            sleep: scores.sleep_quality || 0
        };

        // Update all active visualizations
        Object.values(state.charts).forEach(chart => {
            if (chart && typeof chart.update === 'function') {
                updateChartData(chart);
            }
        });

        // Update 3D scenes
        Object.values(state.threeScenes).forEach(scene => {
            if (scene && scene.updateScores) {
                scene.updateScores(state.scores);
            }
        });

        // Dispatch event
        window.dispatchEvent(new CustomEvent('walls:scores-updated', {
            detail: state.scores
        }));
    }

    // ========================================================================
    // 3D VISUALIZATIONS (Three.js)
    // ========================================================================

    /**
     * Initialize Three.js if not loaded
     */
    function ensureThreeJS() {
        return new Promise((resolve, reject) => {
            if (window.THREE) {
                resolve(window.THREE);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
            script.onload = () => resolve(window.THREE);
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Create 3D Point Cloud Visualization
     * Points represent emotional state in 3D space
     */
    async function createPointCloud(canvasId) {
        const THREE = await ensureThreeJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const width = canvas.clientWidth;
        const height = canvas.clientHeight;

        // Scene setup
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        camera.position.z = 50;

        const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);

        // Create point cloud
        const particleCount = 500;
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 60;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 60;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 60;
            
            const color = new THREE.Color(COLORS.accent);
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;
            
            sizes[i] = Math.random() * 2 + 0.5;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 1.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            sizeAttenuation: true
        });

        const points = new THREE.Points(geometry, material);
        scene.add(points);

        // Add grid helper
        const gridHelper = new THREE.GridHelper(80, 20, 0x1a1a2e, 0x1a1a2e);
        gridHelper.rotation.x = Math.PI / 2;
        scene.add(gridHelper);

        // Animation
        let rotation = 0;
        function animate() {
            state.animationFrameIds[canvasId] = requestAnimationFrame(animate);
            rotation += 0.002;
            points.rotation.y = rotation;
            points.rotation.x = Math.sin(rotation * 0.5) * 0.2;
            
            // Update positions based on scores
            const positions = geometry.attributes.position.array;
            const { stress, depression, anxiety, sleep } = state.scores;
            
            for (let i = 0; i < particleCount; i++) {
                const offset = Math.sin(rotation * 2 + i * 0.1) * (stress / 30 + 0.1);
                positions[i * 3 + 1] += offset * 0.02;
                
                // Clamp positions
                if (Math.abs(positions[i * 3 + 1]) > 35) {
                    positions[i * 3 + 1] *= -0.9;
                }
            }
            geometry.attributes.position.needsUpdate = true;
            
            renderer.render(scene, camera);
        }
        animate();

        // Store for updates
        const sceneObj = {
            scene, camera, renderer, points, geometry,
            updateScores: (scores) => {
                // Update particle colors based on dominant score
                const colors = geometry.attributes.color.array;
                const maxScore = Math.max(scores.stress, scores.depression, scores.anxiety, scores.sleep);
                let dominantColor;
                
                if (scores.stress === maxScore) dominantColor = new THREE.Color(COLORS.stress.main);
                else if (scores.anxiety === maxScore) dominantColor = new THREE.Color(COLORS.anxiety.main);
                else if (scores.depression === maxScore) dominantColor = new THREE.Color(COLORS.depression.main);
                else dominantColor = new THREE.Color(COLORS.sleep.main);
                
                for (let i = 0; i < particleCount; i++) {
                    const t = Math.random() * 0.3;
                    colors[i * 3] = dominantColor.r * (1 - t) + t;
                    colors[i * 3 + 1] = dominantColor.g * (1 - t) + t;
                    colors[i * 3 + 2] = dominantColor.b * (1 - t) + t;
                }
                geometry.attributes.color.needsUpdate = true;
            },
            dispose: () => {
                cancelAnimationFrame(state.animationFrameIds[canvasId]);
                geometry.dispose();
                material.dispose();
                renderer.dispose();
            }
        };

        state.threeScenes[canvasId] = sceneObj;
        return sceneObj;
    }

    /**
     * Create 3D Hyperplane Visualization
     * Represents decision boundaries of the ML model
     */
    async function createHyperplane(canvasId) {
        const THREE = await ensureThreeJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const width = canvas.clientWidth;
        const height = canvas.clientHeight;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        camera.position.set(30, 30, 30);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);

        // Create multiple planes representing decision boundaries
        const planes = [];
        const planeColors = [COLORS.stress.main, COLORS.depression.main, COLORS.anxiety.main, COLORS.sleep.main];
        
        for (let i = 0; i < 4; i++) {
            const geometry = new THREE.PlaneGeometry(40, 40, 20, 20);
            const material = new THREE.MeshBasicMaterial({
                color: planeColors[i],
                wireframe: true,
                transparent: true,
                opacity: 0.3,
                side: THREE.DoubleSide
            });
            
            const plane = new THREE.Mesh(geometry, material);
            plane.rotation.x = Math.PI / 2 + (i * 0.2);
            plane.rotation.z = i * 0.3;
            plane.position.y = i * 5 - 7.5;
            
            scene.add(plane);
            planes.push(plane);
        }

        // Add axes
        const axesHelper = new THREE.AxesHelper(25);
        scene.add(axesHelper);

        // Add grid
        const gridHelper = new THREE.GridHelper(60, 30, 0x1a1a2e, 0x0a0a0f);
        scene.add(gridHelper);

        // Animation
        let time = 0;
        function animate() {
            state.animationFrameIds[canvasId] = requestAnimationFrame(animate);
            time += 0.01;
            
            const { stress, depression, anxiety, sleep } = state.scores;
            const scores = [stress, depression, anxiety, sleep];
            
            planes.forEach((plane, i) => {
                const intensity = scores[i] / 30 || 0.1;
                plane.rotation.z = Math.sin(time + i) * intensity * 0.5;
                plane.rotation.x = Math.PI / 2 + Math.cos(time * 0.5 + i) * intensity * 0.3;
                plane.position.y = (i * 5 - 7.5) + Math.sin(time * 2 + i) * intensity * 2;
                plane.material.opacity = 0.2 + intensity * 0.3;
            });
            
            camera.position.x = 30 * Math.cos(time * 0.2);
            camera.position.z = 30 * Math.sin(time * 0.2);
            camera.lookAt(0, 0, 0);
            
            renderer.render(scene, camera);
        }
        animate();

        const sceneObj = {
            scene, camera, renderer, planes,
            updateScores: () => {},
            dispose: () => {
                cancelAnimationFrame(state.animationFrameIds[canvasId]);
                planes.forEach(p => { p.geometry.dispose(); p.material.dispose(); });
                renderer.dispose();
            }
        };

        state.threeScenes[canvasId] = sceneObj;
        return sceneObj;
    }

    /**
     * Create 3D Mental State Sphere
     * A pulsing, morphing sphere representing mental state
     */
    async function createMentalSphere(canvasId) {
        const THREE = await ensureThreeJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const width = canvas.clientWidth;
        const height = canvas.clientHeight;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        camera.position.z = 40;

        const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);

        // Create sphere with custom shader-like effect
        const sphereGeometry = new THREE.IcosahedronGeometry(12, 4);
        const sphereMaterial = new THREE.MeshBasicMaterial({
            color: COLORS.accent,
            wireframe: true,
            transparent: true,
            opacity: 0.8
        });
        const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
        scene.add(sphere);

        // Inner glow sphere
        const innerGeometry = new THREE.IcosahedronGeometry(10, 3);
        const innerMaterial = new THREE.MeshBasicMaterial({
            color: COLORS.depression.main,
            transparent: true,
            opacity: 0.3
        });
        const innerSphere = new THREE.Mesh(innerGeometry, innerMaterial);
        scene.add(innerSphere);

        // Outer ring
        const ringGeometry = new THREE.RingGeometry(16, 18, 64);
        const ringMaterial = new THREE.MeshBasicMaterial({
            color: COLORS.anxiety.main,
            transparent: true,
            opacity: 0.5,
            side: THREE.DoubleSide
        });
        const ring = new THREE.Mesh(ringGeometry, ringMaterial);
        scene.add(ring);

        // Store original positions for morphing
        const originalPositions = sphereGeometry.attributes.position.array.slice();

        // Animation
        let time = 0;
        function animate() {
            state.animationFrameIds[canvasId] = requestAnimationFrame(animate);
            time += 0.02;
            
            const { stress, depression, anxiety, sleep } = state.scores;
            
            // Morph sphere based on scores
            const positions = sphereGeometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                const ox = originalPositions[i];
                const oy = originalPositions[i + 1];
                const oz = originalPositions[i + 2];
                
                const distort = (stress / 30) * Math.sin(time * 3 + ox) * 0.5;
                const vibration = (anxiety / 30) * Math.sin(time * 8 + oy * 2) * 0.3;
                
                positions[i] = ox * (1 + distort) + vibration;
                positions[i + 1] = oy * (1 + distort * 0.5);
                positions[i + 2] = oz * (1 + distort);
            }
            sphereGeometry.attributes.position.needsUpdate = true;
            
            // Scale based on stress
            const scale = 1 + (stress / 30) * 0.3;
            sphere.scale.set(scale, scale, scale);
            
            // Rotation based on depression
            sphere.rotation.y = time * 0.5 * (1 + depression / 30);
            sphere.rotation.x = Math.sin(time * 0.3) * 0.3;
            
            // Inner sphere brightness based on depression
            innerMaterial.opacity = 0.2 + (depression / 30) * 0.4;
            innerSphere.rotation.y = -time * 0.3;
            
            // Ring rotation based on anxiety
            ring.rotation.x = Math.PI / 2 + Math.sin(time) * 0.2;
            ring.rotation.z = time * (1 + anxiety / 30);
            
            // Color shift based on sleep
            const hue = (180 + sleep * 5) / 360;
            sphereMaterial.color.setHSL(hue, 0.8, 0.5);
            
            renderer.render(scene, camera);
        }
        animate();

        const sceneObj = {
            scene, camera, renderer, sphere, innerSphere, ring,
            updateScores: () => {},
            dispose: () => {
                cancelAnimationFrame(state.animationFrameIds[canvasId]);
                sphereGeometry.dispose(); sphereMaterial.dispose();
                innerGeometry.dispose(); innerMaterial.dispose();
                ringGeometry.dispose(); ringMaterial.dispose();
                renderer.dispose();
            }
        };

        state.threeScenes[canvasId] = sceneObj;
        return sceneObj;
    }

    // ========================================================================
    // 2D VISUALIZATIONS (Chart.js)
    // ========================================================================

    /**
     * Ensure Chart.js is loaded
     */
    function ensureChartJS() {
        return new Promise((resolve, reject) => {
            if (window.Chart) {
                resolve(window.Chart);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
            script.onload = () => resolve(window.Chart);
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Create Radar Chart comparing all scores
     */
    async function createRadarChart(canvasId) {
        const Chart = await ensureChartJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        // Destroy existing chart
        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }

        const chart = new Chart(canvas, {
            type: 'radar',
            data: {
                labels: ['Stress', 'Depression', 'Anxiety', 'Sleep Quality'],
                datasets: [{
                    label: 'Current State',
                    data: [state.scores.stress, state.scores.depression, state.scores.anxiety, state.scores.sleep],
                    backgroundColor: 'rgba(0, 245, 255, 0.2)',
                    borderColor: COLORS.accent,
                    borderWidth: 2,
                    pointBackgroundColor: [COLORS.stress.main, COLORS.depression.main, COLORS.anxiety.main, COLORS.sleep.main],
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 30,
                        ticks: {
                            stepSize: 10,
                            color: COLORS.text,
                            backdropColor: 'transparent'
                        },
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        pointLabels: {
                            color: COLORS.text,
                            font: { family: 'JetBrains Mono', size: 11 }
                        }
                    }
                },
                animation: { duration: 750, easing: 'easeOutQuart' }
            }
        });

        state.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create Line Chart showing trends over time
     */
    async function createTrendChart(canvasId) {
        const Chart = await ensureChartJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }

        // Process history data
        const sorted = [...state.history].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        const labels = sorted.map(r => {
            const d = new Date(r.timestamp);
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const datasets = [
            { label: 'Stress', data: sorted.map(r => r.scores?.stress_score), borderColor: COLORS.stress.main, tension: 0.4 },
            { label: 'Depression', data: sorted.map(r => r.scores?.depression_score), borderColor: COLORS.depression.main, tension: 0.4 },
            { label: 'Anxiety', data: sorted.map(r => r.scores?.anxiety_score), borderColor: COLORS.anxiety.main, tension: 0.4 },
            { label: 'Sleep', data: sorted.map(r => r.scores?.sleep_quality), borderColor: COLORS.sleep.main, tension: 0.4 }
        ].map(ds => ({
            ...ds,
            fill: false,
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 6
        }));

        const chart = new Chart(canvas, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: COLORS.text, font: { family: 'JetBrains Mono', size: 10 } }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 30,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: COLORS.text }
                    },
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: COLORS.text, maxRotation: 45 }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });

        state.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create Bar Comparison Chart (current vs previous)
     */
    async function createComparisonChart(canvasId) {
        const Chart = await ensureChartJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }

        const current = state.scores;
        const previous = state.history.length > 1 ? state.history[1].scores : {};

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Stress', 'Depression', 'Anxiety', 'Sleep'],
                datasets: [
                    {
                        label: 'Current',
                        data: [current.stress, current.depression, current.anxiety, current.sleep],
                        backgroundColor: [COLORS.stress.main, COLORS.depression.main, COLORS.anxiety.main, COLORS.sleep.main],
                        borderRadius: 6
                    },
                    {
                        label: 'Previous',
                        data: [
                            previous.stress_score || 0,
                            previous.depression_score || 0,
                            previous.anxiety_score || 0,
                            previous.sleep_quality || 0
                        ],
                        backgroundColor: 'rgba(255,255,255,0.2)',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: COLORS.text } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 30,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: COLORS.text }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: COLORS.text }
                    }
                }
            }
        });

        state.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create Gauge Chart for single metric
     */
    async function createGaugeChart(canvasId, metric) {
        const Chart = await ensureChartJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }

        const value = state.scores[metric] || 0;
        const max = 30;
        const color = COLORS[metric]?.main || COLORS.accent;

        const chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [value, max - value],
                    backgroundColor: [color, 'rgba(255,255,255,0.1)'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            },
            plugins: [{
                id: 'gaugeValue',
                afterDraw: (chart) => {
                    const { ctx, chartArea } = chart;
                    const centerX = (chartArea.left + chartArea.right) / 2;
                    const centerY = chartArea.bottom - 10;
                    
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.font = 'bold 24px JetBrains Mono';
                    ctx.fillStyle = color;
                    ctx.fillText(value.toFixed(1), centerX, centerY - 5);
                    ctx.restore();
                }
            }]
        });

        state.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create Intensity Slider Trend Chart
     * Shows the 0-100 intensity values for slider questions over time
     */
    async function createIntensityChart(canvasId) {
        const Chart = await ensureChartJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }

        // Process history data for intensity values
        const sorted = [...state.history]
            .filter(r => r.intensity_values && Object.keys(r.intensity_values).length > 0)
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        if (sorted.length === 0) {
            // No intensity data yet - show placeholder
            canvas.parentElement.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted);">
                    <p>No intensity data yet. Complete a survey with slider questions to see trends.</p>
                </div>
            `;
            return null;
        }

        const labels = sorted.map(r => {
            const d = new Date(r.timestamp);
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        // Intensity slider features
        const intensityFeatures = [
            { key: 'hopelessness_intensity', label: 'Motivation', color: '#8b5cf6' },
            { key: 'anger_intensity', label: 'Frustration', color: '#ff6b6b' },
            { key: 'feeling.tired_intensity', label: 'Fatigue', color: '#3b82f6' }
        ];

        const datasets = intensityFeatures.map(f => ({
            label: f.label,
            data: sorted.map(r => r.intensity_values?.[f.key] || null),
            borderColor: f.color,
            backgroundColor: f.color + '20',
            fill: true,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
        }));

        const chart = new Chart(canvas, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { 
                            color: COLORS.text, 
                            font: { family: 'JetBrains Mono', size: 10 },
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}%`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Intensity (0-100)',
                            color: COLORS.text,
                            font: { size: 11 }
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { 
                            color: COLORS.text,
                            callback: (val) => val + '%'
                        }
                    },
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: COLORS.text, maxRotation: 45 }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });

        state.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create Intensity Distribution Chart (Histogram)
     * Shows the distribution of intensity values
     */
    async function createIntensityHistogram(canvasId) {
        const Chart = await ensureChartJS();
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        if (state.charts[canvasId]) {
            state.charts[canvasId].destroy();
        }

        // Collect all intensity values
        const allIntensities = [];
        state.history.forEach(r => {
            if (r.intensity_values) {
                Object.values(r.intensity_values).forEach(v => {
                    if (typeof v === 'number') allIntensities.push(v);
                });
            }
        });

        if (allIntensities.length === 0) {
            canvas.parentElement.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted);">
                    <p>No intensity data available.</p>
                </div>
            `;
            return null;
        }

        // Create histogram bins
        const bins = [0, 0, 0, 0, 0]; // 0-20, 21-40, 41-60, 61-80, 81-100
        allIntensities.forEach(v => {
            if (v <= 20) bins[0]++;
            else if (v <= 40) bins[1]++;
            else if (v <= 60) bins[2]++;
            else if (v <= 80) bins[3]++;
            else bins[4]++;
        });

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'],
                datasets: [{
                    label: 'Frequency',
                    data: bins,
                    backgroundColor: [
                        'rgba(74, 222, 128, 0.7)',  // Green - low
                        'rgba(134, 239, 172, 0.7)', // Light green
                        'rgba(251, 191, 36, 0.7)',  // Yellow - moderate
                        'rgba(251, 146, 60, 0.7)',  // Orange
                        'rgba(239, 68, 68, 0.7)'    // Red - high
                    ],
                    borderColor: [
                        'rgb(74, 222, 128)',
                        'rgb(134, 239, 172)',
                        'rgb(251, 191, 36)',
                        'rgb(251, 146, 60)',
                        'rgb(239, 68, 68)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Intensity Distribution',
                        color: COLORS.text,
                        font: { family: 'JetBrains Mono', size: 12 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count',
                            color: COLORS.text
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: COLORS.text }
                    },
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: COLORS.text }
                    }
                }
            }
        });

        state.charts[canvasId] = chart;
        return chart;
    }

    // ========================================================================
    // Helper Functions
    // ========================================================================

    function updateChartData(chart) {
        if (!chart || !chart.data) return;
        
        const type = chart.config.type;
        
        if (type === 'radar') {
            chart.data.datasets[0].data = [state.scores.stress, state.scores.depression, state.scores.anxiety, state.scores.sleep];
        } else if (type === 'bar') {
            chart.data.datasets[0].data = [state.scores.stress, state.scores.depression, state.scores.anxiety, state.scores.sleep];
        }
        
        chart.update('none');
    }

    /**
     * Refresh history data and update charts
     */
    async function refreshData() {
        try {
            const historyData = await WallsAPI.getHistory(WallsAPI.getUserId(), 50);
            state.history = historyData.evaluations || [];
            
            const metricsData = await WallsAPI.getMetrics(WallsAPI.getUserId());
            if (metricsData.latest_scores) {
                updateScores(metricsData.latest_scores);
            }
        } catch (e) {
            console.warn('[Viz] Failed to refresh data:', e);
        }
    }

    /**
     * Destroy all visualizations
     */
    function destroy() {
        Object.values(state.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        Object.values(state.threeScenes).forEach(scene => {
            if (scene && typeof scene.dispose === 'function') {
                scene.dispose();
            }
        });

        Object.values(state.animationFrameIds).forEach(id => {
            cancelAnimationFrame(id);
        });

        state.charts = {};
        state.threeScenes = {};
        state.animationFrameIds = {};
        state.initialized = false;
    }

    // ========================================================================
    // Public API
    // ========================================================================

    return {
        init,
        updateScores,
        refreshData,
        destroy,
        
        // 3D Visualizations
        createPointCloud,
        createHyperplane,
        createMentalSphere,
        
        // 2D Charts
        createRadarChart,
        createTrendChart,
        createComparisonChart,
        createGaugeChart,
        
        // Intensity Charts (for slider questions)
        createIntensityChart,
        createIntensityHistogram,
        
        // State access
        getScores: () => ({ ...state.scores }),
        getHistory: () => [...state.history],
        
        // Color scheme
        COLORS
    };
})();

// Make available globally
window.WallsVisualizations = WallsVisualizations;
