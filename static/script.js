/**
 * The Empathy Engine - Frontend JavaScript
 * =========================================
 * Handles API communication, UI updates, waveform visualization,
 * and dynamic rendering of emotion analysis results.
 */

// ==========================================
// Constants & Config
// ==========================================

const API_BASE = '';

const EMOTION_EMOJIS = {
    happy: '😊',
    excited: '🤩',
    calm: '😌',
    neutral: '😐',
    concerned: '😟',
    surprised: '😲',
    inquisitive: '🤔',
    frustrated: '😠',
    sad: '😢'
};

const EMOTION_COLORS = {
    happy: '#fbbf24',
    excited: '#f472b6',
    calm: '#60a5fa',
    neutral: '#94a3b8',
    concerned: '#fb923c',
    surprised: '#a78bfa',
    inquisitive: '#22d3ee',
    frustrated: '#f87171',
    sad: '#818cf8'
};

const EMOTION_MAP_DATA = {
    happy: { rate: '1.10x', pitch: '+2.0st', volume: '1.05x', desc: 'Warm, slightly upbeat delivery', emoji: '😊' },
    excited: { rate: '1.25x', pitch: '+4.0st', volume: '1.15x', desc: 'Energetic, fast-paced, high-pitched', emoji: '🤩' },
    calm: { rate: '0.90x', pitch: '-1.0st', volume: '0.90x', desc: 'Slow, low-toned, gentle delivery', emoji: '😌' },
    neutral: { rate: '1.00x', pitch: '0.0st', volume: '1.00x', desc: 'Standard, unmodulated delivery', emoji: '😐' },
    concerned: { rate: '0.92x', pitch: '-0.5st', volume: '0.95x', desc: 'Measured, slightly cautious tone', emoji: '😟' },
    surprised: { rate: '1.15x', pitch: '+3.5st', volume: '1.10x', desc: 'Quick, high-pitched, emphatic', emoji: '😲' },
    inquisitive: { rate: '0.95x', pitch: '+1.5st', volume: '1.00x', desc: 'Thoughtful pace with rising intonation', emoji: '🤔' },
    frustrated: { rate: '1.12x', pitch: '-2.0st', volume: '1.20x', desc: 'Tense, loud, slightly clipped', emoji: '😠' },
    sad: { rate: '0.80x', pitch: '-3.0st', volume: '0.80x', desc: 'Slow, low, subdued delivery', emoji: '😢' }
};

// ==========================================
// DOM Elements
// ==========================================

const textInput = document.getElementById('textInput');
const charCount = document.getElementById('charCount');
const engineSelect = document.getElementById('engineSelect');
const synthesizeBtn = document.getElementById('synthesizeBtn');
const btnLoader = document.getElementById('btnLoader');
const resultsGrid = document.getElementById('resultsGrid');
const audioSection = document.getElementById('audioSection');
const audioPlayer = document.getElementById('audioPlayer');
const downloadBtn = document.getElementById('downloadBtn');
const waveformVisual = document.getElementById('waveformVisual');

// Emotion display elements
const emotionEmoji = document.getElementById('emotionEmoji');
const emotionName = document.getElementById('emotionName');
const emotionConfidence = document.getElementById('emotionConfidence');
const intensityValue = document.getElementById('intensityValue');
const intensityFill = document.getElementById('intensityFill');
const emotionBars = document.getElementById('emotionBars');

// Sentiment scores
const vaderScore = document.getElementById('vaderScore');
const polarityScore = document.getElementById('polarityScore');
const subjectivityScore = document.getElementById('subjectivityScore');

// Voice params
const rateValue = document.getElementById('rateValue');
const pitchValue = document.getElementById('pitchValue');
const volumeValue = document.getElementById('volumeValue');
const rateProgress = document.getElementById('rateProgress');
const pitchProgress = document.getElementById('pitchProgress');
const volumeProgress = document.getElementById('volumeProgress');
const voiceDescText = document.getElementById('voiceDescText');

// Processing info
const engineUsed = document.getElementById('engineUsed');
const audioDuration = document.getElementById('audioDuration');
const processingTime = document.getElementById('processingTime');

// State
let currentAudioUrl = null;

// ==========================================
// Initialization
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initWaveform();
    initEmotionMap();
    initEventListeners();
});

// ==========================================
// Event Listeners
// ==========================================

function initEventListeners() {
    // Text input
    textInput.addEventListener('input', () => {
        charCount.textContent = textInput.value.length;
        synthesizeBtn.disabled = textInput.value.trim().length === 0;
    });

    // Example chips
    document.querySelectorAll('.example-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            textInput.value = chip.dataset.text;
            charCount.textContent = textInput.value.length;
            synthesizeBtn.disabled = false;
            textInput.focus();
            
            // Animate the chip
            chip.style.transform = 'scale(0.95)';
            setTimeout(() => chip.style.transform = '', 150);
        });
    });

    // Synthesize button
    synthesizeBtn.addEventListener('click', handleSynthesize);

    // Download button
    downloadBtn.addEventListener('click', handleDownload);

    // Audio player events
    audioPlayer.addEventListener('play', () => startWaveformAnimation());
    audioPlayer.addEventListener('pause', () => stopWaveformAnimation());
    audioPlayer.addEventListener('ended', () => stopWaveformAnimation());

    // Keyboard shortcut: Ctrl+Enter to synthesize
    textInput.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !synthesizeBtn.disabled) {
            handleSynthesize();
        }
    });
}

// ==========================================
// API Calls
// ==========================================

async function handleSynthesize() {
    const text = textInput.value.trim();
    if (!text) return;

    // Set loading state
    synthesizeBtn.disabled = true;
    synthesizeBtn.classList.add('loading');

    try {
        const response = await fetch(`${API_BASE}/api/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                engine: engineSelect.value
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Synthesis failed');
        }

        const data = await response.json();
        updateUI(data);

    } catch (error) {
        showError(error.message);
    } finally {
        synthesizeBtn.disabled = false;
        synthesizeBtn.classList.remove('loading');
    }
}

// ==========================================
// UI Updates
// ==========================================

function updateUI(data) {
    const { emotion_analysis, voice_params, audio_url, duration_ms, processing_time_ms } = data;

    // Show results
    resultsGrid.style.display = 'grid';
    audioSection.style.display = 'block';

    // Update emotion display
    updateEmotionDisplay(emotion_analysis);

    // Update voice params
    updateVoiceParams(voice_params);

    // Update processing info
    engineUsed.textContent = voice_params.engine || engineSelect.value;
    audioDuration.textContent = formatDuration(duration_ms);
    processingTime.textContent = `${processing_time_ms}ms`;

    // Update audio player
    currentAudioUrl = audio_url;
    audioPlayer.src = audio_url;
    audioPlayer.load();

    // Scroll to results
    resultsGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateEmotionDisplay(analysis) {
    const emotion = analysis.emotion;

    // Emoji & name
    emotionEmoji.textContent = EMOTION_EMOJIS[emotion] || '🔍';
    emotionName.textContent = emotion;
    emotionName.style.background = `linear-gradient(135deg, ${EMOTION_COLORS[emotion] || '#a78bfa'}, ${EMOTION_COLORS[emotion] || '#60a5fa'}88)`;
    emotionName.style.webkitBackgroundClip = 'text';
    emotionName.style.webkitTextFillColor = 'transparent';
    emotionName.style.backgroundClip = 'text';

    // Confidence
    emotionConfidence.textContent = `${(analysis.confidence * 100).toFixed(0)}% confidence`;

    // Intensity
    const intensityPct = Math.round(analysis.intensity * 100);
    intensityValue.textContent = `${intensityPct}%`;
    intensityFill.style.width = `${intensityPct}%`;

    // Color the intensity bar based on emotion
    const color = EMOTION_COLORS[emotion] || '#a78bfa';
    intensityFill.style.background = `linear-gradient(90deg, ${color}88, ${color})`;

    // Emotion bars
    updateEmotionBars(analysis.all_emotions, emotion);

    // Sentiment scores
    vaderScore.textContent = analysis.vader_scores.compound.toFixed(3);
    polarityScore.textContent = analysis.textblob_scores.polarity.toFixed(3);
    subjectivityScore.textContent = analysis.textblob_scores.subjectivity.toFixed(3);

    // Color code sentiment scores
    colorScore(vaderScore, analysis.vader_scores.compound);
    colorScore(polarityScore, analysis.textblob_scores.polarity);
}

function colorScore(element, value) {
    if (value > 0.1) {
        element.style.color = '#34d399';
    } else if (value < -0.1) {
        element.style.color = '#f87171';
    } else {
        element.style.color = '#94a3b8';
    }
}

function updateEmotionBars(allEmotions, primaryEmotion) {
    // Sort emotions by score descending
    const sorted = Object.entries(allEmotions)
        .sort(([, a], [, b]) => b - a);

    emotionBars.innerHTML = sorted.map(([emotion, score]) => {
        const color = EMOTION_COLORS[emotion] || '#94a3b8';
        const width = Math.max(score * 100, 1);
        const isPrimary = emotion === primaryEmotion;

        return `
            <div class="emotion-bar-row" style="${isPrimary ? 'opacity: 1;' : 'opacity: 0.7;'}">
                <span class="emotion-bar-label">${EMOTION_EMOJIS[emotion] || ''} ${emotion}</span>
                <div class="emotion-bar-track">
                    <div class="emotion-bar-fill" style="width: ${width}%; background: ${color};"></div>
                </div>
                <span class="emotion-bar-value">${(score * 100).toFixed(0)}%</span>
            </div>
        `;
    }).join('');
}

function updateVoiceParams(params) {
    const rate = params.rate_multiplier;
    const pitch = params.pitch_shift_semitones;
    const volume = params.volume_multiplier;

    // Update text values
    rateValue.textContent = `${rate.toFixed(2)}x`;
    pitchValue.textContent = `${pitch >= 0 ? '+' : ''}${pitch.toFixed(1)}st`;
    volumeValue.textContent = `${volume.toFixed(2)}x`;

    // Update dial progress (0-314 dashoffset, where 314 = full circumference)
    // Map rate (0.7 - 1.3) → progress %
    const ratePercent = ((rate - 0.7) / 0.6) * 100;
    setDialProgress(rateProgress, ratePercent);

    // Map pitch (-4 to +4) → progress %
    const pitchPercent = ((pitch + 4) / 8) * 100;
    setDialProgress(pitchProgress, pitchPercent);

    // Map volume (0.7 - 1.3) → progress %
    const volumePercent = ((volume - 0.7) / 0.6) * 100;
    setDialProgress(volumeProgress, volumePercent);

    // Description
    voiceDescText.textContent = params.description;
}

function setDialProgress(element, percent) {
    const clamped = Math.max(0, Math.min(100, percent));
    const circumference = 314; // 2 * π * 50
    const offset = circumference - (circumference * clamped / 100);
    element.style.strokeDashoffset = offset;
}

// ==========================================
// Waveform Visualization
// ==========================================

function initWaveform() {
    const barCount = 50;
    waveformVisual.innerHTML = '';
    for (let i = 0; i < barCount; i++) {
        const bar = document.createElement('div');
        bar.className = 'waveform-bar';
        bar.style.height = '8px';
        bar.style.animationDelay = `${i * 0.05}s`;
        waveformVisual.appendChild(bar);
    }
}

function startWaveformAnimation() {
    document.querySelectorAll('.waveform-bar').forEach(bar => {
        bar.classList.add('active');
    });
}

function stopWaveformAnimation() {
    document.querySelectorAll('.waveform-bar').forEach(bar => {
        bar.classList.remove('active');
        bar.style.height = '8px';
    });
}

// ==========================================
// Background Particles
// ==========================================

function initParticles() {
    const container = document.getElementById('particles');
    const particleCount = 25;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';

        const size = Math.random() * 4 + 2;
        const left = Math.random() * 100;
        const duration = Math.random() * 15 + 10;
        const delay = Math.random() * 10;
        const hue = Math.random() * 60 + 220; // Blue-purple range

        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${left}%;
            background: hsla(${hue}, 70%, 65%, 0.4);
            animation-duration: ${duration}s;
            animation-delay: ${delay}s;
            box-shadow: 0 0 ${size * 2}px hsla(${hue}, 70%, 65%, 0.3);
        `;

        container.appendChild(particle);
    }
}

// ==========================================
// Emotion Map Reference
// ==========================================

function initEmotionMap() {
    const grid = document.getElementById('emotionMapGrid');

    grid.innerHTML = Object.entries(EMOTION_MAP_DATA).map(([emotion, data]) => {
        const color = EMOTION_COLORS[emotion] || '#94a3b8';
        return `
            <div class="map-card" style="border-left: 3px solid ${color};">
                <div class="map-card-header">
                    <span class="map-card-emoji">${data.emoji}</span>
                    <span class="map-card-name">${emotion}</span>
                </div>
                <div class="map-card-params">
                    <div class="map-param">
                        <span class="map-param-label">Rate</span>
                        <span class="map-param-value">${data.rate}</span>
                    </div>
                    <div class="map-param">
                        <span class="map-param-label">Pitch</span>
                        <span class="map-param-value">${data.pitch}</span>
                    </div>
                    <div class="map-param">
                        <span class="map-param-label">Volume</span>
                        <span class="map-param-value">${data.volume}</span>
                    </div>
                </div>
                <div class="map-card-desc">${data.desc}</div>
            </div>
        `;
    }).join('');
}

// ==========================================
// Download
// ==========================================

function handleDownload() {
    if (!currentAudioUrl) return;
    
    const link = document.createElement('a');
    link.href = currentAudioUrl;
    link.download = currentAudioUrl.split('/').pop();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ==========================================
// Utilities
// ==========================================

function formatDuration(ms) {
    if (!ms || ms <= 0) return '—';
    const seconds = (ms / 1000).toFixed(1);
    return `${seconds}s`;
}

function showError(message) {
    // Remove existing toast
    const existing = document.querySelector('.error-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = `⚠️ ${message}`;
    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('visible');
    });

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 400);
    }, 5000);
}
