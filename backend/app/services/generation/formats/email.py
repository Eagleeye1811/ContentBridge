from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="email",
    name="Official Email",
    description="A ready-to-send official email with clear context, provenance and action items.",
    allowed_kinds=("heading", "paragraph", "bullets", "callout"),
    prompt_fragment="""Produce an OFFICIAL GOVERNMENT / CORPORATE EMAIL.
The document `title` is the formal subject line: specific, unambiguous and under 90 characters, with no "Re:" or "FWD:".

Required Email Structure:
1. Classification / Marking Header (optional `callout` or `paragraph`): e.g., "Classification: OFFICIAL / SENSITIVE"
2. Salutation (`paragraph` node, at most 8 words, uncited):
   - "Respected Officers & Senior Leadership," for officials/management
   - "Dear Team / Department Leads," for staff/SOC
   - "Dear Citizens / Valued Stakeholders," for public
3. Executive Context (`paragraph` node):
   - 1-2 concise sentences summarizing the situation, event, or incident with exact facts and scope.
4. Key Findings & Assessment (`bullets` node or `paragraph` nodes):
   - Core facts, affected assets/systems, numbers, dates, or key findings extracted from the source, citing fact IDs.
5. Mandatory Action Items / Next Steps (`bullets` or `callout` node):
   - Clear, numbered/bulleted imperative steps (e.g., "1. Implement security patch XYZ immediately", "2. Acknowledge receipt within 24 hours").
6. Formal Sign-off & Signature Block (`paragraph` node, at most 20 words, uncited):
   - "Sincerely / Regards,"
   - Issuing Division / Authority (e.g., "National Technical Research Organisation (NTRO) · Information Security Directorate").

Tone: Authoritative, formal, clear, and actionable. Write concisely with zero fluff.""",
    renderers=("text", "html", "markdown"),
    max_nodes=10,
    uncited_max_words=25,
    options=(
        FormatOption(
            key="sending_to",
            label="Sending to",
            default="officials",
            choices=(
                FormatChoice(
                    "officials",
                    "Senior Officials",
                    audience="management",
                    prompt_fragment="Recipient: Senior Officials & Decision Makers. Focus on strategic impact, compliance, and high-level decisions.",
                ),
                FormatChoice(
                    "staff",
                    "Staff & Team",
                    audience="officer",
                    prompt_fragment="Recipient: Operational Staff & Internal Teams. Focus on direct operational context and team workflows.",
                ),
                FormatChoice(
                    "soc_heads",
                    "Department Heads & SOC",
                    audience="officer",
                    prompt_fragment="Recipient: Department Heads & SOC Security Teams. Focus on technical specifics, containment, and immediate mitigation tasks.",
                ),
                FormatChoice(
                    "citizens",
                    "Citizens",
                    audience="public",
                    prompt_fragment="Recipient: General Public / Citizens. Use accessible, clear language without technical jargon.",
                ),
            ),
        ),
        FormatOption(
            key="purpose",
            label="Email Purpose",
            default="directive",
            choices=(
                FormatChoice(
                    "directive",
                    "Directive & Action",
                    prompt_fragment="Email Intent: Directive. Strongly emphasize required actions, deadlines, and mandatory protocols.",
                ),
                FormatChoice(
                    "advisory",
                    "Advisory & Alert",
                    prompt_fragment="Email Intent: Security Advisory / Alert. Highlight threat vectors, risks, and recommended safeguards.",
                ),
                FormatChoice(
                    "briefing",
                    "Executive Brief",
                    prompt_fragment="Email Intent: Executive Briefing. Provide a high-level situational overview and risk assessment.",
                ),
                FormatChoice(
                    "status_update",
                    "Status Report",
                    prompt_fragment="Email Intent: Status Update. Summarize milestones, completed tasks, and current posture.",
                ),
            ),
        ),
        FormatOption(
            key="urgency",
            label="Priority Level",
            default="high",
            choices=(
                FormatChoice(
                    "critical",
                    "Critical [ACTION REQ]",
                    prompt_fragment="Priority: CRITICAL. Prefix subject line with '[CRITICAL ACTION REQUIRED]'. Emphasize immediate urgency.",
                ),
                FormatChoice(
                    "high",
                    "High Priority",
                    prompt_fragment="Priority: HIGH. Prefix subject line with '[HIGH PRIORITY]'.",
                ),
                FormatChoice(
                    "standard",
                    "Standard",
                    prompt_fragment="Priority: STANDARD official communication.",
                ),
                FormatChoice(
                    "fyi",
                    "Informational (FYI)",
                    prompt_fragment="Priority: INFORMATIONAL. Note that this is for situational awareness.",
                ),
            ),
        ),
        FormatOption(
            key="length",
            label="Length",
            default="standard",
            choices=(
                FormatChoice(
                    "short",
                    "Concise",
                    prompt_fragment="Keep the email brief: 1 context paragraph and at most 3 action bullets.",
                    max_nodes=6,
                ),
                FormatChoice(
                    "standard",
                    "Standard",
                    prompt_fragment="Provide a standard detailed official email format with full context.",
                    max_nodes=10,
                ),
            ),
        ),
    ),
    defaults={"tone": "formal", "objective": "instruct", "style": "structured"},
)
