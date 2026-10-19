FIELDS = {
    "medicine": "Medicine & Health",
    "health": "Medicine & Health",
    "nursing": "Medicine & Health",
    "pharmacy": "Medicine & Health",
    "public health": "Medicine & Health",
    "clinical": "Medicine & Health",
    "engineering": "Engineering",
    "civil": "Engineering",
    "electrical": "Engineering",
    "mechanical": "Engineering",
    "telecommunication": "Engineering",
    "computer engineering": "Engineering",
    "software": "Computing & IT",
    "computer": "Computing & IT",
    "information": "Computing & IT",
    "it ": "Computing & IT",
    "computing": "Computing & IT",
    "data": "Computing & IT",
    "business": "Business & Management",
    "commerce": "Business & Management",
    "accounting": "Business & Management",
    "management": "Business & Management",
    "economics": "Business & Management",
    "finance": "Business & Management",
    "human resource": "Business & Management",
    "law": "Law & Governance",
    "governance": "Law & Governance",
    "education": "Education",
    "teaching": "Education",
    "agriculture": "Agriculture & Environment",
    "agronomy": "Agriculture & Environment",
    "social": "Arts & Social Sciences",
    "humanities": "Arts & Social Sciences",
    "journalism": "Arts & Social Sciences",
    "communication": "Arts & Social Sciences",
    "development": "Arts & Social Sciences",
    "tourism": "Tourism & Hospitality",
    "hospitality": "Tourism & Hospitality",
}

FIELD_KEYWORDS = {
    "Medicine & Health": [
        "medicine", "surgery", "nursing", "pharmacy", "public health", "clinical", "health",
    ],
    "Engineering": [
        "engineering", "civil", "electrical", "mechanical", "telecommunication",
    ],
    "Computing & IT": [
        "software", "computer", "information", "computing", "business computing",
    ],
    "Business & Management": [
        "business", "commerce", "accounting", "management", "economics", "finance", "human resource",
    ],
    "Law & Governance": ["law"],
    "Education": ["education", "teaching"],
    "Agriculture & Environment": ["agriculture", "agronomy", "environment", "land"],
    "Arts & Social Sciences": ["social", "journalism", "communication", "development", "liberal", "arts"],
    "Tourism & Hospitality": ["tourism", "hospitality", "travel"],
}


def field_for_text(text):
    lowered = (text or "").lower()
    for key, field in FIELDS.items():
        if key in lowered:
            return field
    return ""


def keyword_matches_programme(programme, keywords):
    if not keywords:
        return True
    text = (programme.name or "").lower()
    career_texts = " ".join(c.name.lower() for c in programme.careers)
    for keyword in keywords:
        if keyword in text or keyword in career_texts:
            return True
    return False


def subject_combinations(field=None, interests=None):
    combos = {
        "Medicine & Health": [
            {
                "title": "Science Core",
                "subjects": ["Biology", "Chemistry", "Physics"],
                "note": "Biology and Chemistry are essential for Medicine, Nursing, Pharmacy and allied health programmes.",
            },
            {
                "title": "Science with Mathematics",
                "subjects": ["Biology", "Chemistry", "Mathematics"],
                "note": "Mathematics is a strong relevant subject for clinical and laboratory science programmes.",
            },
        ],
        "Engineering": [
            {
                "title": "Pure Engineering Core",
                "subjects": ["Mathematics", "Physics", "Chemistry"],
                "note": "Mathematics and Physics are essential for most engineering programmes.",
            },
            {
                "title": "Engineering with Computer Science",
                "subjects": ["Mathematics", "Physics", "Computer Science"],
                "note": "Computer Science strengthens applications for computer, telecommunications and software engineering.",
            },
        ],
        "Computing & IT": [
            {
                "title": "Mathematics and Computer Science",
                "subjects": ["Mathematics", "Computer Science", "Physics"],
                "note": "Mathematics plus Computer Science is the strongest entry path for software and computing programmes.",
            },
            {
                "title": "Mathematics with Economics",
                "subjects": ["Mathematics", "Economics", "Entrepreneurship"],
                "note": "Ideal for Business Computing and information systems that blend technology with business.",
            },
        ],
        "Business & Management": [
            {
                "title": "Economics and Business Core",
                "subjects": ["Economics", "Entrepreneurship", "Mathematics"],
                "note": "Economics plus Mathematics suits Commerce, Accounting, Finance and Business Administration.",
            },
            {
                "title": "Business Humanities",
                "subjects": ["Economics", "Entrepreneurship", "Divinity"],
                "note": "A flexible combination for management and human resource programmes.",
            },
        ],
        "Law & Governance": [
            {
                "title": "Humanities for Law",
                "subjects": ["Literature", "History", "Divinity"],
                "note": "Any two principal passes are generally required; History and Literature build the analytical and writing skills law needs.",
            },
            {
                "title": "Law with Social Sciences",
                "subjects": ["History", "Geography", "Economics"],
                "note": "Geography and Economics broaden options into governance, development and diplomacy.",
            },
        ],
        "Education": [
            {
                "title": "Sciences Teaching",
                "subjects": ["Mathematics", "Physics", "Chemistry"],
                "note": "Required for Bachelor of Science with Education in science-heavy teaching subjects.",
            },
            {
                "title": "Humanities Teaching",
                "subjects": ["Literature", "History", "Divinity"],
                "note": "A strong base for Arts-based teaching programmes.",
            },
        ],
        "Agriculture & Environment": [
            {
                "title": "Agricultural Science",
                "subjects": ["Biology", "Chemistry", "Agriculture"],
                "note": "Biology and Chemistry are essential; Agriculture is a recognised relevant subject for agronomy programmes.",
            },
            {
                "title": "Environmental Science",
                "subjects": ["Geography", "Biology", "Chemistry"],
                "note": "Geography strengthens environment, forestry and land management applications.",
            },
        ],
        "Arts & Social Sciences": [
            {
                "title": "Humanities Mix",
                "subjects": ["Literature", "History", "Divinity"],
                "note": "A flexible combination accepted by most arts, journalism and social science programmes.",
            },
            {
                "title": "Social Sciences Mix",
                "subjects": ["Economics", "Geography", "History"],
                "note": "Suitable for development studies, communication and government-related careers.",
            },
        ],
        "Tourism & Hospitality": [
            {
                "title": "Tourism Core",
                "subjects": ["Geography", "History", "Economics"],
                "note": "Geography is highly relevant to tourism, travel and hospitality programmes.",
            },
        ],
    }

    picks = []
    if field and field in combos:
        picks.append(field)
    for interest in interests or []:
        resolved = field_for_text(interest)
        if resolved and resolved not in picks:
            picks.append(resolved)
    if not picks:
        picks = list(combos.keys())

    results = []
    for pick in picks[:3]:
        results.extend(combos.get(pick, []))
    return results, picks