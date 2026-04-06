import { useEffect, useRef } from 'react';
import './LandingPage.css';

function LandingPage({ onGetStarted, theme, toggleTheme }) {
  const observerRef = useRef(null);
  const canvasRef = useRef(null);

  // Neural network background animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const count = Math.min(Math.max(Math.floor((window.innerWidth * window.innerHeight) / 18000), 35), 90);
    const nodes = Array.from({ length: count }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.38,
      vy: (Math.random() - 0.5) * 0.38,
      r: Math.random() * 2.5 + 1.0,
      pulse: Math.random() * Math.PI * 2,
    }));

    let raf;
    const maxDist = 200;

    const draw = () => {
      const rgb = '170,85,85';
      const nodeBaseAlpha = 0.9;
      const lineBaseAlpha = 0.5;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      nodes.forEach(n => {
        n.x += n.vx;
        n.y += n.vy;
        n.pulse += 0.012;
        if (n.x < -12) n.x = canvas.width + 12;
        else if (n.x > canvas.width + 12) n.x = -12;
        if (n.y < -12) n.y = canvas.height + 12;
        else if (n.y > canvas.height + 12) n.y = -12;
      });

      // Connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.hypot(dx, dy);
          if (dist < maxDist) {
            const a = (1 - dist / maxDist) * lineBaseAlpha;
            ctx.strokeStyle = `rgba(${rgb},${a})`;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // Nodes with pulse breathing
      nodes.forEach(n => {
        const pulsedR = n.r + Math.sin(n.pulse) * 1.0;
        const a = Math.min(1, nodeBaseAlpha + Math.sin(n.pulse) * 0.1);
        ctx.fillStyle = `rgba(${rgb},${a})`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, pulsedR, 0, Math.PI * 2);
        ctx.fill();
      });

      raf = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry, i) => {
          if (entry.isIntersecting) {
            const delay = entry.target.dataset.delay || 0;
            setTimeout(() => entry.target.classList.add('visible'), delay * 120);
            observerRef.current.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    document.querySelectorAll('.step-card, .feature-card').forEach((el, i) => {
      el.dataset.delay = i % 4;
      observerRef.current.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, []);

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="landing-page">
      <canvas ref={canvasRef} className="landing-canvas" />
      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-nav-logo">
          <img src="/Logo.png" alt="PolyLLM" />
          PolyLLM Council
        </div>
        <div className="landing-nav-links">
          <button className="landing-nav-link" onClick={() => scrollTo('how-it-works')}>How It Works</button>
          <button className="landing-nav-link" onClick={() => scrollTo('features')}>Features</button>
          <button className="landing-theme-btn" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
            {theme === 'dark' ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
                <circle cx="12" cy="12" r="5"/>
                <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>
          <button className="landing-cta-btn" onClick={onGetStarted}>Get Started</button>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="hero-glow" />
        <div className="hero-badge">
          <span className="hero-badge-dot" />
          Multi-model deliberation system
        </div>
        <h1 className="hero-title">Collective Agentic Intelligence</h1>
        <p className="hero-subtitle">
          Multiple LLMs deliberate, peer-review anonymously, and synthesize a single superior answer — like a council of experts reaching consensus.
        </p>
        <div className="hero-actions">
          <button className="hero-cta-primary" onClick={onGetStarted}>Get Started →</button>
          <button className="hero-cta-secondary" onClick={() => scrollTo('how-it-works')}>Learn More</button>
        </div>
      </section>

      {/* How It Works */}
      <section className="landing-section" id="how-it-works">
        <p className="section-label">How It Works</p>
        <h2 className="section-title">Four stages. One answer.</h2>
        <p className="section-subtitle">
          Every query passes through a rigorous deliberation pipeline, combining the strengths of multiple models.
        </p>
        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">Parallel Queries</h3>
            <p className="step-desc">
              Your question is sent to multiple frontier LLMs simultaneously. Each model produces an independent response with no knowledge of others.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">Anonymized Peer Review</h3>
            <p className="step-desc">
              Responses are anonymized and redistributed. Each model evaluates and ranks all responses blindly, preventing bias and favoritism.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Council Review</h3>
            <p className="step-desc">
              An independent reviewer model critiques the deliberation record, summarizing points of agreement and divergence across all council members.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">4</div>
            <h3 className="step-title">Chairman Synthesis</h3>
            <p className="step-desc">
              A fine-tuned chairman model reads all responses, peer rankings, and the council review to produce a single, calibrated final answer.
            </p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="landing-section" id="features">
        <p className="section-label">Features</p>
        <h2 className="section-title">Built for accuracy & trust</h2>
        <p className="section-subtitle">
          Every design decision serves transparency, reducing hallucinations and exposing reasoning.
        </p>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3 className="feature-title">Multi-Model Deliberation</h3>
            <p className="feature-desc">
              Harness GPT-4, Claude, Gemini, and more in parallel. Diverse model architectures catch each other's blind spots.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3 className="feature-title">Anonymized Peer Review</h3>
            <p className="feature-desc">
              Models evaluate responses labeled A, B, C — never knowing which model authored which. True blind review eliminates bias.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3 className="feature-title">Calibrated Confidence</h3>
            <p className="feature-desc">
              Aggregate rankings reveal consensus and disagreement. Know when the council is certain and when it's split.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <h3 className="feature-title">Transparent Process</h3>
            <p className="feature-desc">
              Inspect every stage — individual responses, raw evaluations, parsed rankings. Full auditability from query to answer.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-logo">
          <img src="/Logo.png" alt="" />
          PolyLLM Council
        </div>
        <span>Built with collective intelligence.</span>
      </footer>
    </div>
  );
}

export default LandingPage;
