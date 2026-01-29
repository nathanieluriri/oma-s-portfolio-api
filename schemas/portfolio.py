# ============================================================================
#PORTFOLIO SCHEMA 
# ============================================================================
# This file was auto-generated on: 2026-01-28 16:49:51 WAT
# It contains Pydantic classes  database
# for managing attributes and validation of data in and out of the MongoDB database.
#
# ============================================================================

from schemas.imports import *
from pydantic import AliasChoices, Field
import time

class NavItem(BaseModel):
    href: str
    label: str

class FooterContent(BaseModel):
    copyright: str = "© 2026 Oma Dashi"
    tagline: str = "Built with calm systems thinking."

class AvailabilityBadge(BaseModel):
    label: str = "Available"
    status: str = "available"

class HeroSection(BaseModel):
    name: str = "Oma Dashi"
    title: str = "Systems Engineer · Product Builder"
    bio: List[str] = Field(
        default_factory=lambda: [
            "I design systems that scale with clarity, care, and restraint.",
            "I build products that make complex ideas feel simple.",
        ]
    )
    availability: AvailabilityBadge = Field(default_factory=AvailabilityBadge)

class ExperienceEntry(BaseModel):
    date: str
    role: str
    company: str
    link: Optional[str] = None
    description: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    current: bool = False

class ProjectRole(BaseModel):
    title: str = "Full-Stack Engineer"
    bullets: List[str] = Field(default_factory=list)

class ProjectScreenshot(BaseModel):
    src: str
    alt: str = ""
    caption: Optional[str] = None

class ProjectCaseStudy(BaseModel):
    overview: str = ""
    goal: str = ""
    role: ProjectRole = Field(default_factory=ProjectRole)
    screenshots: List[ProjectScreenshot] = Field(default_factory=list)
    outcomes: List[str] = Field(default_factory=list)

class ProjectEntry(BaseModel):
    title: str
    tags: List[str] = Field(default_factory=list)
    description: str
    link: str
    caseStudy: ProjectCaseStudy = Field(
        default_factory=ProjectCaseStudy,
        validation_alias=AliasChoices("caseStudy", "case_study"),
        serialization_alias="caseStudy",
    )

class SkillGroup(BaseModel):
    title: str
    items: List[str] = Field(default_factory=list)

class ContactEntry(BaseModel):
    label: str
    value: str
    href: str
    icon: Optional[str] = None

class EducationEntry(BaseModel):
    degree: str = ""
    institution: str = ""
    location: str = ""
    graduationDate: str = ""
    gpa: str = ""

class ThemeColors(BaseModel):
    text_primary: str = "#1B1B1B"
    text_secondary: str = "#4B4B4B"
    text_muted: str = "#7A7A7A"
    bg_primary: str = "#F7F4EF"
    bg_surface: str = "#FFFFFF"
    bg_surface_hover: str = "#F0ECE6"
    bg_divider: str = "#E5DED5"
    accent_primary: str = "#E6772E"
    accent_muted: str = "#F2B28E"

class AnimationSettings(BaseModel):
    staggerChildren: float = 0.12
    delayChildren: float = 0.08
    duration: float = 0.45
    ease: str = "easeOut"

class Metadata(BaseModel):
    title: str = "Chioma Ejike"
    description: str = "Portfolio for Chioma Ejike."
    author: str = "Chioma Ejike"

class PortfolioBase(BaseModel):
    # Add other fields here 
    user_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("user_id", "userId"),
        serialization_alias="userId",
    )
    navItems: List[NavItem] = Field(
        default_factory=lambda: [
            {"href": "/", "label": "about"},
            {"href": "/#experience", "label": "experience"},
            {"href": "/#projects", "label": "projects"},
            {"href": "/#tools", "label": "tools"},
            {"href": "/#contact", "label": "contact"},
        ]
    ) # type: ignore
    footer: FooterContent = Field(default_factory=FooterContent)
    hero: HeroSection = Field(default_factory=HeroSection)
    experience: List[ExperienceEntry] = Field(
        default_factory=lambda: [
            {
                "date": "2023 — Present",
                "role": "Senior Systems Engineer",
                "company": "Nordlane Labs",
                "link": "https://example.com",
                "description": "Leading platform architecture and core infrastructure.",
                "highlights": [
                    "Designed a fault-tolerant ingestion pipeline.",
                    "Reduced latency by 38% across critical paths.",
                    "Mentored a cross-functional platform team.",
                ],
                "current": True,
            }
        ]
    ) # type: ignore
    projects: List[ProjectEntry] = Field(
        default_factory=lambda: [
            {
                "title": "SignalForge Analytics",
                "tags": ["Observability", "SaaS", "B2B"],
                "description": "A real-time ops console for multi-cloud systems.",
                "link": "/projects/signalforge",
            }
        ]
    ) # type: ignore
    skillGroups: List[SkillGroup] = Field(
        default_factory=lambda: [
            {
                "title": "Languages & Frameworks",
                "items": ["TypeScript", "Go", "Python", "Node.js", "React", "Next.js", "PostgreSQL", "Redis"],
            },
            {
                "title": "Infrastructure & Tools",
                "items": ["Docker", "Kubernetes", "AWS", "Terraform", "Grafana", "Prometheus", "GitHub Actions", "Vercel"],
            },
        ]
    ) # type: ignore
    education: List[EducationEntry] = Field(default_factory=list)
    contacts: List[ContactEntry] = Field(
        default_factory=lambda: [
            {"label": "Email", "value": "hello@oma.com", "href": "mailto:hello@oma.com", "icon": None},
            {"label": "GitHub", "value": "github.com/oma", "href": "https://github.com/oma", "icon": None},
            {"label": "LinkedIn", "value": "linkedin.com/in/oma", "href": "https://linkedin.com/in/oma", "icon": None},
            {"label": "Location", "value": "Remote", "href": "#", "icon": None},
        ]
    ) # type: ignore
    theme: ThemeColors = Field(default_factory=ThemeColors)
    animations: AnimationSettings = Field(default_factory=AnimationSettings)
    metadata: Metadata = Field(default_factory=Metadata)
    resumeUrl: str = "/resume.pdf"

class PortfolioCreate(PortfolioBase):
    # Add other fields here 
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class PortfolioUpdate(BaseModel):
    # Add other fields here 
    navItems: Optional[List[NavItem]] = None
    footer: Optional[FooterContent] = None
    hero: Optional[HeroSection] = None
    experience: Optional[List[ExperienceEntry]] = None
    projects: Optional[List[ProjectEntry]] = None
    skillGroups: Optional[List[SkillGroup]] = None
    education: Optional[List[EducationEntry]] = None
    contacts: Optional[List[ContactEntry]] = None
    theme: Optional[ThemeColors] = None
    animations: Optional[AnimationSettings] = None
    metadata: Optional[Metadata] = None
    resumeUrl: Optional[str] = None
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class PortfolioOut(PortfolioBase):
    # Add other fields here 
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    date_created: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("date_created", "dateCreated"),
        serialization_alias="dateCreated",
    )
    last_updated: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("last_updated", "lastUpdated"),
        serialization_alias="lastUpdated",
    )
    
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])  # coerce to string before validation
        return values
            
    class Config:
        populate_by_name = True  # allows using `id` when constructing the model
        arbitrary_types_allowed = True  # allows ObjectId type
        json_encoders ={
            ObjectId: str  # automatically converts ObjectId → str
        }
