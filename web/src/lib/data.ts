// Reads the JSON exported by pipeline/export_web.py (data/web/, not in git: it contains exam text).
import { readFile } from "node:fs/promises";
import path from "node:path";
import { cacheLife } from "next/cache";

const DATA_DIR = process.env.TOPIK_DATA_DIR ?? path.join(process.cwd(), "..", "data", "web");

async function load<T>(name: string): Promise<T> {
  "use cache";
  cacheLife("max");
  return JSON.parse(await readFile(path.join(DATA_DIR, name), "utf8")) as T;
}

export type Text = { en: string; th: string; ko?: string };

export type QuestionType = {
  section: "reading" | "writing";
  instruction: string;
  numbers: number[];
  same_in_all_rounds: boolean;
  task: Text;
  words: [string, string, string][];
};

export type Overview = {
  rounds: number[];
  counts: { questions: number; reading: number; writing: number; words: number; grammar: number };
  question_types: QuestionType[];
  answer_distribution: Record<string, Record<string, Record<string, number>>>;
  withheld: string[];
};

export type Example = { sentence: string; source: string };

export type Grammar = {
  id: number;
  name: string;
  meaning: Text;
  form: Partial<Text>;
  rules: { t: "ok" | "no" | "note"; en: string; th: string }[];
  similar: { g: string; exam?: string }[];
  note: Partial<Text>;
  count: number;
  rounds: number[];
  in_q1_4: string[];
  questions: string[];
  examples: Example[];
  reviewed: boolean;
};

export type Word = {
  lemma: string;
  pos: string[];
  count: number;
  rounds: number[];
  n_questions: number;
  where: Record<string, number>;
  examples: Example[];
};

export const getOverview = () => load<Overview>("overview.json");
export const getGrammar = () => load<Grammar[]>("grammar.json");
export const getVocab = () => load<Word[]>("vocab.json");

// "96-reading-3" -> "96 Q3",  "102-writing-54" -> "102 W54"
export function sourceLabel(id: string) {
  const [round, section, number] = id.split("-");
  return `${round} ${section === "writing" ? "W" : "Q"}${number}`;
}
