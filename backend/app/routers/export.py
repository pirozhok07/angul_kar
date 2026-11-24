from collections import defaultdict
from datetime import datetime
import io
import re
from copy import copy
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from sqlalchemy.orm import Session

import app.tournament_models as tournament_models
from app.tournament_database import get_tournament_db
from app.tournament_models import (
    AthleteCategory,
    BronzeMatchResult,
    Category,
    Athlete,
    CategoryDistribution,
    Club,
    Coach,
    KataCompetition,
    KataGroup,
    KataGroupAthlete,
    KataRound,
    KataRoundParticipant,
    KataScore,
    KumiteDrawEntry,
    KumiteDrawMatch,
)
from app.routes.kumite_competition import (
    get_loser,
    athlete_name as format_athlete_name,
)


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/export",
    tags=["Export"],
)


def category_matches(db: Session, category_id: int):
    return (
        db.query(KumiteDrawMatch)
        .filter(KumiteDrawMatch.category_id == category_id)
        .order_by(
            KumiteDrawMatch.round_number,
            KumiteDrawMatch.match_number,
        )
        .all()
    )
# ---------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------

def safe_sheet_title(title: str, used: set) -> str:
    title = re.sub(r'[\[\]:*?/\\]', '_', str(title or 'Категория'))
    title = title[:31] or 'Категория'

    original = title
    counter = 1

    while title in used:
        suffix = f'_{counter}'
        title = original[:31 - len(suffix)] + suffix
        counter += 1

    used.add(title)
    return title


def athlete_name(athlete):
    if not athlete:
        return ''

    parts = [
        getattr(athlete, 'last_name', ''),
        getattr(athlete, 'first_name', ''),
        getattr(athlete, 'middle_name', ''),
    ]

    return ' '.join(
        str(part).strip()
        for part in parts
        if part
    )


def get_athlete_club(db, athlete):
    if not athlete or not getattr(athlete, 'club_id', None):
        return ''

    club = db.query(Club).filter(
        Club.id == athlete.club_id
    ).first()

    return club.name if club else ''


# =========================================================
# ЦВЕТА И СТИЛИ (те же, что в выгрузке кумите)
# =========================================================

DARK_BLUE = "17365D"
HEADER_BLUE = "24476B"
LIGHT_GRAY = "F4F6F8"
BORDER_COLOR = "C5CED8"
SEPARATOR_BLUE = "DCE6F1"
GREEN_FILL = "D9EAD3"
GREEN_TEXT = "274E13"
GRAY_TEXT = "7A8794"
BRONZE_COLOR = "FCE4D6"
BRONZE_TEXT = "7F4120"
GOLD_COLOR = "FFF2CC"
GOLD_TEXT = "7F6000"
SILVER_COLOR = "E7E6E6"
WHITE = "FFFFFF"

thin = Side(style="thin", color=BORDER_COLOR)
medium_blue = Side(style="medium", color=DARK_BLUE)
sign_line = Side(style="thin", color=DARK_BLUE)

cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)

center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left_center = Alignment(
    horizontal="left", vertical="center", indent=1, shrink_to_fit=True,
)
left_wrap = Alignment(
    horizontal="left", vertical="center", indent=1, wrap_text=True,
)

title_fill = PatternFill("solid", fgColor=DARK_BLUE)
header_fill = PatternFill("solid", fgColor=HEADER_BLUE)
gray_fill = PatternFill("solid", fgColor=LIGHT_GRAY)
green_fill = PatternFill("solid", fgColor=GREEN_FILL)
gold_fill = PatternFill("solid", fgColor=GOLD_COLOR)
silver_fill = PatternFill("solid", fgColor=SILVER_COLOR)
bronze_fill = PatternFill("solid", fgColor=BRONZE_COLOR)

PLACE_FILLS = {1: gold_fill, 2: silver_fill, 3: bronze_fill}
PLACE_TEXT = {1: GOLD_TEXT, 2: DARK_BLUE, 3: BRONZE_TEXT}

# Сколько призовых мест выводить в итоговой таблице
PODIUM_PLACES = 3

# Колонки листа
COL_NO = 1
COL_NAME = 2
COL_CLUB = 3
COL_J1 = 4           # судьи 1..5 — колонки 4..8
COL_SUM = 9
COL_MAX = 10
COL_MIN = 11
COL_PLACE = 12       # только в последнем туре
LAST_COL = COL_PLACE

JUDGES = 5

title_fill = PatternFill("solid", fgColor=DARK_BLUE)
header_fill = PatternFill("solid", fgColor=HEADER_BLUE)
zebra_fill = PatternFill("solid", fgColor=LIGHT_GRAY)
separator_fill = PatternFill("solid", fgColor=SEPARATOR_BLUE)

TYPE_ORDER = ("Кумите", "Ката", "Ката-группа")


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def safe_sheet_title(title: str, used: set) -> str:
    title = re.sub(r'[\[\]:*?/\\]', '_', str(title or 'Категория'))
    title = title[:31] or 'Категория'

    original = title
    counter = 1

    while title in used:
        suffix = f'_{counter}'
        title = original[:31 - len(suffix)] + suffix
        counter += 1

    used.add(title)
    return title


def athlete_name(athlete):
    if not athlete:
        return ''

    parts = [
        getattr(athlete, 'last_name', ''),
        getattr(athlete, 'first_name', ''),
        getattr(athlete, 'middle_name', ''),
    ]

    return ' '.join(
        str(part).strip()
        for part in parts
        if part
    )


def get_athlete_club(db, athlete):
    if not athlete or not getattr(athlete, 'club_id', None):
        return ''

    club = db.query(Club).filter(
        Club.id == athlete.club_id
    ).first()

    return club.name if club else ''


def get_participant_key(participant):
    if participant.athlete_id:
        return ('athlete', participant.athlete_id)

    if participant.kata_group_id:
        return ('group', participant.kata_group_id)

    return None


def get_group_members(db, group_id):
    return (
        db.query(Athlete)
        .join(
            KataGroupAthlete,
            KataGroupAthlete.athlete_id == Athlete.id
        )
        .filter(KataGroupAthlete.kata_group_id == group_id)
        .all()
    )


def get_participant_name(db, participant):
    if participant.athlete_id:
        athlete = db.query(Athlete).filter(
            Athlete.id == participant.athlete_id
        ).first()

        return athlete_name(athlete)

    if participant.kata_group_id:
        group = db.query(KataGroup).filter(
            KataGroup.id == participant.kata_group_id
        ).first()

        if not group:
            return f'Ката-группа {participant.kata_group_id}'

        members = get_group_members(db, group.id)
        names = [athlete_name(a) for a in members]

        return getattr(group, 'name', None) or ', '.join(names)

    return ''


def get_participant_club(db, participant):
    if participant.athlete_id:
        athlete = db.query(Athlete).filter(
            Athlete.id == participant.athlete_id
        ).first()

        return get_athlete_club(db, athlete)

    if participant.kata_group_id:
        clubs = []

        for athlete in get_group_members(db, participant.kata_group_id):
            club_name = get_athlete_club(db, athlete)

            if club_name and club_name not in clubs:
                clubs.append(club_name)

        return ', '.join(clubs)

    return ''


def get_round_label(round_obj):
    if round_obj.round_type == 'tiebreak':
        return f'ДОП. ТУР {round_obj.number}'

    return f'ТУР {round_obj.number}'


def get_score_data(db, participant):
    score = db.query(KataScore).filter(
        KataScore.round_participant_id == participant.id
    ).first()

    if not score:
        return {
            'scores': [None] * JUDGES,
            'total_score': participant.total_score,
            'max_score': None,
            'min_score': None,
            'is_confirmed': False,
        }

    return {
        'scores': [
            score.score1,
            score.score2,
            score.score3,
            score.score4,
            score.score5,
        ],
        'total_score': (
            score.total_score
            if score.total_score is not None
            else participant.total_score
        ),
        'max_score': score.max_score,
        'min_score': score.min_score,
        'is_confirmed': score.is_confirmed,
    }


def format_number(value):
    if value is None:
        return ''

    return round(float(value), 2)


def get_tournament_info(db, tournament_id, date_override, place_override):
    """
    Дата и место берутся из параметров запроса (?date=...&place=...),
    а если их нет — из модели турнира (поля подбираются по имени).
    """
    date_value = date_override
    place_value = place_override

    if date_value and place_value:
        return date_value, place_value

    Tournament = getattr(tournament_models, "Tournament", None)

    if Tournament is None:
        return date_value or "", place_value or ""

    try:
        query = db.query(Tournament)
        tournament = (
            query.filter(Tournament.id == tournament_id).first()
            or query.first()
        )
    except Exception:
        tournament = None

    if tournament is None:
        return date_value or "", place_value or ""

    def first_attr(names):
        for attr in names:
            value = getattr(tournament, attr, None)
            if value:
                return value
        return None

    if not date_value:
        raw_date = first_attr(
            ("date", "start_date", "event_date", "tournament_date")
        )
        if hasattr(raw_date, "strftime"):
            raw_date = raw_date.strftime("%d.%m.%Y")
        date_value = str(raw_date) if raw_date else ""

    if not place_value:
        raw_place = first_attr(
            ("place", "location", "venue", "city", "address")
        )
        place_value = str(raw_place) if raw_place else ""

    return date_value, place_value


# =========================================================
# ОТРИСОВКА БЛОКОВ ЛИСТА
# =========================================================

def style_cell(cell, fill=None, font=None, alignment=None, border=True):
    if fill is not None:
        cell.fill = fill
    if font is not None:
        cell.font = font
    cell.alignment = alignment or center
    if border:
        cell.border = cell_border


def merge_row(ws, row, c1, c2):
    if c2 > c1:
        ws.merge_cells(
            start_row=row, start_column=c1,
            end_row=row, end_column=c2,
        )


def draw_span_header(ws, row, c1, c2, text, fill, size=10):
    """Заголовок, объединённый по колонкам c1..c2."""
    merge_row(ws, row, c1, c2)

    for c in range(c1, c2 + 1):
        style_cell(ws.cell(row, c), fill=fill)

    first = ws.cell(row, c1, text)
    first.font = Font(name="Arial", size=size, bold=True, color=WHITE)


def draw_sheet_top(ws, title_text, subtitle, date_text, place_text):
    """Название категории, место/дата и подзаголовок."""

    merge_row(ws, 1, 1, LAST_COL)

    title = ws.cell(1, 1, title_text)
    title.fill = title_fill
    title.font = Font(name="Arial", size=18, bold=True, color=WHITE)
    title.alignment = center
    title.border = Border(bottom=medium_blue)

    ws.row_dimensions[1].height = 40

    info_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)
    split_col = 6

    merge_row(ws, 2, 1, split_col)
    merge_row(ws, 2, split_col + 1, LAST_COL)

    place_cell = ws.cell(
        2, 1, f"Место проведения: {place_text or '______________________'}",
    )
    place_cell.font = info_font
    place_cell.alignment = Alignment(
        horizontal="left", vertical="center", indent=1,
    )

    date_cell = ws.cell(
        2, split_col + 1, f"Дата: {date_text or '______________'}",
    )
    date_cell.font = info_font
    date_cell.alignment = Alignment(
        horizontal="right", vertical="center", indent=1,
    )

    ws.row_dimensions[2].height = 26

    merge_row(ws, 3, 1, LAST_COL)

    sub = ws.cell(3, 1, subtitle)
    sub.font = Font(name="Arial", size=10, italic=True, color=GRAY_TEXT)
    sub.alignment = center

    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 12


def draw_round_block(ws, start_row, round_obj, rows, is_last):
    """
    Блок одного тура:
      строка 1 — название тура;
      строка 2 — заголовки колонок;
      далее — участники.
    В последнем туре добавляется колонка «Место».
    Возвращает номер строки после блока.
    """

    end_col = COL_PLACE if is_last else COL_MIN

    # Название тура
    draw_span_header(
        ws, start_row, 1, end_col, get_round_label(round_obj),
        title_fill, size=12,
    )
    ws.row_dimensions[start_row].height = 28

    # Заголовки колонок
    headers = {
        COL_NO: '№',
        COL_NAME: 'УЧАСТНИК',
        COL_CLUB: 'КЛУБ',
        COL_SUM: 'СУММА',
        COL_MAX: 'МАКС.',
        COL_MIN: 'МИН.',
    }

    for judge in range(JUDGES):
        headers[COL_J1 + judge] = f'СУДЬЯ {judge + 1}'

    if is_last:
        headers[COL_PLACE] = 'МЕСТО'

    header_row = start_row + 1

    for col, text in headers.items():
        cell = ws.cell(header_row, col, text)
        style_cell(
            cell,
            fill=header_fill,
            font=Font(name="Arial", size=10, bold=True, color=WHITE),
        )

    ws.row_dimensions[header_row].height = 26

    # Участники
    row = header_row + 1

    if not rows:
        merge_row(ws, row, 1, end_col)

        for c in range(1, end_col + 1):
            style_cell(ws.cell(row, c), fill=gray_fill)

        empty = ws.cell(row, 1, 'В этом туре нет участников')
        empty.font = Font(name="Arial", size=10, italic=True, color=GRAY_TEXT)

        ws.row_dimensions[row].height = 22
        return row + 1

    base_font = Font(name="Arial", size=10, color=DARK_BLUE)
    bold_font = Font(name="Arial", size=10, bold=True, color=DARK_BLUE)
    small_font = Font(name="Arial", size=9, italic=True, color=GRAY_TEXT)

    for index, item in enumerate(rows, start=1):
        score = item['score']
        confirmed = score['is_confirmed']

        style_cell(ws.cell(row, COL_NO, index), font=base_font)

        style_cell(
            ws.cell(row, COL_NAME, item['name']),
            font=bold_font,
            alignment=left_center,
        )

        style_cell(
            ws.cell(row, COL_CLUB, item['club']),
            font=small_font,
            alignment=left_center,
        )

        # Оценки судей
        for judge, value in enumerate(score['scores']):
            style_cell(
                ws.cell(row, COL_J1 + judge, format_number(value)),
                fill=green_fill if confirmed else None,
                font=base_font,
            )

        # Сумма — выделена
        style_cell(
            ws.cell(row, COL_SUM, format_number(score['total_score'])),
            fill=gold_fill,
            font=Font(name="Arial", size=11, bold=True, color=GOLD_TEXT),
        )

        style_cell(
            ws.cell(row, COL_MAX, format_number(score['max_score'])),
            font=small_font,
        )
        style_cell(
            ws.cell(row, COL_MIN, format_number(score['min_score'])),
            font=small_font,
        )

        # Место — только в последнем туре
        if is_last:
            place = item['position']

            style_cell(
                ws.cell(row, COL_PLACE, place or ''),
                fill=PLACE_FILLS.get(place, gray_fill),
                font=Font(
                    name="Arial",
                    size=11,
                    bold=True,
                    color=PLACE_TEXT.get(place, DARK_BLUE),
                ),
            )

        ws.row_dimensions[row].height = 22
        row += 1

    return row


def draw_results_table(ws, start_row, last_round_rows):
    """Итоговая таблица: место — ФИО — клуб."""

    # Заголовок таблицы
    draw_span_header(
        ws, start_row, COL_NO, COL_CLUB, "ИТОГОВЫЕ РЕЗУЛЬТАТЫ",
        title_fill, size=12,
    )
    ws.row_dimensions[start_row].height = 28

    header_row = start_row + 1

    for col, text in ((COL_NO, 'МЕСТО'), (COL_NAME, 'ФИО'), (COL_CLUB, 'КЛУБ')):
        style_cell(
            ws.cell(header_row, col, text),
            fill=header_fill,
            font=Font(name="Arial", size=10, bold=True, color=WHITE),
        )

    ws.row_dimensions[header_row].height = 24

    by_place = {}

    for item in last_round_rows:
        if item['position'] and item['position'] not in by_place:
            by_place[item['position']] = item

    bold_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)
    base_font = Font(name="Arial", size=11, color=DARK_BLUE)

    for place in range(1, PODIUM_PLACES + 1):
        row = header_row + place
        item = by_place.get(place)
        fill = PLACE_FILLS.get(place, gray_fill)

        style_cell(ws.cell(row, COL_NO, place), fill=fill, font=bold_font)
        style_cell(
            ws.cell(row, COL_NAME, item['name'] if item else ''),
            fill=fill, font=bold_font, alignment=left_center,
        )
        style_cell(
            ws.cell(row, COL_CLUB, item['club'] if item else ''),
            fill=fill, font=base_font, alignment=left_center,
        )

        ws.row_dimensions[row].height = 24

    return header_row + PODIUM_PLACES + 1


def draw_signatures(ws, start_row):
    """Подписи главного судьи и главного секретаря."""

    caption_font = Font(name="Arial", size=8, color=GRAY_TEXT)
    sign_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)

    row = start_row

    for title in ("Главный судья", "Главный секретарь"):
        ws.row_dimensions[row].height = 30
        ws.row_dimensions[row + 1].height = 14

        # Должность
        merge_row(ws, row, COL_NO, COL_NAME)
        label = ws.cell(row, COL_NO, title)
        label.font = sign_font
        label.alignment = Alignment(
            horizontal="left", vertical="bottom", indent=1,
        )

        # Линия подписи и линия ФИО
        for (c1, c2), caption in (
            ((COL_CLUB, COL_J1 + 2), "подпись"),
            ((COL_J1 + 3, COL_MIN), "ФИО"),
        ):
            merge_row(ws, row, c1, c2)
            for c in range(c1, c2 + 1):
                ws.cell(row, c).border = Border(bottom=sign_line)

            merge_row(ws, row + 1, c1, c2)
            cap = ws.cell(row + 1, c1, caption)
            cap.font = caption_font
            cap.alignment = center

        row += 3


def setup_sheet(ws):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90

    ws.column_dimensions[get_column_letter(COL_NO)].width = 8
    ws.column_dimensions[get_column_letter(COL_NAME)].width = 34
    ws.column_dimensions[get_column_letter(COL_CLUB)].width = 26

    for judge in range(JUDGES):
        ws.column_dimensions[
            get_column_letter(COL_J1 + judge)
        ].width = 10

    ws.column_dimensions[get_column_letter(COL_SUM)].width = 11
    ws.column_dimensions[get_column_letter(COL_MAX)].width = 9
    ws.column_dimensions[get_column_letter(COL_MIN)].width = 9
    ws.column_dimensions[get_column_letter(COL_PLACE)].width = 10

    # Печать
    ws.freeze_panes = "A4"
    ws.print_title_rows = "1:3"

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


# =========================================================
# ЛИСТ КАТЕГОРИИ
# =========================================================

# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def safe_sheet_title(title: str, used: set) -> str:
    title = re.sub(r'[\[\]:*?/\\]', '_', str(title or 'Категория'))
    title = title[:31] or 'Категория'

    original = title
    counter = 1

    while title in used:
        suffix = f'_{counter}'
        title = original[:31 - len(suffix)] + suffix
        counter += 1

    used.add(title)
    return title


def athlete_name(person):
    if not person:
        return ''

    parts = [
        getattr(person, 'last_name', ''),
        getattr(person, 'first_name', ''),
        getattr(person, 'middle_name', ''),
    ]

    return ' '.join(
        str(part).strip()
        for part in parts
        if part
    )


def get_category_type(category):
    """Кумите / Ката / Ката-группа — по полям категории и её названию."""
    parts = [
        str(getattr(category, attr, '') or '')
        for attr in ('discipline', 'type', 'category_type', 'kind')
    ]
    parts.append(category.name or '')

    text = ' '.join(parts).lower()

    if 'кумит' in text or 'kumite' in text:
        return 'Кумите'

    if (
        'ката-группа' in text
        or 'ката группа' in text
        or 'kata_group' in text
        or 'kata-group' in text
    ):
        return 'Ката-группа'

    return 'Ката'


def normalize_gender(value):
    text = str(value or '').strip()

    if text.lower() in ('m', 'male', 'м', 'муж', 'мужской'):
        return 'М'

    if text.lower() in ('f', 'female', 'ж', 'жен', 'женский'):
        return 'Ж'

    return text


def calc_age(athlete):
    """Возраст: готовое поле age, иначе считается по дате рождения."""
    age = getattr(athlete, 'age', None)

    if age is not None:
        return age

    birth = getattr(athlete, 'birth_date', None)

    if isinstance(birth, datetime):
        birth = birth.date()

    if not isinstance(birth, Date):
        return ''

    today = Date.today()

    return today.year - birth.year - (
        (today.month, today.day) < (birth.month, birth.day)
    )


def get_athletes_for_category(db, category):
    return (
        db.query(Athlete)
        .join(
            CategoryDistribution,
            CategoryDistribution.athlete_id == Athlete.id
        )
        .filter(CategoryDistribution.category_id == category.id)
        .order_by(Athlete.last_name, Athlete.first_name)
        .all()
    )


def get_tournament_info(db, tournament_id, date_override, place_override):
    """
    Дата и место берутся из параметров запроса (?date=...&place=...),
    а если их нет — из модели турнира (поля подбираются по имени).
    """
    date_value = date_override
    place_value = place_override

    if date_value and place_value:
        return date_value, place_value

    Tournament = getattr(tournament_models, "Tournament", None)

    if Tournament is None:
        return date_value or "", place_value or ""

    try:
        query = db.query(Tournament)
        tournament = (
            query.filter(Tournament.id == tournament_id).first()
            or query.first()
        )
    except Exception:
        tournament = None

    if tournament is None:
        return date_value or "", place_value or ""

    def first_attr(names):
        for attr in names:
            value = getattr(tournament, attr, None)
            if value:
                return value
        return None

    if not date_value:
        raw_date = first_attr(
            ("date", "start_date", "event_date", "tournament_date")
        )
        if hasattr(raw_date, "strftime"):
            raw_date = raw_date.strftime("%d.%m.%Y")
        date_value = str(raw_date) if raw_date else ""

    if not place_value:
        raw_place = first_attr(
            ("place", "location", "venue", "city", "address")
        )
        place_value = str(raw_place) if raw_place else ""

    return date_value, place_value


class Lookups:
    """Клуб и тренер спортсмена: каждый запрашивается из БД один раз."""

    def __init__(self, db):
        self.db = db
        self._clubs = {}
        self._coaches = {}

    def club(self, athlete):
        club_id = getattr(athlete, 'club_id', None)

        if not club_id:
            return ''

        if club_id not in self._clubs:
            club = self.db.query(Club).filter(Club.id == club_id).first()
            self._clubs[club_id] = club.name if club else ''

        return self._clubs[club_id]

    def coach(self, athlete):
        coach_id = getattr(athlete, 'coach_id', None)

        if not coach_id:
            return ''

        if coach_id not in self._coaches:
            coach = self.db.query(Coach).filter(Coach.id == coach_id).first()

            self._coaches[coach_id] = (
                (athlete_name(coach) or getattr(coach, 'name', '') or '')
                if coach else ''
            )

        return self._coaches[coach_id]


# =========================================================
# КОЛОНКИ
# =========================================================

def build_columns(with_category, with_weight):
    """Список колонок: (ключ, заголовок, ширина)."""
    columns = [('no', '№', 7)]

    if with_category:
        columns.append(('category', 'КАТЕГОРИЯ', 28))

    columns += [
        ('name', 'ФАМИЛИЯ, ИМЯ', 34),
        ('gender', 'ПОЛ', 8),
        ('birth', 'ДАТА РОЖДЕНИЯ', 16),
        ('age', 'ВОЗРАСТ', 10),
    ]

    if with_weight:
        columns.append(('weight', 'ВЕС, КГ', 10))

    columns += [
        ('club', 'КЛУБ', 28),
        ('coach', 'ТРЕНЕР', 28),
    ]

    return columns


def cell_value(key, number, athlete, category, lookups):
    if key == 'no':
        return number

    if key == 'category':
        return category.name

    if key == 'name':
        return athlete_name(athlete)

    if key == 'gender':
        return normalize_gender(getattr(athlete, 'gender', ''))

    if key == 'birth':
        birth = getattr(athlete, 'birth_date', None)

        if isinstance(birth, datetime):
            return birth.date()

        return birth or ''

    if key == 'age':
        return calc_age(athlete)

    if key == 'weight':
        weight = getattr(athlete, 'weight', None)
        return '' if weight is None else weight

    if key == 'club':
        return lookups.club(athlete)

    if key == 'coach':
        return lookups.coach(athlete)

    return ''


# =========================================================
# ОТРИСОВКА ЛИСТА
# =========================================================

def merge_row(ws, row, c1, c2):
    if c2 > c1:
        ws.merge_cells(
            start_row=row, start_column=c1,
            end_row=row, end_column=c2,
        )


def draw_sheet_top(ws, last_col, title_text, subtitle, date_text, place_text):
    """Название, место/дата и подзаголовок."""

    merge_row(ws, 1, 1, last_col)

    title = ws.cell(1, 1, title_text)
    title.fill = title_fill
    title.font = Font(name="Arial", size=18, bold=True, color=WHITE)
    title.alignment = center
    title.border = Border(bottom=medium_blue)

    ws.row_dimensions[1].height = 40

    info_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)
    split_col = (last_col + 1) // 2

    merge_row(ws, 2, 1, split_col)
    merge_row(ws, 2, split_col + 1, last_col)

    place_cell = ws.cell(
        2, 1, f"Место проведения: {place_text or '______________________'}",
    )
    place_cell.font = info_font
    place_cell.alignment = Alignment(
        horizontal="left", vertical="center", indent=1,
    )

    date_cell = ws.cell(
        2, split_col + 1, f"Дата: {date_text or '______________'}",
    )
    date_cell.font = info_font
    date_cell.alignment = Alignment(
        horizontal="right", vertical="center", indent=1,
    )

    ws.row_dimensions[2].height = 26

    merge_row(ws, 3, 1, last_col)

    sub = ws.cell(3, 1, subtitle)
    sub.font = Font(name="Arial", size=10, italic=True, color=GRAY_TEXT)
    sub.alignment = center

    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 12


def draw_header_row(ws, row, columns):
    for col, (_, header, width) in enumerate(columns, start=1):
        cell = ws.cell(row, col, header)
        cell.fill = header_fill
        cell.font = Font(name="Arial", size=10, bold=True, color=WHITE)
        cell.alignment = center
        cell.border = cell_border

        ws.column_dimensions[get_column_letter(col)].width = width

    ws.row_dimensions[row].height = 28


def draw_message_row(ws, row, last_col, text):
    merge_row(ws, row, 1, last_col)

    for c in range(1, last_col + 1):
        ws.cell(row, c).border = cell_border

    cell = ws.cell(row, 1, text)
    cell.font = Font(name="Arial", size=10, italic=True, color=GRAY_TEXT)
    cell.alignment = center

    ws.row_dimensions[row].height = 22


def draw_athlete_rows(
    ws, row, columns, category, athletes, lookups, start_number,
):
    """Строки спортсменов. Возвращает (следующая строка, следующий №)."""

    base_font = Font(name="Arial", size=10, color=DARK_BLUE)
    bold_font = Font(name="Arial", size=10, bold=True, color=DARK_BLUE)
    small_font = Font(name="Arial", size=9, color=DARK_BLUE)

    number = start_number

    for index, athlete in enumerate(athletes):
        fill = zebra_fill if index % 2 else None

        for col, (key, _, _) in enumerate(columns, start=1):
            value = cell_value(key, number, athlete, category, lookups)
            cell = ws.cell(row, col, value)

            cell.border = cell_border

            if fill:
                cell.fill = fill

            if key == 'name':
                cell.font = bold_font
                cell.alignment = left_center
            elif key in ('category', 'club', 'coach'):
                cell.font = small_font
                cell.alignment = left_center
            else:
                cell.font = base_font
                cell.alignment = center

            if key == 'birth' and value:
                cell.number_format = 'DD.MM.YYYY'

        ws.row_dimensions[row].height = 22
        row += 1
        number += 1

    return row, number


def draw_signatures(ws, start_row, last_col):
    """Подписи главного судьи и главного секретаря."""

    caption_font = Font(name="Arial", size=8, color=GRAY_TEXT)
    sign_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)

    # Должность — колонки 1..2, подпись — 3..4, ФИО — остальные
    ranges = (
        ((3, 4), "подпись"),
        ((5, last_col), "ФИО"),
    )

    row = start_row

    for title in ("Главный судья", "Главный секретарь"):
        ws.row_dimensions[row].height = 30
        ws.row_dimensions[row + 1].height = 14

        merge_row(ws, row, 1, 2)
        label = ws.cell(row, 1, title)
        label.font = sign_font
        label.alignment = Alignment(
            horizontal="left", vertical="bottom", indent=1,
        )

        for (c1, c2), caption in ranges:
            merge_row(ws, row, c1, c2)

            for c in range(c1, c2 + 1):
                ws.cell(row, c).border = Border(bottom=sign_line)

            merge_row(ws, row + 1, c1, c2)
            cap = ws.cell(row + 1, c1, caption)
            cap.font = caption_font
            cap.alignment = center

        row += 3


def finish_sheet(ws, header_row):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90

    ws.freeze_panes = f"A{header_row + 1}"
    ws.print_title_rows = f"1:{header_row}"

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


HEADER_ROW = 5


def create_category_sheet(
    wb, db, category, used_titles, lookups, date_text, place_text,
):
    """Отдельный лист на одну категорию."""

    ws = wb.create_sheet(safe_sheet_title(category.name, used_titles))

    category_type = get_category_type(category)
    columns = build_columns(
        with_category=False,
        with_weight=category_type == 'Кумите',
    )
    last_col = len(columns)

    athletes = get_athletes_for_category(db, category)

    draw_sheet_top(
        ws,
        last_col,
        category.name,
        f'Список спортсменов · {category_type} · всего: {len(athletes)}',
        date_text,
        place_text,
    )

    draw_header_row(ws, HEADER_ROW, columns)

    row = HEADER_ROW + 1

    if athletes:
        row, _ = draw_athlete_rows(
            ws, row, columns, category, athletes, lookups, 1,
        )

        ws.auto_filter.ref = f'A{HEADER_ROW}:{get_column_letter(last_col)}{row - 1}'
    else:
        draw_message_row(
            ws, row, last_col, 'Нет зарегистрированных спортсменов',
        )
        row += 1

    draw_signatures(ws, row + 2, last_col)
    finish_sheet(ws, HEADER_ROW)


def create_type_sheet(
    wb, db, type_name, categories, used_titles, lookups,
    date_text, place_text,
):
    """Один лист на вид программы: категории идут друг под другом."""

    ws = wb.create_sheet(safe_sheet_title(type_name, used_titles))

    columns = build_columns(
        with_category=True,
        with_weight=type_name == 'Кумите',
    )
    last_col = len(columns)

    athletes_by_category = [
        (category, get_athletes_for_category(db, category))
        for category in categories
    ]

    total = sum(len(athletes) for _, athletes in athletes_by_category)

    draw_sheet_top(
        ws,
        last_col,
        f'Список спортсменов — {type_name}',
        f'Категорий: {len(categories)} · всего спортсменов: {total}',
        date_text,
        place_text,
    )

    draw_header_row(ws, HEADER_ROW, columns)

    row = HEADER_ROW + 1
    number = 1

    for category, athletes in athletes_by_category:
        # Разделитель категории
        merge_row(ws, row, 1, last_col)

        for c in range(1, last_col + 1):
            ws.cell(row, c).fill = separator_fill
            ws.cell(row, c).border = cell_border

        separator = ws.cell(row, 1, f'{category.name} · {len(athletes)}')
        separator.font = Font(name="Arial", size=10, bold=True, color=DARK_BLUE)
        separator.alignment = Alignment(
            horizontal="left", vertical="center", indent=1,
        )

        ws.row_dimensions[row].height = 24
        row += 1

        if athletes:
            row, number = draw_athlete_rows(
                ws, row, columns, category, athletes, lookups, number,
            )
        else:
            draw_message_row(
                ws, row, last_col, 'Нет зарегистрированных спортсменов',
            )
            row += 1

    draw_signatures(ws, row + 2, last_col)
    finish_sheet(ws, HEADER_ROW)

# =========================================================
# ОБЩИЕ ФУНКЦИИ
# =========================================================

def athlete_name(athlete):
    if not athlete:
        return ''

    parts = [
        getattr(athlete, 'last_name', ''),
        getattr(athlete, 'first_name', ''),
        getattr(athlete, 'middle_name', ''),
    ]

    return ' '.join(
        str(part).strip()
        for part in parts
        if part
    )


def get_tournament_info(db, tournament_id, date_override, place_override):
    """
    Дата и место берутся из параметров запроса (?date=...&place=...),
    а если их нет — из модели турнира (поля подбираются по имени).
    """
    date_value = date_override
    place_value = place_override

    if date_value and place_value:
        return date_value, place_value

    Tournament = getattr(tournament_models, "Tournament", None)

    if Tournament is None:
        return date_value or "", place_value or ""

    try:
        query = db.query(Tournament)
        tournament = (
            query.filter(Tournament.id == tournament_id).first()
            or query.first()
        )
    except Exception:
        tournament = None

    if tournament is None:
        return date_value or "", place_value or ""

    def first_attr(names):
        for attr in names:
            value = getattr(tournament, attr, None)
            if value:
                return value
        return None

    if not date_value:
        raw_date = first_attr(
            ("date", "start_date", "event_date", "tournament_date")
        )
        if hasattr(raw_date, "strftime"):
            raw_date = raw_date.strftime("%d.%m.%Y")
        date_value = str(raw_date) if raw_date else ""

    if not place_value:
        raw_place = first_attr(
            ("place", "location", "venue", "city", "address")
        )
        place_value = str(raw_place) if raw_place else ""

    return date_value, place_value


# =========================================================
# СБОР ПРИЗЁРОВ
# =========================================================
# Призёр — словарь {'place': int, 'name': str, 'clubs': [str, ...]}

class ResultsCollector:
    def __init__(self, db):
        self.db = db
        self._clubs = {}
        self._kumite_athletes = {}

    # ---------- общие ----------

    def club_name(self, club_id):
        if not club_id:
            return ''

        if club_id not in self._clubs:
            club = self.db.query(Club).filter(Club.id == club_id).first()
            self._clubs[club_id] = club.name if club else ''

        return self._clubs[club_id]

    def athlete_club(self, athlete):
        return self.club_name(getattr(athlete, 'club_id', None))

    # ---------- кумите ----------

    def kumite_athlete(self, athlete_id):
        """(ФИО, [клуб]) спортсмена кумите."""
        if not athlete_id:
            return None

        if athlete_id not in self._kumite_athletes:
            athlete = (
                self.db.query(Athlete)
                .filter(Athlete.id == athlete_id)
                .first()
            )

            if not athlete:
                self._kumite_athletes[athlete_id] = None
            else:
                club = self.athlete_club(athlete)

                self._kumite_athletes[athlete_id] = (
                    format_athlete_name(athlete) or '',
                    [club] if club else [],
                )

        return self._kumite_athletes[athlete_id]

    def kumite_podium(self, category):
        """Призёры категории кумите или None, если сетки нет."""
        matches = (
            self.db.query(KumiteDrawMatch)
            .filter(KumiteDrawMatch.category_id == category.id)
            .order_by(
                KumiteDrawMatch.round_number,
                KumiteDrawMatch.match_number,
            )
            .all()
        )

        if not matches:
            return None

        max_round = max(m.round_number for m in matches)

        by_round = {}

        for match in matches:
            by_round.setdefault(match.round_number, []).append(match)

        for round_matches in by_round.values():
            round_matches.sort(key=lambda m: m.match_number)

        podium = []

        def add(place, athlete_id):
            info = self.kumite_athlete(athlete_id)

            if info:
                podium.append({
                    'place': place,
                    'name': info[0],
                    'clubs': info[1],
                })

        final = by_round[max_round][0]

        if final.winner_athlete_id:
            add(1, final.winner_athlete_id)
            add(2, get_loser(final))

        # 3 место — победитель боя за бронзу
        semifinals = sorted(
            by_round.get(max_round - 1, []),
            key=lambda m: m.match_number,
        )

        if max_round >= 2 and len(semifinals) >= 2:
            loser1 = get_loser(semifinals[0])
            loser2 = get_loser(semifinals[1])

            bronze = (
                self.db.query(BronzeMatchResult)
                .filter(BronzeMatchResult.category_id == category.id)
                .first()
            )

            if (
                bronze
                and bronze.winner_athlete_id
                and bronze.athlete1_id == loser1
                and bronze.athlete2_id == loser2
            ):
                add(3, bronze.winner_athlete_id)

        return podium

    # ---------- ката ----------

    def kata_participant(self, participant):
        """(ФИО, [клубы]) участника ката: спортсмена или группы."""
        if participant.athlete_id:
            athlete = (
                self.db.query(Athlete)
                .filter(Athlete.id == participant.athlete_id)
                .first()
            )

            club = self.athlete_club(athlete) if athlete else ''

            return athlete_name(athlete), [club] if club else []

        if participant.kata_group_id:
            group = (
                self.db.query(KataGroup)
                .filter(KataGroup.id == participant.kata_group_id)
                .first()
            )

            members = (
                self.db.query(Athlete)
                .join(
                    KataGroupAthlete,
                    KataGroupAthlete.athlete_id == Athlete.id
                )
                .filter(
                    KataGroupAthlete.kata_group_id
                    == participant.kata_group_id
                )
                .all()
            )

            clubs = []

            for member in members:
                club = self.athlete_club(member)

                if club and club not in clubs:
                    clubs.append(club)

            if not group:
                name = f'Ката-группа {participant.kata_group_id}'
            else:
                name = (
                    getattr(group, 'name', None)
                    or ', '.join(athlete_name(a) for a in members)
                )

            return name, clubs

        return '', []

    def kata_podium(self, category):
        """Призёры категории ката или None, если соревнования нет."""
        competition = (
            self.db.query(KataCompetition)
            .filter(KataCompetition.category_id == category.id)
            .first()
        )

        if not competition:
            return None

        rounds = (
            self.db.query(KataRound)
            .filter(KataRound.competition_id == competition.id)
            .order_by(KataRound.number, KataRound.id)
            .all()
        )

        if not rounds:
            return []

        participants = (
            self.db.query(KataRoundParticipant)
            .filter(KataRoundParticipant.round_id == rounds[-1].id)
            .order_by(KataRoundParticipant.position, KataRoundParticipant.id)
            .all()
        )

        podium = []

        for participant in participants:
            place = participant.position
            print(place)
            print(PODIUM_PLACES)
            if place not in range(1, PODIUM_PLACES + 1):
                continue

            # Место засчитывается, только если участник оценён
            score = (
                self.db.query(KataScore)
                .filter(KataScore.round_participant_id == participant.id)
                .first()
            )

            total = (
                score.total_score
                if score is not None and score.total_score is not None
                else participant.total_score
            )

            if total is None:
                continue

            name, clubs = self.kata_participant(participant)

            podium.append({'place': place, 'name': name, 'clubs': clubs})

        return podium


# =========================================================
# ОТРИСОВКА
# =========================================================

def merge_row(ws, row, c1, c2):
    if c2 > c1:
        ws.merge_cells(
            start_row=row, start_column=c1,
            end_row=row, end_column=c2,
        )


def style_cell(cell, fill=None, font=None, alignment=None):
    if fill is not None:
        cell.fill = fill
    if font is not None:
        cell.font = font
    cell.alignment = alignment or center
    cell.border = cell_border


def draw_sheet_top(ws, last_col, title_text, subtitle, date_text, place_text):
    """Название, место/дата и подзаголовок."""

    merge_row(ws, 1, 1, last_col)

    title = ws.cell(1, 1, title_text)
    title.fill = title_fill
    title.font = Font(name="Arial", size=18, bold=True, color=WHITE)
    title.alignment = center
    title.border = Border(bottom=medium_blue)

    ws.row_dimensions[1].height = 40

    info_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)
    split_col = (last_col + 1) // 2

    merge_row(ws, 2, 1, split_col)
    merge_row(ws, 2, split_col + 1, last_col)

    place_cell = ws.cell(
        2, 1, f"Место проведения: {place_text or '______________________'}",
    )
    place_cell.font = info_font
    place_cell.alignment = Alignment(
        horizontal="left", vertical="center", indent=1,
    )

    date_cell = ws.cell(
        2, split_col + 1, f"Дата: {date_text or '______________'}",
    )
    date_cell.font = info_font
    date_cell.alignment = Alignment(
        horizontal="right", vertical="center", indent=1,
    )

    ws.row_dimensions[2].height = 26

    merge_row(ws, 3, 1, last_col)

    sub = ws.cell(3, 1, subtitle)
    sub.font = Font(name="Arial", size=10, italic=True, color=GRAY_TEXT)
    sub.alignment = center

    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 12


def draw_header_row(ws, row, headers, fills=None):
    """headers — список (текст, ширина); fills — {индекс: (fill, цвет текста)}."""
    fills = fills or {}

    for col, (text, width) in enumerate(headers, start=1):
        fill, color = fills.get(col, (header_fill, WHITE))

        cell = ws.cell(row, col, text)
        style_cell(
            cell,
            fill=fill,
            font=Font(name="Arial", size=10, bold=True, color=color),
        )

        ws.column_dimensions[get_column_letter(col)].width = width

    ws.row_dimensions[row].height = 28


def draw_message_row(ws, row, last_col, text):
    merge_row(ws, row, 1, last_col)

    for c in range(1, last_col + 1):
        ws.cell(row, c).border = cell_border

    cell = ws.cell(row, 1, text)
    cell.font = Font(name="Arial", size=11, italic=True, color=GRAY_TEXT)
    cell.alignment = center

    ws.row_dimensions[row].height = 28


def draw_signatures(ws, start_row, label_cols, sign_cols, fio_cols):
    """Подписи главного судьи и главного секретаря."""

    caption_font = Font(name="Arial", size=8, color=GRAY_TEXT)
    sign_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)

    row = start_row

    for title in ("Главный судья", "Главный секретарь"):
        ws.row_dimensions[row].height = 30
        ws.row_dimensions[row + 1].height = 14

        merge_row(ws, row, *label_cols)
        label = ws.cell(row, label_cols[0], title)
        label.font = sign_font
        label.alignment = Alignment(
            horizontal="left", vertical="bottom", indent=1,
        )

        for (c1, c2), caption in ((sign_cols, "подпись"), (fio_cols, "ФИО")):
            merge_row(ws, row, c1, c2)

            for c in range(c1, c2 + 1):
                ws.cell(row, c).border = Border(bottom=sign_line)

            merge_row(ws, row + 1, c1, c2)
            cap = ws.cell(row + 1, c1, caption)
            cap.font = caption_font
            cap.alignment = center

        row += 3


def finish_sheet(ws, header_row):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90

    ws.freeze_panes = f"A{header_row + 1}"
    ws.print_title_rows = f"1:{header_row}"

    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.page_margins.left = 0.4
    ws.page_margins.right = 0.4
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


HEADER_ROW = 5


# ---------------------------------------------------------
# Лист 1: призёры по категориям
# ---------------------------------------------------------

def create_results_sheet(wb, results, date_text, place_text):
    ws = wb.create_sheet("Результаты")

    headers = [
        ("КАТЕГОРИЯ", 36),
        ("МЕСТО", 10),
        ("ПРИЗЁР", 34),
        ("КЛУБ", 30),
    ]
    last_col = len(headers)

    prize_count = sum(
        len(podium) for _, podium in results
    )

    draw_sheet_top(
        ws,
        last_col,
        "ИТОГОВЫЕ РЕЗУЛЬТАТЫ",
        f"Категорий: {len(results)} · призёров: {prize_count}",
        date_text,
        place_text,
    )

    draw_header_row(ws, HEADER_ROW, headers)

    row = HEADER_ROW + 1

    category_font = Font(name="Arial", size=10, bold=True, color=DARK_BLUE)
    name_font = Font(name="Arial", size=10, bold=True, color=DARK_BLUE)
    club_font = Font(name="Arial", size=9, color=DARK_BLUE)
    empty_font = Font(name="Arial", size=10, color=GRAY_TEXT)

    if not results:
        draw_message_row(ws, row, last_col, "Нет категорий с результатами")
        row += 1

    for category, podium in results:
        by_place = {}

        for prize in podium:
            by_place.setdefault(prize['place'], []).append(prize)

        category_start = row

        for place in range(1, PODIUM_PLACES + 1):
            # Несколько призёров на одном месте — несколько строк
            for prize in by_place.get(place) or [None]:
                style_cell(
                    ws.cell(row, 2, place),
                    fill=PLACE_FILLS[place],
                    font=Font(
                        name="Arial", size=11, bold=True,
                        color=PLACE_TEXT[place],
                    ),
                )

                style_cell(
                    ws.cell(row, 3, prize['name'] if prize else '—'),
                    font=name_font if prize else empty_font,
                    alignment=left_center,
                )

                club_text = ', '.join(prize['clubs']) if prize else ''

                style_cell(
                    ws.cell(row, 4, club_text),
                    font=club_font,
                    alignment=left_center,
                )

                ws.row_dimensions[row].height = 22
                row += 1

        # Категория — одна ячейка на все строки призёров
        merge_row_range(ws, category_start, row - 1, 1)

        for r in range(category_start, row):
            ws.cell(r, 1).border = cell_border
            ws.cell(r, 1).fill = gray_fill

        cat_cell = ws.cell(category_start, 1, category.name)
        cat_cell.font = category_font
        cat_cell.alignment = left_wrap

    draw_signatures(ws, row + 2, (1, 1), (2, 3), (4, 4))
    finish_sheet(ws, HEADER_ROW)


def merge_row_range(ws, row_start, row_end, col):
    """Вертикальное объединение ячеек одной колонки."""
    if row_end > row_start:
        ws.merge_cells(
            start_row=row_start, start_column=col,
            end_row=row_end, end_column=col,
        )


# ---------------------------------------------------------
# Лист 2: зачёт клубов
# ---------------------------------------------------------

def count_club_medals(results):
    """{клуб: [золото, серебро, бронза]}."""
    medals = {}

    for _, podium in results:
        for prize in podium:
            # Командный результат засчитывается каждому клубу участников
            clubs = prize['clubs'] or '-'

            for club in clubs:
                counts = medals.setdefault(club, [0, 0, 0])
                counts[prize['place'] - 1] += 1

    return medals


def create_clubs_sheet(wb, results, date_text, place_text):
    ws = wb.create_sheet("Зачёт клубов")

    medals = count_club_medals(results)

    ordered = sorted(
        medals.items(),
        key=lambda item: (
            -item[1][0], -item[1][1], -item[1][2], item[0].lower(),
        ),
    )

    headers = [
        ("№", 7),
        ("КЛУБ", 42),
        ("1 МЕСТО", 12),
        ("2 МЕСТО", 12),
        ("3 МЕСТО", 12),
        ("ВСЕГО", 12),
    ]
    last_col = len(headers)

    total_prizes = sum(sum(counts) for _, counts in ordered)

    draw_sheet_top(
        ws,
        last_col,
        "ЗАЧЁТ КЛУБОВ",
        f"Клубов: {len(ordered)} · всего призовых мест: {total_prizes}",
        date_text,
        place_text,
    )

    draw_header_row(
        ws,
        HEADER_ROW,
        headers,
        fills={
            3: (gold_fill, GOLD_TEXT),
            4: (silver_fill, DARK_BLUE),
            5: (bronze_fill, BRONZE_TEXT),
        },
    )

    row = HEADER_ROW + 1

    base_font = Font(name="Arial", size=10, color=DARK_BLUE)
    bold_font = Font(name="Arial", size=10, bold=True, color=DARK_BLUE)

    if not ordered:
        draw_message_row(ws, row, last_col, "Призёров пока нет")
        row += 1

    # Места клубов: при равенстве всех медалей место общее
    rank = 0
    previous = None

    for index, (club, counts) in enumerate(ordered, start=1):
        if counts != previous:
            rank = index
            previous = counts

        gold, silver, bronze = counts

        style_cell(ws.cell(row, 1, rank), font=bold_font)
        style_cell(ws.cell(row, 2, club), font=bold_font, alignment=left_center)

        for col, value, fill in (
            (3, gold, gold_fill),
            (4, silver, silver_fill),
            (5, bronze, bronze_fill),
        ):
            style_cell(
                ws.cell(row, col, value or ''),
                fill=fill if value else None,
                font=base_font,
            )

        style_cell(
            ws.cell(row, 6, gold + silver + bronze),
            fill=gray_fill,
            font=bold_font,
        )

        ws.row_dimensions[row].height = 22
        row += 1

    # Итого
    if ordered:
        totals = [sum(counts[i] for _, counts in ordered) for i in range(3)]

        merge_row(ws, row, 1, 2)

        for c in range(1, last_col + 1):
            style_cell(ws.cell(row, c), fill=header_fill)

        total_font = Font(name="Arial", size=10, bold=True, color=WHITE)

        ws.cell(row, 1, "ИТОГО").font = total_font

        for col, value in zip((3, 4, 5, 6), (*totals, sum(totals))):
            ws.cell(row, col, value).font = total_font

        ws.row_dimensions[row].height = 24
        row += 1

    draw_signatures(ws, row + 2, (1, 2), (3, 4), (5, 6))
    finish_sheet(ws, HEADER_ROW)


# =========================================================
# ENDPOINT ЭКСПОРТА
# =========================================================

@router.get("/results")
def export_results(
    tournament_id: int,
    date: Optional[str] = Query(None, description="Дата турнира (необязательно)"),
    place: Optional[str] = Query(None, description="Место проведения (необязательно)"),
    db: Session = Depends(get_tournament_db),
):
    categories = (
        db.query(Category)
        .order_by(Category.name)
        .all()
    )

    if not categories:
        raise HTTPException(
            status_code=404,
            detail='Категории не найдены'
        )

    date_text, place_text = get_tournament_info(
        db, tournament_id, date, place,
    )

    collector = ResultsCollector(db)

    # (категория, список призёров) — только категории с кумите-сеткой
    # или соревнованием по ката
    results = []

    for category in categories:
        podium = collector.kumite_podium(category)

        if podium is None:
            podium = collector.kata_podium(category)

        if podium is None:
            continue

        results.append((category, podium))

    wb = Workbook()
    wb.remove(wb.active)

    create_results_sheet(wb, results, date_text, place_text)
    create_clubs_sheet(wb, results, date_text, place_text)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        ),
        headers={
            'Content-Disposition':
                'attachment; filename="tournament_results.xlsx"'
        }
    )
# =========================================================
# ENDPOINT ЭКСПОРТА
# =========================================================

@router.get("/categories")
def export_categories_athletes(
    tournament_id: int,
    group_by: str = Query(
        "category",
        description="category — лист на категорию, type — лист на вид (кумите/ката/ката-группа)",
    ),
    date: Optional[str] = Query(None, description="Дата турнира (необязательно)"),
    place: Optional[str] = Query(None, description="Место проведения (необязательно)"),
    db: Session = Depends(get_tournament_db),
):
    if group_by not in ("category", "type"):
        raise HTTPException(
            status_code=400,
            detail="group_by должен быть 'category' или 'type'",
        )

    categories = (
        db.query(Category)
        .order_by(Category.name)
        .all()
    )

    if not categories:
        raise HTTPException(
            status_code=404,
            detail='Категории не найдены'
        )

    date_text, place_text = get_tournament_info(
        db, tournament_id, date, place,
    )

    lookups = Lookups(db)

    wb = Workbook()
    wb.remove(wb.active)

    used_titles = set()

    if group_by == "category":
        for category in categories:
            create_category_sheet(
                wb, db, category, used_titles, lookups,
                date_text, place_text,
            )
    else:
        grouped = {}

        for category in categories:
            grouped.setdefault(get_category_type(category), []).append(category)

        for type_name in TYPE_ORDER:
            if type_name in grouped:
                create_type_sheet(
                    wb, db, type_name, grouped[type_name], used_titles,
                    lookups, date_text, place_text,
                )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        ),
        headers={
            'Content-Disposition':
                'attachment; filename="categories_athletes.xlsx"'
        }
    )


@router.get('/kata')
def export_kata(
    tournament_id: int,
    date: Optional[str] = Query(None, description="Дата турнира (необязательно)"),
    place: Optional[str] = Query(None, description="Место проведения (необязательно)"),
    db: Session = Depends(get_tournament_db),
):
    categories = (
        db.query(Category)
        .join(
            KataCompetition,
            KataCompetition.category_id == Category.id
        )
        .order_by(Category.name)
        .all()
    )

    if not categories:
        raise HTTPException(
            status_code=404,
            detail='Нет категорий с соревнованиями по ката'
        )

    wb = Workbook()
    wb.remove(wb.active)

    used_titles = set()

    for category in categories:
        create_category_sheet(
            wb,
            db,
            category,
            used_titles,
            tournament_id,
            date,
            place,
        )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        ),
        headers={
            'Content-Disposition':
                'attachment; filename="kata_results.xlsx"'
        }
    )

@router.get("/kumite")
def export_kumite_draw(
    tournament_id: int,
    date: Optional[str] = Query(None, description="Дата турнира (необязательно)"),
    place: Optional[str] = Query(None, description="Место проведения (необязательно)"),
    db: Session = Depends(get_tournament_db),
):
    wb = Workbook()
    wb.remove(wb.active)

    # =====================================================
    # ЦВЕТА И СТИЛИ
    # =====================================================

    DARK_BLUE = "17365D"
    HEADER_BLUE = "24476B"
    LIGHT_GRAY = "F4F6F8"
    BORDER_COLOR = "C5CED8"
    GREEN_FILL = "D9EAD3"
    GREEN_TEXT = "274E13"
    GREEN_LINE = "228B22"
    GRAY_LINE = "AAB4BE"
    GRAY_TEXT = "7A8794"
    BRONZE_COLOR = "FCE4D6"
    BRONZE_TEXT = "7F4120"
    GOLD_COLOR = "FFF2CC"
    GOLD_TEXT = "7F6000"
    WHITE = "FFFFFF"

    thin = Side(style="thin", color=BORDER_COLOR)
    medium_blue = Side(style="medium", color=DARK_BLUE)
    green_side = Side(style="medium", color=GREEN_LINE)
    gray_side = Side(style="medium", color=GRAY_LINE)

    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

    # В карточках длинные имена сжимаются, а не растягивают строку
    card_align = Alignment(
        horizontal="center",
        vertical="center",
        shrink_to_fit=True,
    )

    title_fill = PatternFill("solid", fgColor=DARK_BLUE)
    header_fill = PatternFill("solid", fgColor=HEADER_BLUE)
    athlete_fill = PatternFill("solid", fgColor=LIGHT_GRAY)
    winner_fill = PatternFill("solid", fgColor=GREEN_FILL)
    bronze_fill = PatternFill("solid", fgColor=BRONZE_COLOR)
    gold_fill = PatternFill("solid", fgColor=GOLD_COLOR)

    number_fill = PatternFill("solid", fgColor="E4EAF1")

    athlete_cache = {}
    club_cache = {}

    # Номер спортсмена в жеребьёвке (заполняется для каждой категории)
    draw_position_by_athlete = {}

    # =====================================================
    # ДАННЫЕ СПОРТСМЕНА
    # =====================================================

    def get_athlete_data(athlete_id):
        if not athlete_id:
            return "", ""

        if athlete_id not in athlete_cache:
            athlete = (
                db.query(Athlete)
                .filter(Athlete.id == athlete_id)
                .first()
            )

            if not athlete:
                athlete_cache[athlete_id] = ("", "")
            else:
                name = format_athlete_name(athlete) or ""
                club_name = ""

                if athlete.club_id:
                    if athlete.club_id not in club_cache:
                        club = (
                            db.query(Club)
                            .filter(Club.id == athlete.club_id)
                            .first()
                        )
                        club_cache[athlete.club_id] = (
                            club.name if club else ""
                        )

                    club_name = club_cache[athlete.club_id] or ""

                athlete_cache[athlete_id] = (name, club_name)

        return athlete_cache[athlete_id]

    # =====================================================
    # ДАТА И МЕСТО ТУРНИРА
    # =====================================================

    def get_tournament_info(date_override, place_override):
        """
        Дата и место берутся из параметров запроса (?date=...&place=...),
        а если их нет — из модели турнира (поля подбираются по имени).
        """
        date_value = date_override
        place_value = place_override

        if date_value and place_value:
            return date_value, place_value

        Tournament = getattr(tournament_models, "Tournament", None)

        if Tournament is None:
            return date_value or "", place_value or ""

        try:
            query = db.query(Tournament)
            tournament = (
                query.filter(Tournament.id == tournament_id).first()
                or query.first()
            )
        except Exception:
            tournament = None

        if tournament is None:
            return date_value or "", place_value or ""

        def first_attr(names):
            for attr in names:
                value = getattr(tournament, attr, None)
                if value:
                    return value
            return None

        if not date_value:
            raw_date = first_attr(
                ("date", "start_date", "event_date", "tournament_date")
            )
            if hasattr(raw_date, "strftime"):
                raw_date = raw_date.strftime("%d.%m.%Y")
            date_value = str(raw_date) if raw_date else ""

        if not place_value:
            raw_place = first_attr(
                ("place", "location", "venue", "city", "address")
            )
            place_value = str(raw_place) if raw_place else ""

        return date_value, place_value

    # =====================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # =====================================================

    def make_sheet_title(name, used):
        name = re.sub(r'[\\/*?:\[\]]', "_", name or "Категория")
        name = name[:31] or "Категория"

        base = name
        index = 1

        while name in used:
            suffix = f"_{index}"
            name = base[:31 - len(suffix)] + suffix
            index += 1

        used.add(name)
        return name

    def round_name(number, max_round):
        names = {
            max_round: "ФИНАЛ",
            max_round - 1: "ПОЛУФИНАЛ",
            max_round - 2: "1/4 ФИНАЛА",
            max_round - 3: "1/8 ФИНАЛА",
            max_round - 4: "1/16 ФИНАЛА",
            max_round - 5: "1/32 ФИНАЛА",
        }
        return names.get(number, f"РАУНД {number}")

    # На каждый раунд 5 колонок:
    #   col - 1 — номер спортсмена
    #   col     — карточки спортсменов (имя / клуб)
    #   col + 1 — «усики» от карточек
    #   col + 2 — вертикаль схождения и выход победителя
    #   col + 3 — вертикаль к следующему матчу и вход в его карточку
    # round_col возвращает колонку карточки (col).
    COLS_PER_ROUND = 5

    def round_col(number):
        return 2 + (number - 1) * COLS_PER_ROUND

    def is_bye(match):
        return (
            getattr(match, "match_type", None) == "bye"
            or getattr(match, "status", None) == "bye"
        )

    def set_cell_border(cell, **kwargs):
        current = copy(cell.border)

        for side_name, side_value in kwargs.items():
            setattr(current, side_name, side_value)

        cell.border = current

    def draw_horizontal(ws, row, col, side):
        """Линия по верхней границе строки row в колонке col."""
        set_cell_border(ws.cell(row=row, column=col), top=side)

    def draw_vertical(ws, col, row_start, row_end, side):
        """
        Вертикальная линия по левому краю колонки col
        от верхней границы row_start до верхней границы row_end.
        """
        for row in range(row_start, row_end):
            set_cell_border(ws.cell(row=row, column=col), left=side)

    def draw_athlete_card(
        ws,
        athlete_id,
        first_row,
        col,
        is_winner=False,
        fill=None,
        text_color=None,
    ):
        """
        Карточка спортсмена:
        первая строка — имя, вторая строка — клуб.
        Центр карточки — верхняя граница второй строки.
        """

        name, club = get_athlete_data(athlete_id)
        empty = not athlete_id

        if empty:
            name = "—"

        if fill is None:
            fill = winner_fill if is_winner else athlete_fill

        if text_color is None:
            text_color = GREEN_TEXT if is_winner else DARK_BLUE

        if empty:
            text_color = GRAY_TEXT

        name_cell = ws.cell(first_row, col, name)
        club_cell = ws.cell(first_row + 1, col, club)

        name_cell.font = Font(
            name="Arial",
            size=10,
            bold=is_winner and not empty,
            color=text_color,
        )
        club_cell.font = Font(
            name="Arial",
            size=9,
            italic=True,
            color=GREEN_TEXT if is_winner else GRAY_TEXT,
        )

        for cell in (name_cell, club_cell):
            cell.fill = fill
            cell.border = cell_border
            cell.alignment = card_align

        # Номер спортсмена — слева от карточки, на две строки
        number = draw_position_by_athlete.get(athlete_id, "") if athlete_id else ""

        ws.merge_cells(
            start_row=first_row,
            start_column=col - 1,
            end_row=first_row + 1,
            end_column=col - 1,
        )

        number_cell = ws.cell(first_row, col - 1, number)
        number_cell.font = Font(
            name="Arial",
            size=11,
            bold=True,
            color=text_color,
        )

        num_fill = fill if fill is not athlete_fill else number_fill

        for row in (first_row, first_row + 1):
            cell = ws.cell(row, col - 1)
            cell.fill = num_fill
            cell.border = cell_border
            cell.alignment = center

    def draw_span_header(ws, row, c1, c2, text, fill, font_color, size=10):
        """Заголовок, объединённый по колонкам c1..c2."""
        if c2 > c1:
            ws.merge_cells(
                start_row=row, start_column=c1,
                end_row=row, end_column=c2,
            )

        for c in range(c1, c2 + 1):
            cell = ws.cell(row, c)
            cell.fill = fill
            cell.border = cell_border

        first = ws.cell(row, c1, text)
        first.font = Font(name="Arial", size=size, bold=True, color=font_color)
        first.alignment = center

    def draw_bout_label(ws, row, col, number):
        cell = ws.cell(row, col, f"БОЙ № {number}")
        cell.font = Font(name="Arial", size=8, bold=True, color="5B7083")
        cell.alignment = Alignment(horizontal="left", vertical="center")

    def draw_simple_header(ws, row, col, text, fill, font_color, size=12):
        cell = ws.cell(row, col, text)
        cell.fill = fill
        cell.font = Font(name="Arial", size=size, bold=True, color=font_color)
        cell.alignment = center
        cell.border = cell_border

    def draw_match_lines(ws, J, col, athlete1_id, athlete2_id, winner_id):
        """
        Линии одного боя. J — строка точки схождения.
        Карточка 1: строки J-2, J-1 (центр — верх строки J-1).
        Карточка 2: строки J, J+1 (центр — верх строки J+1).
        Возвращает сторону линии выхода победителя.
        """

        def side_for(athlete_id):
            if athlete_id and winner_id == athlete_id:
                return green_side
            return gray_side

        side1 = side_for(athlete1_id)
        side2 = side_for(athlete2_id)

        stub_col = col + 1   # «усики» от карточек
        join_col = col + 2   # вертикаль схождения и выход победителя

        # Линии из середины карточек (граница «имя / клуб»)
        draw_horizontal(ws, J - 1, stub_col, side1)
        draw_horizontal(ws, J + 1, stub_col, side2)

        # Вертикаль, соединяющая соперников
        draw_vertical(ws, join_col, J - 1, J, side1)
        draw_vertical(ws, join_col, J, J + 1, side2)

        # Выход победителя из точки схождения
        out_side = green_side if winner_id else gray_side
        draw_horizontal(ws, J, join_col, out_side)

        return out_side

    # =====================================================
    # КАТЕГОРИИ
    # =====================================================

    used_sheet_names = set()

    categories = (
        db.query(Category)
        .order_by(Category.name)
        .all()
    )

    for category in categories:
        matches = category_matches(db, category.id)

        if not matches:
            continue

        matches.sort(key=lambda m: (m.round_number, m.match_number))

        max_round = max(m.round_number for m in matches)

        matches_by_round = {}

        for match in matches:
            matches_by_round.setdefault(match.round_number, []).append(match)

        for round_matches in matches_by_round.values():
            round_matches.sort(key=lambda m: m.match_number)

        # Позиции жеребьёвки
        entries = (
            db.query(KumiteDrawEntry)
            .filter(KumiteDrawEntry.category_id == category.id)
            .order_by(KumiteDrawEntry.draw_position)
            .all()
        )

        positions = {
            entry.athlete_id: entry.draw_position
            for entry in entries
        }

        draw_position_by_athlete.clear()
        draw_position_by_athlete.update(positions)

        first_round = matches_by_round.get(1, [])

        # Первый раунд сортируется по исходной позиции жеребьёвки
        first_round.sort(
            key=lambda match: min(
                positions.get(match.athlete1_id, 10**9),
                positions.get(match.athlete2_id, 10**9),
            )
        )

        ws = wb.create_sheet(
            make_sheet_title(category.name, used_sheet_names)
        )

        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 80

        # Последняя колонка — колонка чемпиона (после финала)
        champion_col = round_col(max_round + 1)

        # Таблица итогов и подписи занимают 3 блока по 5 колонок,
        # поэтому лист не уже трёх раундов.
        BLOCK = COLS_PER_ROUND
        last_col = max(champion_col, BLOCK * 3)

        # =================================================
        # ЗАГОЛОВОК
        # =================================================

        ws.merge_cells(
            start_row=1,
            start_column=1,
            end_row=1,
            end_column=last_col,
        )

        title = ws.cell(1, 1, category.name)
        title.fill = title_fill
        title.font = Font(name="Arial", size=18, bold=True, color=WHITE)
        title.alignment = center
        title.border = Border(bottom=medium_blue)

        ws.row_dimensions[1].height = 40

        # =================================================
        # ДАТА И МЕСТО
        # =================================================

        date_text, place_text = get_tournament_info(date, place)

        info_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)
        split_col = BLOCK * 2

        ws.merge_cells(
            start_row=2, start_column=1, end_row=2, end_column=split_col,
        )
        ws.merge_cells(
            start_row=2, start_column=split_col + 1,
            end_row=2, end_column=last_col,
        )

        place_cell = ws.cell(
            2, 1, f"Место проведения: {place_text or '______________________'}",
        )
        place_cell.font = info_font
        place_cell.alignment = Alignment(
            horizontal="left", vertical="center", indent=1,
        )

        date_cell = ws.cell(
            2, split_col + 1, f"Дата: {date_text or '______________'}",
        )
        date_cell.font = info_font
        date_cell.alignment = Alignment(
            horizontal="right", vertical="center", indent=1,
        )

        ws.row_dimensions[2].height = 26

        # =================================================
        # ЗАГОЛОВКИ РАУНДОВ
        # =================================================

        for number in range(1, max_round + 1):
            col = round_col(number)

            draw_span_header(
                ws, 3, col - 1, col + 3,
                round_name(number, max_round),
                header_fill, WHITE,
            )

        # Колонка чемпиона (номер + карточка)
        draw_span_header(
            ws, 3, champion_col - 1, champion_col, "ЧЕМПИОН",
            header_fill, WHITE,
        )

        # Ширина колонок для всех блоков (включая блоки под таблицу
        # итогов, если сетка маленькая)
        for number in range(1, max(max_round + 1, 3) + 1):
            col = round_col(number)
            ws.column_dimensions[get_column_letter(col - 1)].width = 5
            ws.column_dimensions[get_column_letter(col)].width = 30
            for offset in (1, 2, 3):
                ws.column_dimensions[
                    get_column_letter(col + offset)
                ].width = 3.5

        ws.row_dimensions[3].height = 30
        ws.row_dimensions[4].height = 12

        # =================================================
        # РАССТАНОВКА БОЁВ
        # =================================================
        #
        # Для каждого боя задаётся строка J — точка схождения линий:
        #
        #   J-2  имя 1
        #   J-1  клуб 1     <- линия карточки 1 (верхняя граница этой строки)
        #   J    имя 2      <- выход победителя (верхняя граница этой строки)
        #   J+1  клуб 2     <- линия карточки 2 (верхняя граница этой строки)
        #
        # Карточки соперников стоят вплотную, J — ровно посередине
        # между линиями двух карточек. Каждый бой следующего раунда
        # стоит посередине между двумя боями предыдущего раунда.

        FIRST_JUNCTION = 8  # J-3 = 5 (строка номера боя), J-2 = 6
        SPACING = 6         # 4 строки на бой + 2 строки зазора между боями

        junction_by_match = {}

        for index, match in enumerate(first_round):
            junction_by_match[match.id] = FIRST_JUNCTION + index * SPACING

        for number in range(2, max_round + 1):
            previous = matches_by_round.get(number - 1, [])
            current = matches_by_round.get(number, [])

            for index, match in enumerate(current):
                left_index = index * 2
                right_index = left_index + 1

                if right_index < len(previous):
                    junction_by_match[match.id] = (
                        junction_by_match[previous[left_index].id]
                        + junction_by_match[previous[right_index].id]
                    ) // 2

                elif left_index < len(previous):
                    junction_by_match[match.id] = (
                        junction_by_match[previous[left_index].id]
                    )

                else:
                    junction_by_match[match.id] = (
                        FIRST_JUNCTION
                        + index * SPACING * (2 ** (number - 1))
                    )

        # =================================================
        # НОМЕРА БОЁВ
        # =================================================
        # Сквозная нумерация: сначала все бои до финала, затем бой
        # за 3 место, финал — последний.

        semifinals_for_bronze = matches_by_round.get(max_round - 1, [])
        has_bronze = max_round >= 2 and len(semifinals_for_bronze) >= 2

        bout_number = {}
        counter = 0

        for number in range(1, max_round):
            for m in matches_by_round.get(number, []):
                if not is_bye(m):
                    counter += 1
                    bout_number[m.id] = counter

        bronze_bout_number = None

        if has_bronze:
            counter += 1
            bronze_bout_number = counter

        for m in matches_by_round.get(max_round, []):
            if not is_bye(m):
                counter += 1
                bout_number[m.id] = counter

        # =================================================
        # КАРТОЧКИ СПОРТСМЕНОВ
        # =================================================

        for match in matches:
            if is_bye(match):
                # BYE не отображаем, но его место в сетке остаётся.
                continue

            junction = junction_by_match[match.id]
            col = round_col(match.round_number)

            draw_bout_label(
                ws, junction - 3, col, bout_number[match.id],
            )

            draw_athlete_card(
                ws,
                match.athlete1_id,
                junction - 2,
                col,
                is_winner=(
                    match.athlete1_id is not None
                    and match.winner_athlete_id == match.athlete1_id
                ),
            )
            draw_athlete_card(
                ws,
                match.athlete2_id,
                junction,
                col,
                is_winner=(
                    match.athlete2_id is not None
                    and match.winner_athlete_id == match.athlete2_id
                ),
            )

        # =================================================
        # ЛИНИИ
        # =================================================

        for number in range(1, max_round + 1):
            current = matches_by_round.get(number, [])
            following = matches_by_round.get(number + 1, [])

            col = round_col(number)
            link_col = col + 3   # путь к следующему матчу

            for index, match in enumerate(current):
                if is_bye(match):
                    continue

                J = junction_by_match[match.id]

                out_side = draw_match_lines(
                    ws,
                    J,
                    col,
                    match.athlete1_id,
                    match.athlete2_id,
                    match.winner_athlete_id,
                )

                # Финал: линия идёт к карточке чемпиона
                if number == max_round:
                    draw_horizontal(ws, J, link_col, out_side)
                    continue

                # Путь к карточке в следующем бое
                next_index = index // 2

                if next_index >= len(following):
                    continue

                next_match = following[next_index]
                next_J = junction_by_match[next_match.id]

                # верхний бой пары -> слот 1, нижний -> слот 2
                dest_row = next_J - 1 if index % 2 == 0 else next_J + 1

                if dest_row > J:
                    draw_vertical(ws, link_col, J, dest_row, out_side)
                elif dest_row < J:
                    draw_vertical(ws, link_col, dest_row, J, out_side)

                # Вход в карточку следующего боя (в её середину)
                draw_horizontal(ws, dest_row, link_col, out_side)

        # =================================================
        # ЧЕМПИОН
        # =================================================

        final_matches = matches_by_round.get(max_round, [])

        champion_id = None
        runner_up_id = None
        bronze_shown = False
        bronze_winner_id = None
        bronze_loser_id = None

        if final_matches:
            final_match = final_matches[0]
            final_J = junction_by_match[final_match.id]
            champion_id = final_match.winner_athlete_id
            runner_up_id = get_loser(final_match) if champion_id else None

            draw_athlete_card(
                ws,
                champion_id,
                final_J - 1,
                champion_col,
                is_winner=champion_id is not None,
                fill=gold_fill if champion_id else athlete_fill,
                text_color=GOLD_TEXT if champion_id else None,
            )

        # =================================================
        # БОЙ ЗА 3 МЕСТО (только чтение, в БД ничего не пишем)
        # =================================================

        semifinal_round = max_round - 1
        semifinals = matches_by_round.get(semifinal_round, [])

        if max_round >= 2 and len(semifinals) >= 2:
            semifinals = sorted(semifinals, key=lambda m: m.match_number)

            loser1 = get_loser(semifinals[0])
            loser2 = get_loser(semifinals[1])

            bronze = (
                db.query(BronzeMatchResult)
                .filter(BronzeMatchResult.category_id == category.id)
                .first()
            )

            # Результат бронзового боя учитываем, только если он
            # относится к тем же полуфиналистам.
            bronze_shown = True

            if (
                bronze
                and bronze.athlete1_id == loser1
                and bronze.athlete2_id == loser2
            ):
                bronze_winner_id = bronze.winner_athlete_id

            if bronze_winner_id:
                bronze_loser_id = (
                    loser2 if bronze_winner_id == loser1 else loser1
                )

            # Бронзовый бой рисуется под финалом, в тех же колонках,
            # и устроен так же, как обычный бой: линии сходятся
            # и ведут к карточке победителя в колонке чемпиона.
            final_J = junction_by_match[final_matches[0].id]
            bronze_col = round_col(max_round)
            bronze_title_row = final_J + 5
            bronze_J = bronze_title_row + 4

            draw_span_header(
                ws, bronze_title_row, bronze_col - 1, bronze_col,
                "БОЙ ЗА 3 МЕСТО", bronze_fill, BRONZE_TEXT, size=11,
            )
            draw_span_header(
                ws, bronze_title_row, champion_col - 1, champion_col,
                "3 МЕСТО", bronze_fill, BRONZE_TEXT, size=11,
            )

            draw_bout_label(
                ws, bronze_J - 3, bronze_col, bronze_bout_number,
            )

            for athlete_id, top_row in (
                (loser1, bronze_J - 2),
                (loser2, bronze_J),
            ):
                draw_athlete_card(
                    ws,
                    athlete_id,
                    top_row,
                    bronze_col,
                    is_winner=(
                        athlete_id is not None
                        and bronze_winner_id == athlete_id
                    ),
                    fill=bronze_fill,
                )

            out_side = draw_match_lines(
                ws,
                bronze_J,
                bronze_col,
                loser1,
                loser2,
                bronze_winner_id,
            )
            draw_horizontal(ws, bronze_J, bronze_col + 3, out_side)

            # Победитель боя за 3 место
            draw_athlete_card(
                ws,
                bronze_winner_id,
                bronze_J - 1,
                champion_col,
                is_winner=bronze_winner_id is not None,
                fill=bronze_fill if bronze_winner_id else athlete_fill,
                text_color=BRONZE_TEXT if bronze_winner_id else None,
            )

        # =================================================
        # ВЫСОТЫ СТРОК
        # =================================================
        # Одинаковая высота строк — иначе точка схождения
        # визуально «уезжает» от середины между карточками.

        for row in range(5, ws.max_row + 1):
            ws.row_dimensions[row].height = 21

        # =================================================
        # ТАБЛИЦА ИТОГОВ
        # =================================================

        def merged_cell(row, block, value="", fill=None, font=None,
                        align=None, border=None):
            """Ячейка на весь блок из 4 колонок (block = 0, 1, 2)."""
            c1 = 1 + block * BLOCK
            c2 = c1 + BLOCK - 1

            ws.merge_cells(
                start_row=row, start_column=c1,
                end_row=row, end_column=c2,
            )

            for c in range(c1, c2 + 1):
                cell = ws.cell(row, c)
                if fill:
                    cell.fill = fill
                if border:
                    cell.border = border

            first = ws.cell(row, c1, value)
            if font:
                first.font = font
            first.alignment = align or center

            return c1, c2

        table_font = Font(name="Arial", size=11, color=DARK_BLUE)
        table_font_bold = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)
        left_center = Alignment(
            horizontal="left", vertical="center",
            indent=1, shrink_to_fit=True,
        )

        silver_fill = PatternFill("solid", fgColor="E7E6E6")

        results_title_row = ws.max_row + 3

        ws.merge_cells(
            start_row=results_title_row, start_column=1,
            end_row=results_title_row, end_column=BLOCK * 3,
        )
        draw_simple_header(
            ws, results_title_row, 1, "ИТОГОВЫЕ РЕЗУЛЬТАТЫ",
            title_fill, WHITE, size=12,
        )
        for c in range(1, BLOCK * 3 + 1):
            ws.cell(results_title_row, c).fill = title_fill
            ws.cell(results_title_row, c).border = cell_border
        ws.row_dimensions[results_title_row].height = 28

        header_row = results_title_row + 1
        header_font = Font(name="Arial", size=10, bold=True, color=WHITE)

        for block, text in enumerate(("МЕСТО", "ФИО", "КЛУБ")):
            merged_cell(
                header_row, block, text,
                fill=header_fill, font=header_font, border=cell_border,
            )
        ws.row_dimensions[header_row].height = 24

        result_rows = [(1, champion_id, gold_fill), (2, runner_up_id, silver_fill)]

        if bronze_shown:
            result_rows.append((3, bronze_winner_id, bronze_fill))
            result_rows.append((4, bronze_loser_id, athlete_fill))

        for offset, (place, athlete_id, fill) in enumerate(result_rows, start=1):
            row = header_row + offset
            name, club = get_athlete_data(athlete_id)

            merged_cell(
                row, 0, place, fill=fill,
                font=table_font_bold, border=cell_border,
            )
            merged_cell(
                row, 1, name, fill=fill,
                font=table_font_bold if name else table_font,
                align=left_center, border=cell_border,
            )
            merged_cell(
                row, 2, club, fill=fill,
                font=table_font, align=left_center, border=cell_border,
            )
            ws.row_dimensions[row].height = 24

        # =================================================
        # ПОДПИСИ
        # =================================================

        sign_line = Side(style="thin", color=DARK_BLUE)
        caption_font = Font(name="Arial", size=8, color=GRAY_TEXT)
        sign_font = Font(name="Arial", size=11, bold=True, color=DARK_BLUE)

        sign_row = header_row + len(result_rows) + 3

        for title in ("Главный судья", "Главный секретарь"):
            ws.row_dimensions[sign_row].height = 30
            ws.row_dimensions[sign_row + 1].height = 14

            merged_cell(
                sign_row, 0, title, font=sign_font,
                align=Alignment(
                    horizontal="left", vertical="bottom", indent=1,
                ),
            )

            for block, caption in ((1, "подпись"), (2, "ФИО")):
                c1, c2 = merged_cell(
                    sign_row, block,
                    border=Border(bottom=sign_line),
                )
                merged_cell(
                    sign_row + 1, block, caption, font=caption_font,
                )

            sign_row += 3

        # =================================================
        # ПЕЧАТЬ И ОТОБРАЖЕНИЕ
        # =================================================

        ws.freeze_panes = "A4"
        ws.print_title_rows = "1:3"

        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.fitToWidth = 1
        # Небольшие сетки целиком на одном листе (вместе с подписями),
        # большие разбиваются по высоте на несколько страниц.
        ws.page_setup.fitToHeight = 1 if ws.max_row <= 80 else 0

        ws.page_margins.left = 0.25
        ws.page_margins.right = 0.25
        ws.page_margins.top = 0.5
        ws.page_margins.bottom = 0.5

        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)

    # =====================================================
    # ЕСЛИ СЕТОК НЕТ
    # =====================================================

    if not wb.sheetnames:
        ws = wb.create_sheet("Сетки")
        ws.sheet_view.showGridLines = False
        ws["A1"] = "Нет сформированных сеток"
        ws["A1"].font = Font(name="Arial", size=14, bold=True)

    # =====================================================
    # СОХРАНЕНИЕ
    # =====================================================

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="kumite_draw.xlsx"'
        },
    )