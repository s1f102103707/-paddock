"""ローカルSQLite DB（仕様書 5章 非機能要件: データ保存）。

M1（基礎データ）とM4（手動パドック評価）の永続化、M8（バックテスト）用の
過去結果保存を担当する。JRA-VANデータの二次配布は規約上不可のため、実データは
本リポジトリにコミットしない（.gitignoreでdata/以下のDB/CSVを除外済み）。
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from keiba.models import BodyWeight, Entry, Odds, PaddockManualScore, Race, RaceResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    race_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    course TEXT NOT NULL,
    distance INTEGER NOT NULL,
    race_class TEXT NOT NULL,
    weather TEXT NOT NULL,
    track_condition TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    race_id TEXT NOT NULL,
    horse_number INTEGER NOT NULL,
    horse_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    sex TEXT NOT NULL,
    jockey TEXT NOT NULL,
    trainer TEXT NOT NULL,
    weight_carried REAL NOT NULL,
    sire TEXT NOT NULL,
    dam TEXT NOT NULL,
    dam_sire TEXT NOT NULL,
    PRIMARY KEY (race_id, horse_number)
);

CREATE TABLE IF NOT EXISTS body_weights (
    race_id TEXT NOT NULL,
    horse_number INTEGER NOT NULL,
    weight INTEGER NOT NULL,
    weight_diff INTEGER NOT NULL,
    PRIMARY KEY (race_id, horse_number)
);

CREATE TABLE IF NOT EXISTS odds (
    race_id TEXT NOT NULL,
    horse_number INTEGER NOT NULL,
    win_odds REAL NOT NULL,
    place_odds_low REAL NOT NULL,
    place_odds_high REAL NOT NULL,
    PRIMARY KEY (race_id, horse_number)
);

CREATE TABLE IF NOT EXISTS paddock_manual_scores (
    race_id TEXT NOT NULL,
    horse_number INTEGER NOT NULL,
    item_scores_json TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (race_id, horse_number)
);

CREATE TABLE IF NOT EXISTS race_results (
    race_id TEXT NOT NULL,
    horse_number INTEGER NOT NULL,
    finish_position INTEGER NOT NULL,
    PRIMARY KEY (race_id, horse_number)
);
"""


@contextmanager
def connect(db_path: str | Path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def save_race(conn: sqlite3.Connection, race: Race) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO races VALUES (?, ?, ?, ?, ?, ?, ?)",
        (race.race_id, race.date, race.course, race.distance, race.race_class, race.weather, race.track_condition),
    )


def save_entry(conn: sqlite3.Connection, entry: Entry) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry.race_id,
            entry.horse_number,
            entry.horse_name,
            entry.age,
            entry.sex,
            entry.jockey,
            entry.trainer,
            entry.weight_carried,
            entry.sire,
            entry.dam,
            entry.dam_sire,
        ),
    )


def save_body_weight(conn: sqlite3.Connection, bw: BodyWeight) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO body_weights VALUES (?, ?, ?, ?)",
        (bw.race_id, bw.horse_number, bw.weight, bw.weight_diff),
    )


def save_odds(conn: sqlite3.Connection, odds: Odds) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO odds VALUES (?, ?, ?, ?, ?)",
        (odds.race_id, odds.horse_number, odds.win_odds, odds.place_odds_low, odds.place_odds_high),
    )


def save_paddock_score(conn: sqlite3.Connection, score: PaddockManualScore) -> None:
    import json

    conn.execute(
        "INSERT OR REPLACE INTO paddock_manual_scores VALUES (?, ?, ?, ?)",
        (score.race_id, score.horse_number, json.dumps(score.item_scores, ensure_ascii=False), score.note),
    )


def load_paddock_score(conn: sqlite3.Connection, race_id: str, horse_number: int) -> PaddockManualScore | None:
    import json

    row = conn.execute(
        "SELECT item_scores_json, note FROM paddock_manual_scores WHERE race_id = ? AND horse_number = ?",
        (race_id, horse_number),
    ).fetchone()
    if row is None:
        return None
    return PaddockManualScore(race_id=race_id, horse_number=horse_number, item_scores=json.loads(row[0]), note=row[1])


def save_race_result(conn: sqlite3.Connection, result: RaceResult) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO race_results VALUES (?, ?, ?)",
        (result.race_id, result.horse_number, result.finish_position),
    )
