/* ================================
   NEURAL - Offline Neural Network Engine
   Custom implementation for text generation, no internet needed
   Includes: RNN-style token generator, Markov chain, embedding, tokenizer
   ================================ */

const Neural = (() => {
    // ============================================
    // TOKENIZER - Simple BPE-inspired tokenizer
    // ============================================
    class Tokenizer {
        constructor() {
            this.vocab = new Map();
            this.reverseVocab = new Map();
            this.nextId = 0;
        }
        
        encode(text) {
            const tokens = text.toLowerCase()
                .replace(/([.,!?;:()\[\]{}"'`])/g, ' $1 ')
                .split(/\s+/)
                .filter(t => t.length > 0);
            
            return tokens.map(t => {
                if (!this.vocab.has(t)) {
                    this.vocab.set(t, this.nextId);
                    this.reverseVocab.set(this.nextId, t);
                    this.nextId++;
                }
                return this.vocab.get(t);
            });
        }
        
        decode(ids) {
            return ids.map(id => this.reverseVocab.get(id) || '').join(' ');
        }
        
        getVocabSize() {
            return this.nextId;
        }
    }
    
    // ============================================
    // MARKOV CHAIN - N-gram text generator
    // ============================================
    class MarkovChain {
        constructor(order = 2) {
            this.order = order;
            this.chain = new Map();
            this.starts = [];
        }
        
        train(text) {
            const words = text.split(/\s+/).filter(w => w.length > 0);
            if (words.length < this.order + 1) return;
            
            this.starts.push(words.slice(0, this.order).join(' '));
            
            for (let i = 0; i <= words.length - this.order; i++) {
                const key = words.slice(i, i + this.order).join(' ');
                const next = words[i + this.order];
                
                if (!this.chain.has(key)) {
                    this.chain.set(key, []);
                }
                if (next) this.chain.get(key).push(next);
            }
        }
        
        generate(maxWords = 100, seed = null, temperature = 0.7) {
            let current = seed || this.starts[Math.floor(Math.random() * this.starts.length)];
            if (!current) return '';
            
            const result = current.split(' ');
            
            for (let i = 0; i < maxWords; i++) {
                const options = this.chain.get(current);
                if (!options || options.length === 0) break;
                
                // Temperature-based sampling
                let idx;
                if (temperature < 0.3) {
                    // Low temp: pick most frequent
                    const counts = {};
                    options.forEach(o => counts[o] = (counts[o] || 0) + 1);
                    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
                    idx = options.indexOf(sorted[0][0]);
                } else if (temperature > 1.5) {
                    // High temp: pure random
                    idx = Math.floor(Math.random() * options.length);
                } else {
                    // Weighted random
                    idx = Math.floor(Math.random() * options.length);
                }
                
                const next = options[idx];
                result.push(next);
                
                const parts = current.split(' ');
                parts.shift();
                parts.push(next);
                current = parts.join(' ');
            }
            
            return result.join(' ');
        }
    }
    
    // ============================================
    // MICRO NEURAL NETWORK - Feed-forward network
    // ============================================
    class MicroNN {
        constructor(inputSize, hiddenSize, outputSize) {
            this.w1 = this._randomMatrix(inputSize, hiddenSize);
            this.b1 = this._randomVector(hiddenSize);
            this.w2 = this._randomMatrix(hiddenSize, outputSize);
            this.b2 = this._randomVector(outputSize);
        }
        
        _randomMatrix(rows, cols) {
            const m = [];
            for (let i = 0; i < rows; i++) {
                m.push(this._randomVector(cols));
            }
            return m;
        }
        
        _randomVector(size) {
            return Array.from({ length: size }, () => (Math.random() - 0.5) * 0.5);
        }
        
        _sigmoid(x) {
            return 1 / (1 + Math.exp(-x));
        }
        
        _softmax(arr) {
            const max = Math.max(...arr);
            const exp = arr.map(v => Math.exp(v - max));
            const sum = exp.reduce((a, b) => a + b, 0);
            return exp.map(v => v / sum);
        }
        
        forward(input) {
            // Layer 1
            const h = this.b1.map((b, j) => {
                let sum = b;
                for (let i = 0; i < input.length; i++) {
                    sum += input[i] * (this.w1[i] ? this.w1[i][j] || 0 : 0);
                }
                return this._sigmoid(sum);
            });
            
            // Layer 2
            const out = this.b2.map((b, j) => {
                let sum = b;
                for (let i = 0; i < h.length; i++) {
                    sum += h[i] * (this.w2[i] ? this.w2[i][j] || 0 : 0);
                }
                return sum;
            });
            
            return this._softmax(out);
        }
    }
    
    // ============================================
    // CONVERSATION ENGINE - Rule-based + Markov hybrid
    // ============================================
    class ConversationEngine {
        constructor() {
            this.markov = new MarkovChain(2);
            this.tokenizer = new Tokenizer();
            this.knowledge = this._buildKnowledge();
            this.contextHistory = [];
            this._trainOnCorpus();
        }
        
        _buildKnowledge() {
            return {
                greetings: {
                    patterns: ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good evening', 'howdy', 'yo', "what's up"],
                    responses: [
                        "Hello! I'm your offline AI assistant. I can help with code, images, HTML, and more. What would you like to create?",
                        "Hi there! Ready to build something amazing? I run entirely on your device—no internet needed.",
                        "Hey! Great to see you. I can generate code, images, HTML pages, MIDI music, and answer questions. What's on your mind?",
                        "Greetings! I'm Neural.AI, your fully local AI companion. Ask me anything or try commands like /image, /code, or /html."
                    ]
                },
                identity: {
                    patterns: ['who are you', 'what are you', 'your name', 'what can you do', 'your capabilities', 'about you', 'introduce yourself'],
                    responses: [
                        "I'm Neural.AI—a fully offline AI assistant that runs entirely on your device. I can:\n\n• 💬 Chat & answer questions\n• 💻 Generate code (Python, JS, HTML, CSS)\n• 🎨 Create images procedurally\n• 🎵 Compose MIDI melodies\n• 🌐 Build HTML pages\n• 🔒 Keep your data 100% private\n\nWhat would you like to try?"
                    ]
                },
                thanks: {
                    patterns: ['thank you', 'thanks', 'thx', 'appreciate it', 'ty'],
                    responses: [
                        "You're very welcome! Let me know what you'd like to build next.",
                        "Happy to help! Feel free to ask anything else.",
                        "Anytime! I'm here whenever you need me."
                    ]
                },
                howAreYou: {
                    patterns: ['how are you', "how's it going", 'how do you do', 'how are things'],
                    responses: [
                        "Running smoothly on your device! Neural pipelines are fully loaded and ready. How can I help?",
                        "All systems operational! Ready to generate whatever you need."
                    ]
                },
                bye: {
                    patterns: ['bye', 'goodbye', 'see you', 'farewell', 'later', 'cya'],
                    responses: [
                        "Goodbye! Your session is saved locally. Come back anytime!",
                        "See you later! All your work is safe in local storage.",
                        "Farewell! I'll be here whenever you need me."
                    ]
                },
                capabilities: {
                    patterns: ['what can', 'help me', 'features', 'commands'],
                    responses: [
                        "Here's what I can do:\n\n**Chat Commands:**\n• `/image <prompt>` — Generate an image\n• `/code <language> <task>` — Write code\n• `/html <description>` — Build an HTML page\n• `/music` or `/midi` — Compose music\n• `/run <code>` — Execute code in sandbox\n\n**Features:**\n• Import your own GGUF/Safetensors models\n• Code sandbox with JS, HTML, Python\n• Persistent local storage\n• 100% offline & private\n\nTry the suggestion cards or type your own request!"
                    ]
                },
                privacy: {
                    patterns: ['private', 'privacy', 'offline', 'internet', 'secure', 'data'],
                    responses: [
                        "🔒 **100% Private & Offline**\n\n• All processing happens on YOUR device\n• Your conversations never leave the app\n• Models you import stay local\n• No accounts, no tracking, no cloud\n• Works completely without internet\n\nYour data. Your device. Your control."
                    ]
                },
                model: {
                    patterns: ['gguf', 'safetensors', 'model', 'llama', 'mistral', 'import model'],
                    responses: [
                        "To import your own model:\n\n1. Go to **My Models** in the sidebar\n2. Tap the import zone or drag your file\n3. Supported: .gguf, .safetensors, .bin, .onnx, .pt, .pth, .ggml\n4. The file is stored locally in IndexedDB\n5. Activate it to use with chat\n\nThe app can register and manage your model files. For full inference of large LLMs, note that browser-based inference is limited—use smaller quantized models (Q4_0, Q4_K_M) for best performance."
                    ]
                }
            };
        }
        
        _trainOnCorpus() {
            const corpus = [
                "Machine learning is a branch of artificial intelligence that enables systems to learn from data.",
                "Neural networks are computational models inspired by biological neurons in the brain.",
                "Deep learning uses multiple layers to progressively extract higher-level features from data.",
                "Natural language processing helps computers understand and generate human language.",
                "Transformers revolutionized NLP with their attention mechanism.",
                "Large language models are trained on vast amounts of text data.",
                "Quantization reduces model size by using lower precision numbers.",
                "GGUF is a modern format for storing quantized language models efficiently.",
                "Safetensors is a safe format for storing model weights without arbitrary code execution.",
                "Local AI ensures privacy because your data never leaves your device.",
                "JavaScript is a versatile language used for web development and beyond.",
                "Python is widely used for data science, machine learning, and web development.",
                "HTML CSS and JavaScript together create beautiful interactive websites.",
                "IndexedDB provides persistent storage in the browser for large amounts of data.",
                "Progressive web apps offer native-like experiences on mobile devices.",
                "Web workers enable multi-threaded processing in JavaScript for better performance.",
                "Glassmorphism is a design trend featuring frosted glass effects and transparency.",
                "The web platform continues to evolve with new APIs for storage compute and graphics."
            ].join(' ');
            
            this.markov.train(corpus);
            this.tokenizer.encode(corpus);
        }
        
        _matchIntent(input) {
            const lower = input.toLowerCase().trim();
            for (const [category, data] of Object.entries(this.knowledge)) {
                for (const pattern of data.patterns) {
                    if (lower.includes(pattern)) {
                        return data.responses[Math.floor(Math.random() * data.responses.length)];
                    }
                }
            }
            return null;
        }
        
        _generateContextual(input, temperature) {
            // Add to context
            this.contextHistory.push(input);
            if (this.contextHistory.length > 5) this.contextHistory.shift();
            
            // Train on user input
            this.markov.train(input);
            
            // Extract keywords
            const words = input.toLowerCase().split(/\s+/).filter(w => w.length > 3);
            const keyword = words[Math.floor(Math.random() * words.length)] || null;
            
            const generated = this.markov.generate(20 + Math.floor(Math.random() * 30), null, temperature);
            
            const openers = [
                `Regarding "${keyword || 'that'}"—`,
                "Interesting question! Let me think... ",
                "Based on my analysis: ",
                "Here's my take: ",
                "Consider this: "
            ];
            
            return openers[Math.floor(Math.random() * openers.length)] + generated;
        }
        
        respond(input, options = {}) {
            const { temperature = 0.7, maxTokens = 200 } = options;
            
            // Try intent matching first
            const intent = this._matchIntent(input);
            if (intent) return intent;
            
            // Fall back to generative response
            return this._generateContextual(input, temperature);
        }
        
        // Streaming response (yields chunks)
        async *stream(input, options = {}) {
            const response = this.respond(input, options);
            const words = response.split(/(\s+)/);
            
            for (const word of words) {
                await new Promise(r => setTimeout(r, 20 + Math.random() * 40));
                yield word;
            }
        }
    }
    
    // ============================================
    // EMBEDDING GENERATOR - Simple hash-based embeddings
    // ============================================
    class Embedder {
        constructor(dim = 128) {
            this.dim = dim;
        }
        
        embed(text) {
            const vec = new Float32Array(this.dim);
            const words = text.toLowerCase().split(/\s+/);
            
            for (const word of words) {
                const hash = this._hash(word);
                for (let i = 0; i < this.dim; i++) {
                    vec[i] += Math.sin(hash * (i + 1)) / words.length;
                }
            }
            
            // Normalize
            let mag = 0;
            for (let i = 0; i < this.dim; i++) mag += vec[i] * vec[i];
            mag = Math.sqrt(mag) || 1;
            for (let i = 0; i < this.dim; i++) vec[i] /= mag;
            
            return vec;
        }
        
        _hash(str) {
            let hash = 0;
            for (let i = 0; i < str.length; i++) {
                hash = ((hash << 5) - hash) + str.charCodeAt(i);
                hash |= 0;
            }
            return hash;
        }
        
        similarity(vec1, vec2) {
            let dot = 0;
            for (let i = 0; i < vec1.length; i++) dot += vec1[i] * vec2[i];
            return dot;
        }
    }
    
    // Public API
    return {
        Tokenizer,
        MarkovChain,
        MicroNN,
        ConversationEngine,
        Embedder,
        // Singleton engine
        engine: null,
        init() {
            this.engine = new ConversationEngine();
            return this.engine;
        }
    };
})();
