# Recommendation Engine Logic & Algorithm
## Personalized Learning Recommendation System

### 1. Mathematical Formulation

The recommendation engine is a **deterministic, rule-based, and pedagogical ranking engine**. It computes a composite score $S(c, l)$ for each candidate learning activity $c$ and learner $l$:

$$S(c, l) = S_{\text{gap}}(c, l) + S_{\text{diff}}(c, l) + S_{\text{rel}}(c, l) + S_{\text{context}}(c, l)$$

Where:

1. **Skill Gap Factor ($S_{\text{gap}}$)**:
   $$S_{\text{gap}}(c, l) = (100 - M(s, l)) \times 1.0$$
   Where $M(s, l) \in [0, 100]$ is learner $l$'s calculated mastery on skill $s$. When mastery is low (e.g. $30\%$), the gap score is high ($70.0$).

2. **Difficulty Alignment Factor ($S_{\text{diff}}$)**:
   - If $M(s, l) < 40\%$, preferred difficulty is `BEGINNER`.
   - If $40\% \le M(s, l) < 70\%$, preferred difficulty is `INTERMEDIATE`.
   - If $M(s, l) \ge 70\%$, preferred difficulty is `ADVANCED`.
   $$S_{\text{diff}} = \begin{cases} +25.0 & \text{if } \text{Difficulty}(c) = \text{Preferred}(l) \\ -15.0 & \text{otherwise} \end{cases}$$

3. **Curricular Relevance ($S_{\text{rel}}$)**:
   $$S_{\text{rel}} = W(c, s) \times 20.0$$
   Where $W(c, s) \in (0.0, 1.0]$ is the content-to-skill relevance weight.

4. **Contextual Context Boost ($S_{\text{context}}$)**:
   - **Recent Failed Assessment**: If learner recently failed an assessment in skill $s$, add **$+120.0$** (tagged `ASSESSMENT_FAILED`).
   - **Cold Start Onboarding**: If learner has 0 attempts, foundational beginner activities receive **$+150.0$** (tagged `COLD_START`).
   - **Prerequisites Met Milestone**: If learner just unlocked an advanced course, fundamental advance modules receive **$+80.0$** (tagged `PREREQUISITES_MET`).

---

### 2. Standardized Reason Codes

Every recommendation emitted by Tier 2 includes a standardized reason code and natural language pedagogical explanation:

| Reason Code | Pedagogical Trigger | Sample Explanation |
| :--- | :--- | :--- |
| `COLD_START` | Learner has 0 past attempts. | "Recommended as an essential foundational module for your initial learning trajectory." |
| `ASSESSMENT_FAILED` | Recent quiz in mapped skill failed. | "Targeted revision activity addressing key gaps from your recent assessment on 'Python Syntax'." |
| `SKILL_GAP` | Current mastery is below $70.0\%$. | "Knowledge gap identified: your current mastery in 'Algorithms' is 35.0% (target >= 70%)." |
| `PREREQUISITES_MET` | Prerequisites satisfied for advanced module. | "Prerequisites satisfied! You have unlocked this advanced module in 'Python Object-Oriented Programming'." |
| `DIFFICULTY_MATCH` | Content difficulty matches knowledge tier. | "Content difficulty (Beginner) matches your current knowledge level." |
| `NOT_COMPLETED` | Core curriculum activity pending completion. | "Core curriculum activity in 'Python Fundamentals' scheduled for completion." |

---

### 3. Mastery Level Classification

Mastery is computed deterministically from verified assessment attempts:

$$\text{Mastery Percentage} = \frac{\sum_{i=1}^{N} \text{Percentage}_i}{N}$$

Tiers:
- **Needs Improvement**: $< 40.0\%$
- **Developing**: $40.0\% - 69.9\%$
- **Proficient**: $70.0\% - 84.9\%$
- **Mastered**: $\ge 85.0\%$

All thresholds are environment-configurable in `.env`.
