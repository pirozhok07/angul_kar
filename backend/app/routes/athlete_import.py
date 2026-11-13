from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
import unicodedata

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from app.tournament_database import get_tournament_db
from app.tournament_models import Athlete, Club, Coach


router = APIRouter(
    prefix="/api/tournaments/{tournament_id}/athletes/import",
    tags=["Athlete Import"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024

HEADERS = [
    "ФИО",
    "Дата рождения",
    "Пол",
    "Стилевая квалификация",
    "Спортивная квалификация",
    "Клуб",
    "Тренер",
    "Вес",
]

ALIASES = {
    "ФИО": ("full_name",),
    "Дата рождения": ("birth_date",),
    "Пол": ("gender", "sex"),
    "Стилевая квалификация": ("rank_kyu",),
    "Спортивная квалификация": ("rank_sport",),
    "Клуб": ("club_id",),
    "Тренер": ("coach_id",),
    "Вес": ("weight",),
}


def get_columns():
    return {column.key for column in inspect(Athlete).columns}


def normalize_header(value):
    return str(value or "").strip().lower()


def normalize_gender(value):
    value = normalize_header(value)

    aliases = {
        "м": "male",
        "муж": "male",
        "мужской": "male",
        "male": "male",
        "m": "male",
        "ж": "female",
        "жен": "female",
        "женский": "female",
        "female": "female",
        "f": "female",
    }

    return aliases.get(value)


def parse_birth_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        value = value.strip()

        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass

    raise ValueError("Некорректная дата рождения")


def normalize_name(value):
    value = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()

def get_or_create_club(db: Session, club_name: str):
    club_name = normalize_header(club_name)

    if not club_name: 
        return None
    
    db_club = (
        db.query(Club)
        .filter(func.lower(Club.name) == club_name.lower())
        .first()
    )

    if db_club:
        return db_club
    
    new_club = Club(name=club_name)
    db.add(new_club)
    db.flush()

    return new_club

def get_or_create_coach(
    db: Session, 
    full_name: str,
    club_id: int
):
    name = full_name.split()
    first_name = normalize_name(name[1]) if  len(name) > 1 else ""
    second_name = normalize_name(name[2]) if  len(name) > 2 else ""
    last_name = normalize_name(name[0]) if  len(name) > 0 else ""

    if not first_name and not last_name: 
        raise ValueError(
            "Обязательно укажите ФИО тренера"
        )
    
    db_coach = (
        db.query(Coach).filter(
            func.lower(Coach.first_name) == first_name.lower(),
            func.lower(Coach.second_name) == second_name.lower(),
            func.lower(Coach.last_name) == last_name.lower(),
            Coach.club_id == club_id
        )
        .first()
    )

    if db_coach:
        return db_coach
    
    new_coach = Coach(
        first_name=first_name,
        second_name=second_name,
        last_name=last_name,
        club_id=club_id,
    )
    db.add(new_coach)
    db.flush()

    return new_coach

def resolve_name_fields(full_name):
    parts = full_name.split()

    if len(parts) < 2:
        raise ValueError("Укажите минимум фамилию и имя")

    if len(parts) == 2:
        parts.append("")

    return {
        "last_name": parts[0],
        "first_name": parts[1],
        "second_name": " ".join(parts[2:]),
    }


def map_row(db: Session, row, columns):
    data = {}
    errors = []

    raw_name = normalize_name(row.get("ФИО"))

    if not raw_name:
        errors.append("Не указано ФИО")
    else:
        if "full_name" in columns:
            data["full_name"] = raw_name
        elif "name" in columns:
            data["name"] = raw_name
        elif {"last_name", "first_name"}.issubset(columns):
            try:
                name_fields = resolve_name_fields(raw_name)
                data.update({
                    key: value
                    for key, value in name_fields.items()
                    if key in columns
                })
            except ValueError as exc:
                errors.append(str(exc))
        else:
            errors.append(
                "В модели Athlete нет поддерживаемых полей ФИО"
            )

    birth_field = next(
        (name for name in ALIASES["Дата рождения"] if name in columns),
        None,
    )

    if not birth_field:
        errors.append(
            "В модели Athlete отсутствует поле даты рождения"
        )
    else:
        try:
            data[birth_field] = parse_birth_date(
                row.get("Дата рождения")
            )
        except ValueError as exc:
            errors.append(str(exc))

    gender_field = next(
        (name for name in ALIASES["Пол"] if name in columns),
        None,
    )

    if not gender_field:
        errors.append("В модели Athlete отсутствует поле пола")
    else:
        gender = normalize_gender(row.get("Пол"))
        if not gender:
            errors.append("Пол должен быть male или female")
        else:
            data[gender_field] = gender

    club_field = next(
        (name for name in ALIASES["Клуб"] if name in columns),
        None,
    )

    if not club_field:
        errors.append("В модели Athlete отсутствует поле клуба")
    else:
        club = get_or_create_club(db, row.get("Клуб"))
        data[club_field] = club.id
        
    coach_field = next(
        (name for name in ALIASES["Тренер"] if name in columns),
        None,
    )

    if not coach_field:
        errors.append("В модели Athlete отсутствует поле клуба")
    else:
        coach = get_or_create_coach(db, row.get("Тренер"), club.id)
        data[coach_field] = coach.id

    optional_fields = {
        "Стилевая квалификация": "rank_kyu",
        "Спортивная квалификация": "rank_sport",
        "Клуб": "club",
        "Тренер": "coach",
    }

    for header, field in optional_fields.items():
        if field in columns:
            value = row.get(header)
            data[field] = str(value).strip() if value is not None else None

    if "weight" in columns:
        value = row.get("Вес")

        if value not in (None, ""):
            try:
                weight = Decimal(str(value).replace(",", "."))
                if weight <= 0 or weight > 300:
                    raise ValueError()
                data["weight"] = weight
            except (InvalidOperation, ValueError):
                errors.append("Вес должен быть числом от 0 до 300 кг")
        else:
            data["weight"] = None

    return data, errors


def read_excel(content):
    try:
        workbook = load_workbook(
            BytesIO(content),
            read_only=True,
            data_only=True,
        )
    except Exception:
        raise HTTPException(400, "Не удалось прочитать Excel-файл")

    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)

    header_row = next(rows, None)

    if not header_row:
        raise HTTPException(400, "Excel-файл пуст")

    normalized_headers = [
        normalize_header(value) for value in header_row
    ]

    expected = {
        normalize_header(header): header for header in HEADERS
    }

    positions = {}

    for index, header in enumerate(normalized_headers):
        if header in expected:
            positions[expected[header]] = index

    missing = [
        header
        for header in HEADERS[:3]
        if header not in positions
    ]

    if missing:
        raise HTTPException(
            422,
            f"Не найдены обязательные столбцы: {', '.join(missing)}",
        )

    result = []

    for excel_row_number, values in enumerate(rows, start=2):
        if not any(value is not None for value in values):
            continue

        row = {
            header: (
                values[index]
                if index < len(values)
                else None
            )
            for header, index in positions.items()
        }

        result.append((excel_row_number, row))

    workbook.close()

    if not result:
        raise HTTPException(422, "В файле нет строк со спортсменами")

    return result


def duplicate_identity(data, columns):
    if "full_name" in columns:
        name = data.get("full_name")
    else:
        name = " ".join(
            str(data.get(field, "") or "")
            for field in ("last_name", "first_name", "middle_name")
        ).strip()

    birth = (
        data.get("birth_date")
    )

    gender = data.get("gender") or data.get("sex")

    return (
        normalize_name(name).casefold(),
        birth,
        gender,
    )


async def read_upload(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Поддерживаются только файлы .xlsx")

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Размер файла не должен превышать 10 МБ")

    return content


@router.get("/template")
def download_template():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Спортсмены"
    sheet.append(HEADERS)

    sheet.append([
        "Иванов Иван Иванович",
        date(2014, 5, 12),
        "male",
        "1 кю",
        "КМС",
        "Додзё",
        "Петров",
        42.5,
    ])

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:G2"

    for column, width in {
        "A": 30,
        "B": 18,
        "C": 15,
        "D": 12,
        "E": 12,
        "F": 22,
        "G": 22,
        "H": 15,
        "I": 12,
    }.items():
        sheet.column_dimensions[column].width = width

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="athletes_template.xlsx"'
        },
    )


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_tournament_db),
):
    content = await read_upload(file)
    excel_rows = read_excel(content)
    columns = get_columns()

    existing = db.query(Athlete).all()
    existing_keys = {
        duplicate_identity(
            {
                key: getattr(item, key)
                for key in columns
            },
            columns,
        )
        for item in existing
    }

    seen_in_file = set()
    result = []

    for row_number, row in excel_rows:
        data, errors = map_row(db, row, columns)

        if not errors:
            key = duplicate_identity(data, columns)

            if key in existing_keys:
                errors.append("Такой спортсмен уже есть в базе турнира")
            elif key in seen_in_file:
                errors.append("Повтор спортсмена внутри Excel-файла")
            else:
                seen_in_file.add(key)

        result.append({
            "row": row_number,
            "full_name": normalize_name(row.get("ФИО")),
            "data": {
                key: str(value) if isinstance(value, (date, Decimal))
                else value
                for key, value in data.items()
            },
            "errors": errors,
            "valid": not errors,
        })

    return {
        "total": len(result),
        "valid": sum(1 for item in result if item["valid"]),
        "invalid": sum(1 for item in result if not item["valid"]),
        "rows": result,
    }


@router.post("/confirm")
async def confirm_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_tournament_db),
):
    content = await read_upload(file)
    excel_rows = read_excel(content)
    columns = get_columns()
    existing = db.query(Athlete).all()
    existing_keys = {
        duplicate_identity(
            {key: getattr(item, key) for key in columns},
            columns,
        )
        for item in existing
    }

    seen = set()
    prepared = []
    errors = []

    for row_number, row in excel_rows:
        data, row_errors = map_row(db, row, columns)

        if not row_errors:
            key = duplicate_identity(data, columns)

            if key in existing_keys or key in seen:
                row_errors.append("Дубликат спортсмена")
            else:
                seen.add(key)

        if row_errors:
            errors.append({
                "row": row_number,
                "errors": row_errors,
            })
        else:
            prepared.append(data)

    if errors:
        raise HTTPException(
            422,
            detail={
                "message": "Импорт отменён: найдены ошибки или дубликаты",
                "rows": errors,
            },
        )

    try:
        for data in prepared:
            db.add(Athlete(**data, registration_status='pending'))

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Ошибка сохранения спортсменов: {e}")

    return {
        "imported": len(prepared),
        "message": "Импорт успешно завершён",
    }