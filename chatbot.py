from models import Programme


def answer(question):
    q = (question or "").lower()
    programmes = [p for p in Programme.query.filter_by(active=True).all()]

    if not q.strip():
        return "Hello! Ask me things like: 'Which course suits software development?' or 'Which university can I join with a C in Mathematics?'"

    if "software" in q or "developer" in q or "programming" in q:
        names = ["Software Engineering", "Computer Science", "Information Technology", "Computer Engineering"]
        matches = [p for p in programmes if any(n in p.name for n in names)]
        lines = _describe_short(matches[:3], "Computing & IT")
        return "Courses that suit a software development career:\n" + lines

    if "data" in q or "scientist" in q:
        names = ["Computer Science", "Economics", "Business Computing"]
        matches = [p for p in programmes if any(n in p.name for n in names)]
        return "A data career is well served by:\n" + _describe_short(matches[:3], "Data")

    if "network" in q or "telecom" in q or "telecommunication" in q:
        names = ["Telecommunication", "Computer Engineering", "Information Technology"]
        matches = [p for p in programmes if any(n in p.name for n in names)]
        return "Networking and telecom careers:\n" + _describe_short(matches[:3], "Networks")

    if "medicine" in q or "doctor" in q or "surgeon" in q:
        names = ["Medicine and Bachelor of Surgery"]
        matches = [p for p in programmes if "Medicine" in p.name]
        return ("For medicine you should have Biology, Chemistry and Physics.\n"
                "Programmes that offer this route:\n" + _describe_short(matches[:4], "Medicine"))

    if "nurse" in q or "nursing" in q:
        matches = [p for p in programmes if "Nursing" in p.name]
        return "Nursing programmes:\n" + _describe_short(matches[:4], "Nursing")

    if "pharmac" in q:
        matches = [p for p in programmes if "Pharmacy" in p.name]
        return "Pharmacy programmes:\n" + _describe_short(matches[:3], "Pharmacy")

    if "engineer" in q:
        matches = [p for p in programmes if "Engineering" in p.name]
        return "Engineering programmes (Mathematics and Physics essential):\n" + _describe_short(matches[:6], "Engineering")

    if "law" in q or "lawyer" in q:
        matches = [p for p in programmes if "Laws" in p.name]
        return "Law programmes usually need two principal passes and are offered at:\n" + _describe_short(matches[:3], "Law")

    if "account" in q or "finance" in q or "commerce" in q:
        names = ["Accounting and Finance", "Commerce", "Business Administration"]
        matches = [p for p in programmes if any(n in p.name for n in names)]
        return "Business, accounting and finance programmes:\n" + _describe_short(matches[:4], "Business")

    if "econom" in q:
        matches = [p for p in programmes if "Economic" in p.name]
        return "Economics programmes:\n" + _describe_short(matches[:3], "Economics")

    if "agricult" in q or "agronomy" in q:
        matches = [p for p in programmes if "Agriculture" in p.name]
        return "Agriculture programme:\n" + _describe_short(matches[:2], "Agriculture")

    if "tourism" in q or "hospitality" in q or "travel" in q:
        matches = [p for p in programmes if "Tourism" in p.name]
        return "Tourism and hospitality programme:\n" + _describe_short(matches[:2], "Tourism")

    if "teach" in q or "education" in q:
        matches = [p for p in programmes if "Education" in p.name]
        return "Education programmes:\n" + _describe_short(matches[:3], "Education")

    if "grade" in q or "score" in q or "cut" in q or "cutoff" in q:
        matches = sorted([p for p in programmes], key=lambda p: -(p.cutoff_government or 0 or p.cutoff_private or 0))
        return ("Cut-off points change each year and by sponsorship scheme. Examples for recent years:\n"
                + _describe_short(matches[:5], "Cut-offs"))

    if "fee" in q or "tuition" in q or "money" in q or "budget" in q:
        matches = sorted([p for p in programmes], key=lambda p: p.tuition_private or 0)
        return "Cheapest private-fee options (verify on the official fee structure):\n" + _describe_short(matches[:5], "Fees")

    if "university" in q or "which" in q:
        return ("I can guide you from verified admission data. Open your profile, add your grades, "
                "then run 'Find My University' for ranked matches. Your eligibility should be confirmed "
                "with the university admissions office before you apply.")

    return ("I need more detail to match you. Try asking about a specific course or career, for example: "
            "'Which course suits software development?', 'What cut-offs does medicine need?', "
            "or 'Which universities are cheapest?'")


def _describe_short(programmes, context):
    if not programmes:
        return "No programmes currently listed. Check the verified dataset or ask about another field."
    lines = []
    for p in programmes[:6]:
        gov = p.cutoff_government
        priv = p.cutoff_private
        cutoff = "".join(
            [("Gov " + str(gov)) if gov else "", (" / Private " + str(priv)) if priv else ""]
        ).strip(" /") or "cut-off not published"
        lines.append("- {0} at {1} ({2})".format(p.name, p.university.name, cutoff))
    return "\n".join(lines)