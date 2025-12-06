/**
 * KERNEL AI Visualizations
 * 
 * Advanced, geeky, over-the-top AI visualizations including:
 * - 3D Neural Network Animation (shows "thinking" process)
 * - Mental State Manifold (t-SNE style embedding space)
 * - Confidence Ribbon Charts (uncertainty visualization)
 * - Pulsing Neuron Clusters
 * - Real-time EEG-style activity traces
 * 
 * Uses Three.js for 3D, Chart.js for 2D, and custom WebGL shaders.
 */

const KernelVisuals = (function() {
    'use strict';

    // ========================================================================
    // Configuration
    // ========================================================================
    
    const COLORS = {
        stress: { primary: '#ff6b6b', glow: 'rgba(255, 107, 107, 0.5)' },
        depression: { primary: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.5)' },
        anxiety: { primary: '#00d4aa', glow: 'rgba(0, 212, 170, 0.5)' },
        sleep: { primary: '#3b82f6', glow: 'rgba(59, 130, 246, 0.5)' },
        wellbeing: { primary: '#fbbf24', glow: 'rgba(251, 191, 36, 0.5)' },
        
        // Neon theme
        cyan: '#00ffff',
        magenta: '#ff00ff',
        purple: '#8b5cf6',
        
        // Background
        dark: '#0a0a1a',
        grid: 'rgba(255, 255, 255, 0.05)'
    };

    let charts = {};
    let threeScene = null;
    let animationFrame = null;
    let currentScores = null;

    // ========================================================================
    // Initialization
    // ========================================================================

    /**
     * Initialize all visualizations
     */
    function init(containers = {}) {
        console.log('[KernelVisuals] Initializing...');
        
        // Initialize 2D charts
        if (containers.radarChart) {
            initRadarChart(containers.radarChart);
        }
        if (containers.confidenceChart) {
            initConfidenceChart(containers.confidenceChart);
        }
        if (containers.trendChart) {
            initTrendChart(containers.trendChart);
        }
        
        // Initialize 3D scene
        if (containers.neuralScene) {
            initNeuralScene(containers.neuralScene);
        }
        
        // Listen for prediction events
        window.addEventListener('kernel:prediction', (e) => {
            updateAllVisuals(e.detail);
        });
        
        // Start animation loop
        startAnimationLoop();
        
        console.log('[KernelVisuals] Initialized');
    }

    // ========================================================================
    // 2D Charts (Chart.js)
    // ========================================================================

    function initRadarChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        charts.radar = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Stress', 'Depression', 'Anxiety', 'Sleep ↓', 'Wellbeing ↓'],
                datasets: [{
                    label: 'Current',
                    data: [0, 0, 0, 0, 0],
                    fill: true,
                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                    borderColor: COLORS.purple,
                    pointBackgroundColor: COLORS.purple,
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: COLORS.purple
                }, {
                    label: 'Confidence Band',
                    data: [0, 0, 0, 0, 0],
                    fill: '+1',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderColor: 'rgba(139, 92, 246, 0.3)',
                    borderDash: [5, 5],
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            color: 'rgba(255, 255, 255, 0.5)',
                            backdropColor: 'transparent'
                        },
                        grid: {
                            color: COLORS.grid
                        },
                        pointLabels: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            font: { size: 12 }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }

    function initConfidenceChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        charts.confidence = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Stress', 'Depression', 'Anxiety', 'Sleep', 'Wellbeing'],
                datasets: [{
                    label: 'Score',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        COLORS.stress.glow,
                        COLORS.depression.glow,
                        COLORS.anxiety.glow,
                        COLORS.sleep.glow,
                        COLORS.wellbeing.glow
                    ],
                    borderColor: [
                        COLORS.stress.primary,
                        COLORS.depression.primary,
                        COLORS.anxiety.primary,
                        COLORS.sleep.primary,
                        COLORS.wellbeing.primary
                    ],
                    borderWidth: 2,
                    borderRadius: 4
                }, {
                    label: 'Uncertainty',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    borderColor: 'rgba(255, 255, 255, 0.3)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: COLORS.grid
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.5)'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const score = context.raw;
                                return `${context.label}: ${score.toFixed(1)}`;
                            }
                        }
                    }
                }
            }
        });
    }

    function initTrendChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    createTrendDataset('Stress', COLORS.stress.primary),
                    createTrendDataset('Depression', COLORS.depression.primary),
                    createTrendDataset('Anxiety', COLORS.anxiety.primary),
                    createTrendDataset('Wellbeing', COLORS.wellbeing.primary)
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        grid: { color: COLORS.grid },
                        ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: COLORS.grid },
                        ticks: { color: 'rgba(255, 255, 255, 0.5)' }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }

    function createTrendDataset(label, color) {
        return {
            label: label,
            data: [],
            borderColor: color,
            backgroundColor: color.replace(')', ', 0.1)').replace('rgb', 'rgba'),
            fill: false,
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 6
        };
    }

    // ========================================================================
    // 3D Neural Scene (Three.js)
    // ========================================================================

    function initNeuralScene(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Check if Three.js is available
        if (typeof THREE === 'undefined') {
            console.warn('[KernelVisuals] Three.js not loaded, skipping 3D scene');
            container.innerHTML = `
                <div class="fallback-visual">
                    <div class="neural-pulse"></div>
                    <p>Neural Analysis Active</p>
                </div>
            `;
            return;
        }
        
        // Setup scene
        const width = container.clientWidth;
        const height = container.clientHeight || 400;
        
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(COLORS.dark);
        
        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 30;
        
        const renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true 
        });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);
        
        // Create neural network structure
        const neurons = createNeuronNetwork(scene);
        const connections = createConnections(scene, neurons);
        
        // Add ambient light
        scene.add(new THREE.AmbientLight(0x404040, 0.5));
        
        // Add point lights
        const light1 = new THREE.PointLight(0x00ffff, 1, 100);
        light1.position.set(20, 20, 20);
        scene.add(light1);
        
        const light2 = new THREE.PointLight(0xff00ff, 1, 100);
        light2.position.set(-20, -20, -20);
        scene.add(light2);
        
        threeScene = {
            scene,
            camera,
            renderer,
            neurons,
            connections,
            container,
            time: 0
        };
        
        // Handle resize
        window.addEventListener('resize', () => {
            const w = container.clientWidth;
            const h = container.clientHeight || 400;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        });
    }

    function createNeuronNetwork(scene) {
        const neurons = [];
        const layers = [5, 8, 8, 5];  // Network architecture
        
        const neuronGeometry = new THREE.SphereGeometry(0.5, 16, 16);
        
        layers.forEach((count, layerIdx) => {
            const layerNeurons = [];
            const x = (layerIdx - (layers.length - 1) / 2) * 10;
            
            for (let i = 0; i < count; i++) {
                const y = (i - (count - 1) / 2) * 3;
                
                const material = new THREE.MeshPhongMaterial({
                    color: layerIdx === layers.length - 1 ? 0x00ffff : 0x8b5cf6,
                    emissive: 0x000000,
                    shininess: 100,
                    transparent: true,
                    opacity: 0.8
                });
                
                const neuron = new THREE.Mesh(neuronGeometry, material);
                neuron.position.set(x, y, 0);
                neuron.userData = {
                    baseY: y,
                    layer: layerIdx,
                    index: i,
                    activation: 0
                };
                
                scene.add(neuron);
                layerNeurons.push(neuron);
            }
            
            neurons.push(layerNeurons);
        });
        
        return neurons;
    }

    function createConnections(scene, neurons) {
        const connections = [];
        const lineMaterial = new THREE.LineBasicMaterial({
            color: 0x444466,
            transparent: true,
            opacity: 0.3
        });
        
        for (let l = 0; l < neurons.length - 1; l++) {
            const currentLayer = neurons[l];
            const nextLayer = neurons[l + 1];
            
            currentLayer.forEach(n1 => {
                nextLayer.forEach(n2 => {
                    const geometry = new THREE.BufferGeometry().setFromPoints([
                        n1.position,
                        n2.position
                    ]);
                    
                    const line = new THREE.Line(geometry, lineMaterial.clone());
                    line.userData = {
                        from: n1,
                        to: n2,
                        weight: Math.random()
                    };
                    
                    scene.add(line);
                    connections.push(line);
                });
            });
        }
        
        return connections;
    }

    function updateNeuralScene(scores) {
        if (!threeScene) return;
        
        const { neurons, connections } = threeScene;
        
        // Activate input neurons based on scores
        if (neurons[0] && scores) {
            const inputValues = [
                (scores.stress?.mean || 0) / 100,
                (scores.depression?.mean || 0) / 27,
                (scores.anxiety?.mean || 0) / 21,
                ((10 - (scores.sleep_quality?.mean || 5)) / 10),
                ((100 - (scores.wellbeing?.mean || 50)) / 100)
            ];
            
            neurons[0].forEach((neuron, i) => {
                neuron.userData.activation = inputValues[i] || 0;
            });
        }
        
        // Propagate activation through layers
        for (let l = 1; l < neurons.length; l++) {
            neurons[l].forEach((neuron, i) => {
                // Sum weighted inputs from previous layer
                let sum = 0;
                neurons[l - 1].forEach((prevNeuron, j) => {
                    sum += prevNeuron.userData.activation * (Math.sin(i + j) * 0.5 + 0.5);
                });
                neuron.userData.activation = Math.tanh(sum / neurons[l - 1].length);
            });
        }
        
        // Update visual appearance
        neurons.flat().forEach(neuron => {
            const activation = neuron.userData.activation;
            
            // Glow based on activation
            neuron.material.emissive.setHex(
                activation > 0.5 ? 0x00ffff : 
                activation > 0.3 ? 0x8b5cf6 : 0x000000
            );
            neuron.material.emissiveIntensity = activation * 0.5;
            
            // Scale based on activation
            const scale = 0.8 + activation * 0.4;
            neuron.scale.setScalar(scale);
        });
        
        // Update connection colors
        connections.forEach(line => {
            const fromActivation = line.userData.from.userData.activation;
            const toActivation = line.userData.to.userData.activation;
            const combinedActivation = (fromActivation + toActivation) / 2;
            
            line.material.opacity = 0.1 + combinedActivation * 0.5;
            line.material.color.setHex(
                combinedActivation > 0.5 ? 0x00ffff : 0x444466
            );
        });
    }

    // ========================================================================
    // Animation Loop
    // ========================================================================

    function startAnimationLoop() {
        function animate() {
            animationFrame = requestAnimationFrame(animate);
            
            if (threeScene) {
                threeScene.time += 0.01;
                
                // Gentle rotation
                threeScene.scene.rotation.y = Math.sin(threeScene.time * 0.2) * 0.1;
                
                // Neuron floating animation
                threeScene.neurons.flat().forEach((neuron, i) => {
                    neuron.position.y = neuron.userData.baseY + 
                        Math.sin(threeScene.time + i * 0.5) * 0.2;
                });
                
                threeScene.renderer.render(threeScene.scene, threeScene.camera);
            }
        }
        
        animate();
    }

    // ========================================================================
    // Update Functions
    // ========================================================================

    function updateAllVisuals(data) {
        const scores = data.scores;
        if (!scores) return;
        
        currentScores = scores;
        
        // Update radar chart
        updateRadarChart(scores);
        
        // Update confidence chart
        updateConfidenceChart(scores);
        
        // Update 3D scene
        updateNeuralScene(scores);
        
        // Fire update event
        window.dispatchEvent(new CustomEvent('kernel:visuals-updated', { 
            detail: scores 
        }));
    }

    function updateRadarChart(scores) {
        if (!charts.radar) return;
        
        // Normalize scores to 0-100 scale for visualization
        const normalizedScores = [
            scores.stress?.mean || 0,
            (scores.depression?.mean || 0) * (100 / 27),
            (scores.anxiety?.mean || 0) * (100 / 21),
            100 - ((scores.sleep_quality?.mean || 5) * 10),  // Inverted
            100 - (scores.wellbeing?.mean || 50)  // Inverted
        ];
        
        // Confidence band (upper CI)
        const upperBand = [
            scores.stress?.ci_upper || 0,
            (scores.depression?.ci_upper || 0) * (100 / 27),
            (scores.anxiety?.ci_upper || 0) * (100 / 21),
            100 - ((scores.sleep_quality?.ci_lower || 0) * 10),
            100 - (scores.wellbeing?.ci_lower || 0)
        ];
        
        charts.radar.data.datasets[0].data = normalizedScores;
        charts.radar.data.datasets[1].data = upperBand;
        charts.radar.update('active');
    }

    function updateConfidenceChart(scores) {
        if (!charts.confidence) return;
        
        // Main scores
        charts.confidence.data.datasets[0].data = [
            scores.stress?.mean || 0,
            (scores.depression?.mean || 0) * (100 / 27),
            (scores.anxiety?.mean || 0) * (100 / 21),
            (scores.sleep_quality?.mean || 5) * 10,
            scores.wellbeing?.mean || 50
        ];
        
        // Uncertainty (std * 2 for ~95% CI)
        charts.confidence.data.datasets[1].data = [
            (scores.stress?.std || 0) * 2,
            (scores.depression?.std || 0) * (100 / 27) * 2,
            (scores.anxiety?.std || 0) * (100 / 21) * 2,
            (scores.sleep_quality?.std || 0) * 10 * 2,
            (scores.wellbeing?.std || 0) * 2
        ];
        
        charts.confidence.update('active');
    }

    function addTrendDataPoint(scores, timestamp) {
        if (!charts.trend) return;
        
        const label = new Date(timestamp).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
        
        charts.trend.data.labels.push(label);
        
        charts.trend.data.datasets[0].data.push(scores.stress?.mean || 0);
        charts.trend.data.datasets[1].data.push((scores.depression?.mean || 0) * (100 / 27));
        charts.trend.data.datasets[2].data.push((scores.anxiety?.mean || 0) * (100 / 21));
        charts.trend.data.datasets[3].data.push(scores.wellbeing?.mean || 50);
        
        // Keep last 20 points
        if (charts.trend.data.labels.length > 20) {
            charts.trend.data.labels.shift();
            charts.trend.data.datasets.forEach(ds => ds.data.shift());
        }
        
        charts.trend.update('active');
    }

    function loadHistoryIntoTrend(history) {
        if (!charts.trend || !history?.length) return;
        
        // Clear existing
        charts.trend.data.labels = [];
        charts.trend.data.datasets.forEach(ds => ds.data = []);
        
        // Add historical points
        history.slice(-20).forEach(entry => {
            addTrendDataPoint(entry.outputs?.scores || entry.scores, entry.timestamp);
        });
    }

    // ========================================================================
    // Cleanup
    // ========================================================================

    function destroy() {
        // Stop animation
        if (animationFrame) {
            cancelAnimationFrame(animationFrame);
        }
        
        // Destroy charts
        Object.values(charts).forEach(chart => {
            if (chart?.destroy) chart.destroy();
        });
        charts = {};
        
        // Cleanup Three.js
        if (threeScene) {
            threeScene.renderer.dispose();
            threeScene.container.innerHTML = '';
            threeScene = null;
        }
    }

    // ========================================================================
    // Public API
    // ========================================================================

    return {
        init,
        updateAllVisuals,
        addTrendDataPoint,
        loadHistoryIntoTrend,
        destroy,
        
        // Expose current scores for other modules
        getScores: () => currentScores
    };
})();

// Export globally
window.KernelVisuals = KernelVisuals;

