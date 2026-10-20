// Interface text in Korean / English / Thai. The language is the first part of the URL: /ko, /en, /th.
export const LANGS = ["ko", "en", "th"] as const;
export type Lang = (typeof LANGS)[number];
export const LANG_NAME: Record<Lang, string> = { ko: "한국어", en: "English", th: "ไทย" };

export function isLang(x: string): x is Lang {
  return (LANGS as readonly string[]).includes(x);
}

// Content exists in English and Thai; Korean falls back to English until Korean text is written.
export function pick(text: { en?: string; th?: string; ko?: string } | undefined, lang: Lang) {
  if (!text) return "";
  return text[lang] || text.en || "";
}

const dict = {
  appName: { ko: "TOPIK 지름길", en: "TOPIK Shortcut", th: "TOPIK ทางลัด" },
  tagline: {
    ko: "기출문제 분석으로 TOPIK II PBT를 더 빠르게",
    en: "Pass TOPIK II PBT faster with real past-exam analysis",
    th: "สอบ TOPIK II PBT ได้เร็วขึ้นด้วยการวิเคราะห์ข้อสอบจริง",
  },
  navHome: { ko: "홈", en: "Home", th: "หน้าแรก" },
  navTypes: { ko: "문제 유형", en: "Question types", th: "ประเภทคำถาม" },
  navGeneral: { ko: "일반", en: "General", th: "ทั่วไป" },
  chooseLang: { ko: "언어를 선택하세요", en: "Choose your language", th: "เลือกภาษา" },
  navGrammar: { ko: "문법", en: "Grammar", th: "แกรมมาร์" },
  navVocab: { ko: "어휘", en: "Vocabulary", th: "คำศัพท์" },
  navAsk: { ko: "TOPIK에 묻기", en: "Ask TOPIK", th: "ถาม TOPIK" },
  navWriting: { ko: "쓰기 검사", en: "Writing check", th: "ตรวจงานเขียน" },
  notReviewed: {
    ko: "베타: 설명은 아직 검토 중입니다.",
    en: "Beta: explanations are not yet reviewed.",
    th: "เบต้า: คำอธิบายยังไม่ได้ตรวจทาน",
  },
  rounds: { ko: "분석한 TOPIK II PBT 시험", en: "TOPIK II PBT exams analysed", th: "ข้อสอบ TOPIK II PBT ที่ใช้วิเคราะห์" },
  questions: { ko: "문항", en: "Questions", th: "ข้อสอบ" },
  words: { ko: "어휘", en: "Words", th: "คำศัพท์" },
  grammarPoints: { ko: "문법", en: "Grammar points", th: "แกรมมาร์" },
  shortcut1Title: { ko: "번호만 보면 유형을 안다", en: "The number tells you the task", th: "ดูเลขข้อก็รู้ประเภท" },
  shortcut1Body: {
    ko: "분석한 모든 회차에서 같은 번호는 같은 유형이었습니다.",
    en: "In every round we analysed, the same question number had the same task type.",
    th: "ในทุกครั้งที่วิเคราะห์ เลขข้อเดียวกันเป็นคำถามประเภทเดียวกัน",
  },
  shortcut2Title: { ko: "정답 번호는 고르게 나온다", en: "Answers are spread evenly", th: "คำตอบกระจายเท่า ๆ กัน" },
  shortcut2Body: {
    ko: "최근 시험에서 ①②③④는 영역별로 각각 11~14번 정답이었습니다. 확신이 없을 때 참고하세요.",
    en: "In recent exams, each of ①②③④ was the answer 11–14 times per section. A tip for when you are unsure.",
    th: "ในข้อสอบล่าสุด ①②③④ เป็นคำตอบข้อละ 11–14 ครั้งต่อพาร์ท ใช้เป็นเคล็ดลับเมื่อไม่แน่ใจ",
  },
  shortcut3Title: { ko: "문법 문제는 1~4번", en: "Grammar questions: Q1–4", th: "ข้อแกรมมาร์: ข้อ 1–4" },
  shortcut3Body: {
    ko: "읽기 1~4번은 문법을 직접 묻습니다.",
    en: "Reading Q1–4 test grammar directly.",
    th: "พาร์ทอ่าน ข้อ 1–4 ถามแกรมมาร์โดยตรง",
  },
  listening: { ko: "듣기", en: "Listening", th: "พาร์ทฟัง" },
  reading: { ko: "읽기", en: "Reading", th: "พาร์ทอ่าน" },
  writing: { ko: "쓰기", en: "Writing", th: "พาร์ทเขียน" },
  items: { ko: "문항", en: "questions", th: "ข้อ" },
  minutes: { ko: "분", en: "min", th: "นาที" },
  answerSpread: { ko: "선택지별 정답 수", en: "Answers per choice", th: "จำนวนคำตอบแต่ละตัวเลือก" },
  round: { ko: "회", en: "Round", th: "ครั้งที่" },
  sameEveryRound: { ko: "모든 회차 동일", en: "Same in every round", th: "เหมือนกันทุกครั้ง" },
  keyWords: { ko: "핵심 단어", en: "Key words", th: "คำสำคัญ" },
  search: { ko: "검색", en: "Search", th: "ค้นหา" },
  onlyQ14: { ko: "읽기 1~4번만", en: "Reading Q1–4 only", th: "เฉพาะพาร์ทอ่าน ข้อ 1–4" },
  times: { ko: "회", en: "×", th: "ครั้ง" },
  partOfSpeech: { ko: "품사", en: "Part of speech", th: "ชนิดของคำ" },
  inQ14: { ko: "1~4번 출제", en: "In Q1–4", th: "อยู่ในข้อ 1–4" },
  meaning: { ko: "의미", en: "Meaning", th: "ความหมาย" },
  form: { ko: "형태", en: "Form", th: "รูปแบบ" },
  rules: { ko: "규칙", en: "Rules", th: "กฎ" },
  similar: { ko: "비슷한 문법", en: "Similar grammar", th: "แกรมมาร์ที่คล้ายกัน" },
  note: { ko: "차이", en: "Difference", th: "ความแตกต่าง" },
  memoryTip: { ko: "암기 팁", en: "Memory trick", th: "ทริคลับจำดี" },
  examPair: { ko: "기출 출제", en: "In the exam", th: "เคยออกข้อสอบ" },
  sameGrammar: { ko: "다른 기출문제에서 같은 문법", en: "Same grammar in other exam questions", th: "แกรมมาร์เดียวกันในข้อสอบอื่น" },
  showAll: { ko: "모두 보기", en: "Show all", th: "ดูทั้งหมด" },
  back: { ko: "← 목록", en: "← List", th: "← รายการ" },
  where: { ko: "나온 곳", en: "Where", th: "พบที่" },
  passage: { ko: "지문", en: "Passage", th: "บทอ่าน" },
  question: { ko: "문제", en: "Question", th: "คำถาม" },
  choice: { ko: "선택지", en: "Choices", th: "ตัวเลือก" },
  answerChoice: { ko: "정답", en: "Correct answer", th: "คำตอบที่ถูก" },
  vocabNote: {
    ko: "번역은 준비 중입니다. 지금은 빈도와 기출 예문을 보여 줍니다.",
    en: "Translations are coming. For now: frequency and real exam sentences.",
    th: "คำแปลกำลังจัดทำ ตอนนี้แสดงความถี่และประโยคจากข้อสอบจริง",
  },
  askPlaceholder: { ko: "예: -는 바람에는 언제 써요?", en: "e.g. What is the difference between -아/어 두다 and -아/어 놓다?", th: "เช่น -(으)ㄹ 뻔하다 แปลว่าอะไร" },
  askButton: { ko: "질문하기", en: "Ask", th: "ถาม" },
  asking: { ko: "답변을 만드는 중… (내 컴퓨터의 AI라서 15~60초)", en: "Thinking… (local AI on this computer: 15–60 s)", th: "กำลังคิด… (AI ในเครื่องนี้ 15–60 วินาที)" },
  askIntro: {
    ko: "기출문제와 문법 카드만 보고 답하고, 모든 내용에 출처를 표시합니다.",
    en: "Answers only from past exams and grammar cards, with a source for every fact.",
    th: "ตอบจากข้อสอบเก่าและการ์ดแกรมมาร์เท่านั้น พร้อมแหล่งที่มาทุกข้อ",
  },
  sources: { ko: "출처", en: "Sources", th: "แหล่งที่มา" },
  apiDown: {
    ko: "AI 서버가 꺼져 있습니다. 터미널에서 실행하세요:",
    en: "The AI server is not running. Start it in a terminal:",
    th: "เซิร์ฟเวอร์ AI ไม่ได้ทำงาน ให้รันในเทอร์มินัล:",
  },
  pickQuestion: { ko: "기출문제", en: "Exam", th: "ข้อสอบ" },
  yourAnswer: { ko: "내 답안", en: "Your answer", th: "คำตอบของคุณ" },
  characters: { ko: "자", en: "characters", th: "คำ" },
  useAI: { ko: "AI 맞춤법 검사 포함", en: "Include AI spelling check", th: "ตรวจการสะกดด้วย AI" },
  check: { ko: "검사하기", en: "Check", th: "ตรวจ" },
  needLength: { ko: "분량을 맞춰야 검사할 수 있습니다", en: "Write within the length limit to check", th: "ต้องเขียนให้ได้ตามจำนวนที่กำหนดก่อนตรวจ" },
  needBlanks: { ko: "㉠과 ㉡을 모두 쓰세요", en: "Fill in both ㉠ and ㉡", th: "เขียนทั้ง ㉠ และ ㉡ ก่อนตรวจ" },
  checking: { ko: "검사 중…", en: "Checking…", th: "กำลังตรวจ…" },
  noIssues: { ko: "문제를 찾지 못했습니다.", en: "No issues found.", th: "ไม่พบข้อผิดพลาด" },
  layerRule: { ko: "공식 규칙", en: "Official rules", th: "กฎอย่างเป็นทางการ" },
  layerLanguage: { ko: "언어", en: "Language", th: "ภาษา" },
  layerContent: { ko: "내용", en: "Content", th: "เนื้อหา" },
  layerAI: { ko: "AI (가능한 오류)", en: "AI (possible errors)", th: "AI (ข้อผิดพลาดที่เป็นไปได้)" },
  feedbackLang: { ko: "피드백은 영어로 표시됩니다.", en: "", th: "" },
} as const;

export type Key = keyof typeof dict;

export function t(lang: Lang) {
  return (key: Key) => dict[key][lang];
}
