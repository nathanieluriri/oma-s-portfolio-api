import os
import time
from pymongo import MongoClient

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def build_portfolio_payload(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "navItems": [
            {"href": "/", "label": "about"},
            {"href": "/work", "label": "work"},
            {"href": "/experience", "label": "experience"},
        ],
        "footer": {
            "copyright": "© 2026 Okpe Onoja Godwin",
            "tagline": "Built with calm systems thinking.",
        },
        "hero": {
            "name": "Okpe Onoja Godwin",
            "title": "Fullstack Engineer, Nigeria",
            "bio": [
                "A focused full-stack engineer with experience building full-stack products to solve complex real world problems. I have a strong background in building and shipping real-world products across fintech, healthcare, commerce, and developer tooling. I enjoy working close to the core of a system designing APIs, data models, and infrastructure that are reliable, scalable, and easy for teams to build on.",
                "In recent roles, I've worked on high-traffic systems including POS platforms, real estate marketplaces, and AI-powered tools. My work often involves handling payments, real-time communication, and performance-sensitive workflows, with a strong emphasis on correctness, security, and long-term maintainability.",
                "Outside of work, I like breaking things down and understanding how they work whether that's exploring new ideas, refining side projects, or quietly improving the small details that most people never notice.",
            ],
            "availability": {"label": "Open to Work", "status": "open"},
        },
        "experience": [
            {
                "date": "Sep 2024 – Present",
                "role": "Backend Engineer",
                "company": "Lunix POS",
                "link": "",
                "description": "Working on high-scale POS systems powering real-world businesses. I've built bill payment APIs supporting 150+ providers and developed a time-tracking system with automated payroll calculations. I also led the rebuild of FixMaster POS API v2 to significantly improve performance, reliability, and scalability.",
                "highlights": [],
                "current": True,
            },
            {
                "date": "Feb 2023 – Dec 2025",
                "role": "CTO / Backend Engineer",
                "company": "Turfind",
                "link": "",
                "description": "Architected and built a full real estate platform from the ground up, including escrow-based payments, property listings, 3D virtual tours, and in-app messaging. Led technical decisions across the platform while maintaining 99.9% uptime as the product scaled.",
                "highlights": [],
                "current": False,
            },
            {
                "date": "Jun 2024 – Dec 2025",
                "role": "Mobile Engineer",
                "company": "ScriptDesk",
                "link": "",
                "description": "Developed and shipped multiple mobile applications across fintech, health, and media. Work included loan platforms, health booking systems, NFC-powered fan experiences, and real-time audio recognition features using ShazamKit.",
                "highlights": [],
                "current": False,
            },
            {
                "date": "Mar 2024 – Jul 2024",
                "role": "Backend Engineer",
                "company": "PocketLawyers.io",
                "link": "",
                "description": "Built the backend for a virtual legal services platform, including encrypted real-time chat, secure document sharing, escrow payments, KYC verification, and an analytics-driven admin dashboard.",
                "highlights": [],
                "current": False,
            },
            {
                "date": "Jun 2023 – Sep 2023",
                "role": "Backend Engineer",
                "company": "RHIPFactory Healthcare Studio",
                "link": "",
                "description": "Worked on healthcare-focused platforms for events and donations, implementing secure payment flows, real-time activity feeds, and analytics to improve engagement and fundraising outcomes.",
                "highlights": [],
                "current": False,
            },
        ],
        "projects": [
            {
                "title": "Synqly",
                "tags": ["AI", "Developer Tools", "APIs", "SaaS", "Infrastructure"],
                "description": "Architected a unified API platform that abstracts complexity across multiple LLM providers. Built intelligent fallback mechanisms and real-time observability dashboards for cost optimization.",
                "link": "/work",
            },
            {
                "title": "Knowledge Sweeper",
                "tags": ["SaaS", "Productivity", "Fullstack"],
                "description": "Engineered a distributed system that aggregates and surfaces organizational knowledge from Slack and Discord. Built scalable ingestion pipelines with full-text search and semantic ranking.",
                "link": "/work",
            },
            {
                "title": "Fantaform",
                "tags": ["AI", "Sports Tech", "Fullstack", "Data-driven"],
                "description": "Built a machine learning pipeline that analyzes player stats and fixture difficulty to generate weekly FPL recommendations. Designed predictive models with real-time performance dashboards.",
                "link": "/work",
            },
            {
                "title": "Stock Report",
                "tags": ["Fintech", "APIs", "Fullstack", "Data Visualization"],
                "description": "Architected a real-time financial aggregation platform consolidating market metrics from multiple APIs. Implemented intelligent caching with interactive visualizations for portfolio tracking.",
                "link": "/work",
            },
            {
                "title": "How Much",
                "tags": ["AI", "API Design", "Backend", "Developer Tools"],
                "description": "Designed a RESTful API leveraging GPT models to generate context-aware pricing recommendations for freelance projects. Built MongoDB analytics for pricing trend analysis.",
                "link": "/work",
            },
            {
                "title": "Springten",
                "tags": ["Blockchain", "Mobile", "DeFi", "Fullstack"],
                "description": "Built a production-ready mobile cryptocurrency wallet with React Native. Integrated blockchain APIs for multi-chain management with secure biometric authentication and DeFi protocol support.",
                "link": "/work",
            },
            {
                "title": "Bazaar Africa",
                "tags": ["E-commerce", "Payments", "Mobile", "APIs"],
                "description": "Architected scalable backend infrastructure for a B2C e-commerce platform serving African artisans. Built payment gateway integrations and mobile-first APIs optimized for low-bandwidth environments.",
                "link": "/work",
            },
            {
                "title": "Kurenode",
                "tags": ["Health Tech", "Mobile", "TypeScript", "Firebase"],
                "description": "Built a HIPAA-compliant mobile health platform for patient management and EHR integration. Implemented real-time Firebase sync with secure authentication and tablet-optimized clinical workflows.",
                "link": "/work",
            },
            {
                "title": "Dishpatch",
                "tags": ["Backend", "APIs", "Logistics", "Scalability"],
                "description": "Designed a high-throughput backend system for restaurant operations and last-mile delivery. Built event-driven architecture for real-time order tracking with payment processing pipelines.",
                "link": "/work",
            },
        ],
        "skillGroups": [
            {
                "title": "Languages & Frameworks",
                "items": [
                    "Node.js & Nest.js",
                    "TypeScript",
                    "React & React Native",
                    "Python",
                    "Golang",
                    "GraphQL",
                    "PostgreSQL",
                    "MongoDB",
                ],
            },
            {
                "title": "Infrastructure & Tools",
                "items": [
                    "AWS & Cloud",
                    "Docker",
                    "Redis",
                    "Microservices",
                    "CI/CD",
                    "Git",
                    "REST APIs",
                    "WebSockets",
                ],
            },
        ],
        "contacts": [
            {
                "label": "Email",
                "value": "okpeonoja18@gmail.com",
                "href": "mailto:okpeonoja18@gmail.com",
                "icon": "email",
            },
            {
                "label": "GitHub",
                "value": "github.com/onoja123",
                "href": "https://github.com/onoja123",
                "icon": "github",
            },
            {
                "label": "X (Twitter)",
                "value": "twitter.com/iam_the_code",
                "href": "https://twitter.com/iam_the_code",
                "icon": "x",
            },
            {
                "label": "LinkedIn",
                "value": "linkedin.com/in/okpe-onoja-godwin",
                "href": "https://www.linkedin.com/in/okpe-onoja-godwin/",
                "icon": "linkedin",
            },
            {
                "label": "Contra",
                "value": "contra.com/onoja_okpe",
                "href": "https://contra.com/onoja_okpe",
                "icon": "shield",
            },
        ],
        "theme": {
            "text_primary": "#111827",
            "text_secondary": "#374151",
            "text_muted": "#6B7280",
            "bg_primary": "#FAFAF9",
            "bg_surface": "#FFFFFF",
            "bg_surface_hover": "#F3F4F6",
            "bg_divider": "#E5E7EB",
            "accent_primary": "#EA580C",
            "accent_muted": "#FFEDD5",
        },
        "animations": {
            "staggerChildren": 0.12,
            "delayChildren": 0.08,
            "duration": 0.45,
            "ease": "easeOut",
        },
        "metadata": {
            "title": "Welcome | Okpe Onoja Godwin",
            "description": "Hi, I'm Okpe Onoja Godwin, a full-stack developer creating products that solve real-world problems. I specialize in scalable backend systems and intuitive frontend interfaces. Explore my projects and my journey!",
            "author": "Okpe Onoja Godwin",
        },
        "resumeUrl": "/okpeonojagodwin_resume.pdf",
    }


def load_settings() -> tuple[str, str, set[str]]:
    if load_dotenv:
        load_dotenv()
    else:
        load_env_file()
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
    db_name = os.getenv("DB_NAME", "OmaPortfolio")
    allowed_emails = {
        email.strip().lower()
        for email in os.getenv("ALLOWED_GOOGLE_EMAILS", "").split(",")
        if email.strip()
    }
    return mongo_url, db_name, allowed_emails


def seed_portfolio_for_user_id(collection, user_id: str) -> None:
    payload = build_portfolio_payload(user_id)
    now = int(time.time())

    existing = collection.find_one({"user_id": user_id})
    if existing and "date_created" in existing:
        payload["date_created"] = existing["date_created"]
    else:
        payload["date_created"] = now
    payload["last_updated"] = now

    collection.update_one({"user_id": user_id}, {"$set": payload}, upsert=True)

    print(f"Seeded portfolio for user_id={user_id}")


def seed_portfolios_for_allowed_emails(collection, users_collection, allowed_emails: set[str]) -> None:
    if not allowed_emails:
        print("No allowed emails configured; nothing to seed.")
        return

    for email in sorted(allowed_emails):
        user = users_collection.find_one({"email": email})
        if not user:
            print(f"Skipping {email}: no matching user found.")
            continue
        user_id = str(user.get("_id"))
        if not user_id:
            print(f"Skipping {email}: user_id missing.")
            continue
        seed_portfolio_for_user_id(collection, user_id)


if __name__ == "__main__":
    default_user_id = "697a3a30fa806c842c24d553"
    mongo_url, db_name, allowed_emails = load_settings()
    client = MongoClient(mongo_url)
    db = client[db_name]
    portfolios = db["portfolios"]
    users = db["users"]

    seed_all_allowed = os.getenv("SEED_ALL_ALLOWED_EMAILS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }
    arg = os.sys.argv[1] if len(os.sys.argv) > 1 else ""

    if arg in {"--allowed-emails", "--allowed"} or seed_all_allowed:
        seed_portfolios_for_allowed_emails(portfolios, users, allowed_emails)
    else:
        user_id = os.getenv("SEED_USER_ID") or arg or default_user_id
        seed_portfolio_for_user_id(portfolios, user_id)
