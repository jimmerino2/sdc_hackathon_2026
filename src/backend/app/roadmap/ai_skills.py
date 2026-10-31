"""The AI skills a roadmap can include: a fixed list. The model only chooses which of them a role's roadmap gets, and in what order, and
words one line on each for the role (see planner.choose_guides). Everything else here is fixed on purpose: a model asked for steps or
links writes ones that don't exist. Every link is a YouTube video that was checked to exist; none was written by a model.

The list is in the order they are offered when the model can't be used: what AI is and how to ask it first, then building with it,
then checking and safeguarding it.
"""
from dataclasses import dataclass

PREFIX = "ai:"  # a skill_id is PREFIX + slug; the same id for every role (onet_role_skills is keyed by role and id)


@dataclass(frozen=True)
class Video:
    title: str
    url: str


@dataclass(frozen=True)
class AiSkill:
    slug: str
    title: str  # at most 40 characters: it names a node
    about: str  # what it covers, for the model that chooses
    description: str  # the line shown when the model can't write one for the role
    steps: tuple[str, str, str]
    videos: tuple[Video, Video]

    @property
    def id(self) -> str:
        return PREFIX + self.slug


def _yt(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


CATALOG: tuple[AiSkill, ...] = (
    AiSkill(
        "generative-ai", "Generative AI",
        "how text, image and code AI works and where it fails",
        "Understand how text, image and code AI works, so you know what to trust and where it fails.",
        ("Ask a chat AI to explain how it works, then explain it back.", "Find one thing it gets wrong and say why.", "Check one claim it makes against a trusted source."),
        (Video("Intro to generative AI (Google Cloud)", _yt("9Eh7gsIH5h4")), Video("Generative AI explained in 2 minutes (KI-Campus)", _yt("rwF-X5STYks"))),
    ),
    AiSkill(
        "prompt-engineering", "Prompt Engineering",
        "asking an AI clearly: role, context, examples and format",
        "Ask AI clearly with a role, context, examples and a format, then check the answer.",
        ("Rewrite a vague prompt with a role, context and format.", "Add one example and compare the answers.", "Ask the AI to show its steps, then check them."),
        (Video("Prompt engineering essentials (GitHub)", _yt("LAF-lACf2QY")), Video("Prompt Engineering crash course, 5 hours (Zero To Mastery)", _yt("LWiMwhDZ9as"))),
    ),
    AiSkill(
        "ai-tools", "AI Tools",
        "choosing and using everyday AI tools for study and work",
        "Choose and use everyday AI tools for study and work, and know what you should never paste into them.",
        ("Try two AI tools on the same task and compare.", "Load your own notes into a notebook tool and ask questions.", "Write down what you will not paste into an AI."),
        (Video("An AI study system in Gemini and NotebookLM (Sabba Quidwai)", _yt("5UHoXEFZiHg")), Video("10 ways to use NotebookLM to learn fast (Blazing Zebra)", _yt("tIRkQeHwsm0"))),
    ),
    AiSkill(
        "ai-assisted-development", "AI-assisted Development",
        "using coding assistants and agents to write, review and debug code",
        "Use AI assistants to write, review and debug code faster, while you stay in charge of the thinking.",
        ("Ask an AI to explain an error, then fix it yourself.", "Have an AI review your code and check each point it raises.", "Write one small function without AI, then compare."),
        (Video("AI-Assisted Coding Tutorial (freeCodeCamp)", _yt("wlpBCazAY9Q")), Video("8 best practices to generate code using AI tools (Qodo)", _yt("3WApsAwSV78"))),
    ),
    AiSkill(
        "context-engineering", "Context Engineering",
        "deciding what goes into an AI's limited context window, and what stays out",
        "Decide what goes into an AI's limited context so it has what it needs and nothing that misleads it.",
        ("List what an AI needs to know to do one task well.", "Cut anything it doesn't need and compare the answers.", "Put the key facts first and see if results improve."),
        (Video("Context engineering for AI agents: 4 failure modes (IBM Technology)", _yt("BwXremQ-i6I")), Video("Context engineering explained (MLTut)", _yt("D9vE-9mSUaw"))),
    ),
    AiSkill(
        "rag", "Retrieval-Augmented Generation (RAG)",
        "giving an AI your own documents so its answers come from them",
        "Give an AI your own documents so its answers come from them, and learn to check the sources.",
        ("Pick 5 documents and ask an AI questions about them.", "Check that each answer points to the right passage.", "Ask something the documents don't cover and see what happens."),
        (Video("What is Retrieval Augmented Generation? (Google Cloud Tech)", _yt("9_IKLDGzB5Q")), Video("What is RAG? Explained simply (Redis)", _yt("xPMQ2cVbUTI"))),
    ),
    AiSkill(
        "agentic-workflows", "Agentic Workflows",
        "breaking a goal into steps an AI plans, runs and checks",
        "Break a goal into steps an AI plans, runs and checks, and know where a person still decides.",
        ("Split a task into 3 steps an AI could do one by one.", "Add a check after each step before the next starts.", "Run it and note where a human still has to decide."),
        (Video("What's next for AI agentic workflows, Andrew Ng (Sequoia Capital)", _yt("sal78ACtGTc")), Video("Building more effective AI agents (Anthropic)", _yt("uhJJgc-0iTQ"))),
    ),
    AiSkill(
        "mcp", "Model Context Protocol (MCP)",
        "the open standard that connects AI apps to tools and data",
        "MCP is the open standard that lets AI apps connect to tools and data. Learn what it does and what to allow.",
        ("Explain in your own words what an MCP server does.", "Connect one existing MCP server to an AI app.", "List what it can read and what it can change."),
        (Video("The Model Context Protocol (Anthropic)", _yt("CQywdSdi5iA")), Video("MCP explained in 20 minutes (Shaw Talebi)", _yt("N3vHJcHBS-w"))),
    ),
    AiSkill(
        "agent-skills", "Agent Skills",
        "packaging instructions as reusable skill folders an agent loads when a task needs them",
        "Package what you know as a reusable skill that an AI agent loads only when the task needs it.",
        ("Pick a task you repeat and write its steps down.", "Put them in a SKILL.md with a clear description.", "Try it on a fresh task and fix what the agent misses."),
        (Video("Claude Agent Skills explained (Anthropic)", _yt("fOxC44g8vig")), Video("The only Claude Skills guide you need (Kenny Liao)", _yt("421T2iWTQio"))),
    ),
    AiSkill(
        "agents-md", "Agents MD Files",
        "writing an AGENTS.md so coding agents know a project's rules",
        "Write an AGENTS.md so coding agents know how to build, test and follow the rules of your project.",
        ("Write the commands to build and test your project.", "Add your code style rules in a few short lines.", "Run an agent and trim what it ignores or gets wrong."),
        (Video("Agents.md explained (Prompt Engineering)", _yt("XDP94mYMCzA")), Video("How I write my AGENTS.md files (NeuralNine)", _yt("6w88NVf2_lY"))),
    ),
    AiSkill(
        "llm-evaluation", "LLM Evaluation",
        "testing whether AI output is good: test cases, scoring, AI judges",
        "Test whether AI output is actually good, with test questions, scores and an AI judge you check yourself.",
        ("Write 10 test questions with the answers you expect.", "Run them through an AI and score each answer.", "Compare an AI judge's scores with your own."),
        (Video("How to evaluate an LLM application (Evidently AI)", _yt("RIGU1hy3UR8")), Video("LLM evaluation: reference-free evals (Evidently AI)", _yt("-zoIqOpt2DA"))),
    ),
    AiSkill(
        "ai-security", "AI Security",
        "prompt injection, and keeping keys and private data safe around AI tools",
        "Spot prompt injection and keep keys, files and private data safe when AI tools can reach them.",
        ("Try a prompt injection on a toy chatbot you built.", "List which secrets and files your AI tools can reach.", "Remove one permission they don't need."),
        (Video("Prompt injection explained: protecting AI-generated code (Secure Code Warrior)", _yt("H4ydu6HmxC0")), Video("Prompt injection attacks explained, OWASP (Cyber&Tech)", _yt("3tsF7CnsgHM"))),
    ),
    AiSkill(
        "ai-compliance", "AI Compliance",
        "rules and good practice for using and building AI responsibly: privacy, transparency, risk",
        "Know the rules and good habits for using AI responsibly: privacy, transparency and who checks the output.",
        ("List what personal data your AI use touches.", "Check the AI rules that apply to your work and region.", "Write down who reviews the AI's output before it is used."),
        (Video("EU AI Act explained: everything you must know (Deloitte Nederland)", _yt("oWHCyLfUgUw")), Video("EU AI Act for developers (Analysis Cloud IT Vlog)", _yt("w-fcZKq4Ew8"))),
    ),
)

BY_ID: dict[str, AiSkill] = {s.id: s for s in CATALOG}
