

COMPETENCY_BANK: dict[str, str] = {
    "adaptability": (
        "The ability to shift or change opinions, actions, or behaviors when faced with "
        "multiple demands, shifting priorities, rapid change, or ambiguity. "
        "Key behaviors: sees the positive in change, seeks to understand change, "
        "adjusts behavior to accommodate change, drives the change."
    ),
    "communication": (
        "The ability to express ideas or a message in a clear and convincing manner, "
        "listening attentively to ensure the message is understood and appropriately "
        "tailored to the audience. "
        "Key behaviors: delivers clear and concise message, uses proper grammar, "
        "shares information, verifies understanding, engages others, tailors message to audience."
    ),
    "compassion": (
        "The ability to express genuine concern or interest in the wellbeing of others "
        "while showing empathy for another person's situation, considering needs and "
        "difficulties people are facing. "
        "Key behaviors: acknowledges and considers others' needs, recognizes emotions, "
        "concerned for others' welfare, sensitive to individual differences, remains courteous."
    ),
    "composure": (
        "The capacity to control emotions in the face of pressure, complaint, or failure "
        "while thinking clearly and logically despite the difficult situation. "
        "Key behaviors: effectively manages emotions, recognizes sources of stress, "
        "reacts constructively, recognizes areas of vulnerability, maintains order and civility."
    ),
    "coordination": (
        "The ability to effectively utilize people, resources, and one's own time to "
        "accomplish an objective, working with others to prioritize work activities and "
        "achieve optimal efficiency. "
        "Key behaviors: organizes others to achieve goals, understands the broader picture, "
        "leverages individuals' unique skill sets, distills project to manageable tasks."
    ),
    "dependability": (
        "The tendency to maintain high standards while following through on obligations, "
        "exhibiting integrity and taking pride in the quality of work, willing to admit mistakes. "
        "Key behaviors: sets a high work standard, takes a principled and ethical approach, "
        "takes accountability, safeguards resources."
    ),
    "developing_others": (
        "The ability to understand the strengths and developmental needs of others to help "
        "them reach their full professional potential through coaching, feedback, and encouragement. "
        "Key behaviors: identifies others' strengths and addresses skill gaps, holds constructive "
        "performance conversations, provides ongoing coaching, instructs on performance expectations."
    ),
    "drive_for_results": (
        "The tendency to make continual strides toward exceeding goals or improving performance, "
        "focusing on the bottom line and pushing self and others to achieve optimal results. "
        "Key behaviors: overcomes obstacles, establishes high performance goals, aligns goals, "
        "focuses on process improvement, monitors performance of self and others."
    ),
    "negotiation_persuasion": (
        "The ability to work effectively with others to produce agreement on a course of action, "
        "influencing others to embrace a position or point of view by establishing trust. "
        "Key behaviors: convinces others, adjusts approach to persuade, provides compelling "
        "rationale, neutralizes tension and gains agreement."
    ),
    "problem_solving": (
        "The ability to identify, analyze, determine causative factors, and find solutions "
        "for problems by isolating the issue and using appropriate techniques. "
        "Key behaviors: recognizes and addresses issues, anticipates problems, "
        "identifies appropriate solutions, solves problems using critical and analytical thinking."
    ),
    "relationship_building": (
        "The ability to establish, build upon, enhance, and maintain friendly and mutually "
        "beneficial relationships for professional development and workplace effectiveness. "
        "Key behaviors: seeks to build and nurture relationships, ensures mutual benefits, "
        "aligns on shared goals, establishes personal connection."
    ),
    "service_orientation": (
        "The ability to interact effectively with customers, clients, or stakeholders to "
        "identify their needs, address issues, meet expectations, and ensure satisfaction. "
        "Key behaviors: builds rapport, determines others' needs, resolves problems, "
        "delivers timely and effective service, ensures others' satisfaction."
    ),
    "team_orientation": (
        "The ability to collaboratively define success in terms of the team or organization "
        "as a whole, focusing on team accomplishment rather than personal gain. "
        "Key behaviors: prioritizes team success, mitigates team conflict, maximizes team "
        "effectiveness, leverages strengths, shares success equally."
    ),
    "willingness_to_learn": (
        "The motivation to absorb and apply new information, techniques, or procedures, "
        "inquisitively seeking opportunities to close performance gaps and upgrade skill level. "
        "Key behaviors: open to feedback, closes knowledge gaps, explores opportunities "
        "for growth, applies new knowledge, promotes a learning environment."
    ),
}

# Flat list of keys — used by routes and AI prompts
COMPETENCY_KEYS: list[str] = list(COMPETENCY_BANK.keys())