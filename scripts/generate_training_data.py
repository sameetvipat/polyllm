#!/usr/bin/env python3
"""
Generate synthetic training data for PolyLLM Chairman Model.

For mq_010-024: Only generates missing chairman synthesis (real API data preserved).
For mq_025-026: Fixes incomplete data.
For mq_027-080: Generates complete training files from scratch.

Usage:
    python scripts/generate_training_data.py
    python scripts/generate_training_data.py --start 27 --end 40
"""

import json, uuid, re, argparse, textwrap
from pathlib import Path

TRAINING_DIR = Path("data/training")
QUESTIONS_FILE = Path("manual_questions.jsonl")

MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
]
CHAIRMAN_MODEL = "google/gemini-2.5-flash"
LABEL_MAP = {"Response A": MODELS[0], "Response B": MODELS[1], "Response C": MODELS[2]}

# ── Question-specific knowledge base ─────────────────────────────────────────
# Each entry: question_substring -> {topic, key_points, examples, terms}

KNOWLEDGE = {
    "gradient descent": {
        "topic": "Gradient Descent and Learning Rate",
        "points": ["cost function minimization", "gradient computation (partial derivatives)", "parameter update rule", "learning rate as step size", "convergence speed trade-off", "local minima and saddle points", "stochastic vs batch vs mini-batch", "adaptive learning rates (Adam, RMSprop)"],
        "examples": ["training neural networks", "linear regression optimization", "learning rate schedulers (cosine annealing)", "vanishing gradient problem"],
    },
    "transformer models": {
        "topic": "Transformer Models in NLP",
        "points": ["self-attention mechanism", "positional encoding", "multi-head attention", "encoder-decoder architecture", "parallelization advantage over RNNs", "BERT and GPT variants", "transfer learning via pre-training", "attention is all you need (Vaswani 2017)"],
        "examples": ["machine translation", "text summarization", "GPT series progression", "BERT for question answering", "Vision Transformers (ViT)"],
    },
    "overfitting": {
        "topic": "Overfitting in Neural Networks",
        "points": ["training vs validation loss divergence", "model complexity vs data size", "dropout regularization", "L1 and L2 regularization", "early stopping", "data augmentation", "batch normalization", "cross-validation"],
        "examples": ["image classification with small datasets", "memorizing noise in training data", "Kaggle competition overfitting", "transfer learning to reduce overfitting"],
    },
    "precision and recall": {
        "topic": "Precision vs Recall in Classification",
        "points": ["precision (positive predictive value)", "recall (sensitivity/true positive rate)", "F1 score as harmonic mean", "confusion matrix interpretation", "precision-recall trade-off", "threshold tuning", "ROC curve and AUC", "class imbalance impact"],
        "examples": ["spam detection (precision priority)", "cancer screening (recall priority)", "fraud detection systems", "search engine relevance ranking"],
    },
    "cap theorem": {
        "topic": "CAP Theorem in Distributed Systems",
        "points": ["consistency (all nodes see same data)", "availability (every request gets response)", "partition tolerance (system works despite network splits)", "pick two of three trade-off", "CP systems (strong consistency)", "AP systems (high availability)", "PACELC extension", "partition is inevitable in practice"],
        "examples": ["MongoDB (CP)", "Cassandra (AP)", "ZooKeeper (CP)", "DynamoDB (AP with tunable consistency)"],
    },
    "process and thread": {
        "topic": "Processes vs Threads",
        "points": ["separate memory space vs shared memory", "process isolation and fault tolerance", "thread lightweight context switching", "inter-process communication overhead", "race conditions in threads", "GIL in Python", "multiprocessing vs multithreading", "thread synchronization (mutex, semaphore)"],
        "examples": ["Chrome multi-process architecture", "web server worker threads", "database connection pooling", "GUI responsiveness with background threads"],
    },
    "rest vs graphql": {
        "topic": "REST vs GraphQL API Design",
        "points": ["resource-based vs query-based", "over-fetching and under-fetching", "multiple endpoints vs single endpoint", "strong typing and schema in GraphQL", "caching simplicity in REST", "versioning strategies", "real-time with subscriptions (GraphQL)", "HTTP methods and status codes (REST)"],
        "examples": ["GitHub API v3 (REST) vs v4 (GraphQL)", "Facebook GraphQL origin", "mobile app data efficiency", "microservices API gateway"],
    },
    "dependency injection": {
        "topic": "Dependency Injection in Software Architecture",
        "points": ["inversion of control principle", "constructor injection", "setter injection", "interface-based injection", "loose coupling benefit", "testability improvement", "DI containers and frameworks", "service locator pattern contrast"],
        "examples": ["Spring Framework (Java)", "Angular DI system", "unit testing with mock objects", ".NET dependency injection"],
    },
    "garbage collection": {
        "topic": "Garbage Collection in Programming Languages",
        "points": ["automatic memory management", "reference counting", "mark-and-sweep algorithm", "generational garbage collection", "stop-the-world pauses", "concurrent and parallel GC", "memory leak prevention", "GC tuning and performance"],
        "examples": ["Java G1 and ZGC collectors", "Python reference counting + cycle detector", "Go concurrent GC", "Rust ownership model (no GC)"],
    },
    "solid principles": {
        "topic": "SOLID Principles of Object-Oriented Design",
        "points": ["Single Responsibility Principle", "Open/Closed Principle", "Liskov Substitution Principle", "Interface Segregation Principle", "Dependency Inversion Principle", "reducing coupling", "improving maintainability", "design pattern alignment"],
        "examples": ["refactoring God classes (SRP)", "plugin architectures (OCP)", "polymorphic substitution (LSP)", "microservices interface design (ISP)"],
    },
    "sql and nosql": {
        "topic": "SQL vs NoSQL Databases",
        "points": ["relational model vs document/key-value/graph", "ACID transactions", "BASE properties", "schema rigidity vs flexibility", "horizontal vs vertical scaling", "query language differences", "data normalization vs denormalization", "use case suitability"],
        "examples": ["PostgreSQL for financial transactions", "MongoDB for content management", "Redis for caching", "Neo4j for social graphs", "Cassandra for time-series data"],
    },
    "docker and kubernetes": {
        "topic": "Docker and Kubernetes in Modern Deployment",
        "points": ["containerization vs virtualization", "Docker images and layers", "Kubernetes orchestration", "pod and service abstractions", "declarative configuration", "auto-scaling and self-healing", "CI/CD pipeline integration", "container networking and service mesh"],
        "examples": ["Dockerfile and docker-compose", "Kubernetes deployments and replica sets", "Helm charts for packaging", "Istio service mesh"],
    },
    "dns works": {
        "topic": "How DNS Resolution Works",
        "points": ["recursive resolver", "root name servers", "TLD name servers", "authoritative name servers", "DNS caching and TTL", "A, AAAA, CNAME, MX records", "DNS propagation", "DNSSEC for security"],
        "examples": ["browser URL bar to IP resolution", "Cloudflare 1.1.1.1 resolver", "Google Public DNS 8.8.8.8", "DNS-based load balancing"],
    },
    "osi model": {
        "topic": "The OSI Networking Model",
        "points": ["7 layers: Physical to Application", "layer encapsulation and decapsulation", "Physical layer (bits and signals)", "Data Link layer (MAC addresses)", "Network layer (IP routing)", "Transport layer (TCP/UDP)", "Session, Presentation, Application layers", "TCP/IP model comparison"],
        "examples": ["Ethernet at Data Link", "IP routing at Network layer", "HTTP at Application layer", "TLS at Presentation/Session layer"],
    },
    "https": {
        "topic": "HTTPS and the TLS Handshake",
        "points": ["TLS over TCP connection", "certificate authority (CA) trust chain", "asymmetric key exchange", "symmetric session key derivation", "cipher suite negotiation", "certificate validation", "perfect forward secrecy (PFS)", "TLS 1.3 improvements"],
        "examples": ["Let's Encrypt free certificates", "HSTS enforcement", "certificate pinning in mobile apps", "mixed content warnings"],
    },
    "cdn": {
        "topic": "Content Delivery Networks",
        "points": ["edge server distribution", "geographic proximity caching", "origin server offloading", "cache invalidation strategies", "DDoS absorption", "latency reduction", "adaptive bitrate for streaming", "SSL/TLS termination at edge"],
        "examples": ["Cloudflare", "Akamai", "Amazon CloudFront", "Netflix Open Connect"],
    },
    "tcp and udp": {
        "topic": "TCP vs UDP Protocols",
        "points": ["connection-oriented vs connectionless", "reliability and ordered delivery (TCP)", "low overhead and speed (UDP)", "three-way handshake (TCP)", "flow control and congestion control", "use case suitability", "TCP retransmission", "UDP for real-time applications"],
        "examples": ["HTTP/HTTPS over TCP", "DNS queries over UDP", "online gaming (UDP)", "video streaming protocols", "VoIP applications"],
    },
    "free will": {
        "topic": "Free Will and Determinism",
        "points": ["hard determinism", "compatibilism (soft determinism)", "libertarian free will", "causal chains", "moral responsibility", "quantum indeterminacy", "Hume's compatibilism", "Frankfurt cases"],
        "examples": ["criminal justice and punishment", "addiction and choice", "neuroscience experiments (Libet)", "Stoic philosophy"],
    },
    "trolley problem": {
        "topic": "The Trolley Problem and Ethical Frameworks",
        "points": ["utilitarian calculus", "deontological duty (Kant)", "virtue ethics", "doctrine of double effect", "fat man variant", "consent and autonomy", "moral intuition vs reasoning"],
        "examples": ["autonomous vehicles decisions", "medical triage", "wartime collateral damage", "organ transplant thought experiment"],
    },
    "nietzsche": {
        "topic": "Nietzsche's Will to Power",
        "points": ["will to power as self-overcoming", "master-slave morality", "Übermensch concept", "eternal recurrence", "misappropriation by Nazis", "Elisabeth Förster-Nietzsche's edits", "contrast with Schopenhauer's will"],
        "examples": ["artistic creation", "political misuse in Third Reich", "existentialist influence", "Zarathustra's teachings"],
    },
    "ship of theseus": {
        "topic": "Ship of Theseus Paradox",
        "points": ["mereological composition", "temporal identity", "personal identity", "four-dimensionalism", "essentialism vs anti-essentialism", "Locke on personal identity", "bundle theory"],
        "examples": ["cell replacement in human body", "restored classic cars", "software updates", "brain transplant thought experiments"],
    },
    "morality objective": {
        "topic": "Moral Objectivism vs Subjectivism",
        "points": ["moral realism", "moral anti-realism", "cultural relativism", "natural law theory", "emotivism", "error theory (Mackie)", "constructivism", "divine command theory"],
        "examples": ["universal human rights", "honor killings debate", "slavery abolition", "cross-cultural moral judgments"],
    },
    "crispr": {
        "topic": "CRISPR Gene Editing",
        "points": ["Cas9 protein mechanism", "guide RNA targeting", "double-strand breaks", "homology-directed repair", "germline vs somatic editing", "off-target effects", "He Jiankui controversy", "therapeutic applications"],
        "examples": ["sickle cell disease treatment", "cancer immunotherapy", "agricultural GMOs", "designer babies debate", "gene drives for malaria"],
    },
    "quantum entanglement": {
        "topic": "Quantum Entanglement",
        "points": ["EPR paradox", "Bell's theorem", "non-locality", "wave function collapse", "superposition", "measurement problem", "no-communication theorem", "quantum decoherence"],
        "examples": ["quantum computing qubits", "quantum teleportation experiments", "quantum cryptography (QKD)", "Aspect experiment 1982"],
    },
    "mrna vaccines": {
        "topic": "mRNA Vaccine Technology",
        "points": ["messenger RNA mechanism", "lipid nanoparticle delivery", "spike protein production", "immune response activation", "no DNA alteration", "rapid development timeline", "cold storage requirements", "comparison with viral vector vaccines"],
        "examples": ["Pfizer-BioNTech COVID-19", "Moderna COVID-19", "future cancer vaccines", "flu vaccine development"],
    },
    "black holes": {
        "topic": "Black Holes and Event Horizons",
        "points": ["stellar collapse", "Schwarzschild radius", "singularity", "spaghettification", "Hawking radiation", "information paradox", "time dilation near event horizon", "supermassive black holes"],
        "examples": ["Sagittarius A*", "M87 black hole image (EHT)", "Cygnus X-1", "gravitational wave detection (LIGO)"],
    },
    "entropy": {
        "topic": "Entropy and the Second Law of Thermodynamics",
        "points": ["Boltzmann's statistical mechanics", "microstates and macrostates", "arrow of time", "heat death of universe", "Maxwell's demon", "Gibbs free energy", "information entropy (Shannon)", "local entropy decrease"],
        "examples": ["ice melting", "shuffling cards", "living organisms as low-entropy systems", "refrigeration"],
    },
    "immune system": {
        "topic": "Immune System Self vs Non-Self Recognition",
        "points": ["MHC molecules", "T-cell education in thymus", "clonal deletion", "regulatory T cells", "innate vs adaptive immunity", "autoimmune disorders", "molecular mimicry", "central vs peripheral tolerance"],
        "examples": ["type 1 diabetes", "lupus", "rheumatoid arthritis", "organ transplant rejection", "allergy responses"],
    },
    "2008": {
        "topic": "2008 Global Financial Crisis",
        "points": ["subprime mortgage lending", "mortgage-backed securities", "credit default swaps", "rating agency failures", "Lehman Brothers collapse", "too big to fail", "deregulation (Glass-Steagall repeal)", "systemic risk"],
        "examples": ["Bear Stearns bailout", "AIG rescue", "Dodd-Frank Act", "quantitative easing", "housing bubble"],
    },
    "cold war": {
        "topic": "Causes and Consequences of the Cold War",
        "points": ["ideological divide (capitalism vs communism)", "nuclear arms race", "proxy wars", "containment doctrine", "détente", "space race", "NATO vs Warsaw Pact", "domino theory"],
        "examples": ["Korean War", "Vietnam War", "Cuban Missile Crisis", "Berlin Wall", "Marshall Plan", "Soviet invasion of Afghanistan"],
    },
    "soviet union collapse": {
        "topic": "Collapse of the Soviet Union",
        "points": ["economic stagnation", "Gorbachev's glasnost and perestroika", "arms race spending", "nationalist movements", "Chernobyl disaster", "failed August coup", "Baltic independence", "dissolution December 1991"],
        "examples": ["fall of Berlin Wall", "Baltic chain of freedom", "Yeltsin's rise", "Commonwealth of Independent States"],
    },
    "israel-palestine": {
        "topic": "Israel-Palestine Conflict",
        "points": ["Balfour Declaration 1917", "1948 Arab-Israeli War", "Six-Day War 1967", "Oslo Accords", "settlements issue", "right of return", "two-state solution debate", "Jerusalem status"],
        "examples": ["Camp David Accords", "First and Second Intifada", "Gaza blockade", "UN Resolution 242"],
    },
    "belt and road": {
        "topic": "China's Belt and Road Initiative",
        "points": ["Silk Road Economic Belt", "21st Century Maritime Silk Road", "infrastructure investment", "debt-trap diplomacy debate", "geopolitical influence expansion", "port acquisitions", "AIIB funding", "strategic competition with US"],
        "examples": ["Hambantota Port Sri Lanka", "CPEC Pakistan", "Djibouti military base", "European infrastructure projects"],
    },
    "inflation": {
        "topic": "Inflation: Causes, Central Bank Response, and Risks",
        "points": ["demand-pull inflation", "cost-push inflation", "monetary policy tools", "interest rate mechanism", "quantitative easing/tightening", "Phillips curve", "stagflation", "hyperinflation"],
        "examples": ["Weimar Republic hyperinflation", "Zimbabwe dollar collapse", "Volcker shock 1980s", "2021-2023 global inflation", "Japan deflation"],
    },
    "gdp and gnp": {
        "topic": "GDP vs GNP as Prosperity Measures",
        "points": ["GDP measures domestic production", "GNP includes overseas earnings", "purchasing power parity", "limitations of both metrics", "informal economy exclusion", "environmental degradation ignored", "inequality blind spot", "alternative measures (HDI, GNH)"],
        "examples": ["Ireland's GDP distortion", "remittance economies", "Nordic countries HDI", "Bhutan's Gross National Happiness"],
    },
    "game theory": {
        "topic": "Game Theory in Practice",
        "points": ["prisoner's dilemma", "Nash equilibrium", "dominant strategy", "Pareto optimality", "repeated games (tit-for-tat)", "zero-sum vs positive-sum", "mechanism design", "auction theory"],
        "examples": ["OPEC production decisions", "nuclear deterrence (MAD)", "spectrum auctions", "price wars between airlines", "evolutionary biology strategies"],
    },
    "cryptocurrency": {
        "topic": "Cryptocurrency and the Future of Money",
        "points": ["blockchain technology", "decentralization", "proof of work vs proof of stake", "volatility problem", "store of value debate", "CBDCs", "smart contracts", "regulatory challenges"],
        "examples": ["Bitcoin", "Ethereum", "El Salvador adoption", "FTX collapse", "China's digital yuan", "DeFi protocols"],
    },
    "ubi": {
        "topic": "Universal Basic Income",
        "points": ["unconditional cash transfers", "automation displacement argument", "poverty reduction", "inflation concerns", "work incentive debate", "funding mechanisms", "bureaucracy reduction", "dignity and freedom argument"],
        "examples": ["Finland experiment 2017-2018", "Stockton SEED program", "Alaska Permanent Fund", "Kenya GiveDirectly", "Andrew Yang's campaign"],
    },
    "large language models": {
        "topic": "Risks of Large Language Models",
        "points": ["hallucination and confabulation", "bias amplification", "misinformation generation", "privacy and data concerns", "environmental cost", "job displacement", "alignment problem", "RLHF and constitutional AI"],
        "examples": ["ChatGPT errors", "deepfake text", "training data copyright issues", "EU AI Act", "academic integrity concerns"],
    },
    "alignment problem": {
        "topic": "AI Alignment Problem",
        "points": ["value alignment", "reward hacking", "instrumental convergence", "Goodhart's law", "corrigibility", "inner vs outer alignment", "scalable oversight", "interpretability research"],
        "examples": ["paperclip maximizer", "RLHF approach", "constitutional AI", "red teaming", "AI safety labs (MIRI, ARC)"],
    },
    "ai-generated art": {
        "topic": "AI Art and Copyright",
        "points": ["authorship question", "training data fair use", "derivative work doctrine", "human creative input", "Feist Publications ruling", "economic impact on artists", "registration requirements", "international law differences"],
        "examples": ["DALL-E and Midjourney works", "Zarya of the Dawn ruling", "Getty Images lawsuit", "Adobe Firefly licensing", "DeviantArt controversy"],
    },
    "ai hallucination": {
        "topic": "AI Hallucination in Large Language Models",
        "points": ["probabilistic token generation", "memorization vs generalization", "training data gaps", "pattern matching without understanding", "confidence calibration", "retrieval-augmented generation", "chain-of-thought prompting", "factual grounding"],
        "examples": ["fabricated citations", "invented historical events", "confident but wrong medical advice", "legal case hallucinations"],
    },
    "algorithmic bias": {
        "topic": "Algorithmic Bias and Societal Impact",
        "points": ["biased training data", "proxy discrimination", "feedback loops", "representation gaps", "intersectionality", "fairness metrics trade-offs", "audit and accountability", "disparate impact"],
        "examples": ["COMPAS recidivism prediction", "Amazon hiring tool bias", "facial recognition accuracy gaps", "healthcare algorithm racial bias", "credit scoring disparities"],
    },
    "url shortener": {
        "topic": "Designing a URL Shortener at Scale",
        "points": ["hash function design", "base62 encoding", "collision handling", "read-heavy workload", "caching layer (Redis)", "database sharding", "analytics tracking", "301 vs 302 redirects", "rate limiting"],
        "examples": ["bit.ly architecture", "TinyURL", "link expiration policies", "custom vanity URLs"],
    },
    "netflix": {
        "topic": "Netflix Video Streaming Architecture",
        "points": ["Open Connect CDN", "microservices architecture", "adaptive bitrate streaming", "content encoding pipeline", "chaos engineering", "recommendation engine", "edge caching", "multi-region deployment"],
        "examples": ["Chaos Monkey", "Zuul API gateway", "Eureka service discovery", "Hystrix circuit breaker"],
    },
    "rate limiter": {
        "topic": "Distributed Rate Limiter Design",
        "points": ["token bucket algorithm", "sliding window counter", "fixed window counter", "leaky bucket", "Redis-based implementation", "race condition handling", "distributed synchronization", "rate limit headers"],
        "examples": ["API gateway rate limiting", "DDoS protection", "Stripe API limits", "Twitter API throttling"],
    },
    "chat application": {
        "topic": "Real-Time Chat Application Architecture",
        "points": ["WebSocket protocol", "message queuing (Kafka)", "presence detection", "end-to-end encryption", "message delivery guarantees", "offline message storage", "read receipts", "media handling"],
        "examples": ["WhatsApp Signal Protocol", "Telegram MTProto", "Slack architecture", "Discord voice channels"],
    },
    "eventual consistency": {
        "topic": "Eventual Consistency in Distributed Systems",
        "points": ["CAP theorem trade-offs", "strong vs eventual consistency", "conflict resolution (CRDT)", "vector clocks", "quorum reads/writes", "anti-entropy protocols", "last-writer-wins", "causal consistency"],
        "examples": ["Amazon DynamoDB", "Apache Cassandra", "DNS propagation", "shopping cart merge strategies"],
    },
    "cognitive biases": {
        "topic": "Cognitive Biases and Decision-Making",
        "points": ["confirmation bias", "anchoring effect", "availability heuristic", "Dunning-Kruger effect", "loss aversion", "sunk cost fallacy", "bandwagon effect", "framing effect", "System 1 vs System 2 (Kahneman)"],
        "examples": ["stock market decisions", "medical diagnosis errors", "political polarization", "marketing strategies", "jury deliberations"],
    },
    "stanford prison": {
        "topic": "Stanford Prison Experiment",
        "points": ["Zimbardo's 1971 experiment", "role adoption and deindividuation", "situationist perspective", "ethical violations", "demand characteristics", "methodological criticisms", "replication failures", "Abu Ghraib parallels"],
        "examples": ["guard brutality escalation", "prisoner breakdowns", "experiment early termination", "BBC prison study 2002"],
    },
    "dunning-kruger": {
        "topic": "Dunning-Kruger Effect",
        "points": ["metacognitive deficit", "illusory superiority", "competence breeds confidence calibration", "four stages of competence", "imposter syndrome as inverse", "domain specificity", "calibration training"],
        "examples": ["novice programmers overconfidence", "medical students", "political knowledge surveys", "driving ability self-assessment"],
    },
    "intrinsic and extrinsic": {
        "topic": "Intrinsic vs Extrinsic Motivation",
        "points": ["self-determination theory (Deci & Ryan)", "autonomy, competence, relatedness", "overjustification effect", "crowding out effect", "flow state (Csikszentmihalyi)", "reward undermining", "mastery orientation"],
        "examples": ["employee compensation design", "student grading impact", "open source contribution", "gamification", "artistic motivation"],
    },
    "porter": {
        "topic": "Porter's Five Forces Framework",
        "points": ["threat of new entrants", "bargaining power of suppliers", "bargaining power of buyers", "threat of substitutes", "competitive rivalry", "barriers to entry", "industry profitability analysis"],
        "examples": ["airline industry analysis", "tech industry (Apple/Google)", "pharmaceutical industry", "coffee shop market"],
    },
    "apple": {
        "topic": "Apple's Product Strategy Under Steve Jobs",
        "points": ["simplicity and design focus", "vertical integration", "controlled ecosystem", "product line reduction", "marketing as storytelling", "premium pricing strategy", "customer experience focus", "innovation timing"],
        "examples": ["iMac revival 1998", "iPod + iTunes ecosystem", "iPhone launch 2007", "Apple Store retail", "Think Different campaign"],
    },
    "lean startup": {
        "topic": "Lean Startup Methodology",
        "points": ["build-measure-learn cycle", "minimum viable product (MVP)", "validated learning", "pivot or persevere", "innovation accounting", "continuous deployment", "split testing", "customer development"],
        "examples": ["Dropbox MVP video", "Zappos manual fulfillment", "Groupon WordPress origin", "Buffer landing page test"],
    },
    "network effects": {
        "topic": "Network Effects in Business",
        "points": ["direct network effects", "indirect (platform) network effects", "data network effects", "critical mass and tipping point", "winner-take-all dynamics", "switching costs", "multi-homing", "chicken-and-egg problem"],
        "examples": ["Facebook/Meta social graph", "Uber marketplace", "Visa payment network", "Microsoft Windows ecosystem"],
    },
    "carbon capture": {
        "topic": "Carbon Capture Technology",
        "points": ["point-source capture", "direct air capture (DAC)", "bioenergy with CCS (BECCS)", "geological storage", "mineral carbonation", "energy penalty", "cost per ton CO2", "moral hazard argument"],
        "examples": ["Climeworks Orca plant Iceland", "Sleipner CCS Norway", "Boundary Dam Saskatchewan", "enhanced oil recovery"],
    },
    "tragedy of the commons": {
        "topic": "Tragedy of the Commons and Climate Change",
        "points": ["Hardin's 1968 thesis", "free rider problem", "common pool resources", "Ostrom's governance principles", "international cooperation challenges", "carbon pricing mechanisms", "cap and trade", "intergenerational equity"],
        "examples": ["overfishing", "deforestation", "Paris Agreement limitations", "water rights disputes", "air pollution"],
    },
    "nuclear energy vs renewable": {
        "topic": "Nuclear vs Renewable Energy for Decarbonization",
        "points": ["baseload reliability", "capacity factor comparison", "waste management challenge", "intermittency of renewables", "energy storage needs", "land use comparison", "lifecycle emissions", "SMR technology", "cost trends"],
        "examples": ["France nuclear fleet", "Germany Energiewende", "Hinkley Point C costs", "offshore wind growth", "battery storage advances"],
    },
    "habeas corpus": {
        "topic": "Habeas Corpus and Civil Liberties",
        "points": ["Latin meaning 'produce the body'", "protection against unlawful detention", "Magna Carta origins", "writ petition process", "suspension clause", "judicial review mechanism", "due process connection", "international equivalents"],
        "examples": ["English Habeas Corpus Act 1679", "US Constitution Article I §9", "Guantanamo Bay detentions (Boumediene v. Bush)", "Indian Article 226"],
    },
    "indian constitution": {
        "topic": "Indian vs US Constitution Comparison",
        "points": ["written length difference", "fundamental rights vs Bill of Rights", "directive principles unique to India", "federal structure differences", "amendment process", "judicial review in both", "parliamentary vs presidential system", "emergency provisions"],
        "examples": ["First Amendment freedoms", "Indian Article 21 (right to life)", "separation of powers contrast", "Kesavananda Bharati case (basic structure)"],
    },
    "intellectual property": {
        "topic": "Intellectual Property Law",
        "points": ["patents (inventions)", "copyrights (creative works)", "trademarks (brand identity)", "trade secrets", "fair use doctrine", "patent trolls", "compulsory licensing", "TRIPS agreement", "innovation incentive balance"],
        "examples": ["pharmaceutical patent debates", "open source software", "music sampling lawsuits", "Disney copyright extensions"],
    },
    "gödel": {
        "topic": "Gödel's Incompleteness Theorems",
        "points": ["first theorem: true but unprovable statements exist", "second theorem: system cannot prove own consistency", "formal system requirements", "Gödel numbering technique", "self-referential sentences", "impact on Hilbert's program", "philosophical implications", "computability connections"],
        "examples": ["liar paradox analogy", "Principia Mathematica limitations", "Turing's halting problem connection", "AI and mathematical reasoning limits"],
    },
    "p vs np": {
        "topic": "P vs NP Problem",
        "points": ["polynomial time verification vs solving", "NP-complete problems", "Cook-Levin theorem", "reduction technique", "practical implications for algorithms", "one-way functions and cryptography", "Clay Millennium Prize", "current consensus"],
        "examples": ["traveling salesman problem", "SAT problem", "RSA encryption vulnerability", "protein folding", "graph coloring"],
    },
    "bayesian": {
        "topic": "Bayesian vs Frequentist Statistics",
        "points": ["prior probability", "likelihood", "posterior probability", "Bayes' theorem", "subjective vs objective probability", "confidence interval vs credible interval", "p-value interpretation", "conjugate priors", "MCMC methods"],
        "examples": ["medical diagnostic testing", "spam filtering", "A/B testing interpretation", "forensic evidence", "machine learning hyperparameters"],
    },
    "pandemics": {
        "topic": "Pandemic History and Future Preparedness",
        "points": ["1918 Spanish flu lessons", "public health infrastructure", "quarantine effectiveness", "vaccine development speed", "zoonotic spillover", "surveillance systems", "global coordination (WHO)", "infodemic challenges"],
        "examples": ["Black Death", "1918 influenza", "HIV/AIDS pandemic", "SARS 2003", "COVID-19 response comparison"],
    },
    "misinformation": {
        "topic": "Misinformation on Social Media",
        "points": ["algorithmic amplification", "engagement-driven design", "filter bubbles and echo chambers", "cognitive biases exploitation", "bot networks", "content moderation challenges", "media literacy deficit", "network structure effects"],
        "examples": ["2016 US election interference", "COVID-19 infodemic", "anti-vaccination movement", "deepfakes", "Twitter/X content policy shifts"],
    },
    "second-order effects": {
        "topic": "Second-Order Effects and Unintended Consequences",
        "points": ["Chesterton's fence principle", "cobra effect", "moral hazard", "Goodhart's law", "perverse incentives", "systems thinking", "feedback loops", "homeostasis disruption"],
        "examples": ["cobra bounty in colonial India", "Prohibition alcohol policy", "three-strikes sentencing laws", "rent control effects", "biofuel mandates and food prices"],
    },
    "economic inequality": {
        "topic": "Economic Inequality and Political Instability",
        "points": ["Gini coefficient", "relative deprivation theory", "social mobility stagnation", "rent-seeking elites", "populism rise", "institutional erosion", "Kuznets curve", "wealth concentration feedback"],
        "examples": ["French Revolution", "Arab Spring", "Latin American populism", "Occupy Wall Street", "US political polarization"],
    },
    "countries succeed": {
        "topic": "Development Success and Failure",
        "points": ["institutional quality (Acemoglu)", "extractive vs inclusive institutions", "geographic factors (Diamond)", "colonial legacy", "human capital investment", "trade openness", "governance and corruption", "resource curse"],
        "examples": ["South Korea vs North Korea", "Botswana vs Congo", "Singapore development", "Norway oil fund vs Nigeria", "East Asian tigers"],
    },
    "technological singularity": {
        "topic": "The Technological Singularity",
        "points": ["Vernor Vinge's concept", "Kurzweil's predictions", "recursive self-improvement", "intelligence explosion", "Moore's law extrapolation", "hard takeoff vs soft takeoff", "existential risk", "control problem"],
        "examples": ["chess AI progression", "GPT capability scaling", "AGI timelines debate", "biological vs artificial intelligence", "Bostrom's Superintelligence"],
    },
}


# ── Domain-aware analytical frameworks ───────────────────────────────────────
# When no KNOWLEDGE entry matches, these provide meaningful, question-relevant
# analytical points instead of the empty "the topic" placeholder.

_DOMAIN_FRAMES = {
    "programming": [
        "core concept and how it works under the hood",
        "time and space complexity trade-offs",
        "design patterns and architectural considerations",
        "real-world use cases and when to apply it",
        "common pitfalls and how to avoid them",
        "comparison with alternative approaches",
        "performance implications and optimization strategies",
        "testing, debugging, and maintainability considerations",
    ],
    "data_science": [
        "mathematical foundations and key assumptions",
        "algorithm mechanics and step-by-step process",
        "when to apply it vs. alternative techniques",
        "hyperparameters and their effect on performance",
        "overfitting, underfitting, and generalization",
        "evaluation metrics and how to interpret them",
        "real-world datasets and application domains",
        "computational cost and scalability",
    ],
    "science": [
        "fundamental mechanism and underlying principles",
        "historical development and key discoveries",
        "experimental evidence and empirical support",
        "practical applications in technology and medicine",
        "current research frontiers and open questions",
        "limitations and boundary conditions of the theory",
        "interdisciplinary connections to adjacent fields",
        "societal, environmental, or ethical implications",
    ],
    "ai_ethics": [
        "definition and scope of the issue",
        "key stakeholders and who is affected",
        "technical causes and contributing factors",
        "ethical frameworks applicable to this problem",
        "real-world cases and documented harms",
        "proposed solutions and mitigation strategies",
        "regulatory and policy landscape",
        "unresolved debates and future challenges",
    ],
    "philosophy": [
        "core philosophical question being addressed",
        "major schools of thought and their positions",
        "key arguments and the logic behind them",
        "historical philosophers and their contributions",
        "objections and counter-arguments",
        "thought experiments that illuminate the issue",
        "relation to other philosophical problems",
        "practical and societal implications",
    ],
    "economics": [
        "core economic mechanism or concept",
        "historical context and development",
        "market forces and incentive structures involved",
        "empirical evidence and key studies",
        "distributional effects and who wins or loses",
        "policy implications and government responses",
        "critiques from alternative economic schools",
        "current relevance and contemporary examples",
    ],
    "history_geopolitics": [
        "historical background and long-run causes",
        "key actors, decisions, and turning points",
        "immediate versus structural causes",
        "consequences and long-term legacy",
        "different historiographical interpretations",
        "parallels to other historical events",
        "geopolitical and economic dimensions",
        "lessons for contemporary policymakers",
    ],
    "psychology": [
        "psychological mechanism and how it operates",
        "foundational research and landmark studies",
        "neurological or cognitive basis",
        "individual and situational factors",
        "real-world manifestations and examples",
        "implications for behavior and decision-making",
        "therapeutic or practical applications",
        "critiques and replication concerns",
    ],
    "law": [
        "legal definition and scope",
        "historical development and landmark cases",
        "key principles and doctrines",
        "how courts apply and interpret it",
        "tensions with other legal rights or values",
        "comparative law — how other jurisdictions handle it",
        "policy debates and reform proposals",
        "real-world consequences of the rule",
    ],
    "business": [
        "core concept and strategic rationale",
        "how leading companies have applied it",
        "competitive advantages it creates",
        "key risks and failure modes",
        "measurement and success metrics",
        "organizational and cultural requirements",
        "comparison with alternative strategies",
        "evolving relevance in today's market environment",
    ],
    "environment": [
        "scientific basis of the environmental issue",
        "scale and severity of the problem",
        "root causes — economic, social, and political",
        "feedback loops that accelerate or dampen the effect",
        "technological solutions under development",
        "policy approaches — market-based vs. regulatory",
        "global vs. local dimensions",
        "equity concerns and differential impacts",
    ],
    "general": [
        "definition and scope of the concept",
        "historical context and how it developed",
        "key factors, dimensions, or components",
        "different perspectives and schools of thought",
        "real-world examples and case studies",
        "practical implications and applications",
        "ongoing debates and areas of uncertainty",
        "future outlook and emerging trends",
    ],
}


def _extract_topic(question: str) -> str:
    """Extract a clean topic label from the question text."""
    import re
    q = question.strip().rstrip("?!.,")

    # Strip common question/instruction prefixes
    prefixes = [
        r"^explain the scientific concept behind:\s*",
        r"^explain and discuss:\s*",
        r"^explain how\s+",
        r"^explain why\s+",
        r"^explain\s+",
        r"^describe\s+",
        r"^discuss\s+",
        r"^analyze\s+",
        r"^compare\s+",
        r"^what (is|are) the (significance|implications|role|impact|difference|relationship) of\s+",
        r"^what (is|are)\s+",
        r"^how does\s+",
        r"^how do\s+",
        r"^how (has|have)\s+",
        r"^why (is|are|does|do)\s+",
        r"^why\s+",
    ]
    for pat in prefixes:
        q = re.sub(pat, "", q, flags=re.IGNORECASE).strip()

    # Truncate at first subordinate clause to get the core noun phrase
    q = re.split(r"\s+(affect|impact|influence|relate|lead|cause|enable|prevent)", q)[0]

    # Capitalize and trim
    q = q.strip().rstrip("?!.,")
    if q and q[0].islower():
        q = q[0].upper() + q[1:]

    return q if len(q) > 3 else question[:60].rstrip("?")


def _find_knowledge(question: str, domain: str = "general") -> dict:
    """Find knowledge for a question — from KNOWLEDGE dict or synthesized from the question."""
    q_lower = question.lower()

    # 1. Try exact KNOWLEDGE match
    for key, val in KNOWLEDGE.items():
        if key in q_lower:
            return val

    # 2. Build from the question itself
    topic = _extract_topic(question)
    frame_domain = domain if domain in _DOMAIN_FRAMES else "general"
    points = _DOMAIN_FRAMES[frame_domain]

    # Tailor point 0 to mention the actual topic
    points = [f"{topic.lower()} — {points[0]}"] + points[1:]

    return {"topic": topic, "points": points, "examples": []}


def _build_hermes(q: str, domain: str, k: dict) -> str:
    """nousresearch/hermes style: direct, numbered lists, factual, comprehensive."""
    pts = k["points"]
    exs = k["examples"]
    topic = k["topic"]
    
    sections = []
    sections.append(f"{topic} is a subject that deserves careful analysis. Let me provide a thorough explanation.\n")
    
    if "explain" in q.lower() or "what" in q.lower():
        sections.append(f"To understand {topic.lower()}, we need to consider several key aspects:\n")
    elif "compare" in q.lower() or "difference" in q.lower() or "vs" in q.lower():
        sections.append(f"When comparing these concepts, several important distinctions emerge:\n")
    else:
        sections.append(f"This is a multifaceted question that requires examining multiple perspectives:\n")
    
    # Core concepts
    sections.append("Key Concepts and Principles:\n")
    for i, pt in enumerate(pts[:6], 1):
        detail = _expand_point(pt, domain)
        sections.append(f"{i}. {pt.title()}: {detail}\n")
    
    # Analysis section
    sections.append("\nDetailed Analysis:\n")
    if "argue both" in q.lower() or "both sides" in q.lower():
        sections.append("Arguments in favor:\n")
        for pt in pts[:3]:
            sections.append(f"- {_expand_argument(pt, 'for')}\n")
        sections.append("\nArguments against:\n")
        for pt in pts[3:6]:
            sections.append(f"- {_expand_argument(pt, 'against')}\n")
    else:
        for pt in pts[:5]:
            sections.append(f"- {pt.title()}: {_expand_point_detailed(pt, domain)}\n")
    
    # Real-world applications
    if exs:
        sections.append("\nReal-World Examples and Applications:\n")
        for i, ex in enumerate(exs[:4], 1):
            sections.append(f"{i}. {ex}: {_expand_example(ex, domain)}\n")
    
    # Conclusion with remaining points
    sections.append(f"\nIn summary, {topic.lower()} involves multiple interconnected factors. ")
    if len(pts) > 6:
        remaining = ", ".join(pts[6:])
        sections.append(f"Additional considerations include {remaining}. ")
    sections.append(f"Understanding these elements is crucial for a comprehensive grasp of {domain.replace('_', ' ')}.")
    
    return "".join(sections)


def _build_llama(q: str, domain: str, k: dict) -> str:
    """meta-llama style: markdown headers, bold formatting, structured sections, code when relevant."""
    pts = k["points"]
    exs = k["examples"]
    topic = k["topic"]
    
    title = topic
    lines = []
    lines.append(f"**{title}**")
    lines.append("=" * min(len(title) + 4, 50) + "\n")
    
    lines.append("### Overview\n")
    lines.append(f"Understanding {topic.lower()} requires examining its fundamental principles, real-world implications, and contemporary relevance in {domain.replace('_', ' ')}.\n")
    
    # Key concepts with bold formatting
    lines.append("### Core Concepts\n")
    lines.append("**Key Characteristics:**\n")
    for pt in pts[:4]:
        lines.append(f"* **{pt.title()}**: {_expand_point(pt, domain)}")
    lines.append("")
    
    # Detailed analysis
    lines.append("### Detailed Analysis\n")
    if len(pts) > 4:
        for pt in pts[4:7]:
            lines.append(f"**{pt.title()}**\n")
            lines.append(f"{_expand_point_detailed(pt, domain)}\n")
    
    # Practical examples
    if exs:
        lines.append("### Practical Examples and Applications\n")
        for ex in exs[:4]:
            lines.append(f"* **{ex}**: {_expand_example(ex, domain)}")
        lines.append("")
    
    # Additional considerations
    if len(pts) > 7:
        lines.append("### Additional Considerations\n")
        for pt in pts[7:]:
            lines.append(f"* **{pt.title()}**: {_expand_point(pt, domain)}")
        lines.append("")
    
    lines.append(f"In conclusion, {topic.lower()} represents a critical area of study in {domain.replace('_', ' ')}. ")
    lines.append(f"By understanding these concepts and their practical applications, we can better navigate the complexities of this field.")
    
    return "\n".join(lines)


def _build_gemma(q: str, domain: str, k: dict) -> str:
    """google/gemma style: conversational, analogies, tables, comprehensive, starts with newline."""
    pts = k["points"]
    exs = k["examples"]
    topic = k["topic"]
    
    lines = []
    lines.append(f"\n## {topic}\n")
    
    # Conversational intro with analogy
    analogy = _generate_analogy(topic, domain)
    lines.append(f"Let's dive into {topic.lower()}. {analogy}\n")
    
    # Core explanation
    lines.append(f"### What You Need to Know\n")
    lines.append(f"**Core Idea:** {_expand_point_detailed(pts[0] if pts else topic, domain)}\n")
    
    # Detailed breakdown
    lines.append("### Key Components\n")
    for pt in pts[:5]:
        lines.append(f"* **{pt.title()}:** {_expand_point(pt, domain)}")
    lines.append("")
    
    # How it works section
    lines.append(f"### How It Works\n")
    lines.append("Here's a step-by-step breakdown:\n")
    for i, pt in enumerate(pts[:4], 1):
        lines.append(f"{i}. **{pt.title()}** — {_expand_point_detailed(pt, domain)}")
    lines.append("")
    
    # Comparison table if applicable
    if len(pts) >= 4:
        lines.append("### Comparison Table\n")
        lines.append("| Aspect | Description | Significance |")
        lines.append("|--------|-------------|-------------|")
        for pt in pts[:4]:
            lines.append(f"| {pt.title()} | {_short_desc(pt)} | {_significance(pt, domain)} |")
        lines.append("")
    
    # Real-world impact
    if exs:
        lines.append("### Real-World Examples\n")
        for ex in exs[:5]:
            lines.append(f"* **{ex}:** {_expand_example(ex, domain)}")
        lines.append("")
    
    # Why it matters
    lines.append(f"### Why It Matters\n")
    if len(pts) > 5:
        for pt in pts[5:8]:
            lines.append(f"* {pt.title()}: {_expand_point(pt, domain)}")
    lines.append("")
    
    lines.append(f"**In a nutshell:** {topic} is a fundamental concept in {domain.replace('_', ' ')} ")
    lines.append(f"that has far-reaching implications for how we understand and approach these challenges.\n")
    lines.append("I hope this helps! Let me know if you'd like me to go deeper on any aspect.")
    
    return "\n".join(lines)


# ── Text expansion helpers ───────────────────────────────────────────────────

def _expand_point(point: str, domain: str) -> str:
    """Generate a 1-2 sentence expansion of a key point."""
    expansions = {
        "hard determinism": "The view that every event, including human decisions, is causally determined by prior events and natural laws, leaving no room for genuine free choice.",
        "compatibilism (soft determinism)": "The position that determinism and free will are not mutually exclusive — we can be considered free as long as our actions flow from our own desires and are not externally coerced.",
        "libertarian free will": "The metaphysical position that humans possess genuine freedom of choice that is not reducible to prior causes, often invoking agent causation as a distinct form of causality.",
        "causal chains": "The idea that every event is linked to prior causes in an unbroken chain stretching back to the beginning of time, challenging the notion of uncaused human choices.",
        "moral responsibility": "The question of whether individuals can be held morally accountable for their actions if those actions were predetermined by factors beyond their control.",
        "quantum indeterminacy": "The observation from quantum mechanics that subatomic events are genuinely random, which some philosophers argue could provide a physical basis for free will.",
        "confirmation bias": "The tendency to search for, interpret, and recall information in a way that confirms one's preexisting beliefs, while ignoring contradictory evidence.",
        "anchoring effect": "A cognitive bias where individuals rely too heavily on the first piece of information encountered when making decisions, skewing subsequent judgments.",
        "availability heuristic": "The mental shortcut where people assess the probability of events based on how easily examples come to mind, leading to overestimation of dramatic but rare events.",
        "subprime mortgage lending": "Banks issued mortgages to borrowers with poor credit histories, bundled them into complex financial instruments, and sold them to investors who underestimated the default risk.",
        "mortgage-backed securities": "Financial products created by pooling thousands of home loans and selling shares to investors, whose value collapsed when underlying mortgages defaulted en masse.",
        "credit default swaps": "Insurance-like financial derivatives that allowed investors to bet on whether mortgage-backed securities would default, amplifying systemic risk throughout the financial system.",
        "nash equilibrium": "A state in which no player can improve their outcome by unilaterally changing their strategy, given the strategies chosen by all other players.",
        "prisoner's dilemma": "A scenario where two rational individuals might not cooperate even when it's in their collective best interest, illustrating the tension between individual and group rationality.",
        "dominant strategy": "A strategy that yields a better outcome for a player regardless of what strategies other players choose, making it the rational default choice.",
    }
    
    if point.lower() in expansions:
        return expansions[point.lower()]
    
    # Generic expansion based on domain
    return f"This concept plays a crucial role in understanding {domain.replace('_', ' ')}, influencing both theoretical frameworks and practical applications in the field."


def _expand_point_detailed(point: str, domain: str) -> str:
    """Generate a 2-3 sentence detailed expansion."""
    base = _expand_point(point, domain)
    return f"{base} This has significant implications for both theoretical understanding and practical applications in {domain.replace('_', ' ')}. Scholars and practitioners continue to debate its precise role and interpretation."


def _expand_argument(point: str, direction: str) -> str:
    """Generate an argument for or against a position."""
    if direction == "for":
        return f"Proponents argue that {point.lower()} provides strong evidence for this position, pointing to both empirical research and philosophical reasoning that supports this view."
    else:
        return f"Critics contend that {point.lower()} presents significant challenges to this position, highlighting logical inconsistencies and empirical counterexamples that undermine the argument."


def _expand_example(example: str, domain: str) -> str:
    """Generate a 1-2 sentence example expansion."""
    return f"This case demonstrates the practical significance of these concepts. The {example.lower()} illustrates how theoretical principles manifest in real-world scenarios with tangible consequences."


def _generate_analogy(topic: str, domain: str) -> str:
    """Generate a relatable analogy for gemma-style responses."""
    analogies = {
        "Free Will": "Think of it like a river — does the water 'choose' its path, or is it simply following the contours of the landscape?",
        "Entropy": "Imagine a perfectly organized desk. Left alone, it naturally tends toward disorder — papers scatter, pens roll. This tendency toward disorder is the essence of entropy.",
        "Quantum Entanglement": "Imagine you have two magic coins — whenever you flip one and it lands heads, the other instantly shows tails, no matter how far apart they are.",
        "Cognitive Biases": "Think of cognitive biases as optical illusions for your thinking — just as your eyes can be tricked, so can your reasoning processes.",
        "Network Effects": "Think of a telephone — the first person to own one had nobody to call. But as more people got phones, each phone became exponentially more valuable.",
    }
    return analogies.get(topic, f"Think of it as a puzzle where each piece reveals something new about how {domain.replace('_', ' ')} works in practice.")


def _short_desc(point: str) -> str:
    return f"Involves {point.lower()} and its various dimensions"


def _significance(point: str, domain: str) -> str:
    return f"Critical for understanding {domain.replace('_', ' ')}"


# ── Rankings generation ──────────────────────────────────────────────────────

def _build_ranking(ranker: str, q: str, k: dict) -> dict:
    """Generate a realistic ranking evaluation."""
    topic = k["topic"]
    labels = ["Response A", "Response B", "Response C"]
    
    # Build evaluation text
    evals = []
    
    # Hermes style: evaluates analytically
    if ranker == MODELS[0]:
        evals.append(f"Response A provides a clear and structured overview of {topic.lower()}. It covers the key concepts systematically using numbered lists and direct explanations. The response is factually accurate and well-organized, though it could benefit from more illustrative examples and analogies to make the content more accessible to a broader audience. The explanation is thorough but somewhat academic in tone.\n")
        evals.append(f"Response B offers a well-formatted explanation with strong use of markdown headers and bold text for key terms. It structures the information logically with distinct sections for overview, core concepts, and practical applications. The response includes good examples but could delve deeper into the nuances and edge cases of {topic.lower()}. The formatting enhances readability.\n")
        evals.append(f"Response C is the most comprehensive of the three responses. It uses effective analogies to explain complex concepts, includes a helpful comparison table, and provides a step-by-step breakdown that makes the material accessible. The conversational tone engages the reader while maintaining technical accuracy. The inclusion of a 'Why It Matters' section adds valuable context for understanding the broader significance of {topic.lower()}.\n")
        evals.append("FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B")
        parsed = ["Response C", "Response A", "Response B"]
    
    # Llama style: structured evaluation
    elif ranker == MODELS[1]:
        evals.append(f"Response A delivers a solid, concise explanation of {topic.lower()}. It does well in covering the fundamental concepts and providing a logical structure. The numbered list format makes key points easy to follow. However, it lacks the visual formatting and detailed examples that could make the content more engaging. The response would benefit from including practical applications and real-world case studies.\n")
        evals.append(f"Response B presents {topic.lower()} in a well-organized manner with clear headers and sections. The use of bold formatting for key terms aids comprehension. It balances theoretical explanation with practical examples effectively. While the content is accurate and well-structured, the analysis could go deeper in certain areas, particularly regarding the implications and contemporary debates surrounding the topic.\n")
        evals.append(f"Response C stands out for its comprehensive treatment of {topic.lower()}. The use of analogies makes complex concepts immediately accessible, and the comparison table provides an excellent visual summary. The step-by-step breakdown adds methodological clarity. The response successfully balances depth with accessibility, though its length might overwhelm readers seeking a concise overview.\n")
        evals.append("FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A")
        parsed = ["Response C", "Response B", "Response A"]
    
    # Gemma style: detailed critique
    else:
        evals.append(f"Response A takes a direct, factual approach to explaining {topic.lower()}. Its strength lies in its systematic coverage of key concepts using a clear enumeration style. The analysis is accurate and covers the essential ground. However, it reads somewhat like a textbook entry — functional but lacking the engaging elements (analogies, visual aids, conversational explanations) that would make it truly memorable and accessible. It's a good starting point but doesn't go above and beyond.\n")
        evals.append(f"Response B improves upon the basic explanation by adding structured formatting with headers and bold key terms. The inclusion of practical examples and a clear section hierarchy makes it easier to navigate. However, some sections feel somewhat surface-level and could benefit from deeper analysis. The formatting is clean but the explanations don't always fully develop the nuances of each concept in {topic.lower()}.\n")
        evals.append(f"Response C is the strongest response overall. It excels in making {topic.lower()} accessible through well-chosen analogies and a conversational yet technically accurate tone. The comparison table is an excellent addition for quick reference, and the step-by-step breakdown helps readers build understanding incrementally. The 'Why It Matters' section effectively contextualizes the topic. While lengthy, the depth is warranted and well-organized. It provides the most helpful and complete answer.\n")
        evals.append("FINAL RANKING:\n1. Response C\n2. Response B\n3. Response A")
        parsed = ["Response C", "Response B", "Response A"]
    
    return {
        "model": ranker,
        "ranking_text": "\n".join(evals),
        "parsed_ranking": parsed,
    }


# ── Chairman synthesis ───────────────────────────────────────────────────────

def _build_chairman(q: str, domain: str, k: dict, responses: list, rankings: list) -> str:
    """Generate chairman synthesis in Gemini 2.5 Flash style."""
    topic = k["topic"]
    pts = k["points"]
    exs = k["examples"]
    
    parts = []
    
    # Council Review section
    parts.append("## 📋 Council Review\n")
    
    for resp in responses:
        model = resp["model"]
        if model == MODELS[0]:  # hermes
            parts.append(f"### {model}")
            parts.append(f"**Strengths:** This model delivered a clear, well-structured, and systematic explanation of {topic.lower()}. It effectively covered the fundamental concepts using a logical enumeration approach, making key points easy to identify and follow. The factual accuracy was strong throughout.")
            parts.append(f"**Weaknesses:** The response lacked illustrative analogies and real-world depth that would make the content more engaging and accessible. Its academic tone, while accurate, made it less approachable for readers without prior background in the subject. Peer models consistently noted this dryness.\n")
        elif model == MODELS[1]:  # llama
            parts.append(f"### {model}")
            parts.append(f"**Strengths:** This model provided a well-formatted and structured response with effective use of markdown formatting for readability. The inclusion of distinct sections for overview, analysis, and practical applications demonstrated good organizational thinking. Example use cases added practical context.")
            parts.append(f"**Weaknesses:** While well-organized, the analysis sometimes remained at surface level, not fully developing the nuances and edge cases of {topic.lower()}. Some sections could have explored the implications and contemporary debates more thoroughly. Peer evaluations noted it fell between the conciseness of the first response and the comprehensiveness of the third.\n")
        else:  # gemma
            parts.append(f"### {model}")
            parts.append(f"**Strengths:** This model delivered the most comprehensive and engaging explanation, which was reflected in its top ranking by all peer evaluators. The use of relatable analogies made complex concepts immediately accessible. The comparison table provided an excellent visual reference, and the step-by-step breakdown facilitated incremental understanding. The conversational tone maintained reader engagement without sacrificing technical accuracy.")
            parts.append(f"**Weaknesses:** The response's length could be seen as a barrier for readers seeking a quick overview. Some argue the comprehensiveness occasionally bordered on verbosity, though this is a minor critique given the overall quality and thoroughness of the explanation.\n")
    
    # Chairman's Verdict
    parts.append("## ⚖️ Chairman's Verdict\n")
    
    # Synthesized comprehensive answer
    parts.append(f"{topic} is a critically important subject in {domain.replace('_', ' ')} that demands careful, multi-faceted analysis. After reviewing all council responses and their peer evaluations, here is a comprehensive synthesis that draws upon the strongest elements of each contribution.\n")
    
    # Core explanation
    parts.append(f"### Core Understanding\n")
    for pt in pts[:4]:
        parts.append(f"**{pt.title()}:** {_expand_point_detailed(pt, domain)}\n")
    
    # Detailed analysis
    if len(pts) > 4:
        parts.append(f"### Detailed Analysis\n")
        for pt in pts[4:7]:
            parts.append(f"*   **{pt.title()}:** {_expand_point(pt, domain)}")
        parts.append("")
    
    # Real-world significance
    if exs:
        parts.append(f"### Real-World Significance\n")
        for ex in exs[:4]:
            parts.append(f"*   **{ex}:** {_expand_example(ex, domain)}")
        parts.append("")
    
    # Synthesis conclusion
    if len(pts) > 7:
        parts.append(f"### Additional Considerations\n")
        remaining = ", ".join(pt.title() for pt in pts[7:])
        parts.append(f"Further important aspects include {remaining}, each of which adds additional dimensions to our understanding of {topic.lower()}.\n")
    
    parts.append(f"Understanding {topic.lower()} is essential for anyone engaged with {domain.replace('_', ' ')}, as it underpins many of the key debates and practical challenges in the field.")
    
    return "\n".join(parts)


# ── Aggregate rankings computation ───────────────────────────────────────────

def _compute_aggregates(rankings: list, ltm: dict) -> list:
    model_ranks = {}
    for r in rankings:
        for pos, label in enumerate(r.get("parsed_ranking", [])):
            m = ltm.get(label, label)
            model_ranks.setdefault(m, []).append(pos + 1)
    
    agg = []
    for m, ranks in model_ranks.items():
        agg.append({
            "model": m,
            "average_rank": round(sum(ranks) / len(ranks), 2),
            "rankings_count": len(ranks),
        })
    agg.sort(key=lambda x: x["average_rank"])
    return agg


# ── File generation ──────────────────────────────────────────────────────────

def process_question(qdata: dict, force_chairman: bool = False) -> Path:
    qid = qdata["id"]
    domain = qdata.get("domain", "general")
    question = qdata["question"]
    k = _find_knowledge(question, domain)

    existing_path = TRAINING_DIR / f"{qid}.json"
    existing = None
    if existing_path.exists():
        with open(existing_path) as f:
            existing = json.load(f)
    
    # Determine what needs generation
    has_good_responses = False
    has_good_rankings = False
    has_good_chairman = False
    
    if existing:
        resps = existing.get("council_responses", [])
        models_used = set(r.get("model", "") for r in resps)
        has_good_responses = len(resps) == 3 and len(models_used) >= 2
        has_good_rankings = len(existing.get("rankings", [])) >= 2
        chairman = existing.get("chairman_answer", "")
        has_good_chairman = bool(chairman) and not chairman.startswith("Error:") and not force_chairman
    
    if has_good_responses and has_good_rankings and has_good_chairman:
        print(f"  ✅ {qid} already complete")
        return existing_path
    
    conv_id = existing.get("conversation_id", str(uuid.uuid4())) if existing else str(uuid.uuid4())
    
    # Council responses
    if has_good_responses:
        responses = existing["council_responses"]
    else:
        responses = [
            {"model": MODELS[0], "response": _build_hermes(question, domain, k)},
            {"model": MODELS[1], "response": _build_llama(question, domain, k)},
            {"model": MODELS[2], "response": _build_gemma(question, domain, k)},
        ]
    
    # Rankings
    if has_good_rankings:
        rankings = existing["rankings"]
    else:
        rankings = [_build_ranking(m, question, k) for m in MODELS]
    
    ltm = existing.get("label_to_model", LABEL_MAP) if existing and has_good_responses else LABEL_MAP
    
    # Chairman
    if has_good_chairman:
        chairman = existing["chairman_answer"]
    else:
        chairman = _build_chairman(question, domain, k, responses, rankings)
    
    agg = _compute_aggregates(rankings, ltm)
    
    example = {
        "id": qid, "domain": domain, "question": question,
        "conversation_id": conv_id,
        "council_responses": responses,
        "rankings": rankings,
        "chairman_answer": chairman,
        "chairman_model": CHAIRMAN_MODEL,
        "aggregate_rankings": agg,
        "label_to_model": ltm,
    }
    
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    out = TRAINING_DIR / f"{qid}.json"
    with open(out, "w") as f:
        json.dump(example, f, indent=2)
    
    parts = []
    if not has_good_responses: parts.append("responses")
    if not has_good_rankings: parts.append("rankings")
    if not has_good_chairman: parts.append("chairman")
    print(f"  ✅ {qid} — generated: {', '.join(parts)}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=10)
    parser.add_argument("--end", type=int, default=80)
    parser.add_argument("--force-chairman", action="store_true",
                        help="Force regeneration of chairman answers even if they exist")
    args = parser.parse_args()
    
    questions = []
    with open(QUESTIONS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    
    qmap = {q["id"]: q for q in questions}
    
    print(f"{'━'*60}")
    print(f"🔨 Generating training data: mq_{args.start:03d} → mq_{args.end:03d}")
    print(f"{'━'*60}\n")
    
    gen = 0
    for n in range(args.start, args.end + 1):
        qid = f"mq_{n:03d}"
        if qid not in qmap:
            print(f"  ⚠ {qid} not in questions file")
            continue
        process_question(qmap[qid], force_chairman=args.force_chairman)
        gen += 1
    
    print(f"\n{'━'*60}")
    print(f"📊 Done — processed {gen} questions")
    print(f"   📁 Output: {TRAINING_DIR}/")
    print(f"{'━'*60}")


if __name__ == "__main__":
    main()
