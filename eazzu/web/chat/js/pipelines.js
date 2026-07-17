/* ================================
   PIPELINES - Content Generation Backends
   Image, HTML, Code, MIDI, Audio generation
   All fully offline - no external calls
   ================================ */

const Pipelines = (() => {
    
    // ============================================
    // IMAGE GENERATION PIPELINE
    // Procedural, algorithmic image synthesis
    // ============================================
    const ImagePipeline = {
        async generate(prompt, options = {}) {
            const { width = 512, height = 512 } = options;
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            
            // Hash prompt to deterministic seed
            const seed = this._hashPrompt(prompt);
            const rng = this._createRNG(seed);
            
            // Analyze prompt for style hints
            const style = this._analyzeStyle(prompt.toLowerCase());
            
            // Render based on style
            switch (style.type) {
                case 'landscape':
                    this._renderLandscape(ctx, width, height, rng, style);
                    break;
                case 'abstract':
                    this._renderAbstract(ctx, width, height, rng, style);
                    break;
                case 'geometric':
                    this._renderGeometric(ctx, width, height, rng, style);
                    break;
                case 'space':
                    this._renderSpace(ctx, width, height, rng, style);
                    break;
                case 'city':
                    this._renderCity(ctx, width, height, rng, style);
                    break;
                default:
                    this._renderNeural(ctx, width, height, rng, style);
            }
            
            // Add prompt watermark
            this._addWatermark(ctx, width, height, prompt);
            
            return canvas.toDataURL('image/png');
        },
        
        _hashPrompt(prompt) {
            let hash = 5381;
            for (let i = 0; i < prompt.length; i++) {
                hash = ((hash << 5) + hash) + prompt.charCodeAt(i);
            }
            return Math.abs(hash);
        },
        
        _createRNG(seed) {
            let state = seed;
            return () => {
                state = (state * 9301 + 49297) % 233280;
                return state / 233280;
            };
        },
        
        _analyzeStyle(prompt) {
            const style = { type: 'neural', colors: [] };
            
            if (/landscape|mountain|forest|nature|sunset|sunrise|ocean|beach|sky/.test(prompt)) style.type = 'landscape';
            else if (/abstract|art|painting|creative/.test(prompt)) style.type = 'abstract';
            else if (/geometric|pattern|shape|hexagon|triangle/.test(prompt)) style.type = 'geometric';
            else if (/space|galaxy|star|nebula|cosmic|planet/.test(prompt)) style.type = 'space';
            else if (/city|urban|building|street|architecture|futuristic/.test(prompt)) style.type = 'city';
            
            // Extract color hints
            const colorMap = {
                red: '#ef4444', blue: '#3b82f6', green: '#10b981',
                yellow: '#f59e0b', purple: '#8b5cf6', pink: '#ec4899',
                orange: '#f97316', cyan: '#06b6d4', dark: '#1f2937',
                warm: '#f97316', cool: '#3b82f6', neon: '#ec4899'
            };
            
            for (const [word, color] of Object.entries(colorMap)) {
                if (prompt.includes(word)) style.colors.push(color);
            }
            
            if (style.colors.length === 0) {
                style.colors = ['#6366f1', '#8b5cf6', '#ec4899'];
            }
            
            return style;
        },
        
        _renderLandscape(ctx, w, h, rng, style) {
            // Sky gradient
            const skyGrad = ctx.createLinearGradient(0, 0, 0, h * 0.7);
            skyGrad.addColorStop(0, style.colors[0]);
            skyGrad.addColorStop(1, style.colors[1] || '#f97316');
            ctx.fillStyle = skyGrad;
            ctx.fillRect(0, 0, w, h * 0.7);
            
            // Sun
            const sunX = w * (0.3 + rng() * 0.4);
            const sunY = h * (0.2 + rng() * 0.3);
            const sunGrad = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, 80);
            sunGrad.addColorStop(0, 'rgba(255, 220, 100, 1)');
            sunGrad.addColorStop(1, 'rgba(255, 220, 100, 0)');
            ctx.fillStyle = sunGrad;
            ctx.fillRect(sunX - 100, sunY - 100, 200, 200);
            
            // Mountains (multiple layers)
            for (let layer = 0; layer < 3; layer++) {
                ctx.fillStyle = `rgba(30, 30, 50, ${0.4 + layer * 0.2})`;
                ctx.beginPath();
                ctx.moveTo(0, h);
                const baseY = h * (0.5 + layer * 0.1);
                let x = 0;
                while (x < w) {
                    const peakH = 50 + rng() * 100;
                    ctx.lineTo(x + 30, baseY - peakH);
                    ctx.lineTo(x + 60, baseY);
                    x += 60;
                }
                ctx.lineTo(w, h);
                ctx.closePath();
                ctx.fill();
            }
            
            // Ground
            ctx.fillStyle = style.colors[2] || '#065f46';
            ctx.fillRect(0, h * 0.7, w, h * 0.3);
        },
        
        _renderAbstract(ctx, w, h, rng, style) {
            // Background
            const grad = ctx.createLinearGradient(0, 0, w, h);
            grad.addColorStop(0, style.colors[0]);
            grad.addColorStop(1, style.colors[1] || style.colors[0]);
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, w, h);
            
            // Abstract shapes
            for (let i = 0; i < 30; i++) {
                ctx.fillStyle = style.colors[Math.floor(rng() * style.colors.length)] + '55';
                ctx.beginPath();
                const x = rng() * w;
                const y = rng() * h;
                const r = 20 + rng() * 150;
                ctx.arc(x, y, r, 0, Math.PI * 2);
                ctx.fill();
            }
            
            // Lines
            ctx.strokeStyle = 'rgba(255,255,255,0.3)';
            ctx.lineWidth = 2;
            for (let i = 0; i < 20; i++) {
                ctx.beginPath();
                ctx.moveTo(rng() * w, rng() * h);
                ctx.lineTo(rng() * w, rng() * h);
                ctx.stroke();
            }
        },
        
        _renderGeometric(ctx, w, h, rng, style) {
            ctx.fillStyle = '#0a0a1a';
            ctx.fillRect(0, 0, w, h);
            
            const size = 40;
            for (let y = 0; y < h; y += size) {
                for (let x = 0; x < w; x += size) {
                    const c = style.colors[Math.floor(rng() * style.colors.length)];
                    ctx.fillStyle = c + Math.floor(rng() * 200 + 55).toString(16).padStart(2, '0');
                    
                    ctx.beginPath();
                    const shape = Math.floor(rng() * 3);
                    if (shape === 0) {
                        // Hexagon
                        for (let i = 0; i < 6; i++) {
                            const angle = (i / 6) * Math.PI * 2;
                            const px = x + size/2 + Math.cos(angle) * size/2.5;
                            const py = y + size/2 + Math.sin(angle) * size/2.5;
                            if (i === 0) ctx.moveTo(px, py);
                            else ctx.lineTo(px, py);
                        }
                    } else if (shape === 1) {
                        ctx.arc(x + size/2, y + size/2, size/2.5, 0, Math.PI * 2);
                    } else {
                        ctx.rect(x + 5, y + 5, size - 10, size - 10);
                    }
                    ctx.closePath();
                    ctx.fill();
                }
            }
        },
        
        _renderSpace(ctx, w, h, rng, style) {
            // Deep space background
            const bgGrad = ctx.createRadialGradient(w/2, h/2, 0, w/2, h/2, w);
            bgGrad.addColorStop(0, '#1a0033');
            bgGrad.addColorStop(0.5, '#0a0a1a');
            bgGrad.addColorStop(1, '#000000');
            ctx.fillStyle = bgGrad;
            ctx.fillRect(0, 0, w, h);
            
            // Nebula
            for (let i = 0; i < 5; i++) {
                const x = rng() * w;
                const y = rng() * h;
                const r = 100 + rng() * 200;
                const nebGrad = ctx.createRadialGradient(x, y, 0, x, y, r);
                nebGrad.addColorStop(0, style.colors[i % style.colors.length] + '80');
                nebGrad.addColorStop(1, 'transparent');
                ctx.fillStyle = nebGrad;
                ctx.fillRect(x - r, y - r, r * 2, r * 2);
            }
            
            // Stars
            for (let i = 0; i < 300; i++) {
                const x = rng() * w;
                const y = rng() * h;
                const size = rng() * 2;
                ctx.fillStyle = `rgba(255, 255, 255, ${rng()})`;
                ctx.fillRect(x, y, size, size);
            }
            
            // Bright stars
            for (let i = 0; i < 20; i++) {
                const x = rng() * w;
                const y = rng() * h;
                const grad = ctx.createRadialGradient(x, y, 0, x, y, 15);
                grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
                grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
                ctx.fillStyle = grad;
                ctx.fillRect(x - 15, y - 15, 30, 30);
            }
        },
        
        _renderCity(ctx, w, h, rng, style) {
            // Sky
            const skyGrad = ctx.createLinearGradient(0, 0, 0, h * 0.6);
            skyGrad.addColorStop(0, '#1a0033');
            skyGrad.addColorStop(1, style.colors[0]);
            ctx.fillStyle = skyGrad;
            ctx.fillRect(0, 0, w, h * 0.6);
            
            // Moon/sun
            const moonX = w * 0.75;
            const moonY = h * 0.2;
            ctx.fillStyle = '#fef3c7';
            ctx.beginPath();
            ctx.arc(moonX, moonY, 40, 0, Math.PI * 2);
            ctx.fill();
            
            // Buildings
            let x = 0;
            while (x < w) {
                const bw = 40 + rng() * 60;
                const bh = 100 + rng() * 300;
                const by = h - bh;
                
                ctx.fillStyle = `rgba(20, 20, 40, ${0.8 + rng() * 0.2})`;
                ctx.fillRect(x, by, bw, bh);
                
                // Windows
                ctx.fillStyle = style.colors[Math.floor(rng() * style.colors.length)];
                for (let wy = by + 15; wy < h - 20; wy += 15) {
                    for (let wx = x + 5; wx < x + bw - 5; wx += 12) {
                        if (rng() > 0.4) {
                            ctx.globalAlpha = 0.6 + rng() * 0.4;
                            ctx.fillRect(wx, wy, 6, 8);
                        }
                    }
                }
                ctx.globalAlpha = 1;
                
                x += bw + 2;
            }
            
            // Reflection
            const refGrad = ctx.createLinearGradient(0, h * 0.9, 0, h);
            refGrad.addColorStop(0, 'rgba(0,0,0,0)');
            refGrad.addColorStop(1, style.colors[1] + '40');
            ctx.fillStyle = refGrad;
            ctx.fillRect(0, h * 0.9, w, h * 0.1);
        },
        
        _renderNeural(ctx, w, h, rng, style) {
            // Neural network visualization
            const grad = ctx.createLinearGradient(0, 0, w, h);
            grad.addColorStop(0, '#0a0a1a');
            grad.addColorStop(1, '#1a0a2a');
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, w, h);
            
            // Nodes
            const layers = [4, 8, 8, 6, 4];
            const nodes = [];
            layers.forEach((count, li) => {
                const x = (w / (layers.length + 1)) * (li + 1);
                for (let i = 0; i < count; i++) {
                    const y = (h / (count + 1)) * (i + 1);
                    nodes.push({ x, y, layer: li });
                }
            });
            
            // Connections
            ctx.lineWidth = 1;
            nodes.forEach(n1 => {
                nodes.forEach(n2 => {
                    if (n2.layer === n1.layer + 1) {
                        const alpha = 0.1 + rng() * 0.3;
                        ctx.strokeStyle = style.colors[0] + Math.floor(alpha * 255).toString(16).padStart(2, '0');
                        ctx.beginPath();
                        ctx.moveTo(n1.x, n1.y);
                        ctx.lineTo(n2.x, n2.y);
                        ctx.stroke();
                    }
                });
            });
            
            // Nodes
            nodes.forEach(n => {
                const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, 20);
                g.addColorStop(0, style.colors[n.layer % style.colors.length]);
                g.addColorStop(1, 'transparent');
                ctx.fillStyle = g;
                ctx.fillRect(n.x - 20, n.y - 20, 40, 40);
                
                ctx.fillStyle = 'white';
                ctx.beginPath();
                ctx.arc(n.x, n.y, 4, 0, Math.PI * 2);
                ctx.fill();
            });
        },
        
        _addWatermark(ctx, w, h, prompt) {
            const truncated = prompt.length > 40 ? prompt.slice(0, 40) + '...' : prompt;
            ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
            ctx.fillRect(0, h - 24, w, 24);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
            ctx.font = '11px sans-serif';
            ctx.fillText(`Neural.AI • ${truncated}`, 8, h - 8);
        }
    };
    
    // ============================================
    // HTML GENERATION PIPELINE
    // ============================================
    const HTMLPipeline = {
        generate(prompt) {
            const lower = prompt.toLowerCase();
            let template = 'landing';
            
            if (/dashboard|admin|panel/.test(lower)) template = 'dashboard';
            else if (/form|contact|signup|login/.test(lower)) template = 'form';
            else if (/portfolio|about|resume/.test(lower)) template = 'portfolio';
            else if (/card|profile|product/.test(lower)) template = 'card';
            else if (/blog|article/.test(lower)) template = 'blog';
            
            return this._templates[template](prompt);
        },
        
        _templates: {
            landing: (prompt) => `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Generated Landing Page</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; color: white; }
.hero { display: flex; align-items: center; justify-content: center; min-height: 100vh; text-align: center; padding: 20px; }
.container { max-width: 700px; }
h1 { font-size: clamp(2rem, 6vw, 4rem); margin-bottom: 20px; font-weight: 800; }
p { font-size: 1.2rem; opacity: 0.9; margin-bottom: 30px; }
.btn { display: inline-block; padding: 14px 32px; background: white; color: #667eea; border: none; font-size: 1rem; font-weight: 600; border-radius: 50px; cursor: pointer; text-decoration: none; transition: transform 0.2s; }
.btn:hover { transform: translateY(-2px); }
.card { background: rgba(255,255,255,0.1); backdrop-filter: blur(20px); padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.2); }
</style>
</head>
<body>
<section class="hero">
<div class="container">
<div class="card">
<h1>${this._extractTitle(prompt)}</h1>
<p>${this._extractDesc(prompt)}</p>
<a href="#" class="btn">Get Started</a>
</div>
</div>
</section>
</body>
</html>`,
            
            dashboard: (prompt) => `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Dashboard</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: sans-serif; }
body { background: #0f172a; color: white; padding: 20px; }
.header { display: flex; justify-content: space-between; margin-bottom: 30px; }
.header h1 { font-size: 28px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
.card { background: linear-gradient(135deg, #1e293b, #334155); padding: 24px; border-radius: 12px; border: 1px solid #475569; }
.stat { font-size: 32px; font-weight: 700; color: #60a5fa; margin-bottom: 4px; }
.label { font-size: 14px; color: #94a3b8; }
</style></head>
<body>
<div class="header"><h1>${this._extractTitle(prompt)}</h1></div>
<div class="grid">
<div class="card"><div class="stat">1,234</div><div class="label">Total Users</div></div>
<div class="card"><div class="stat">$45.6K</div><div class="label">Revenue</div></div>
<div class="card"><div class="stat">89%</div><div class="label">Growth</div></div>
<div class="card"><div class="stat">567</div><div class="label">Active Now</div></div>
</div>
</body></html>`,
            
            form: (prompt) => `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Form</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: sans-serif; }
body { background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
.form-card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); max-width: 400px; width: 100%; }
h2 { margin-bottom: 24px; color: #1f2937; }
.field { margin-bottom: 16px; }
label { display: block; margin-bottom: 6px; font-weight: 500; color: #374151; font-size: 14px; }
input, textarea { width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; outline: none; }
input:focus, textarea:focus { border-color: #667eea; }
.btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 8px; }
</style></head>
<body>
<div class="form-card">
<h2>${this._extractTitle(prompt)}</h2>
<div class="field"><label>Name</label><input type="text" placeholder="Your name"></div>
<div class="field"><label>Email</label><input type="email" placeholder="you@example.com"></div>
<div class="field"><label>Message</label><textarea rows="4" placeholder="Your message"></textarea></div>
<button class="btn">Submit</button>
</div>
</body></html>`,
            
            portfolio: (prompt) => `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Portfolio</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: sans-serif; }
body { background: #fafafa; color: #1f2937; }
.hero { padding: 80px 20px; text-align: center; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; }
.avatar { width: 120px; height: 120px; border-radius: 50%; background: white; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; font-size: 48px; color: #6366f1; font-weight: 700; }
h1 { font-size: 42px; margin-bottom: 8px; }
.tagline { opacity: 0.9; font-size: 18px; }
.section { padding: 60px 20px; max-width: 900px; margin: 0 auto; }
.section h2 { font-size: 28px; margin-bottom: 24px; }
.projects { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
.project { padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
</style></head>
<body>
<section class="hero">
<div class="avatar">A</div>
<h1>${this._extractTitle(prompt)}</h1>
<p class="tagline">Developer • Designer • Creator</p>
</section>
<section class="section">
<h2>Projects</h2>
<div class="projects">
<div class="project"><h3>Project One</h3><p>Description of project one.</p></div>
<div class="project"><h3>Project Two</h3><p>Description of project two.</p></div>
<div class="project"><h3>Project Three</h3><p>Description of project three.</p></div>
</div>
</section>
</body></html>`,
            
            card: (prompt) => `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Card</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: sans-serif; }
body { background: linear-gradient(135deg, #f093fb, #f5576c); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
.card { background: rgba(255,255,255,0.15); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.3); border-radius: 24px; padding: 40px; max-width: 340px; color: white; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.icon { width: 80px; height: 80px; background: rgba(255,255,255,0.2); border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; font-size: 40px; }
h2 { font-size: 24px; margin-bottom: 8px; }
p { opacity: 0.9; margin-bottom: 20px; line-height: 1.6; }
.btn { padding: 12px 24px; background: white; color: #f5576c; border: none; border-radius: 50px; font-weight: 600; cursor: pointer; }
</style></head>
<body>
<div class="card">
<div class="icon">✨</div>
<h2>${this._extractTitle(prompt)}</h2>
<p>${this._extractDesc(prompt)}</p>
<button class="btn">Learn More</button>
</div>
</body></html>`,
            
            blog: (prompt) => `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Blog</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family: Georgia, serif; }
body { background: #fafafa; color: #1f2937; line-height: 1.7; }
.container { max-width: 700px; margin: 0 auto; padding: 60px 20px; }
h1 { font-size: 42px; margin-bottom: 12px; }
.meta { color: #6b7280; margin-bottom: 40px; font-size: 14px; }
h2 { margin: 32px 0 16px; font-size: 26px; }
p { margin-bottom: 16px; font-size: 17px; }
</style></head>
<body>
<article class="container">
<h1>${this._extractTitle(prompt)}</h1>
<div class="meta">Published today • 5 min read</div>
<p>${this._extractDesc(prompt)}</p>
<h2>Introduction</h2>
<p>This is the introduction to your article. Add your compelling opening here to hook readers.</p>
<h2>Main Content</h2>
<p>Your main content goes here. Elaborate on your ideas and share valuable insights.</p>
<h2>Conclusion</h2>
<p>Wrap up your article with key takeaways and a call to action.</p>
</article>
</body></html>`
        },
        
        _extractTitle(prompt) {
            const words = prompt.replace(/create|build|make|generate|html|page|for|a|an|the/gi, '').trim();
            const clean = words.split(/[.,!?]/)[0].trim();
            return clean ? clean.charAt(0).toUpperCase() + clean.slice(1, 60) : 'Welcome';
        },
        
        _extractDesc(prompt) {
            const clean = prompt.charAt(0).toUpperCase() + prompt.slice(1);
            return clean.length > 120 ? clean.slice(0, 120) + '...' : clean;
        }
    };
    
    // ============================================
    // CODE GENERATION PIPELINE
    // ============================================
    const CodePipeline = {
        generate(prompt, language = null) {
            const lower = prompt.toLowerCase();
            
            // Detect language
            if (!language) {
                if (/python|py\b/.test(lower)) language = 'python';
                else if (/javascript|js\b|node/.test(lower)) language = 'javascript';
                else if (/html|css/.test(lower)) language = 'html';
                else if (/react/.test(lower)) language = 'jsx';
                else language = 'javascript';
            }
            
            // Match task
            let code = '';
            if (/fibonacci/.test(lower)) code = this._fibonacci(language);
            else if (/sort|quicksort|bubble/.test(lower)) code = this._sort(language);
            else if (/prime/.test(lower)) code = this._prime(language);
            else if (/factorial/.test(lower)) code = this._factorial(language);
            else if (/reverse.*string|palindrome/.test(lower)) code = this._reverse(language);
            else if (/fetch|api|http|request/.test(lower)) code = this._api(language);
            else if (/class|object/.test(lower)) code = this._class(language);
            else if (/array|list/.test(lower)) code = this._array(language);
            else if (/hello|world/.test(lower)) code = this._hello(language);
            else code = this._general(language, prompt);
            
            return { language, code };
        },
        
        _fibonacci(lang) {
            if (lang === 'python') return `def fibonacci(n):
    """Generate fibonacci sequence up to n terms"""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    seq = [0, 1]
    for i in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq

# Example usage
print(fibonacci(10))
# Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]`;
            return `function fibonacci(n) {
    if (n <= 0) return [];
    if (n === 1) return [0];
    
    const seq = [0, 1];
    for (let i = 2; i < n; i++) {
        seq.push(seq[i - 1] + seq[i - 2]);
    }
    return seq;
}

console.log(fibonacci(10));
// Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]`;
        },
        
        _sort(lang) {
            if (lang === 'python') return `def quicksort(arr):
    """Sort array using quicksort algorithm"""
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quicksort(left) + middle + quicksort(right)

# Example
nums = [3, 6, 8, 10, 1, 2, 1]
print(quicksort(nums))
# Output: [1, 1, 2, 3, 6, 8, 10]`;
            return `function quicksort(arr) {
    if (arr.length <= 1) return arr;
    
    const pivot = arr[Math.floor(arr.length / 2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    
    return [...quicksort(left), ...middle, ...quicksort(right)];
}

const nums = [3, 6, 8, 10, 1, 2, 1];
console.log(quicksort(nums));
// Output: [1, 1, 2, 3, 6, 8, 10]`;
        },
        
        _prime(lang) {
            if (lang === 'python') return `def is_prime(n):
    """Check if a number is prime"""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

def primes_up_to(limit):
    """Get all primes up to limit"""
    return [n for n in range(2, limit + 1) if is_prime(n)]

print(primes_up_to(30))
# Output: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`;
            return `function isPrime(n) {
    if (n < 2) return false;
    for (let i = 2; i <= Math.sqrt(n); i++) {
        if (n % i === 0) return false;
    }
    return true;
}

function primesUpTo(limit) {
    const primes = [];
    for (let n = 2; n <= limit; n++) {
        if (isPrime(n)) primes.push(n);
    }
    return primes;
}

console.log(primesUpTo(30));
// Output: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`;
        },
        
        _factorial(lang) {
            if (lang === 'python') return `def factorial(n):
    """Calculate factorial recursively"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))  # 120
print(factorial(10)) # 3628800`;
            return `function factorial(n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

console.log(factorial(5));   // 120
console.log(factorial(10));  // 3628800`;
        },
        
        _reverse(lang) {
            if (lang === 'python') return `def reverse_string(s):
    """Reverse a string"""
    return s[::-1]

def is_palindrome(s):
    """Check if string is palindrome"""
    clean = s.lower().replace(' ', '')
    return clean == clean[::-1]

print(reverse_string("Hello World"))  # dlroW olleH
print(is_palindrome("racecar"))       # True`;
            return `function reverseString(s) {
    return s.split('').reverse().join('');
}

function isPalindrome(s) {
    const clean = s.toLowerCase().replace(/\\s/g, '');
    return clean === clean.split('').reverse().join('');
}

console.log(reverseString("Hello World")); // dlroW olleH
console.log(isPalindrome("racecar"));      // true`;
        },
        
        _api(lang) {
            if (lang === 'python') return `import requests

def fetch_data(url):
    """Fetch JSON data from an API"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error: {e}")
        return None

data = fetch_data("https://api.example.com/data")
if data:
    print(data)`;
            return `async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(\`HTTP \${response.status}\`);
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        return null;
    }
}

// Usage
fetchData('https://api.example.com/data')
    .then(data => console.log(data));`;
        },
        
        _class(lang) {
            if (lang === 'python') return `class Animal:
    """Base animal class"""
    
    def __init__(self, name, species):
        self.name = name
        self.species = species
    
    def speak(self):
        return f"{self.name} makes a sound"
    
    def __repr__(self):
        return f"Animal({self.name}, {self.species})"

class Dog(Animal):
    def __init__(self, name):
        super().__init__(name, "Dog")
    
    def speak(self):
        return f"{self.name} says Woof!"

dog = Dog("Rex")
print(dog.speak())`;
            return `class Animal {
    constructor(name, species) {
        this.name = name;
        this.species = species;
    }
    
    speak() {
        return \`\${this.name} makes a sound\`;
    }
}

class Dog extends Animal {
    constructor(name) {
        super(name, 'Dog');
    }
    
    speak() {
        return \`\${this.name} says Woof!\`;
    }
}

const dog = new Dog('Rex');
console.log(dog.speak());`;
        },
        
        _array(lang) {
            if (lang === 'python') return `# Array/List operations
nums = [1, 2, 3, 4, 5]

# Map
doubled = [n * 2 for n in nums]
print(doubled)  # [2, 4, 6, 8, 10]

# Filter
evens = [n for n in nums if n % 2 == 0]
print(evens)  # [2, 4]

# Reduce
total = sum(nums)
print(total)  # 15

# Sort
sorted_desc = sorted(nums, reverse=True)
print(sorted_desc)  # [5, 4, 3, 2, 1]`;
            return `// Array operations
const nums = [1, 2, 3, 4, 5];

// Map
const doubled = nums.map(n => n * 2);
console.log(doubled); // [2, 4, 6, 8, 10]

// Filter
const evens = nums.filter(n => n % 2 === 0);
console.log(evens); // [2, 4]

// Reduce
const total = nums.reduce((sum, n) => sum + n, 0);
console.log(total); // 15

// Sort descending
const sorted = [...nums].sort((a, b) => b - a);
console.log(sorted); // [5, 4, 3, 2, 1]`;
        },
        
        _hello(lang) {
            if (lang === 'python') return `# Hello World in Python
def greet(name="World"):
    return f"Hello, {name}!"

print(greet())
print(greet("Neural.AI"))`;
            return `// Hello World
function greet(name = 'World') {
    return \`Hello, \${name}!\`;
}

console.log(greet());
console.log(greet('Neural.AI'));`;
        },
        
        _general(lang, prompt) {
            const cleaned = prompt.replace(/write|create|generate|code|for|a|an|the|in|python|javascript/gi, '').trim();
            if (lang === 'python') return `# ${cleaned || 'Generated code'}

def main():
    """Main function"""
    print("Generated by Neural.AI")
    # TODO: Implement ${cleaned}
    
    # Example: basic setup
    data = []
    for i in range(10):
        data.append(i * 2)
    
    return data

if __name__ == "__main__":
    result = main()
    print("Result:", result)`;
            return `// ${cleaned || 'Generated code'}

function main() {
    console.log('Generated by Neural.AI');
    // TODO: Implement ${cleaned}
    
    // Example: basic setup
    const data = [];
    for (let i = 0; i < 10; i++) {
        data.push(i * 2);
    }
    
    return data;
}

const result = main();
console.log('Result:', result);`;
        }
    };
    
    // ============================================
    // MIDI / MUSIC GENERATION PIPELINE
    // ============================================
    const MusicPipeline = {
        // Generate a MIDI file as base64 blob
        generateMIDI(prompt = '') {
            const scale = this._detectScale(prompt);
            const tempo = this._detectTempo(prompt);
            const notes = this._composeMelody(scale, 32);
            return this._encodeMIDI(notes, tempo);
        },
        
        // Play a synthesized melody via Web Audio API
        async playMelody(prompt = '') {
            if (!window.AudioContext && !window.webkitAudioContext) {
                throw new Error('Web Audio API not supported');
            }
            
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const scale = this._detectScale(prompt);
            const notes = this._composeMelody(scale, 16);
            
            const now = audioCtx.currentTime;
            const noteDuration = 0.35;
            
            notes.forEach((noteMidi, i) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                
                osc.type = 'triangle';
                osc.frequency.value = this._midiToFreq(noteMidi);
                
                gain.gain.setValueAtTime(0, now + i * noteDuration);
                gain.gain.linearRampToValueAtTime(0.2, now + i * noteDuration + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.001, now + (i + 1) * noteDuration);
                
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                
                osc.start(now + i * noteDuration);
                osc.stop(now + (i + 1) * noteDuration);
            });
            
            // Also render to WAV for download
            return this._renderToWav(notes, noteDuration);
        },
        
        _detectScale(prompt) {
            const lower = prompt.toLowerCase();
            if (/minor|sad|dark|melancholy/.test(lower)) {
                return [60, 62, 63, 65, 67, 68, 70, 72]; // C minor
            }
            if (/pentatonic|asian|eastern/.test(lower)) {
                return [60, 62, 64, 67, 69, 72];
            }
            if (/blues/.test(lower)) {
                return [60, 63, 65, 66, 67, 70, 72];
            }
            return [60, 62, 64, 65, 67, 69, 71, 72]; // C major
        },
        
        _detectTempo(prompt) {
            const lower = prompt.toLowerCase();
            if (/slow|calm|ballad/.test(lower)) return 70;
            if (/fast|upbeat|energetic/.test(lower)) return 140;
            return 100;
        },
        
        _composeMelody(scale, length) {
            const notes = [];
            let idx = Math.floor(scale.length / 2);
            
            for (let i = 0; i < length; i++) {
                notes.push(scale[idx]);
                // Random walk with bias to center
                const step = Math.floor(Math.random() * 5) - 2;
                idx = Math.max(0, Math.min(scale.length - 1, idx + step));
                
                // Occasionally jump octaves
                if (Math.random() < 0.08) {
                    notes[notes.length - 1] += (Math.random() > 0.5 ? 12 : -12);
                }
            }
            
            return notes;
        },
        
        _midiToFreq(midi) {
            return 440 * Math.pow(2, (midi - 69) / 12);
        },
        
        _renderToWav(notes, noteDuration) {
            const sampleRate = 44100;
            const totalSamples = Math.floor(notes.length * noteDuration * sampleRate);
            const samplesPerNote = Math.floor(noteDuration * sampleRate);
            const buffer = new Float32Array(totalSamples);
            
            notes.forEach((noteMidi, i) => {
                const freq = this._midiToFreq(noteMidi);
                const offset = i * samplesPerNote;
                for (let j = 0; j < samplesPerNote; j++) {
                    const t = j / sampleRate;
                    const envelope = Math.max(0, 1 - (j / samplesPerNote));
                    // Triangle wave
                    const phase = (freq * t) % 1;
                    const wave = 2 * Math.abs(2 * phase - 1) - 1;
                    buffer[offset + j] = wave * envelope * 0.25;
                }
            });
            
            return this._encodeWav(buffer, sampleRate);
        },
        
        _encodeWav(samples, sampleRate) {
            const buffer = new ArrayBuffer(44 + samples.length * 2);
            const view = new DataView(buffer);
            
            const writeStr = (offset, str) => {
                for (let i = 0; i < str.length; i++) {
                    view.setUint8(offset + i, str.charCodeAt(i));
                }
            };
            
            writeStr(0, 'RIFF');
            view.setUint32(4, 36 + samples.length * 2, true);
            writeStr(8, 'WAVE');
            writeStr(12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, 1, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            writeStr(36, 'data');
            view.setUint32(40, samples.length * 2, true);
            
            for (let i = 0; i < samples.length; i++) {
                const s = Math.max(-1, Math.min(1, samples[i]));
                view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
            
            const blob = new Blob([buffer], { type: 'audio/wav' });
            return URL.createObjectURL(blob);
        },
        
        _encodeMIDI(notes, tempo) {
            // Simple MIDI file encoder
            const microsPerBeat = Math.floor(60000000 / tempo);
            const ticksPerNote = 240; // half of ticksPerQuarter=480
            
            const events = [];
            // Tempo
            events.push([0, 0xFF, 0x51, 0x03, (microsPerBeat >> 16) & 0xFF, (microsPerBeat >> 8) & 0xFF, microsPerBeat & 0xFF]);
            
            notes.forEach((n, i) => {
                events.push([i === 0 ? 0 : 0, 0x90, n, 100]); // Note on
                events.push([ticksPerNote, 0x80, n, 0]); // Note off
            });
            
            // End of track
            events.push([0, 0xFF, 0x2F, 0x00]);
            
            // Encode variable-length delta times
            const trackData = [];
            events.forEach(evt => {
                trackData.push(...this._encodeVarLen(evt[0]));
                for (let i = 1; i < evt.length; i++) trackData.push(evt[i]);
            });
            
            // Header + track
            const header = [
                0x4D, 0x54, 0x68, 0x64, // MThd
                0x00, 0x00, 0x00, 0x06, // Length 6
                0x00, 0x00,             // Format 0
                0x00, 0x01,             // 1 track
                0x01, 0xE0              // 480 TPQ
            ];
            
            const track = [
                0x4D, 0x54, 0x72, 0x6B, // MTrk
                (trackData.length >> 24) & 0xFF,
                (trackData.length >> 16) & 0xFF,
                (trackData.length >> 8) & 0xFF,
                trackData.length & 0xFF,
                ...trackData
            ];
            
            const bytes = new Uint8Array([...header, ...track]);
            const blob = new Blob([bytes], { type: 'audio/midi' });
            return URL.createObjectURL(blob);
        },
        
        _encodeVarLen(value) {
            const result = [];
            let buf = value & 0x7F;
            value >>= 7;
            while (value > 0) {
                buf <<= 8;
                buf |= (value & 0x7F) | 0x80;
                value >>= 7;
            }
            while (true) {
                result.push(buf & 0xFF);
                if (buf & 0x80) buf >>= 8;
                else break;
            }
            return result;
        }
    };
    
    return {
        image: ImagePipeline,
        html: HTMLPipeline,
        code: CodePipeline,
        music: MusicPipeline
    };
})();
