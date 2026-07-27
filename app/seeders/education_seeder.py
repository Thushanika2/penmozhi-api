from datetime import date

from app.extensions import db
from app.models.educational_resource_model import EducationalResource
from app.seeders.education_articles_ta import EDUCATION_ARTICLES_TA
from app.seeders.education_references import SOURCES_EN, SOURCES_TA, append_sources

EDUCATION_ARTICLES = [
    {
        "article_title": "First Period: What Every Girl Should Know",
        "content_category": "puberty",
        "publication_date": date(2026, 1, 5),
        "content_body": """Getting your first period (menarche) is a normal and healthy milestone. Most girls get their first period between ages 10 and 15, though anywhere from 9 to 16 can be normal. Your body is simply showing that it is maturing.

What happens during a period?
Each month, the lining of the uterus builds up to prepare for a possible pregnancy. When pregnancy does not occur, that lining sheds and leaves the body through the vagina as menstrual blood. This usually lasts 3 to 7 days.

What will it look and feel like?
Your first few periods may be light, irregular, or slightly brownish. Some cramping, bloating, or tiredness is common. Using a pad, tampon, or menstrual cup can help you stay comfortable. Change pads every 4–6 hours or sooner if they feel full.

How to prepare
Keep a small kit in your bag: pads or liners, underwear, and wet wipes. Track your period start date — even on paper — so you learn your own pattern over time.

When to tell an adult or doctor
Talk to a parent, guardian, or school nurse if you have not started your period by age 15, if bleeding is so heavy you soak through a pad every hour, if you have severe pain that stops you from daily activities, or if you feel dizzy or faint during your period.

Remember: your first period is not something to hide or feel ashamed about. It is a sign that your body is working as it should.""",
    },
    {
        "article_title": "Understanding Your Menstrual Cycle",
        "content_category": "cycle",
        "publication_date": date(2026, 1, 10),
        "content_body": """Your menstrual cycle is more than just your period — it is a monthly rhythm controlled by hormones that affects your body, mood, and energy.

The four phases
1. Menstrual phase (Days 1–5): The period begins. The uterine lining sheds. You may feel tired or have cramps.
2. Follicular phase (after period until ovulation): Estrogen rises. Energy often improves. The body prepares an egg for release.
3. Ovulation (around mid-cycle): An egg is released from the ovary. Some women notice mild pelvic pain, clearer skin, or increased energy.
4. Luteal phase (after ovulation until next period): Progesterone rises, then falls if pregnancy does not occur. PMS symptoms like mood changes, bloating, or breast tenderness may appear in the days before your period.

How long is a normal cycle?
A typical cycle lasts 21 to 35 days, counted from the first day of one period to the first day of the next. It is normal for cycles to vary slightly, especially in the first few years after menarche.

Why tracking matters
Logging your period dates, flow, pain, mood, and sleep helps you:
- Predict your next period
- Notice irregular patterns early
- Share accurate information with your doctor
- Understand how your cycle affects your daily life

When cycles are irregular
Occasional variation is common during puberty, after stopping birth control, during stress, or with significant weight change. See a gynecologist if your cycles are consistently shorter than 21 days or longer than 35 days, if you miss periods for 3 months or more (and are not pregnant), or if bleeding is unusually heavy.""",
    },
    {
        "article_title": "Period Pain: When It Is Normal and When to See a Doctor",
        "content_category": "cycle",
        "publication_date": date(2026, 1, 18),
        "content_body": """Menstrual cramps (dysmenorrhea) affect many girls and women. Mild to moderate cramping in the lower abdomen, lower back, or thighs during the first 1–2 days of your period is common and usually not dangerous.

Primary dysmenorrhea
This is normal period pain caused by natural chemicals called prostaglandins that help the uterus contract. It often starts within a year or two of your first period and may improve with age or after childbirth.

What helps at home
- Heat: A warm water bottle or heating pad on the lower abdomen
- Movement: Gentle walking, stretching, or yoga
- Pain relief: Ibuprofen or naproxen taken at the start of cramps (follow package directions and ask a parent or doctor first if under 16)
- Rest and hydration
- Regular sleep and balanced meals throughout the month

Secondary dysmenorrhea
This is pain caused by an underlying condition such as endometriosis, fibroids, or pelvic inflammatory disease. It may worsen over time rather than improve.

See a doctor if you have:
- Pain so severe you miss school, work, or sleep regularly
- Pain that starts before your period and lasts many days
- Very heavy bleeding (soaking through a pad or tampon every hour for several hours)
- Pain during sex, urination, or bowel movements
- Fever or foul-smelling discharge with pelvic pain

You do not have to "just endure" period pain. Effective treatments exist, and early evaluation protects your long-term health and quality of life.""",
    },
    {
        "article_title": "Body Changes During Puberty",
        "content_category": "puberty",
        "publication_date": date(2026, 1, 25),
        "content_body": """Puberty is the time when a child's body matures into an adult body capable of reproduction. For girls, this usually begins between ages 8 and 13 and lasts several years. Every body moves at its own pace — comparing yourself to friends is rarely helpful.

Common physical changes
- Breast development: Often the first visible sign. One side may grow faster than the other at first — this is normal.
- Body hair: Hair grows in the armpits and pubic area.
- Height and shape: A growth spurt is common. Hips may widen and body fat distribution changes.
- Skin: Increased oil production can lead to acne on the face, chest, or back.
- Vaginal discharge: Clear or white discharge is normal and helps keep the vagina clean.
- Menstruation: Usually begins 2 to 3 years after breast development starts.

Emotional changes
Hormones also affect mood, self-image, and relationships. Feeling more sensitive, irritable, or self-conscious is common. These feelings are real and valid — they do not mean something is wrong with you.

Self-care during puberty
- Shower daily and wear clean, breathable cotton underwear
- Use a gentle face wash for acne; avoid harsh scrubbing
- Eat regular meals with protein, fruits, vegetables, and whole grains
- Aim for 8–10 hours of sleep
- Talk to someone you trust when feelings feel overwhelming

When to ask for help
See a doctor if breast development has not started by age 13, if you have no period by age 15, if you have sudden severe acne or excessive hair growth, or if mood changes make it hard to function at school or home for more than two weeks.""",
    },
    {
        "article_title": "Vaginal Health and Hygiene for Teens",
        "content_category": "hygiene",
        "publication_date": date(2026, 2, 5),
        "content_body": """The vagina is a self-cleaning organ. Good hygiene is about gentle care — not harsh products or strong fragrances.

Daily care basics
- Wash the outer genital area (vulva) with warm water and mild, unscented soap
- Wipe front to back after using the toilet to prevent bacteria from spreading
- Change underwear daily; cotton fabric breathes better than synthetic materials
- Change pads, tampons, or cups as directed — do not leave tampons in for more than 8 hours

What is normal?
- Clear, white, or slightly yellow discharge without strong odor
- Mild scent that varies through the cycle
- Occasional dryness or extra moisture depending on the time of month

What to avoid
- Douching (washing inside the vagina) — it disrupts healthy bacteria and increases infection risk
- Scented sprays, wipes, or bubble baths on the genital area
- Tight non-breathable clothing every day
- Sharing towels or underwear

Signs that need medical attention
- Itching, burning, or pain
- Thick white discharge like cottage cheese
- Gray or green discharge with a strong fishy odor
- Sores, bumps, or blisters in the genital area
- Bleeding between periods or after sex

If you use tampons
Always use the lowest absorbency needed and change regularly. Know the rare but serious signs of toxic shock syndrome: sudden high fever, vomiting, diarrhea, dizziness, or a sunburn-like rash. Remove the tampon and seek emergency care if these occur.

Your body deserves respect and gentle care. When in doubt, ask a parent, school nurse, or doctor — there is no question too small.""",
    },
    {
        "article_title": "PCOS: Signs and Support",
        "content_category": "pcos",
        "publication_date": date(2026, 2, 12),
        "content_body": """Polycystic Ovary Syndrome (PCOS) is a common hormonal condition that affects roughly 1 in 10 women of reproductive age. It can begin in the teenage years, though diagnosis is sometimes delayed because symptoms overlap with normal puberty.

Possible signs of PCOS
- Irregular or missed periods
- Heavy or prolonged bleeding when periods do occur
- Excess hair growth on the face, chest, or back (hirsutism)
- Acne that persists beyond typical teen years
- Weight gain or difficulty losing weight
- Thinning hair on the scalp
- Dark patches of skin on the neck, armpits, or groin (acanthosis nigricans)
- Difficulty getting pregnant later in life (not a concern during adolescence, but good to know)

How is it diagnosed?
There is no single blood test. A gynecologist or endocrinologist looks at your symptoms, exam findings, blood tests (hormones, blood sugar), and sometimes an ultrasound. Other conditions must be ruled out first.

Why early awareness matters
PCOS is linked to insulin resistance, type 2 diabetes, high cholesterol, sleep apnea, and emotional health challenges. Early lifestyle support and medical care can reduce long-term risks.

What helps
- Regular physical activity you enjoy
- Balanced meals with protein, fiber, and limited sugary drinks
- Consistent sleep schedule
- Tracking cycles and symptoms (apps like Penmozhi help)
- Medical treatment when needed: birth control pills to regulate cycles, metformin for insulin resistance, or other targeted therapies

Emotional support
PCOS can affect body image and mood. You are not lazy or failing — this is a medical condition. Support groups, counseling, and open conversations with your doctor can make a real difference.

If you suspect PCOS, bring a symptom log to your appointment. You deserve answers and a plan tailored to your body.""",
    },
    {
        "article_title": "Nutrition for Hormonal Balance",
        "content_category": "nutrition",
        "publication_date": date(2026, 2, 20),
        "content_body": """Food cannot "fix" hormones overnight, but consistent nutrition supports energy, mood, regular cycles, and long-term reproductive health.

Build your plate across the cycle
- Protein (eggs, lentils, chicken, fish, tofu): Supports stable blood sugar and muscle repair
- Fiber (vegetables, fruits, whole grains, beans): Helps digestion and hormone metabolism
- Healthy fats (nuts, seeds, olive oil, avocado): Needed for hormone production
- Iron-rich foods (spinach, dates, lean red meat, fortified cereals): Important if you have heavy periods
- Calcium and vitamin D (dairy or fortified alternatives, sunlight): Support bone health during puberty

Hydration
Aim for 6–8 glasses of water daily. Dehydration can worsen headaches and fatigue, especially during your period.

Foods to enjoy in moderation
- Sugary drinks and snacks (can cause energy crashes)
- Highly processed fast food (often low in nutrients)
- Excess caffeine (may worsen anxiety or breast tenderness for some)

Special considerations
- Heavy periods: Focus on iron and vitamin C (helps iron absorption)
- PMS: Regular meals prevent blood sugar dips that worsen mood swings; some women benefit from reducing salt to ease bloating
- PCOS: Balanced carbs with protein at each meal can support insulin sensitivity

Supplements
Most teens get enough nutrients from food. Do not start iron, vitamin D, or other supplements without a blood test and doctor's advice — too much can be harmful.

Healthy eating is not about perfection or strict dieting. It is about nourishing your growing body so you have the energy to learn, move, and thrive throughout your cycle.""",
    },
    {
        "article_title": "Mental Health, Mood, and Your Menstrual Cycle",
        "content_category": "mental_health",
        "publication_date": date(2026, 3, 1),
        "content_body": """Your hormones interact with brain chemistry throughout the month. It is normal to notice mood shifts — but severe or disabling mood changes deserve medical attention.

Common emotional patterns
- Follicular phase: Many feel more energetic and social after their period ends
- Premenstrual days: Irritability, sadness, anxiety, or sensitivity may increase
- During period: Fatigue and low mood can occur alongside physical symptoms

PMS vs PMDD
Premenstrual Syndrome (PMS) affects many women with mild to moderate symptoms that resolve when the period starts.

Premenstrual Dysphoric Disorder (PMDD) is a more severe form where mood symptoms significantly disrupt daily life — relationships, school, or work — in the week before the period. It is a real medical condition, not "being dramatic."

Self-care strategies
- Track mood alongside your cycle to identify patterns
- Prioritize sleep — lack of sleep amplifies emotional reactivity
- Move your body: even a 15-minute walk can help
- Limit alcohol and caffeine before your period if they worsen symptoms
- Practice stress tools: deep breathing, journaling, talking to a friend
- Set realistic expectations during low-energy days

When to seek help
Talk to a doctor or mental health professional if you:
- Feel hopeless, worthless, or have thoughts of self-harm
- Cannot attend school or work for several days each month
- Have panic attacks or severe anxiety cyclically
- Notice mood symptoms that do not improve after your period starts

Treatment options include lifestyle changes, therapy, hormonal treatments, or antidepressants used in specific ways for PMDD. You deserve support — mental health is health.""",
    },
    {
        "article_title": "Breast Health Basics for Young Women",
        "content_category": "wellness",
        "publication_date": date(2026, 3, 10),
        "content_body": """Breast development is a normal part of puberty. Understanding what is typical helps you notice changes early and feel confident in your body.

What is normal?
- Tenderness or mild aching during puberty or before your period
- One breast slightly larger than the other
- Small lumps that come and go with the menstrual cycle (often due to normal hormonal tissue changes)
- Montgomery glands (small bumps on the areola) — they are normal

Breast self-awareness
Formal monthly self-exams are no longer emphasized for all young women, but knowing how your breasts normally look and feel is important. Notice changes during dressing or showering — there is no special technique required in your teens.

Choose supportive bras that fit well, especially during sports. Ill-fitting bras can cause back or shoulder discomfort.

When to see a doctor
- A hard lump that does not go away after your next period
- Persistent pain in one spot
- Redness, warmth, or nipple discharge (especially bloody or spontaneous discharge)
- Sudden change in breast size, shape, or skin (dimpling or puckering)
- A lump in the armpit area

Breast cancer is rare in teenagers, but any persistent concern should be evaluated. Most breast lumps in young women are benign (non-cancerous), such as fibroadenomas.

Your breasts are unique. Changes during puberty, pregnancy, and aging are normal life stages — staying informed helps you advocate for your health at every age.""",
    },
    {
        "article_title": "When to See a Gynecologist: A Guide for Teens and Young Women",
        "content_category": "wellness",
        "publication_date": date(2026, 3, 18),
        "content_body": """Many girls wonder when they need their first gynecologist visit. You do not need to wait until you are sexually active or have a problem — preventive care is valuable at every stage.

First visit: what to expect
The American College of Obstetricians and Gynecologists (ACOG) recommends a first reproductive health visit between ages 13 and 15. This is often a conversation, not always a pelvic exam.

Your doctor may ask about:
- Periods (when they started, how regular, how heavy)
- Pain, discharge, or itching
- Sexual activity and contraception (private and confidential in most settings)
- Vaccinations (including HPV)
- Mental health and body image

A pelvic exam is usually not needed at the first teen visit unless there is a specific concern. Pap smears for cervical cancer screening typically begin at age 21.

Reasons to schedule a visit sooner
- No period by age 15
- Periods more than 45 days apart consistently
- Bleeding between periods or after sex
- Severe period pain or very heavy bleeding
- Concerns about PCOS, acne, or excess hair growth
- Need for contraception or STI testing
- Questions about sexuality, consent, or abuse (you deserve a safe space)

How to prepare
Write down your questions beforehand. You can ask to speak with the doctor alone for part of the visit. Bring a period and symptom log if you track one.

Building a relationship with a gynecologist early creates a foundation of trust. You deserve a clinician who listens, explains, and respects your autonomy.""",
    },
    {
        "article_title": "STIs, Consent, and Protecting Your Reproductive Health",
        "content_category": "reproductive_health",
        "publication_date": date(2026, 3, 25),
        "content_body": """Understanding reproductive health empowers you to make informed choices and protect your body. This information is for education — if you are sexually active or planning to be, speak privately with a doctor or counselor.

Consent comes first
Consent means freely agreeing to any physical intimacy without pressure, guilt, or fear. You can change your mind at any time. No one owes anyone sex, and silence is not consent. Healthy relationships respect boundaries.

Sexually transmitted infections (STIs)
STIs such as chlamydia, gonorrhea, HPV, herpes, and HIV can spread through sexual contact. Many have no symptoms at first but can cause long-term harm if untreated, including infertility and cancer (HPV).

Protection options
- Condoms: The only method that also reduces STI transmission when used correctly
- HPV vaccine: Recommended in adolescence; protects against cancer-causing strains
- Regular testing: If sexually active, ask your doctor about confidential STI screening
- Mutual monogamy and open communication with partners

Contraception basics
If pregnancy prevention is needed, options include condoms, birth control pills, patches, injections, implants, and IUDs. Each has benefits and side effects — a gynecologist can help you choose based on your health and lifestyle.

Emergency contraception
If unprotected sex occurs or a condom breaks, emergency contraception pills are most effective within 72 hours (some work up to 5 days). They are not regular birth control but can prevent pregnancy after a single event.

Where to get help
School nurses, community clinics, and gynecologists offer confidential care. In many places, teens can access reproductive health services without parental notification for certain services.

Your body, your choice. Learning these facts early helps you stay safe, healthy, and in control of your future.""",
    },
    {
        "article_title": "Sleep, Stress, and Your Hormones",
        "content_category": "wellness",
        "publication_date": date(2026, 4, 2),
        "content_body": """Sleep and stress are often overlooked, but they deeply influence menstrual regularity, skin health, mood, and overall wellbeing during the teenage years and beyond.

Why sleep matters
During puberty, the body needs about 8–10 hours of sleep nightly. Growth hormone, cortisol, and reproductive hormones all follow daily rhythms tied to sleep. Poor sleep can worsen PMS, acne, anxiety, and irregular cycles.

Tips for better sleep
- Keep a consistent bedtime and wake time, even on weekends
- Limit screens for 30–60 minutes before bed (blue light delays melatonin)
- Keep your room cool, dark, and quiet
- Avoid large meals, energy drinks, and caffeine in the evening
- If period pain disrupts sleep, take pain relief early and use a heating pad

Stress and your cycle
Chronic stress raises cortisol, which can delay ovulation and cause missed or late periods. Exam pressure, family conflict, social media, and bullying all count as stressors — your feelings are valid.

Stress management that works
- Regular movement: dance, sport, walking
- Talking to someone you trust
- Limiting caffeine during anxious periods
- Mindfulness apps or simple breathing exercises
- Setting boundaries on study and screen time

When stress affects your body
See a doctor if you miss multiple periods during a stressful time, if you have chest pain, rapid weight loss, or if anxiety or low mood persist for more than two weeks.

Rest is not laziness — it is biological maintenance. Protecting your sleep and managing stress is one of the most powerful things you can do for hormonal health.""",
    },
]


def seed_education():
    created = 0
    updated = 0

    english_articles = [
        {
            **article,
            "language": "english",
            "content_body": append_sources(article["content_body"], SOURCES_EN[index], "english"),
        }
        for index, article in enumerate(EDUCATION_ARTICLES)
    ]
    tamil_articles = [
        {
            **article,
            "language": "tamil",
            "content_body": append_sources(article["content_body"], SOURCES_TA[index], "tamil"),
        }
        for index, article in enumerate(EDUCATION_ARTICLES_TA)
    ]

    for article in english_articles + tamil_articles:
        existing = EducationalResource.query.filter_by(
            article_title=article["article_title"],
            language=article["language"],
        ).first()

        if not existing:
            existing = EducationalResource.query.filter_by(
                article_title=article["article_title"]
            ).first()

        if existing:
            existing.content_category = article["content_category"]
            existing.content_body = article["content_body"]
            existing.publication_date = article["publication_date"]
            existing.language = article["language"]
            updated += 1
        else:
            db.session.add(EducationalResource(**article))
            created += 1

    db.session.commit()
    print(f"  Education articles — created: {created}, updated: {updated}.")
