"""Evidence-based sources for Penmozhi education articles.

All URLs point to established public-health and medical organizations.
Content is for general education only — not personal medical advice.
"""

DISCLAIMER_EN = """---
Important note
This article is for general education only and does not replace advice from your doctor, nurse, or gynecologist. If you have symptoms that worry you, please speak with a qualified health professional.

Sources & References"""

DISCLAIMER_TA = """---
முக்கிய குறிப்பு
இந்தக் கட்டுரை பொதுக் கல்வி நோக்கத்திற்காக மட்டுமே. இது மருத்துவர், செவிலியர் அல்லது மகப்பேறு நிபுணரின் ஆலோசனைக்கு மாற்றாக அமையாது. அறிகுறிகள் இருந்தால் qualified health professional-ஐ அணுகுங்கள்.

ஆதாரங்கள் மற்றும் குறிப்புகள்"""

# Parallel to EDUCATION_ARTICLES order (12 articles)
SOURCES_EN = [
    [
        "World Health Organization (WHO). Menstrual health fact sheet. https://www.who.int/news-room/fact-sheets/detail/menstrual-health",
        "American College of Obstetricians and Gynecologists (ACOG). Your first period (Especially for Teens). https://www.acog.org/womens-health/faqs/your-first-period",
        "NHS (UK). Periods overview. https://www.nhs.uk/conditions/periods/",
    ],
    [
        "WHO. Menstrual health fact sheet. https://www.who.int/news-room/fact-sheets/detail/menstrual-health",
        "Office on Women's Health (U.S. HHS). Your menstrual cycle. https://www.womenshealth.gov/menstrual-cycle/your-menstrual-cycle",
        "ACOG. The menstrual cycle (Especially for Teens). https://www.acog.org/womens-health/faqs/the-menstrual-cycle",
    ],
    [
        "ACOG. Dysmenorrhea: Painful periods (FAQ). https://www.acog.org/womens-health/faqs/dysmenorrhea-painful-periods",
        "NHS. Period pain. https://www.nhs.uk/conditions/period-pain/",
        "Mayo Clinic. Menstrual cramps — symptoms and causes. https://www.mayoclinic.org/diseases-conditions/menstrual-cramps/symptoms-causes/syc-20374938",
    ],
    [
        "WHO. Adolescent health topic page. https://www.who.int/health-topics/adolescent-health",
        "NHS. Stages of puberty. https://www.nhs.uk/live-well/sexual-health/stages-of-puberty-what-happens-to-boys-and-girls/",
        "ACOG. Your first gynecologic visit (Especially for Teens). https://www.acog.org/womens-health/faqs/your-first-gynecologic-visit-especially-for-teens",
    ],
    [
        "ACOG. Vulvovaginal health (FAQ). https://www.acog.org/womens-health/faqs/vulvovaginal-health",
        "NHS. Vaginal discharge. https://www.nhs.uk/conditions/vaginal-discharge/",
        "Centers for Disease Control and Prevention (CDC). Toxic shock syndrome (TSS). https://www.cdc.gov/group-a-strep/toxic-shock/toxic-shock-syndrome.html",
    ],
    [
        "Eunice Kennedy Shriver National Institute of Child Health and Human Development (NICHD/NIH). Polycystic ovary syndrome (PCOS). https://www.nichd.nih.gov/health/topics/pcos",
        "ACOG. Polycystic ovary syndrome (PCOS) (FAQ). https://www.acog.org/womens-health/faqs/polycystic-ovary-syndrome-pcos",
        "CDC. PCOS and diabetes. https://www.cdc.gov/diabetes/basics/pcos.html",
    ],
    [
        "WHO. Healthy diet fact sheet. https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "Office on Women's Health. Iron-deficiency anemia. https://www.womenshealth.gov/a-z-topics/iron-deficiency-anemia",
        "Academy of Nutrition and Dietetics. Nutrition for women. https://www.eatright.org/health/pregnancy/fertility-and-reproduction/nutrition-and-healthy-eating-for-women",
    ],
    [
        "Office on Women's Health. Premenstrual syndrome (PMS). https://www.womenshealth.gov/menstrual-cycle/premenstrual-syndrome",
        "ACOG. Premenstrual syndrome (PMS) (FAQ). https://www.acog.org/womens-health/faqs/premenstrual-syndrome-pms",
        "NHS. Premenstrual syndrome (PMS). https://www.nhs.uk/conditions/pre-menstrual-syndrome/",
        "American Psychiatric Association. Premenstrual dysphoric disorder (PMDD) in DSM-5. https://www.psychiatry.org/patients-families/pms-and-pmdd",
    ],
    [
        "ACOG. Breast self-awareness (Especially for Teens). https://www.acog.org/womens-health/faqs/breast-self-awareness-especially-for-teens",
        "NHS. Breast changes in teenagers. https://www.nhs.uk/common-health-questions/childrens-health/breast-changes-in-teenagers/",
        "American Cancer Society. Breast cancer signs and symptoms. https://www.cancer.org/cancer/types/breast-cancer/screening-tests-and-early-detection/breast-cancer-signs-and-symptoms.html",
    ],
    [
        "ACOG. Your first gynecologic visit (Especially for Teens). https://www.acog.org/womens-health/faqs/your-first-gynecologic-visit-especially-for-teens",
        "ACOG Committee Opinion: Gynecologic care for adolescents. https://www.acog.org/clinical/clinical-guidance/committee-opinion/articles/2021/11/gynecologic-care-for-adolescents-and-young-women",
        "WHO. Adolescent sexual and reproductive health. https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/adolescent-and-young-adult-health",
    ],
    [
        "CDC. About sexually transmitted infections (STIs). https://www.cdc.gov/sti/about/",
        "WHO. Sexual health topic page. https://www.who.int/health-topics/sexual-health",
        "ACOG. Barrier methods of birth control (FAQ). https://www.acog.org/womens-health/faqs/barrier-methods-of-birth-control-spermicide-condom-sponge-diaphragm-and-cervical-cap",
        "CDC. HPV vaccine information. https://www.cdc.gov/hpv/parents/vaccine.html",
    ],
    [
        "National Institute of Neurological Disorders and Stroke (NIH). Brain basics: Understanding sleep. https://www.ninds.nih.gov/health-information/public-education/brain-basics/brain-basics-understanding-sleep",
        "American Academy of Sleep Medicine. Sleep for teenagers. https://sleepeducation.org/sleep-for-teens/",
        "WHO. Mental health of adolescents. https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health",
    ],
]

SOURCES_TA = [
    [
        "உலக சுகாதார அமைப்பு (WHO). Menstrual health fact sheet. https://www.who.int/news-room/fact-sheets/detail/menstrual-health",
        "American College of Obstetricians and Gynecologists (ACOG). Your first period. https://www.acog.org/womens-health/faqs/your-first-period",
        "NHS (UK). Periods overview. https://www.nhs.uk/conditions/periods/",
    ],
    [
        "WHO. Menstrual health fact sheet. https://www.who.int/news-room/fact-sheets/detail/menstrual-health",
        "Office on Women's Health (U.S.). Your menstrual cycle. https://www.womenshealth.gov/menstrual-cycle/your-menstrual-cycle",
        "ACOG. The menstrual cycle. https://www.acog.org/womens-health/faqs/the-menstrual-cycle",
    ],
    [
        "ACOG. Dysmenorrhea: Painful periods. https://www.acog.org/womens-health/faqs/dysmenorrhea-painful-periods",
        "NHS. Period pain. https://www.nhs.uk/conditions/period-pain/",
        "Mayo Clinic. Menstrual cramps. https://www.mayoclinic.org/diseases-conditions/menstrual-cramps/symptoms-causes/syc-20374938",
    ],
    [
        "WHO. Adolescent health. https://www.who.int/health-topics/adolescent-health",
        "NHS. Stages of puberty. https://www.nhs.uk/live-well/sexual-health/stages-of-puberty-what-happens-to-boys-and-girls/",
        "ACOG. Your first gynecologic visit (Especially for Teens). https://www.acog.org/womens-health/faqs/your-first-gynecologic-visit-especially-for-teens",
    ],
    [
        "ACOG. Vulvovaginal health. https://www.acog.org/womens-health/faqs/vulvovaginal-health",
        "NHS. Vaginal discharge. https://www.nhs.uk/conditions/vaginal-discharge/",
        "CDC. Toxic shock syndrome (TSS). https://www.cdc.gov/group-a-strep/toxic-shock/toxic-shock-syndrome.html",
    ],
    [
        "NICHD/NIH. Polycystic ovary syndrome (PCOS). https://www.nichd.nih.gov/health/topics/pcos",
        "ACOG. PCOS (FAQ). https://www.acog.org/womens-health/faqs/polycystic-ovary-syndrome-pcos",
        "CDC. PCOS and diabetes. https://www.cdc.gov/diabetes/basics/pcos.html",
    ],
    [
        "WHO. Healthy diet fact sheet. https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "Office on Women's Health. Iron-deficiency anemia. https://www.womenshealth.gov/a-z-topics/iron-deficiency-anemia",
        "Academy of Nutrition and Dietetics. https://www.eatright.org/health/pregnancy/fertility-and-reproduction/nutrition-and-healthy-eating-for-women",
    ],
    [
        "Office on Women's Health. Premenstrual syndrome (PMS). https://www.womenshealth.gov/menstrual-cycle/premenstrual-syndrome",
        "ACOG. Premenstrual syndrome (PMS). https://www.acog.org/womens-health/faqs/premenstrual-syndrome-pms",
        "NHS. Premenstrual syndrome. https://www.nhs.uk/conditions/pre-menstrual-syndrome/",
    ],
    [
        "ACOG. Breast self-awareness (Especially for Teens). https://www.acog.org/womens-health/faqs/breast-self-awareness-especially-for-teens",
        "NHS. Breast changes in teenagers. https://www.nhs.uk/common-health-questions/childrens-health/breast-changes-in-teenagers/",
        "American Cancer Society. Breast cancer signs and symptoms. https://www.cancer.org/cancer/types/breast-cancer/screening-tests-and-early-detection/breast-cancer-signs-and-symptoms.html",
    ],
    [
        "ACOG. Your first gynecologic visit (Especially for Teens). https://www.acog.org/womens-health/faqs/your-first-gynecologic-visit-especially-for-teens",
        "ACOG. Gynecologic care for adolescents. https://www.acog.org/clinical/clinical-guidance/committee-opinion/articles/2021/11/gynecologic-care-for-adolescents-and-young-women",
        "WHO. Adolescent sexual and reproductive health. https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/adolescent-and-young-adult-health",
    ],
    [
        "CDC. About sexually transmitted infections (STIs). https://www.cdc.gov/sti/about/",
        "WHO. Sexual health. https://www.who.int/health-topics/sexual-health",
        "CDC. HPV vaccine information. https://www.cdc.gov/hpv/parents/vaccine.html",
    ],
    [
        "NIH/NINDS. Brain basics: Understanding sleep. https://www.ninds.nih.gov/health-information/public-education/brain-basics/brain-basics-understanding-sleep",
        "American Academy of Sleep Medicine. Sleep for teenagers. https://sleepeducation.org/sleep-for-teens/",
        "WHO. Adolescent mental health fact sheet. https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health",
    ],
]


def append_sources(body: str, sources: list[str], language: str) -> str:
    disclaimer = DISCLAIMER_TA if language == "tamil" else DISCLAIMER_EN
    lines = [body.rstrip(), "", disclaimer]
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. {source}")
    return "\n".join(lines)
