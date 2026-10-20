"""Local API for the website: Ask TOPIK (RAG) and the Writing checker.

Run:  .venv/bin/uvicorn api.main:app --port 8000
Docs: http://localhost:8000/docs   (FastAPI generates them from the Pydantic models)

Only the local website may call it (CORS), and it listens on this Mac only (127.0.0.1).
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag.answer import ask
from rag.search import Searcher
from writing.check import question as writing_question
from writing.check import run as check_writing
from writing.rules import LENGTH, cells

ROOT = Path(__file__).resolve().parent.parent
ROUNDS = (102, 96, 91)

app = FastAPI(title="TOPIK Shortcut API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"])
searcher = Searcher()          # load the index once, not on every question


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class CheckIn(BaseModel):
    round: int
    number: int = Field(ge=51, le=54)
    answer: str | dict[str, str]
    ai: bool = True


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ask")
def ask_topik(body: AskIn):
    result = ask(body.question, searcher)
    by_id = {c["id"]: c for c in searcher.chunks}
    result["sources"] = [{"id": i, "kind": by_id[i]["kind"], "text": by_id[i]["text"][:400]}
                         for i in result["retrieved"] if i in by_id]
    return result


@app.get("/writing/prompts")
def writing_prompts():
    out = []
    for rnd in ROUNDS:
        for number in (51, 52, 53, 54):
            q = writing_question(rnd, number)
            out.append({"round": rnd, "number": number, "instruction": q["instruction"], "text": q["text"],
                        "limits": LENGTH.get(number)})
    return out


@app.post("/writing/check")
def writing_check(body: CheckIn):
    if body.round not in ROUNDS:
        raise HTTPException(404, "unknown round")
    if body.number in (51, 52) and not isinstance(body.answer, dict):
        raise HTTPException(422, "51/52: answer must be {'㉠': ..., '㉡': ...}")
    if body.number in (53, 54) and not isinstance(body.answer, str):
        raise HTTPException(422, "53/54: answer must be text")
    issues = check_writing(body.round, body.number, body.answer, use_ai=body.ai)
    length = cells(body.answer) if isinstance(body.answer, str) else None
    return {"length": length, "limits": LENGTH.get(body.number), "issues": issues}
